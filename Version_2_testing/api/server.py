import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..core.model import load_model
from ..services.symbol_service import generate_for_symbol
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="CodeDocSLM")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


ADAPTER_DIR = os.getenv(
    "ADAPTER_DIR",
    "./slm_docgen_final/slm_docgen_adapters",
)

LOAD_IN_4BIT = os.getenv("LOAD_IN_4BIT", "true").lower() == "true"


_model = None
_tokenizer = None


class SymbolRequest(BaseModel):
    code: str
    language: str
    mode: str = "smart_update"


@app.on_event("startup")
async def startup_event():
    global _model
    global _tokenizer

    logger.info("Loading model...")

    _model, _tokenizer = load_model(
        ADAPTER_DIR,
        load_in_4bit=LOAD_IN_4BIT,
    )

    logger.info("Model loaded successfully")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model_loaded": _model is not None,
    }


@app.post("/warmup")
async def warmup():
    await generate_for_symbol(
        code="def hello():\n    pass",
        language="python",
        model=_model,
        tokenizer=_tokenizer,
    )

    return {"status": "warmed"}


@app.post("/generate/symbol")
async def generate_symbol(request: SymbolRequest):
    result = await generate_for_symbol(
        code=request.code,
        language=request.language,
        mode=request.mode,
        model=_model,
        tokenizer=_tokenizer,
    )

    return result