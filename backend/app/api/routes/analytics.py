from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.security import get_current_user
from app.db.database import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])


class DayCount(BaseModel):
    date: str
    count: int


class TopDoc(BaseModel):
    document_id: str
    title: str
    query_count: int


class SummaryOut(BaseModel):
    total_documents: int
    total_queries: int
    avg_latency_ms: float
    retrieval_method_distribution: dict
    query_volume_by_day: List[DayCount]
    top_queried_documents: List[TopDoc]


@router.get("/summary", response_model=SummaryOut)
async def summary(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    since = datetime.utcnow() - timedelta(days=days)

    total_documents = await db.documents.count_documents({})
    
    logs = []
    async for q in db.query_logs.find({"created_at": {"$gte": since}}):
        logs.append(q)
        
    total_queries = len(logs)
    avg_latency = sum(q.get("latency_ms", 0) for q in logs) / max(total_queries, 1)

    method_dist = {}
    for q in logs:
        method = q.get("retrieval_method", "hierarchical")
        method_dist[method] = method_dist.get(method, 0) + 1

    day_counts = {}
    for q in logs:
        # q["created_at"] is datetime object
        dt = q.get("created_at")
        if isinstance(dt, datetime):
            day = dt.strftime("%Y-%m-%d")
            day_counts[day] = day_counts.get(day, 0) + 1

    query_volume = []
    for i in range(days):
        d = (datetime.utcnow() - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        query_volume.append(DayCount(date=d, count=day_counts.get(d, 0)))

    doc_counts = {}
    for q in logs:
        d_id = q.get("document_id")
        if d_id:
            doc_counts[d_id] = doc_counts.get(d_id, 0) + 1

    top_docs = []
    sorted_docs = sorted(doc_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    for doc_id, count in sorted_docs:
        doc = await db.documents.find_one({"_id": doc_id})
        if doc:
            top_docs.append(TopDoc(document_id=doc_id, title=doc["title"], query_count=count))

    return SummaryOut(
        total_documents=total_documents,
        total_queries=total_queries,
        avg_latency_ms=round(avg_latency, 1),
        retrieval_method_distribution=method_dist,
        query_volume_by_day=query_volume,
        top_queried_documents=top_docs,
    )


@router.get("/document/{doc_id}")
async def document_analytics(
    doc_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    doc = await db.documents.find_one({"_id": doc_id})
    if not doc:
        return {"error": "Document not found"}

    logs = []
    async for q in db.query_logs.find({"document_id": doc_id}):
        logs.append(q)

    total = len(logs)
    avg_lat = sum(q.get("latency_ms", 0) for q in logs) / max(total, 1)
    
    feedbacks = [q["feedback_score"] for q in logs if q.get("feedback_score")]
    avg_score = sum(feedbacks) / max(len(feedbacks), 1) if feedbacks else 0.0

    return {
        "document_id": doc_id,
        "title": doc["title"],
        "total_queries": total,
        "avg_latency_ms": round(avg_lat, 1),
        "avg_feedback_score": round(avg_score, 2),
        "page_count": doc.get("page_count", 0),
        "processing_status": doc.get("processing_status"),
    }
