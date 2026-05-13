"""
Code parsing module.

Extracts functions, classes, and methods from Python, Java, and JavaScript/TypeScript
source files using AST (Python) and regex (Java/JS).
"""

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class CodeUnit:
    """Represents a single documentable code unit (function, class, or method)."""
    
    name: str
    kind: str  # 'function', 'class', 'method'
    code: str
    language: str
    file_path: str
    start_line: int
    end_line: int
    docstring: Optional[str] = None  # Existing docstring
    generated_doc: Optional[str] = None  # Generated documentation
    latency: Optional[float] = None  # Generation time in seconds


@dataclass
class FileInfo:
    """Information about a single source file."""
    
    path: str
    language: str
    units: List[CodeUnit] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    has_main: bool = False


@dataclass
class ProjectInfo:
    """Information about an entire project."""
    
    name: str
    root: str
    files: List[FileInfo] = field(default_factory=list)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    languages: List[str] = field(default_factory=list)


# File extensions to language mapping
LANGUAGE_MAP = {
    ".py": "python",
    ".java": "java",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "javascript",
    ".tsx": "javascript",
}

# Directories and files to skip
SKIP_DIRS = {"__pycache__", ".git", "node_modules", "venv", ".venv", "dist", "build", "target", ".pytest_cache", "coverage"}
SKIP_FILES = {"__init__.py", "setup.py", "conftest.py"}


def scan_directory(root: str, max_files: int = 50) -> ProjectInfo:
    """
    Scan a directory recursively for source files.
    
    Args:
        root: Root directory path
        max_files: Maximum number of files to process
        
    Returns:
        ProjectInfo object with all discovered files
    """
    root_path = Path(root).resolve()
    if not root_path.exists():
        raise ValueError(f"Directory not found: {root}")
    
    project_name = root_path.name
    project = ProjectInfo(name=project_name, root=str(root_path))
    
    # Walk directory tree
    file_count = 0
    for file_path in root_path.rglob("*"):
        # Skip directories
        if file_path.is_dir():
            continue
        
        # Skip if in excluded directory
        if any(skip_dir in file_path.parts for skip_dir in SKIP_DIRS):
            continue
        
        # Skip excluded files
        if file_path.name in SKIP_FILES:
            continue
        
        # Check if it's a supported language
        ext = file_path.suffix.lower()
        if ext not in LANGUAGE_MAP:
            continue
        
        # Check file count limit
        if file_count >= max_files:
            logger.warning(f"Reached max file limit ({max_files}), stopping scan")
            break
        
        language = LANGUAGE_MAP[ext]
        
        try:
            file_info = parse_file(str(file_path), language)
            if file_info and file_info.units:  # Only add files with documentable units
                project.files.append(file_info)
                file_count += 1
                
                # Track language
                if language not in project.languages:
                    project.languages.append(language)
                    
        except Exception as e:
            logger.warning(f"Failed to parse {file_path}: {e}")
            continue
    
    # Detect dependencies
    project.dependencies = _detect_dependencies(root_path)
    
    logger.info(f"Scanned {file_count} files across {len(project.languages)} languages")
    return project


def parse_file(path: str, language: str) -> Optional[FileInfo]:
    """
    Parse a single source file and extract documentable units.
    
    Args:
        path: File path
        language: Programming language
        
    Returns:
        FileInfo object or None if parsing failed
    """
    path_obj = Path(path)
    if not path_obj.exists():
        raise ValueError(f"File not found: {path}")
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        logger.warning(f"Failed to read {path} - encoding issue")
        return None
    
    file_info = FileInfo(path=str(path_obj), language=language)
    
    if language == "python":
        _parse_python(content, file_info, path_obj)
    elif language == "java":
        _parse_java(content, file_info, path_obj)
    elif language == "javascript":
        _parse_javascript(content, file_info, path_obj)
    
    return file_info


def _parse_python(content: str, file_info: FileInfo, path: Path) -> None:
    """Parse Python file using AST."""
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        logger.warning(f"Syntax error in {path}: {e}")
        return
    
    lines = content.split("\n")
    
    for node in ast.walk(tree):
        # Extract functions
        if isinstance(node, ast.FunctionDef):
            # Skip private functions
            if node.name.startswith("_") and not node.name.startswith("__"):
                continue
            
            # Get function code
            start_line = node.lineno
            end_line = node.end_lineno or start_line
            
            # Skip very short functions
            if end_line - start_line < 2:
                continue
            
            # Extract code (truncate to 40 lines)
            code_lines = lines[start_line - 1:end_line]
            if len(code_lines) > 40:
                code_lines = code_lines[:40]
                code_lines.append("# ... (truncated)")
            
            code = "\n".join(code_lines)
            
            # Get existing docstring
            docstring = ast.get_docstring(node)
            
            # Determine if it's a method or function
            kind = "function"
            # Check if parent is a class
            for parent in ast.walk(tree):
                if isinstance(parent, ast.ClassDef):
                    if node in ast.walk(parent):
                        kind = "method"
                        break
            
            unit = CodeUnit(
                name=node.name,
                kind=kind,
                code=code,
                language="python",
                file_path=str(path),
                start_line=start_line,
                end_line=end_line,
                docstring=docstring,
            )
            file_info.units.append(unit)
        
        # Extract classes
        elif isinstance(node, ast.ClassDef):
            # Skip private classes
            if node.name.startswith("_"):
                continue
            
            start_line = node.lineno
            end_line = node.end_lineno or start_line
            
            # Extract code (truncate to 40 lines)
            code_lines = lines[start_line - 1:end_line]
            if len(code_lines) > 40:
                code_lines = code_lines[:40]
                code_lines.append("# ... (truncated)")
            
            code = "\n".join(code_lines)
            
            # Get existing docstring
            docstring = ast.get_docstring(node)
            
            unit = CodeUnit(
                name=node.name,
                kind="class",
                code=code,
                language="python",
                file_path=str(path),
                start_line=start_line,
                end_line=end_line,
                docstring=docstring,
            )
            file_info.units.append(unit)
        
        # Check for main block
        elif isinstance(node, ast.If):
            if isinstance(node.test, ast.Compare):
                if (isinstance(node.test.left, ast.Name) and 
                    node.test.left.id == "__name__"):
                    file_info.has_main = True
        
        # Extract imports
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    file_info.imports.append(alias.name)
            else:
                module = node.module or ""
                file_info.imports.append(module)


def _parse_java(content: str, file_info: FileInfo, path: Path) -> None:
    """Parse Java file using regex."""
    lines = content.split("\n")
    
    # Pattern for Java methods and classes
    # Matches: public/protected/private (optional) static (optional) returnType methodName(params) throws (optional)
    method_pattern = re.compile(
        r"^\s*(public|protected|private)?\s*(static)?\s*[\w<>\[\]]+\s+(\w+)\s*\([^)]*\)(?:\s+throws\s+[\w\s,]+)?\s*\{",
        re.MULTILINE
    )
    
    # Pattern for classes
    class_pattern = re.compile(
        r"^\s*(public|private|protected)?\s*(abstract|final)?\s*class\s+(\w+)",
        re.MULTILINE
    )
    
    # Extract methods
    for match in method_pattern.finditer(content):
        method_name = match.group(3)
        
        # Skip if it looks like a constructor or common utility
        if method_name in {"main", "toString", "equals", "hashCode"}:
            continue
        
        # Find line number
        start_pos = match.start()
        start_line = content[:start_pos].count("\n") + 1
        
        # Extract code around the method (try to get full method)
        # Find the matching closing brace
        brace_count = 1
        pos = match.end()
        while pos < len(content) and brace_count > 0:
            if content[pos] == "{":
                brace_count += 1
            elif content[pos] == "}":
                brace_count -= 1
            pos += 1
        
        end_line = content[:pos].count("\n") + 1
        
        # Extract code lines (truncate to 40 lines)
        code_lines = lines[start_line - 1:end_line]
        if len(code_lines) > 40:
            code_lines = code_lines[:40]
            code_lines.append("// ... (truncated)")
        
        code = "\n".join(code_lines)
        
        # Try to extract existing Javadoc (look backwards from match)
        javadoc = None
        javadoc_pattern = re.compile(r"/\*\*(.*?)\*/", re.DOTALL)
        before_method = content[:start_pos]
        javadoc_matches = list(javadoc_pattern.finditer(before_method))
        if javadoc_matches:
            last_javadoc = javadoc_matches[-1]
            # Check if it's close to the method (within 5 lines)
            javadoc_end_line = before_method[:last_javadoc.end()].count("\n") + 1
            if start_line - javadoc_end_line <= 5:
                javadoc = last_javadoc.group(0)
        
        unit = CodeUnit(
            name=method_name,
            kind="method",
            code=code,
            language="java",
            file_path=str(path),
            start_line=start_line,
            end_line=end_line,
            docstring=javadoc,
        )
        file_info.units.append(unit)
    
    # Extract classes
    for match in class_pattern.finditer(content):
        class_name = match.group(3)
        
        start_pos = match.start()
        start_line = content[:start_pos].count("\n") + 1
        
        # Get first 40 lines of class
        end_line = min(start_line + 40, len(lines))
        code_lines = lines[start_line - 1:end_line]
        if end_line - start_line >= 40:
            code_lines.append("// ... (truncated)")
        
        code = "\n".join(code_lines)
        
        # Try to extract Javadoc
        javadoc = None
        javadoc_pattern = re.compile(r"/\*\*(.*?)\*/", re.DOTALL)
        before_class = content[:start_pos]
        javadoc_matches = list(javadoc_pattern.finditer(before_class))
        if javadoc_matches:
            last_javadoc = javadoc_matches[-1]
            javadoc_end_line = before_class[:last_javadoc.end()].count("\n") + 1
            if start_line - javadoc_end_line <= 5:
                javadoc = last_javadoc.group(0)
        
        unit = CodeUnit(
            name=class_name,
            kind="class",
            code=code,
            language="java",
            file_path=str(path),
            start_line=start_line,
            end_line=end_line,
            docstring=javadoc,
        )
        file_info.units.append(unit)
    
    # Check for main method
    if "public static void main" in content:
        file_info.has_main = True


def _parse_javascript(content: str, file_info: FileInfo, path: Path) -> None:
    """Parse JavaScript/TypeScript file using regex."""
    lines = content.split("\n")
    
    # Patterns for JavaScript functions
    # Named function: function name(...) { }
    named_func_pattern = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(", re.MULTILINE)
    
    # Arrow function assigned to const/let/var: const name = (...) => { }
    arrow_func_pattern = re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>", re.MULTILINE)
    
    # Class pattern
    class_pattern = re.compile(r"^\s*(?:export\s+)?class\s+(\w+)", re.MULTILINE)
    
    # Method in class: methodName(...) { }
    method_pattern = re.compile(r"^\s*(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{", re.MULTILINE)
    
    # Process named functions
    for match in named_func_pattern.finditer(content):
        func_name = match.group(1)
        start_pos = match.start()
        start_line = content[:start_pos].count("\n") + 1
        
        # Try to find the end of the function
        brace_count = 0
        pos = content.find("{", match.end())
        if pos == -1:
            continue
        
        brace_count = 1
        pos += 1
        while pos < len(content) and brace_count > 0:
            if content[pos] == "{":
                brace_count += 1
            elif content[pos] == "}":
                brace_count -= 1
            pos += 1
        
        end_line = content[:pos].count("\n") + 1
        
        # Extract code (truncate to 40 lines)
        code_lines = lines[start_line - 1:end_line]
        if len(code_lines) > 40:
            code_lines = code_lines[:40]
            code_lines.append("// ... (truncated)")
        
        code = "\n".join(code_lines)
        
        # Try to extract JSDoc
        jsdoc = _extract_jsdoc(content, start_pos)
        
        unit = CodeUnit(
            name=func_name,
            kind="function",
            code=code,
            language="javascript",
            file_path=str(path),
            start_line=start_line,
            end_line=end_line,
            docstring=jsdoc,
        )
        file_info.units.append(unit)
    
    # Process arrow functions
    for match in arrow_func_pattern.finditer(content):
        func_name = match.group(1)
        start_pos = match.start()
        start_line = content[:start_pos].count("\n") + 1
        
        # Find end - arrow functions can be tricky
        arrow_pos = content.find("=>", match.end())
        if arrow_pos == -1:
            continue
        
        # Check if it's a block or expression
        next_char_pos = arrow_pos + 2
        while next_char_pos < len(content) and content[next_char_pos].isspace():
            next_char_pos += 1
        
        if next_char_pos < len(content) and content[next_char_pos] == "{":
            # Block body
            brace_count = 1
            pos = next_char_pos + 1
            while pos < len(content) and brace_count > 0:
                if content[pos] == "{":
                    brace_count += 1
                elif content[pos] == "}":
                    brace_count -= 1
                pos += 1
            end_line = content[:pos].count("\n") + 1
        else:
            # Expression body - find the semicolon or newline
            pos = next_char_pos
            while pos < len(content) and content[pos] not in (";\n"):
                pos += 1
            end_line = content[:pos].count("\n") + 1
        
        # Extract code (truncate to 40 lines)
        code_lines = lines[start_line - 1:end_line]
        if len(code_lines) > 40:
            code_lines = code_lines[:40]
            code_lines.append("// ... (truncated)")
        
        code = "\n".join(code_lines)
        
        # Try to extract JSDoc
        jsdoc = _extract_jsdoc(content, start_pos)
        
        unit = CodeUnit(
            name=func_name,
            kind="function",
            code=code,
            language="javascript",
            file_path=str(path),
            start_line=start_line,
            end_line=end_line,
            docstring=jsdoc,
        )
        file_info.units.append(unit)
    
    # Process classes
    for match in class_pattern.finditer(content):
        class_name = match.group(1)
        start_pos = match.start()
        start_line = content[:start_pos].count("\n") + 1
        
        # Get first 40 lines
        end_line = min(start_line + 40, len(lines))
        code_lines = lines[start_line - 1:end_line]
        if end_line - start_line >= 40:
            code_lines.append("// ... (truncated)")
        
        code = "\n".join(code_lines)
        
        # Try to extract JSDoc
        jsdoc = _extract_jsdoc(content, start_pos)
        
        unit = CodeUnit(
            name=class_name,
            kind="class",
            code=code,
            language="javascript",
            file_path=str(path),
            start_line=start_line,
            end_line=end_line,
            docstring=jsdoc,
        )
        file_info.units.append(unit)


def _extract_jsdoc(content: str, pos: int) -> Optional[str]:
    """Extract JSDoc comment before a given position."""
    jsdoc_pattern = re.compile(r"/\*\*(.*?)\*/", re.DOTALL)
    before = content[:pos]
    matches = list(jsdoc_pattern.finditer(before))
    if matches:
        last_match = matches[-1]
        # Check if it's close (within 3 lines)
        jsdoc_end_line = before[:last_match.end()].count("\n") + 1
        code_start_line = before[:pos].count("\n") + 1
        if code_start_line - jsdoc_end_line <= 3:
            return last_match.group(0)
    return None


def _detect_dependencies(root: Path) -> Dict[str, List[str]]:
    """Detect project dependencies from various manifest files."""
    deps = {}
    
    # Python: requirements.txt
    req_file = root / "requirements.txt"
    if req_file.exists():
        try:
            with open(req_file, "r") as f:
                python_deps = []
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # Extract package name (before ==, >=, etc.)
                        pkg = re.split(r"[=<>!]", line)[0].strip()
                        python_deps.append(pkg)
                if python_deps:
                    deps["python"] = python_deps
        except Exception as e:
            logger.warning(f"Failed to parse requirements.txt: {e}")
    
    # JavaScript: package.json
    pkg_file = root / "package.json"
    if pkg_file.exists():
        try:
            import json
            with open(pkg_file, "r") as f:
                pkg_data = json.load(f)
                js_deps = []
                for dep_type in ["dependencies", "devDependencies"]:
                    if dep_type in pkg_data:
                        js_deps.extend(pkg_data[dep_type].keys())
                if js_deps:
                    deps["javascript"] = js_deps
        except Exception as e:
            logger.warning(f"Failed to parse package.json: {e}")
    
    # Java: pom.xml (basic extraction)
    pom_file = root / "pom.xml"
    if pom_file.exists():
        try:
            with open(pom_file, "r") as f:
                content = f.read()
                # Extract artifactId from dependencies
                artifact_pattern = re.compile(r"<artifactId>(.*?)</artifactId>")
                artifacts = artifact_pattern.findall(content)
                if artifacts:
                    deps["java"] = artifacts
        except Exception as e:
            logger.warning(f"Failed to parse pom.xml: {e}")
    
    return deps
