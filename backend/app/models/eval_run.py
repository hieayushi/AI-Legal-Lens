import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Text
from app.db.database import Base


class EvalRun(Base):
    __tablename__ = "eval_runs"

    run_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    retrieval_method = Column(String, nullable=False)
    dataset_path = Column(String, nullable=True)
    status = Column(String, default="running")  # running|completed|failed
    total_questions = Column(Integer, default=0)

    # Aggregate metrics
    avg_precision = Column(Float, default=0.0)
    avg_recall = Column(Float, default=0.0)
    avg_f1 = Column(Float, default=0.0)
    avg_citation_accuracy = Column(Float, default=0.0)
    avg_latency_ms = Column(Float, default=0.0)
    hallucination_rate = Column(Float, default=0.0)

    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
