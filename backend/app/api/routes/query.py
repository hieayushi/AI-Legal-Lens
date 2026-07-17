import time
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings
from app.core.security import get_current_user
from app.db.database import get_db
from app.services.retrieval.retriever import retrieve
from app.services.llm.generator import generate_answer

router = APIRouter(prefix="/query", tags=["query"])


class AskRequest(BaseModel):
    query: str
    document_ids: List[str] = []
    retrieval_method: str = "hierarchical"
    top_k: int = 5


class CitationOut(BaseModel):
    document_id: str
    document_title: str
    section_title: Optional[str] = None
    page_number: int
    evidence_text: str
    confidence_score: float
    retrieval_rank: int


class QueryResultOut(BaseModel):
    query_id: str
    answer: str
    citations: List[CitationOut]
    retrieval_method: str
    model_used: str
    latency_ms: int
    warning: Optional[str] = None


class QueryHistoryItem(BaseModel):
    id: str
    query_text: str
    retrieval_method: str
    latency_ms: int
    citation_count: int
    created_at: str


@router.post("/ask", response_model=QueryResultOut)
async def ask(
    req: AskRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    top_k = min(req.top_k, settings.MAX_TOP_K)
    method = req.retrieval_method if req.retrieval_method in ("bm25", "hybrid", "hierarchical") else "hierarchical"

    t0 = time.time()
    citations = await retrieve(db, req.query, req.document_ids, method, top_k)
    llm_result = generate_answer(req.query, citations)

    total_ms = int((time.time() - t0) * 1000)
    latency_ms = llm_result.get("latency_ms") or total_ms

    query_id = str(uuid.uuid4())
    primary_doc_id = citations[0]["document_id"] if citations else None

    query_log = {
        "_id": query_id,
        "query_text": req.query,
        "retrieval_method": method,
        "top_k": top_k,
        "answer": llm_result["answer"],
        "citations": citations,
        "model_used": llm_result["model_used"],
        "latency_ms": latency_ms,
        "citation_count": len(citations),
        "warning": llm_result.get("warning"),
        "document_ids": req.document_ids,
        "user_id": current_user["id"],
        "document_id": primary_doc_id,
        "created_at": datetime.utcnow(),
    }

    await db.query_logs.insert_one(query_log)

    return QueryResultOut(
        query_id=query_id,
        answer=llm_result["answer"],
        citations=[CitationOut(**c) for c in citations],
        retrieval_method=method,
        model_used=llm_result["model_used"],
        latency_ms=latency_ms,
        warning=llm_result.get("warning"),
    )


@router.get("/history", response_model=List[QueryHistoryItem])
async def history(
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    query_filter = {"user_id": current_user["id"]}
    logs = []
    async for q in db.query_logs.find(query_filter).sort("created_at", -1).limit(limit):
        logs.append(QueryHistoryItem(
            id=q["_id"],
            query_text=q["query_text"],
            retrieval_method=q["retrieval_method"],
            latency_ms=q["latency_ms"],
            citation_count=q["citation_count"],
            created_at=q["created_at"].isoformat() if isinstance(q["created_at"], datetime) else str(q["created_at"]),
        ))
    return logs


@router.get("/{query_id}", response_model=QueryResultOut)
async def get_query(
    query_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    log = await db.query_logs.find_one({"_id": query_id, "user_id": current_user["id"]})
    if not log:
        raise HTTPException(status_code=404, detail="Query not found")
    return QueryResultOut(
        query_id=log["_id"],
        answer=log.get("answer", ""),
        citations=[CitationOut(**c) for c in log.get("citations", [])],
        retrieval_method=log["retrieval_method"],
        model_used=log.get("model_used", ""),
        latency_ms=log.get("latency_ms", 0),
        warning=log.get("warning"),
    )


@router.post("/{query_id}/feedback")
async def feedback(
    query_id: str,
    score: int = Query(..., ge=1, le=5),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    log = await db.query_logs.find_one({"_id": query_id, "user_id": current_user["id"]})
    if not log:
        raise HTTPException(status_code=404, detail="Query not found")
    await db.query_logs.update_one({"_id": query_id}, {"$set": {"feedback_score": score}})
    return {"status": "ok"}


@router.post("/summarize/{doc_id}", response_model=QueryResultOut)
async def summarize(
    doc_id: str,
    summary_type: str = Query(default="full"),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    doc = await db.documents.find_one({"_id": doc_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.get("processing_status") != "indexed":
        raise HTTPException(status_code=400, detail="Document is not indexed yet")

    query_map = {
        "full": "Provide a comprehensive summary of this legal document, including key arguments, decisions, and outcomes.",
        "brief": "Provide a brief 3-5 sentence summary of this legal document.",
        "key_points": "List the key points, legal principles, and holdings of this document.",
    }
    query = query_map.get(summary_type, query_map["full"])

    citations = await retrieve(db, query, [doc_id], "hierarchical", 8)
    llm_result = generate_answer(query, citations)

    query_id = str(uuid.uuid4())
    query_log = {
        "_id": query_id,
        "query_text": query,
        "retrieval_method": "hierarchical",
        "top_k": 8,
        "answer": llm_result["answer"],
        "citations": citations,
        "model_used": llm_result["model_used"],
        "latency_ms": llm_result.get("latency_ms", 0),
        "citation_count": len(citations),
        "document_ids": [doc_id],
        "user_id": current_user["id"],
        "document_id": doc_id,
        "created_at": datetime.utcnow(),
    }

    await db.query_logs.insert_one(query_log)

    return QueryResultOut(
        query_id=query_id,
        answer=llm_result["answer"],
        citations=[CitationOut(**c) for c in citations],
        retrieval_method="hierarchical",
        model_used=llm_result["model_used"],
        latency_ms=llm_result.get("latency_ms", 0),
    )


@router.post("/compare", response_model=QueryResultOut)
async def compare(
    document_ids: List[str],
    query: str = Query(default="Compare the key differences and similarities between these documents."),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if len(document_ids) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 document IDs to compare")

    citations = await retrieve(db, query, document_ids, "hierarchical", 10)
    llm_result = generate_answer(query, citations)

    query_id = str(uuid.uuid4())
    query_log = {
        "_id": query_id,
        "query_text": query,
        "retrieval_method": "hierarchical",
        "top_k": 10,
        "answer": llm_result["answer"],
        "citations": citations,
        "model_used": llm_result["model_used"],
        "latency_ms": llm_result.get("latency_ms", 0),
        "citation_count": len(citations),
        "document_ids": document_ids,
        "user_id": current_user["id"],
        "created_at": datetime.utcnow(),
    }

    await db.query_logs.insert_one(query_log)

    return QueryResultOut(
        query_id=query_id,
        answer=llm_result["answer"],
        citations=[CitationOut(**c) for c in citations],
        retrieval_method="hierarchical",
        model_used=llm_result["model_used"],
        latency_ms=llm_result.get("latency_ms", 0),
    )
