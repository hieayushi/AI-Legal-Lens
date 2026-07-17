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


def init_db():
    """
    Initialize indexes on MongoDB collections.
    """
    try:
        # Users indexes
        sync_db.users.create_index("email", unique=True)

        # Documents indexes
        sync_db.documents.create_index("doc_type")
        sync_db.documents.create_index("processing_status")

        # Pages indexes
        sync_db.pages.create_index([("document_id", 1), ("page_number", 1)], unique=True)
        sync_db.pages.create_index("section_title")

        # Sections indexes
        sync_db.sections.create_index("document_id")

        # Query logs indexes
        sync_db.query_logs.create_index("user_id")
        sync_db.query_logs.create_index("document_id")

        # Eval runs indexes
        sync_db.eval_runs.create_index("retrieval_method")

        logger.info("MongoDB Atlas indexes verified and created successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize MongoDB indexes: {e}")
