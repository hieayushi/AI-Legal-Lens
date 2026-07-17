"""
MongoDB Document Indexer Service using Azure OpenAI Embeddings.
Stores document metadata, sections, page index structures, parent relationships,
and builds local BM25 index references + Azure vector embeddings.
"""
import logging
import uuid
from datetime import datetime
from pymongo import UpdateOne
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.database import Database
from openai import AzureOpenAI

from app.core.config import settings
from app.services.indexing.pdf_extractor import extract_document

logger = logging.getLogger(__name__)

# Global BM25 storage references
_bm25_store: dict = {}

try:
    from rank_bm25 import BM25Okapi
    HAS_BM25 = True
except ImportError:
    HAS_BM25 = False


def _get_azure_client() -> AzureOpenAI:
    return AzureOpenAI(
        api_key=settings.AZURE_OPENAI_API_KEY,
        api_version=settings.AZURE_OPENAI_API_VERSION,
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
    )


def _compute_azure_embedding(client: AzureOpenAI, text: str) -> list:
    """Compute vector embeddings using Azure OpenAI deployment model."""
    if not settings.AZURE_OPENAI_API_KEY:
        return []
    try:
        response = client.embeddings.create(
            input=[text],
            model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Azure OpenAI Embedding generation failed: {e}")
        return []


async def index_document(db: AsyncIOMotorDatabase, doc_id: str, file_path: str, filename: str, doc_type: str, title: str = "", description: str = "", tags: list = [], user_id: str = None) -> dict:
    """
    Primary processing pipeline:
      - Reads PDF text & TOC hierarchy via PyMuPDF (fitz)
      - Creates hierarchical relationships (Document -> Sections -> Pages)
      - Persists metadata to MongoDB Atlas collections
      - Computes vector embeddings using Azure OpenAI
      - Generates/caches BM25 scores
    """
    # 1. Update status to processing
    await db.documents.update_one(
        {"_id": doc_id},
        {"$set": {"processing_status": "processing", "updated_at": datetime.utcnow()}}
    )

    try:
        # 2. Extract layout, text, and headings hierarchy
        result = extract_document(file_path)
        page_count = result["page_count"]
        is_scanned = result["is_scanned"]
        toc = result["toc"]
        detected_title = title if title else result["detected_title"]

        # 3. Create Hierarchical Page / Sections Structures
        pages_to_insert = []
        sections_to_insert = []
        toc_tree = []

        # Parse TOC tree nodes
        for idx, item in enumerate(toc):
            sec_id = str(uuid.uuid4())
            sections_to_insert.append({
                "_id": sec_id,
                "document_id": doc_id,
                "title": item["title"],
                "page_number": item["page"],
                "level": item["level"],
                "created_at": datetime.utcnow()
            })
            toc_tree.append({
                "section_id": sec_id,
                "title": item["title"],
                "page": item["page"],
                "level": item["level"]
            })

        # Insert sections
        if sections_to_insert:
            await db.sections.insert_many(sections_to_insert)

        # Initialize Azure Client
        azure_client = _get_azure_client()

        # 4. Generate page records + Azure vector embeddings
        for p in result["pages"]:
            page_text = p["text"]
            embedding = None
            if page_text.strip():
                # Compute embedding via Azure OpenAI
                embedding = _compute_azure_embedding(azure_client, page_text[:8000])

            pages_to_insert.append({
                "_id": str(uuid.uuid4()),
                "document_id": doc_id,
                "page_number": p["page_number"],
                "section_title": p.get("section_title"),
                "section_level": p.get("section_level", 0),
                "text_content": page_text,
                "char_count": len(page_text),
                "embedding": embedding,
                "created_at": datetime.utcnow()
            })

        # Remove previous pages if exist and insert new pages
        await db.pages.delete_many({"document_id": doc_id})
        if pages_to_insert:
            await db.pages.insert_many(pages_to_insert)

        # 5. Populate and update the main document structure
        doc_update = {
            "title": detected_title,
            "doc_type": doc_type,
            "description": description,
            "tags": tags,
            "page_count": page_count,
            "is_scanned": is_scanned,
            "processing_status": "indexed",
            "toc": toc_tree,
            "updated_at": datetime.utcnow()
        }
        await db.documents.update_one({"_id": doc_id}, {"$set": doc_update})

        # 6. Build in-memory BM25 index reference
        build_bm25_index_sync(db.delegate, doc_id)
        
        logger.info(f"Successfully indexed document {doc_id} with {page_count} pages.")
        return doc_update

    except Exception as e:
        logger.error(f"Indexing pipeline failed for document {doc_id}: {e}", exc_info=True)
        await db.documents.update_one(
            {"_id": doc_id},
            {"$set": {
                "processing_status": "failed",
                "processing_error": str(e),
                "updated_at": datetime.utcnow()
            }}
        )
        raise e


def build_bm25_index_sync(sync_db: Database, doc_id: str):
    """
    Build BM25 index synchronously using pymongo sync database client
    """
    if not HAS_BM25:
        return
    pages = list(
        sync_db.pages.find({"document_id": doc_id}).sort("page_number", 1)
    )
    tokenized_corpus = [p.get("text_content", "").lower().split() for p in pages]
    if any(tokenized_corpus):
        _bm25_store[doc_id] = BM25Okapi(tokenized_corpus)


def get_bm25(doc_id: str):
    return _bm25_store.get(doc_id)


def warm_up_bm25_indexes(sync_db: Database):
    """
    Warm-up and rebuild BM25 indexes for all completed docs in MongoDB.
    """
    docs = list(sync_db.documents.find({"processing_status": "indexed"}))
    for d in docs:
        build_bm25_index_sync(sync_db, d["_id"])
    logger.info(f"BM25 Warm-up: rebuilt {len(docs)} document index references.")
