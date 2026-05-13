"""
FastAPI server for slm_docgen.

Provides REST API endpoints for generating documentation for code snippets,
files, and entire projects.
"""

import os
import tempfile
import shutil
import zipfile
from pathlib import Path
from typing import Optional
import logging

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import io

from . import (
    load_model,
    generate_doc,
    generate_overview,
    scan_directory,
    parse_file,
    inject_docstrings,
    inject_project,
    build_readme,
    build_project_summary,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration from environment
ADAPTER_DIR = os.getenv("ADAPTER_DIR", "./slm_docgen_final/slm_docgen_adapters")
LOAD_IN_4BIT = os.getenv("LOAD_IN_4BIT", "true").lower() == "true"
MAX_FILES = int(os.getenv("MAX_FILES", "50"))
MAX_ZIP_MB = int(os.getenv("MAX_ZIP_MB", "50"))

# Global model state
_model = None
_tokenizer = None
_model_loaded = False

# FastAPI app
app = FastAPI(
    title="slm_docgen API",
    description="AI-powered code documentation generator using fine-tuned Qwen2.5-Coder",
    version="1.0.0",
)

# Enable CORS for all origins (needed for VS Code extension)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class GenerateDocRequest(BaseModel):
    code: str = Field(..., description="Source code to document")
    language: str = Field(..., description="Programming language (python, java, javascript)")
    style: Optional[str] = Field(None, description="Documentation style (auto-detected if not provided)")


class GenerateDocResponse(BaseModel):
    documentation: str
    language: str
    style: str
    latency_ms: float


class ProjectStatsResponse(BaseModel):
    files_processed: int
    units_documented: int
    total_latency_ms: float
    languages: list


class GenerateProjectResponse(BaseModel):
    readme: str
    modified_files: dict
    stats: ProjectStatsResponse


class GenerateFileResponse(BaseModel):
    modified_source: str
    units_documented: int
    language: str
    latency_ms: float


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    adapter_dir: str


class InfoResponse(BaseModel):
    title: str
    version: str
    supported_languages: list
    model_info: dict
    config: dict


# Startup event
@app.on_event("startup")
async def startup_event():
    """Load the model at startup."""
    global _model, _tokenizer, _model_loaded
    
    logger.info("Starting slm_docgen API server...")
    logger.info(f"Adapter directory: {ADAPTER_DIR}")
    logger.info(f"4-bit quantization: {LOAD_IN_4BIT}")
    
    try:
        _model, _tokenizer = load_model(ADAPTER_DIR, load_in_4bit=LOAD_IN_4BIT)
        _model_loaded = True
        logger.info("Model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        logger.warning("Server started but model not loaded - API endpoints will fail")


# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check server health and model status."""
    return {
        "status": "ok" if _model_loaded else "model_not_loaded",
        "model_loaded": _model_loaded,
        "adapter_dir": ADAPTER_DIR,
    }


# Info endpoint
@app.get("/info", response_model=InfoResponse)
async def get_info():
    """Get server information and configuration."""
    return {
        "title": "slm_docgen API",
        "version": "1.0.0",
        "supported_languages": ["python", "java", "javascript"],
        "model_info": {
            "base_model": "Qwen/Qwen2.5-Coder-1.5B-Instruct",
            "adapter_dir": ADAPTER_DIR,
            "loaded": _model_loaded,
        },
        "config": {
            "max_files": MAX_FILES,
            "max_zip_mb": MAX_ZIP_MB,
            "load_in_4bit": LOAD_IN_4BIT,
        },
    }


# Generate documentation for a code snippet
@app.post("/generate/doc", response_model=GenerateDocResponse)
async def generate_documentation(request: GenerateDocRequest):
    """
    Generate documentation for a code snippet.
    
    Supports Python, Java, and JavaScript/TypeScript code.
    """
    if not _model_loaded:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    # Validate language
    supported_languages = ["python", "java", "javascript"]
    if request.language.lower() not in supported_languages:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language. Must be one of: {supported_languages}"
        )
    
    try:
        # Generate documentation
        doc, latency = generate_doc(
            code=request.code,
            language=request.language.lower(),
            style=request.style,
            model=_model,
            tokenizer=_tokenizer,
            max_new_tokens=128,
        )
        
        # Determine style used
        style_used = request.style or {
            "python": "Google",
            "java": "Javadoc",
            "javascript": "JSDoc",
        }.get(request.language.lower(), "Standard")
        
        return {
            "documentation": doc,
            "language": request.language.lower(),
            "style": style_used,
            "latency_ms": latency * 1000,
        }
        
    except Exception as e:
        logger.error(f"Documentation generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


# Generate documentation for a single file
@app.post("/generate/file", response_model=GenerateFileResponse)
async def generate_file_documentation(file: UploadFile = File(...)):
    """
    Generate documentation for a single source file.
    
    Parses the file, generates docs for all units, and returns modified source.
    """
    if not _model_loaded:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    # Determine language from extension
    ext = Path(file.filename).suffix.lower()
    language_map = {
        ".py": "python",
        ".java": "java",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "javascript",
        ".tsx": "javascript",
    }
    
    if ext not in language_map:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension: {ext}"
        )
    
    language = language_map[ext]
    
    # Save file to temp location
    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=ext) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        # Parse file
        file_info = parse_file(tmp_path, language)
        if not file_info or not file_info.units:
            raise HTTPException(status_code=400, detail="No documentable units found in file")
        
        # Generate docs for each unit
        total_latency = 0.0
        for unit in file_info.units:
            doc, latency = generate_doc(
                code=unit.code,
                language=language,
                model=_model,
                tokenizer=_tokenizer,
                max_new_tokens=128,
            )
            unit.generated_doc = doc
            unit.latency = latency
            total_latency += latency
        
        # Inject docstrings
        modified_source = inject_docstrings(file_info)
        
        return {
            "modified_source": modified_source,
            "units_documented": len(file_info.units),
            "language": language,
            "latency_ms": total_latency * 1000,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File documentation generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# Generate documentation for entire project
@app.post("/generate/project")
async def generate_project_documentation(
    file: UploadFile = File(...),
    write_back: bool = Form(False),
):
    """
    Generate documentation for an entire project from a ZIP file.
    
    Processes all source files, generates comprehensive README, and optionally
    injects docstrings back into source files.
    """
    if not _model_loaded:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    # Validate file is a zip
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="File must be a ZIP archive")
    
    # Check file size
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_ZIP_MB:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({size_mb:.1f}MB). Max size: {MAX_ZIP_MB}MB"
        )
    
    # Create temp directory
    temp_dir = tempfile.mkdtemp(prefix="slm_docgen_")
    
    try:
        # Extract zip
        zip_path = os.path.join(temp_dir, "project.zip")
        with open(zip_path, "wb") as f:
            f.write(content)
        
        # Validate zip (prevent zip slip)
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            for member in zip_ref.namelist():
                # Check for path traversal
                if member.startswith("/") or ".." in member:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid path in zip: {member}"
                    )
            
            # Extract
            extract_dir = os.path.join(temp_dir, "project")
            zip_ref.extractall(extract_dir)
        
        # Find project root (handle single-folder zips)
        entries = list(Path(extract_dir).iterdir())
        if len(entries) == 1 and entries[0].is_dir():
            project_root = str(entries[0].resolve())
        else:
            project_root = str(Path(extract_dir).resolve())
        
        # Scan directory
        logger.info(f"Scanning project: {project_root}")
        project = scan_directory(project_root, max_files=MAX_FILES)
        
        if not project.files:
            raise HTTPException(status_code=400, detail="No source files found in project")
        
        # Generate docs for each unit
        total_latency = 0.0
        units_documented = 0
        
        for file_info in project.files:
            for unit in file_info.units:
                try:
                    doc, latency = generate_doc(
                        code=unit.code,
                        language=unit.language,
                        model=_model,
                        tokenizer=_tokenizer,
                        max_new_tokens=128,
                    )
                    unit.generated_doc = doc
                    unit.latency = latency
                    total_latency += latency
                    units_documented += 1
                except Exception as e:
                    logger.warning(f"Failed to generate doc for {unit.name}: {e}")
                    continue
        
        # Generate project overview
        project_summary = build_project_summary(project)
        overview, overview_latency = generate_overview(
            project_summary,
            model=_model,
            tokenizer=_tokenizer,
        )
        total_latency += overview_latency
        
        # Build README
        readme_content = build_readme(project, overview)
        
        # Inject docstrings
        modified_files = inject_project(project)
        
        # Convert absolute paths to relative
        relative_modified = {}
        for abs_path, content in modified_files.items():
            rel_path = str(Path(abs_path).resolve().relative_to(project_root))
            relative_modified[rel_path] = content
        
        # If write_back, create a new zip with modified files
        if write_back:
            output_zip = os.path.join(temp_dir, "output.zip")
            with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zip_out:
                # Write modified files
                for rel_path, content in relative_modified.items():
                    zip_out.writestr(rel_path, content)
                
                # Write README
                zip_out.writestr("README_generated.md", readme_content)
                
                # Copy other files
                for root, dirs, files in os.walk(project_root):
                    # Skip excluded directories
                    dirs[:] = [d for d in dirs if d not in {
                        "__pycache__", ".git", "node_modules", "venv", ".venv"
                    }]
                    
                    for filename in files:
                        file_path = Path(root) / filename
                        rel_path = str(file_path.resolve().relative_to(project_root))
                        
                        # Skip if we already wrote this file
                        if rel_path in relative_modified or rel_path == "README_generated.md":
                            continue
                        
                        zip_out.write(file_path, rel_path)
            
            # Return zip file
            def iter_zip():
                with open(output_zip, "rb") as f:
                    yield from f
            
            return StreamingResponse(
                iter_zip(),
                media_type="application/zip",
                headers={"Content-Disposition": f"attachment; filename=documented_project.zip"}
            )
        
        else:
            # Return JSON response
            return {
                "readme": readme_content,
                "modified_files": relative_modified,
                "stats": {
                    "files_processed": len(project.files),
                    "units_documented": units_documented,
                    "total_latency_ms": total_latency * 1000,
                    "languages": project.languages,
                },
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Project documentation generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")
    finally:
        # Clean up temp directory
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


# Root endpoint
@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "message": "slm_docgen API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
