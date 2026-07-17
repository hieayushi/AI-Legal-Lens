import logging
import os
import uuid
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings
from app.core.security import get_current_user
from app.db.database import get_db
from app.services.indexing.indexer import index_document

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_FILE_SIZE = 50 * 1024 * 1024


class DocumentOut(BaseModel):
    id: str
    title: str
    doc_type: str
    description: Optional[str] = None
    tags: List[str] = []
    case_number: Optional[str] = None
    file_name: str
    file_size_bytes: int
    page_count: int
    is_scanned: bool
    processing_status: str
    processing_error: Optional[str] = None
    toc: List[dict] = []
    created_at: str


class PageOut(BaseModel):
    id: str
    page_number: int
    section_title: Optional[str] = None
    section_level: int = 0
    text_content: str
    char_count: int


def _map_doc(doc: dict) -> DocumentOut:
    return DocumentOut(
        id=doc["_id"],
        title=doc["title"],
        doc_type=doc["doc_type"],
        description=doc.get("description"),
        tags=doc.get("tags", []),
        case_number=doc.get("case_number"),
        file_name=doc["file_name"],
        file_size_bytes=doc["file_size_bytes"],
        page_count=doc.get("page_count", 0),
        is_scanned=doc.get("is_scanned", False),
        processing_status=doc["processing_status"],
        processing_error=doc.get("processing_error"),
        toc=doc.get("toc", []),
        created_at=doc["created_at"].isoformat() if isinstance(doc["created_at"], datetime) else str(doc["created_at"]),
    )


@router.post("/upload", response_model=DocumentOut, status_code=201)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    doc_type: str = Form("other"),
    title: str = Form(""),
    description: str = Form(""),
    tags: str = Form(""),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds 50 MB limit")

    doc_id = str(uuid.uuid4())
    storage_dir = Path(settings.STORAGE_PATH)
    storage_dir.mkdir(parents=True, exist_ok=True)
    file_path = storage_dir / f"{doc_id}.pdf"
    file_path.write_bytes(content)

    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    doc_title = title.strip() if title.strip() else file.filename

    doc_doc = {
        "_id": doc_id,
        "title": doc_title,
        "doc_type": doc_type,
        "description": description.strip() or None,
        "tags": tag_list,
        "case_number": None,
        "file_path": str(file_path),
        "file_name": file.filename,
        "file_size_bytes": len(content),
        "page_count": 0,
        "is_scanned": False,
        "processing_status": "pending",
        "toc": [],
        "created_at": datetime.utcnow(),
        "uploaded_by": current_user["id"],
    }

    await db.documents.insert_one(doc_doc)

    background_tasks.add_task(_index_document_bg, doc_id, str(file_path), file.filename, doc_type, doc_title, description, tag_list, current_user["id"])

    return _map_doc(doc_doc)


async def _index_document_bg(doc_id: str, file_path: str, filename: str, doc_type: str, title: str, description: str, tags: list, user_id: str):
    from app.db.database import async_client
    db = async_client[settings.DATABASE_NAME]
    try:
        await index_document(db, doc_id, file_path, filename, doc_type, title, description, tags, user_id)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Background indexing failed for {doc_id}: {e}")


@router.get("/", response_model=List[DocumentOut])
async def list_documents(
    doc_type: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    query_filter = {}
    if doc_type:
        query_filter["doc_type"] = doc_type
    
    docs = []
    async for doc in db.documents.find(query_filter).sort("created_at", -1):
        docs.append(_map_doc(doc))
    return docs


@router.get("/{doc_id}", response_model=DocumentOut)
async def get_document(
    doc_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    doc = await db.documents.find_one({"_id": doc_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return _map_doc(doc)


@router.delete("/{doc_id}", status_code=204)
async def delete_document(
    doc_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    doc = await db.documents.find_one({"_id": doc_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        if os.path.exists(doc["file_path"]):
            os.remove(doc["file_path"])
    except Exception:
        pass

    await db.documents.delete_one({"_id": doc_id})
    await db.pages.delete_many({"document_id": doc_id})
    await db.sections.delete_many({"document_id": doc_id})


@router.get("/{doc_id}/toc")
async def get_toc(
    doc_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    doc = await db.documents.find_one({"_id": doc_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc.get("toc", [])


@router.get("/{doc_id}/pages", response_model=List[PageOut])
async def get_pages(
    doc_id: str,
    page_number: Optional[int] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    query_filter = {"document_id": doc_id}
    if page_number is not None:
        query_filter["page_number"] = page_number
    
    pages = []
    async for p in db.pages.find(query_filter).sort("page_number", 1):
        pages.append(PageOut(
            id=p["_id"],
            page_number=p["page_number"],
            section_title=p.get("section_title"),
            section_level=p.get("section_level", 0),
            text_content=p["text_content"],
            char_count=p["char_count"]
        ))
    return pages


@router.get("/{doc_id}/file")
async def serve_pdf(
    doc_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    doc = await db.documents.find_one({"_id": doc_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not os.path.exists(doc["file_path"]):
        raise HTTPException(status_code=404, detail="File not found on disk")
    return FileResponse(
        doc["file_path"],
        media_type="application/pdf",
        filename=doc["file_name"],
    )
