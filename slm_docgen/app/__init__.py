"""
slm_docgen - AI-powered code documentation generator.

This package provides tools to automatically generate and inject
documentation into Python, Java, and JavaScript/TypeScript source code
using a fine-tuned Qwen2.5-Coder-1.5B-Instruct model.
"""

__version__ = "1.0.0"
__author__ = "SLM DocGen Team"

from .model import load_model, generate_doc, generate_overview
from .parser import (
    CodeUnit,
    FileInfo,
    ProjectInfo,
    scan_directory,
    parse_file,
)
from .injector import inject_docstrings, inject_project
from .assembler import build_readme, build_project_summary

__all__ = [
    "load_model",
    "generate_doc",
    "generate_overview",
    "CodeUnit",
    "FileInfo",
    "ProjectInfo",
    "scan_directory",
    "parse_file",
    "inject_docstrings",
    "inject_project",
    "build_readme",
    "build_project_summary",
]
