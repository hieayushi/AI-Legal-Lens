"""
Seed script: creates an admin user in MongoDB and optionally indexes a PDF.
Usage:
  python seed.py --email admin@legallens.ai --password admin123
  python seed.py --email admin@legallens.ai --password admin123 --pdf path/to/file.pdf
"""
import argparse
import sys
import os
import uuid
import asyncio
from datetime import datetime
from pathlib import Path

# Add backend root to path
sys.path.insert(0, os.path.dirname(__file__))

from app.db.database import get_sync_db, init_db, async_client
from app.core.security import hash_password
from app.services.indexing.indexer import index_document
from app.core.config import settings


async def run_async_indexing(doc_id: str, file_path: str, filename: str, doc_type: str, title: str):
    db = async_client[settings.DATABASE_NAME]
    await index_document(
        db=db,
        doc_id=doc_id,
        file_path=file_path,
        filename=filename,
        doc_type=doc_type,
        title=title
    )


def main():
    parser = argparse.ArgumentParser(description="LegalLens AI MongoDB seed script")
    parser.add_argument("--email", default="admin@legallens.ai")
    parser.add_argument("--password", default="admin123")
    parser.add_argument("--name", default="Admin User")
    parser.add_argument("--pdf", default=None, help="Optional: path to a PDF to index")
    args = parser.parse_args()

    init_db()
    db = get_sync_db()

    existing = db.users.find_one({"email": args.email})
    if existing:
        print(f"User {args.email} already exists (role={existing.get('role')})")
        user_id = existing["_id"]
    else:
        user_id = str(uuid.uuid4())
        user_doc = {
            "_id": user_id,
            "email": args.email,
            "hashed_password": hash_password(args.password),
            "full_name": args.name,
            "role": "admin",
            "is_active": True,
            "created_at": datetime.utcnow()
        }
        db.users.insert_one(user_doc)
        print(f"[OK] Created admin user: {args.email}")

    if args.pdf:
        import shutil
        storage = Path(settings.STORAGE_PATH)
        storage.mkdir(parents=True, exist_ok=True)
        doc_id = str(uuid.uuid4())
        dest = storage / f"{doc_id}.pdf"
        shutil.copy2(args.pdf, dest)

        doc_doc = {
            "_id": doc_id,
            "title": Path(args.pdf).stem,
            "doc_type": "other",
            "file_path": str(dest),
            "file_name": Path(args.pdf).name,
            "file_size_bytes": os.path.getsize(args.pdf),
            "page_count": 0,
            "is_scanned": False,
            "processing_status": "pending",
            "toc": [],
            "created_at": datetime.utcnow(),
            "uploaded_by": user_id
        }
        db.documents.insert_one(doc_doc)
        print(f"Indexing {args.pdf}...")

        # Run async indexing pipeline synchronously for the script CLI context
        asyncio.run(run_async_indexing(doc_id, str(dest), Path(args.pdf).name, "other", Path(args.pdf).stem))
        
        updated_doc = db.documents.find_one({"_id": doc_id})
        print(f"[OK] Indexed: {updated_doc['title']} ({updated_doc.get('page_count')} pages, status={updated_doc['processing_status']})")


if __name__ == "__main__":
    main()
