import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from app.core.config import settings

logger = logging.getLogger(__name__)

# Async Client for FastAPI application endpoints
async_client = AsyncIOMotorClient(settings.MONGODB_URL)
db = async_client[settings.DATABASE_NAME]

# Sync Client for fixtures, migrations, seeds, or specific tasks
sync_client = MongoClient(settings.MONGODB_URL)
sync_db = sync_client[settings.DATABASE_NAME]


def get_db():
    """
    Dependency generator for database requests.
    Returns the motor database instance.
    """
    return db


def get_sync_db():
    """
    Get synchronous DB instance.
    """
    return sync_db


def _ensure_index(collection, keys, **kwargs):
    """
    Create an index only if one with the same key specification does not
    already exist.  This avoids ``IndexKeySpecsConflict`` errors that occur
    when ``create_index`` is called with options that differ from an
    existing index on the same key pattern.
    """
    # Normalise *keys* to the list-of-tuples form used by index_information()
    from pymongo import IndexModel
    idx = IndexModel(keys, **kwargs)
    desired_key = list(idx.document["key"].items())

    existing = collection.index_information()
    for info in existing.values():
        if info.get("key") == desired_key:
            return  # index already exists — nothing to do
    collection.create_index(keys, **kwargs)


def init_db():
    """
    Initialize indexes on MongoDB collections.
    Checks for existing indexes before creating to avoid
    IndexKeySpecsConflict on repeated startups.
    """
    try:
        # Users indexes
        _ensure_index(sync_db.users, "email", unique=True)

        # Documents indexes
        _ensure_index(sync_db.documents, "doc_type")
        _ensure_index(sync_db.documents, "processing_status")

        # Pages indexes
        _ensure_index(sync_db.pages, [("document_id", 1), ("page_number", 1)], unique=True)
        _ensure_index(sync_db.pages, "section_title")

        # Sections indexes
        _ensure_index(sync_db.sections, "document_id")

        # Query logs indexes
        _ensure_index(sync_db.query_logs, "user_id")
        _ensure_index(sync_db.query_logs, "document_id")

        # Eval runs indexes
        _ensure_index(sync_db.eval_runs, "retrieval_method")

        logger.info("MongoDB Atlas indexes verified and created successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize MongoDB indexes: {e}")
