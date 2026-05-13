from ..core.injector import inject_docstring_into_snippet
from .generation_service import generate_documentation


async def generate_for_symbol(
    *,
    code: str,
    language: str,
    model,
    tokenizer,
    mode: str = "smart_update",
):
    """
    Generate docs for a single symbol.
    """

    result = await generate_documentation(
        code=code,
        language=language,
        mode=mode,
        model=model,
        tokenizer=tokenizer,
    )

    updated_code = inject_docstring_into_snippet(
        code=code,
        generated_doc=result["documentation"],
        language=language,
    )

    return {
        "updated_code": updated_code,
        "documentation": result["documentation"],
        "latency_ms": result["latency"] * 1000,
    }