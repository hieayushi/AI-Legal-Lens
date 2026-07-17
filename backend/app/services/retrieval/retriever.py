"""
Retrieval engine supporting BM25, Hybrid, and Hierarchical Page Indexing.
Resolves queries asynchronously against MongoDB Atlas.
Hybrid search uses Azure OpenAI text-embedding deployment for vector scoring.
"""
import logging
from typing import List, Dict, Any, Optional
from pymongo.database import Database
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


def _get_query_embedding(text: str) -> List[float]:
    """
    Compute a query embedding via Azure OpenAI text-embedding deployment.
    Returns an empty list on failure or if Azure is not configured.
    """
    if not settings.AZURE_OPENAI_API_KEY:
        return []
    try:
        from openai import AzureOpenAI
        client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        )
        response = client.embeddings.create(
            input=[text],
            model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME,
        )
        return response.data[0].embedding
    except Exception as e:
        logger.warning(f"Azure embedding for query failed: {e}")
        return []


async def retrieve(
    db: AsyncIOMotorDatabase,
    query: str,
    document_ids: List[str],
    method: str = "hierarchical",
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Retrieves and ranks pages based on hierarchical index structures or hybrid retrieval methods.
    """
    # 1. Fetch scoped documents
    docs = await _resolve_docs(db, document_ids)
    if not docs:
        return []

    # 2. Dispatch to the selected retrieval strategy
    if method == "bm25":
        return await _bm25_retrieve(db, query, docs, top_k)
    elif method == "hybrid":
        return await _hybrid_retrieve(db, query, docs, top_k)
    else:  # hierarchical
        return await _hierarchical_retrieve(db, query, docs, top_k)


async def _resolve_docs(db: AsyncIOMotorDatabase, document_ids: List[str]) -> List[dict]:
    query_filter = {"processing_status": "indexed"}
    if document_ids:
        query_filter["_id"] = {"$in": document_ids}

    docs = []
    async for doc in db.documents.find(query_filter):
        docs.append(doc)
    return docs


async def _get_doc_pages(db: AsyncIOMotorDatabase, doc_id: str) -> List[dict]:
    pages = []
    async for page in db.pages.find({"document_id": doc_id}).sort("page_number", 1):
        pages.append(page)
    return pages


def _text_relevance(query_tokens: List[str], text: str) -> float:
    if not text:
        return 0.0
    text_lower = text.lower()
    matches = sum(1 for token in query_tokens if token in text_lower)
    return matches / max(len(query_tokens), 1)


def _make_citation(doc: dict, page: dict, confidence: float) -> dict:
    text = page.get("text_content", "").strip()
    evidence = text[:500]
    if len(text) > 500:
        evidence += "..."
    return {
        "document_id": doc["_id"],
        "document_title": doc["title"],
        "section_title": page.get("section_title"),
        "page_number": page["page_number"],
        "evidence_text": evidence,
        "confidence_score": round(confidence, 4),
        "retrieval_rank": 0,
    }


def _dedupe_and_rank(results: List[dict], top_k: int) -> List[dict]:
    seen = set()
    deduped = []
    for item in results:
        key = (item["document_id"], item["page_number"])
        if key not in seen:
            seen.add(key)
            deduped.append(item)
        if len(deduped) >= top_k:
            break
    for idx, item in enumerate(deduped, start=1):
        item["retrieval_rank"] = idx
    return deduped


# ── Strategy 1: BM25 ──────────────────────────────────────────────────────────

async def _bm25_retrieve(db: AsyncIOMotorDatabase, query: str, docs: List[dict], top_k: int) -> List[dict]:
    from app.services.indexing.indexer import get_bm25
    query_tokens = query.lower().split()
    results = []

    for doc in docs:
        bm25 = get_bm25(doc["_id"])
        pages = await _get_doc_pages(db, doc["_id"])
        if not pages:
            continue

        if bm25 is not None:
            try:
                scores = bm25.get_scores(query_tokens)
                scored_pages = list(zip(scores, pages))
                scored_pages.sort(key=lambda x: x[0], reverse=True)
            except Exception:
                scored_pages = [(log_score(query_tokens, p), p) for p in pages]
        else:
            scored_pages = [(log_score(query_tokens, p), p) for p in pages]

        for score, page in scored_pages[:top_k]:
            if not page.get("text_content", "").strip():
                continue
            confidence = min(score / (score + 5.0), 1.0) if bm25 else min(score, 1.0)
            results.append(_make_citation(doc, page, confidence))

    results.sort(key=lambda x: x["confidence_score"], reverse=True)
    return _dedupe_and_rank(results, top_k)


def log_score(query_tokens: List[str], page: dict) -> float:
    return _text_relevance(query_tokens, page.get("text_content", ""))


# ── Strategy 2: Hierarchical Page Indexing (Primary) ──────────────────────────

async def _hierarchical_retrieve(db: AsyncIOMotorDatabase, query: str, docs: List[dict], top_k: int) -> List[dict]:
    """
    Hierarchical structural navigation:
      1. Group pages by Section heading structure
      2. Match query keywords to Section scopes
      3. Focus search inside best-matched Sections to extract cited Pages
    """
    query_tokens = query.lower().split()
    results = []

    for doc in docs:
        pages = await _get_doc_pages(db, doc["_id"])
        if not pages:
            continue

        # Group pages by section title
        sections_map = {}
        for page in pages:
            sec_title = page.get("section_title") or "__root__"
            sections_map.setdefault(sec_title, []).append(page)

        # Score sections based on text matching
        sec_scores = []
        for sec_title, sec_pages in sections_map.items():
            aggregated_text = " ".join(p.get("text_content", "") for p in sec_pages)
            sec_relevance = _text_relevance(query_tokens, aggregated_text)
            sec_scores.append((sec_relevance, sec_title, sec_pages))

        sec_scores.sort(key=lambda x: x[0], reverse=True)

        # Navigate within top-scoring sections to fetch individual pages
        candidate_pages = []
        for sec_rel, sec_title, sec_pages in sec_scores[:3]:
            for page in sec_pages:
                pg_relevance = _text_relevance(query_tokens, page.get("text_content", ""))
                # Combined confidence weight (0.6 page relevance + 0.4 section scope match)
                combined_score = 0.6 * pg_relevance + 0.4 * sec_rel
                candidate_pages.append((combined_score, page))

        candidate_pages.sort(key=lambda x: x[0], reverse=True)

        for combined, page in candidate_pages[:top_k]:
            if not page.get("text_content", "").strip():
                continue
            results.append(_make_citation(doc, page, min(combined, 1.0)))

    results.sort(key=lambda x: x["confidence_score"], reverse=True)
    return _dedupe_and_rank(results, top_k)


# ── Strategy 3: Hybrid Search (BM25 + Azure Embeddings) ──────────────────────

async def _hybrid_retrieve(db: AsyncIOMotorDatabase, query: str, docs: List[dict], top_k: int) -> List[dict]:
    """
    Hybrid retrieval: BM25 candidates re-ranked via cosine similarity with
    Azure OpenAI text-embedding vectors stored in MongoDB page documents.
    """
    bm25_results = await _bm25_retrieve(db, query, docs, top_k * 2)
    if not HAS_NUMPY or not bm25_results:
        return bm25_results[:top_k]

    # Compute query embedding via Azure
    query_vec = _get_query_embedding(query)
    if not query_vec:
        logger.warning("Azure query embedding unavailable — returning BM25 results only.")
        return bm25_results[:top_k]

    query_np = np.array(query_vec, dtype=float)

    # Re-rank via vector cosine similarity against stored Azure embeddings
    for item in bm25_results:
        page = await db.pages.find_one({
            "document_id": item["document_id"],
            "page_number": item["page_number"]
        })
        if page and page.get("embedding"):
            page_np = np.array(page["embedding"], dtype=float)
            dot = np.dot(query_np, page_np)
            norm_q = np.linalg.norm(query_np)
            norm_p = np.linalg.norm(page_np)
            cos_sim = float(dot / (norm_q * norm_p + 1e-9))

            # Fuse BM25 confidence score with Azure vector similarity (50/50)
            item["confidence_score"] = 0.5 * item["confidence_score"] + 0.5 * max(cos_sim, 0.0)

    bm25_results.sort(key=lambda x: x["confidence_score"], reverse=True)
    return _dedupe_and_rank(bm25_results, top_k)
