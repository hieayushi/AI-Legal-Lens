import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    doc_type = Column(String, nullable=False, default="other")
    description = Column(Text, nullable=True)
    tags = Column(JSON, default=list)          # list[str]
    case_number = Column(String, nullable=True)
    file_path = Column(String, nullable=False)  # relative to STORAGE_PATH
    file_name = Column(String, nullable=False)
    file_size_bytes = Column(Integer, default=0)
    page_count = Column(Integer, default=0)
    is_scanned = Column(Boolean, default=False)
    processing_status = Column(String, default="pending")  # pending|processing|indexed|failed
    processing_error = Column(Text, nullable=True)
    toc = Column(JSON, default=list)           # list[{title, page, level}]
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    uploaded_by = Column(String, ForeignKey("users.id"), nullable=True)

    pages = relationship("DocumentPage", back_populates="document", cascade="all, delete-orphan")
    queries = relationship("QueryLog", back_populates="document", cascade="all, delete-orphan")


class DocumentPage(Base):
    __tablename__ = "document_pages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    page_number = Column(Integer, nullable=False)
    section_title = Column(String, nullable=True)
    section_level = Column(Integer, default=0)
    text_content = Column(Text, nullable=False, default="")
    char_count = Column(Integer, default=0)
    # BM25 index stored per doc; vector stored as JSON list of floats (small models)
    embedding = Column(JSON, nullable=True)    # list[float] | null
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="pages")
