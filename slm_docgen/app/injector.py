"""
Docstring injection module.

Handles inserting generated documentation back into source files,
preserving existing code structure and formatting.
"""

import re
from typing import Dict
import logging

from .parser import FileInfo, ProjectInfo, CodeUnit

logger = logging.getLogger(__name__)


def inject_docstrings(file_info: FileInfo) -> str:
    """
    Inject generated docstrings into a source file.
    
    Takes a FileInfo object with generated_doc populated for each unit
    and returns the modified source code with docstrings inserted or replaced.
    
    Args:
        file_info: FileInfo object with units containing generated_doc
        
    Returns:
        Modified source code as a string
    """
    # Read original file
    with open(file_info.path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # Sort units by line number in reverse order (process bottom-up to preserve line numbers)
    units_sorted = sorted(file_info.units, key=lambda u: u.start_line, reverse=True)
    
    for unit in units_sorted:
        if not unit.generated_doc:
            continue
        
        if file_info.language == "python":
            lines = _inject_python_docstring(lines, unit)
        elif file_info.language == "java":
            lines = _inject_java_docstring(lines, unit)
        elif file_info.language == "javascript":
            lines = _inject_javascript_docstring(lines, unit)
    
    return "".join(lines)


def inject_project(project: ProjectInfo) -> Dict[str, str]:
    """
    Inject docstrings into all files in a project.
    
    Args:
        project: ProjectInfo object with generated documentation
        
    Returns:
        Dictionary mapping file paths to modified source code
    """
    modified_files = {}
    
    for file_info in project.files:
        try:
            modified_source = inject_docstrings(file_info)
            modified_files[file_info.path] = modified_source
        except Exception as e:
            logger.error(f"Failed to inject docstrings in {file_info.path}: {e}")
            continue
    
    return modified_files


def _inject_python_docstring(lines: list, unit: CodeUnit) -> list:
    """
    Inject docstring into Python code.
    
    Handles both replacement of existing docstrings and insertion of new ones.
    Preserves indentation and handles async functions correctly.
    """
    start_idx = unit.start_line - 1  # Convert to 0-indexed
    
    # Detect indentation from the def/class line
    def_line = lines[start_idx]
    indent_match = re.match(r"^(\s*)", def_line)
    base_indent = indent_match.group(1) if indent_match else ""
    body_indent = base_indent + "    "
    
    # Format the generated docstring
    doc_lines = unit.generated_doc.strip().split("\n")
    formatted_doc = [body_indent + '"""' + doc_lines[0] + "\n"]
    for line in doc_lines[1:]:
        formatted_doc.append(body_indent + line + "\n")
    formatted_doc.append(body_indent + '"""\n')
    
    # Check if there's an existing docstring to replace
    if unit.docstring:
        # Find the existing docstring in the file
        # Look for triple quotes after the def/class line
        search_start = start_idx + 1
        search_end = min(start_idx + 20, len(lines))  # Search within 20 lines
        
        docstring_start = None
        docstring_end = None
        
        for i in range(search_start, search_end):
            line = lines[i].strip()
            # Check for triple-quote start
            if '"""' in line or "'''" in line:
                if docstring_start is None:
                    docstring_start = i
                    # Check if it's a single-line docstring
                    if line.count('"""') == 2 or line.count("'''") == 2:
                        docstring_end = i
                        break
                else:
                    docstring_end = i
                    break
        
        if docstring_start is not None and docstring_end is not None:
            # Replace existing docstring
            lines[docstring_start:docstring_end + 1] = formatted_doc
        else:
            # Couldn't find docstring, insert after def/class line
            lines[start_idx + 1:start_idx + 1] = formatted_doc
    else:
        # No existing docstring, insert after def/class line
        lines[start_idx + 1:start_idx + 1] = formatted_doc
    
    return lines


def _inject_java_docstring(lines: list, unit: CodeUnit) -> list:
    """
    Inject Javadoc comment into Java code.
    
    Inserts /** ... */ comment block immediately above the method/class signature.
    Replaces existing Javadoc if present.
    """
    start_idx = unit.start_line - 1  # Convert to 0-indexed
    
    # Detect indentation from the method/class line
    signature_line = lines[start_idx]
    indent_match = re.match(r"^(\s*)", signature_line)
    indent = indent_match.group(1) if indent_match else ""
    
    # Format the generated Javadoc
    doc_lines = unit.generated_doc.strip().split("\n")
    formatted_doc = [indent + "/**\n"]
    for line in doc_lines:
        # Handle blank lines properly
        if line.strip():
            formatted_doc.append(indent + " * " + line.strip() + "\n")
        else:
            formatted_doc.append(indent + " *\n")
    formatted_doc.append(indent + " */\n")
    
    # Check if there's an existing Javadoc to replace
    if unit.docstring:
        # Look backwards for the existing Javadoc
        search_start = max(0, start_idx - 20)
        
        javadoc_start = None
        javadoc_end = None
        
        for i in range(start_idx - 1, search_start - 1, -1):
            line = lines[i].strip()
            if line.endswith("*/"):
                javadoc_end = i
            elif line.startswith("/**"):
                javadoc_start = i
                break
        
        if javadoc_start is not None and javadoc_end is not None:
            # Replace existing Javadoc
            lines[javadoc_start:javadoc_end + 1] = formatted_doc
        else:
            # Couldn't find it, insert before method/class
            lines[start_idx:start_idx] = formatted_doc
    else:
        # No existing Javadoc, insert before method/class
        lines[start_idx:start_idx] = formatted_doc
    
    return lines


def _inject_javascript_docstring(lines: list, unit: CodeUnit) -> list:
    """
    Inject JSDoc comment into JavaScript/TypeScript code.
    
    Inserts /** ... */ comment block immediately above the function/class.
    Replaces existing JSDoc if present.
    """
    start_idx = unit.start_line - 1  # Convert to 0-indexed
    
    # Detect indentation from the function/class line
    signature_line = lines[start_idx]
    indent_match = re.match(r"^(\s*)", signature_line)
    indent = indent_match.group(1) if indent_match else ""
    
    # Format the generated JSDoc
    doc_lines = unit.generated_doc.strip().split("\n")
    formatted_doc = [indent + "/**\n"]
    for line in doc_lines:
        # Handle blank lines properly
        if line.strip():
            formatted_doc.append(indent + " * " + line.strip() + "\n")
        else:
            formatted_doc.append(indent + " *\n")
    formatted_doc.append(indent + " */\n")
    
    # Check if there's an existing JSDoc to replace
    if unit.docstring:
        # Look backwards for the existing JSDoc
        search_start = max(0, start_idx - 15)
        
        jsdoc_start = None
        jsdoc_end = None
        
        for i in range(start_idx - 1, search_start - 1, -1):
            line = lines[i].strip()
            if line.endswith("*/"):
                jsdoc_end = i
            elif line.startswith("/**"):
                jsdoc_start = i
                break
        
        if jsdoc_start is not None and jsdoc_end is not None:
            # Replace existing JSDoc
            lines[jsdoc_start:jsdoc_end + 1] = formatted_doc
        else:
            # Couldn't find it, insert before function/class
            lines[start_idx:start_idx] = formatted_doc
    else:
        # No existing JSDoc, insert before function/class
        lines[start_idx:start_idx] = formatted_doc
    
    return lines
