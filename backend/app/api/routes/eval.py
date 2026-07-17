import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings
from app.core.security import get_current_user
from app.db.database import get_db

router = APIRouter(prefix="/eval", tags=["evaluation"])

DATASETS_DIR = Path("../evaluation/datasets")


class RunRequest(BaseModel):
    retrieval_method: str = "hierarchical"
    dataset_path: Optional[str] = None


class EvalRunOut(BaseModel):
    run_id: str
    retrieval_method: str
    status: str
    total_questions: int
    avg_precision: float
    avg_recall: float
    avg_f1: float
    avg_citation_accuracy: float
    avg_latency_ms: float
    hallucination_rate: float
    created_at: str
    completed_at: Optional[str] = None


def _map_run(run: dict) -> EvalRunOut:
    return EvalRunOut(
        run_id=run["_id"],
        retrieval_method=run["retrieval_method"],
        status=run["status"],
        total_questions=run.get("total_questions", 0),
        avg_precision=run.get("avg_precision", 0.0),
        avg_recall=run.get("avg_recall", 0.0),
        avg_f1=run.get("avg_f1", 0.0),
        avg_citation_accuracy=run.get("avg_citation_accuracy", 0.0),
        avg_latency_ms=run.get("avg_latency_ms", 0.0),
        hallucination_rate=run.get("hallucination_rate", 0.0),
        created_at=run["created_at"].isoformat() if isinstance(run["created_at"], datetime) else str(run["created_at"]),
        completed_at=run["completed_at"].isoformat() if run.get("completed_at") else None,
    )


@router.post("/run", response_model=EvalRunOut, status_code=202)
async def start_run(
    req: RunRequest,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if req.retrieval_method not in ("bm25", "hybrid", "hierarchical"):
        raise HTTPException(status_code=400, detail="Invalid retrieval method")

    run_id = str(uuid.uuid4())
    run_doc = {
        "_id": run_id,
        "retrieval_method": req.retrieval_method,
        "dataset_path": req.dataset_path,
        "status": "running",
        "total_questions": 0,
        "avg_precision": 0.0,
        "avg_recall": 0.0,
        "avg_f1": 0.0,
        "avg_citation_accuracy": 0.0,
        "avg_latency_ms": 0.0,
        "hallucination_rate": 0.0,
        "created_at": datetime.utcnow(),
    }
    await db.eval_runs.insert_one(run_doc)

    background_tasks.add_task(_run_evaluation_bg, run_id, req.retrieval_method, req.dataset_path)

    return _map_run(run_doc)


async def _run_evaluation_bg(run_id: str, method: str, dataset_path: Optional[str]):
    from app.db.database import async_client
    from app.services.retrieval.retriever import retrieve
    
    db = async_client[settings.DATABASE_NAME]
    try:
        run = await db.eval_runs.find_one({"_id": run_id})
        if not run:
            return

        questions = _load_dataset(dataset_path)
        if not questions:
            # Fallback to generating test questions dynamically from database docs
            questions = await _synthetic_questions(db)

        if not questions:
            await db.eval_runs.update_one(
                {"_id": run_id},
                {"$set": {
                    "status": "failed",
                    "error_message": "No test datasets found or indexed documents available.",
                    "completed_at": datetime.utcnow()
                }}
            )
            return

        precisions, recalls, f1s, citation_accs, latencies = [], [], [], [], []
        hallucinated_count = 0

        for q in questions:
            t0 = time.time()
            try:
                doc_ids = [q["document_id"]] if q.get("document_id") else []
                citations = await retrieve(db, q["question"], doc_ids, method, 5)
                lat = int((time.time() - t0) * 1000)
                latencies.append(lat)

                retrieved_pages = {c["page_number"] for c in citations}
                expected_pages = set(q.get("expected_pages", []))

                if expected_pages:
                    tp = len(retrieved_pages & expected_pages)
                    prec = tp / max(len(retrieved_pages), 1)
                    rec = tp / max(len(expected_pages), 1)
                    f1 = 2 * prec * rec / max(prec + rec, 1e-9)
                    ca = 1.0 if tp > 0 else 0.0
                else:
                    prec = rec = f1 = ca = 1.0

                precisions.append(prec)
                recalls.append(rec)
                f1s.append(f1)
                citation_accs.append(ca)

                if not citations:
                    hallucinated_count += 1
            except Exception:
                precisions.append(0)
                recalls.append(0)
                f1s.append(0)
                citation_accs.append(0)
                latencies.append(0)

        n = max(len(questions), 1)
        await db.eval_runs.update_one(
            {"_id": run_id},
            {"$set": {
                "total_questions": n,
                "avg_precision": sum(precisions) / n,
                "avg_recall": sum(recalls) / n,
                "avg_f1": sum(f1s) / n,
                "avg_citation_accuracy": sum(citation_accs) / n,
                "avg_latency_ms": sum(latencies) / n,
                "hallucination_rate": hallucinated_count / n,
                "status": "completed",
                "completed_at": datetime.utcnow()
            }}
        )
    except Exception as e:
        await db.eval_runs.update_one(
            {"_id": run_id},
            {"$set": {
                "status": "failed",
                "error_message": str(e),
                "completed_at": datetime.utcnow()
            }}
        )


def _load_dataset(dataset_path: Optional[str]) -> List[dict]:
    if not dataset_path:
        path = DATASETS_DIR / "default.jsonl"
    else:
        path = Path(dataset_path)
    if not path.exists():
        return []
    questions = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    questions.append(json.loads(line))
                except Exception:
                    pass
    return questions


async def _synthetic_questions(db: AsyncIOMotorDatabase) -> List[dict]:
    questions = []
    async for doc in db.documents.find({"processing_status": "indexed"}).limit(3):
        questions.append({
            "question": f"What is the core decision in {doc['title']}?",
            "document_id": doc["_id"],
            "expected_pages": [1],
        })
    return questions


@router.get("/runs", response_model=List[EvalRunOut])
async def list_runs(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    runs = []
    async for r in db.eval_runs.find().sort("created_at", -1):
        runs.append(_map_run(r))
    return runs


@router.get("/runs/{run_id}", response_model=EvalRunOut)
async def get_run(
    run_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    run = await db.eval_runs.find_one({"_id": run_id})
    if not run:
        raise HTTPException(status_code=404, detail="Eval run not found")
    return _map_run(run)


@router.get("/compare")
async def compare_runs(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    methods = ["hierarchical", "bm25", "hybrid"]
    result = {}
    for method in methods:
        run = await db.eval_runs.find_one(
            {"retrieval_method": method, "status": "completed"},
            sort=[("created_at", -1)]
        )
        if run:
            result[method] = {
                "avg_precision": run.get("avg_precision", 0.0),
                "avg_recall": run.get("avg_recall", 0.0),
                "avg_f1": run.get("avg_f1", 0.0),
                "avg_citation_accuracy": run.get("avg_citation_accuracy", 0.0),
                "avg_latency_ms": run.get("avg_latency_ms", 0.0),
                "hallucination_rate": run.get("hallucination_rate", 0.0),
                "total_questions": run.get("total_questions", 0),
            }
    return result
