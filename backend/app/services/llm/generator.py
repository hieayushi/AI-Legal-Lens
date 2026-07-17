"""
LLM Orchestrator using Azure OpenAI GPT-4.1.
"""
import logging
import time
from typing import List, Dict, Any, Tuple

from openai import AzureOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_azure_client() -> AzureOpenAI:
    return AzureOpenAI(
        api_key=settings.AZURE_OPENAI_API_KEY,
        api_version=settings.AZURE_OPENAI_API_VERSION,
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
    )


def generate_answer(
    query: str,
    citations: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Generates a grounded answer for the given query using Azure OpenAI GPT-4.1,
    citing specific pages from the retrieved document excerpts.
    """
    if not citations:
        return {
            "answer": "No relevant context found within the uploaded legal documents.",
            "model_used": "none",
            "latency_ms": 0,
            "warning": "No citations retrieved. Please refine your query.",
        }

    context = _build_context(citations)
    prompt = _build_prompt(query, context)

    t0 = time.time()
    warning = None
    try:
        answer, model = _call_azure(prompt)
    except Exception as e:
        logger.error(f"Azure OpenAI GPT-4.1 call failed: {e}", exc_info=True)
        answer = _text_fallback(citations)
        model = "raw_text_extractor"
        warning = f"Azure LLM call failed — raw text excerpt returned. Error: {e}"

    latency_ms = int((time.time() - t0) * 1000)

    return {
        "answer": answer,
        "model_used": model,
        "latency_ms": latency_ms,
        "warning": warning,
    }


def _build_context(citations: List[Dict[str, Any]]) -> str:
    parts = []
    for c in citations:
        parts.append(
            f"[Document: {c['document_title']}, Page {c['page_number']}"
            + (f", Section: {c['section_title']}" if c.get("section_title") else "")
            + f"]\n{c['evidence_text']}"
        )
    return "\n\n---\n\n".join(parts)


def _build_prompt(query: str, context: str) -> str:
    return f"""You are LegalLens AI, an advanced Judicial & Governance analyst.
Answer the following question based ONLY on the provided document excerpts.
Be precise, structured, and cite exact sources by document title and page number.
If the excerpts do not contain enough information, state that clearly.

Excerpts:
{context}

Question: {query}
Answer:"""


def _call_azure(prompt: str) -> Tuple[str, str]:
    """Call Azure OpenAI GPT-4.1 deployment and return (answer_text, model_label)."""
    client = _get_azure_client()
    response = client.chat.completions.create(
        model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are LegalLens AI — a precise, authoritative legal document analyst. "
                    "Always ground your answers in the provided document excerpts and cite page numbers."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=1024,
        temperature=0.1,
    )
    text = response.choices[0].message.content.strip()
    return text, f"azure/{settings.AZURE_OPENAI_DEPLOYMENT_NAME}"


def _text_fallback(citations: List[Dict[str, Any]]) -> str:
    parts = [f"Page {c['page_number']}: {c['evidence_text']}" for c in citations[:2]]
    return "Fallback Excerpts:\n\n" + "\n\n".join(parts)
