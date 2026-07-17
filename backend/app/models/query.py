import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base


class QueryLog(Base):
    __tablename__ = "query_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    query_text = Column(Text, nullable=False)
    retrieval_method = Column(String, nullable=False, default="hierarchical")
    top_k = Column(Integer, default=5)
    answer = Column(Text, nullable=True)
    citations = Column(JSON, default=list)     # list[CitationDict]
    model_used = Column(String, nullable=True)
    latency_ms = Column(Integer, default=0)
    citation_count = Column(Integer, default=0)
    feedback_score = Column(Integer, nullable=True)  # 1-5 stars
    warning = Column(Text, nullable=True)
    document_ids = Column(JSON, default=list)  # list of doc IDs scoped to
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)

    # Optional soft-link to a single "primary" document (for per-doc analytics)
    document_id = Column(String, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    document = relationship("Document", back_populates="queries")
