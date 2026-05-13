import asyncio
import hashlib
import logging
from typing import Optional

from ..core.model import generate_doc
from .cache_service import doc_cache

logger = logging.getLogger(__name__)

# Prevent concurrent GPU overload
_generation_lock = asyncio.Lock()


async def generate_documentation(
    *,
    code: str,
    language: str,
    mode: str = "smart_update",
    model=None,
    tokenizer=None,
    max_new_tokens: int = 96,
):
    """
    Centralized documentation generation service.
    """

    cache_key = _build_cache_key(code, language, mode)

    # Check cache
    cached = doc_cache.get(cache_key)
    if cached:
        logger.info("Using cached generation")
        return cached

    # Generate documentation
    async with _generation_lock:
        doc, latency = generate_doc(
            code=code,
            language=language,
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=max_new_tokens,
        )

    # Build response object
    result = {
        "documentation": doc,
        "latency": latency,
        "language": language,
        "mode": mode,
    }

    # Store in TTLCache
    doc_cache[cache_key] = result

    return result


def _build_cache_key(code: str, language: str, mode: str):
    content = f"{language}:{mode}:{code}"
    return hashlib.sha256(content.encode()).hexdigest()