"""
README assembly module.

Generates comprehensive README.md documentation from project structure
and generated documentation.
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, List
import logging

from .parser import ProjectInfo, FileInfo, CodeUnit

logger = logging.getLogger(__name__)


# Language badges and metadata
LANGUAGE_CONFIG = {
    "python": {
        "badge": "![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)",
        "icon": "🐍",
        "name": "Python",
    },
    "java": {
        "badge": "![Java](https://img.shields.io/badge/java-%23ED8B00.svg?style=for-the-badge&logo=openjdk&logoColor=white)",
        "icon": "☕",
        "name": "Java",
    },
    "javascript": {
        "badge": "![JavaScript](https://img.shields.io/badge/javascript-%23323330.svg?style=for-the-badge&logo=javascript&logoColor=%23F7DF1E)",
        "icon": "🟨",
        "name": "JavaScript",
    },
}


def build_readme(project: ProjectInfo, overview: str) -> str:
    """
    Build a complete README.md from project information.
    
    Generates a user-friendly README with overview, quick start, features,
    usage examples, and minimal API reference.
    
    Args:
        project: ProjectInfo with generated documentation
        overview: LLM-generated project overview paragraph
        
    Returns:
        Complete README.md content as a string
    """
    sections = []
    
    # 1. Title
    title = _format_title(project.name)
    sections.append(f"# {title}\n")
    
    # 2. Language badges
    badges = _build_badges(project.languages)
    if badges:
        sections.append(badges + "\n")
    
    # 3. Overview
    sections.append("## Overview\n")
    sections.append(overview.strip() + "\n")
    
    # 4. Features (NEW)
    features = _build_features(project)
    if features:
        sections.append("\n## Features\n")
        sections.append(features)
    
    # 5. Quick Start (NEW)
    quick_start = _build_quick_start(project)
    if quick_start:
        sections.append("\n## Quick Start\n")
        sections.append(quick_start)
    
    # 6. Usage Examples (MOVED UP)
    usage = _build_usage_examples(project)
    if usage:
        sections.append("\n## Usage\n")
        sections.append(usage)
    
    # 7. Installation
    installation = _build_installation(project)
    if installation:
        sections.append("\n## Installation\n")
        sections.append(installation)
    
    # 8. Project Structure
    structure = _build_structure(project)
    if structure:
        sections.append("\n## Project Structure\n")
        sections.append("```\n")
        sections.append(structure)
        sections.append("```\n")
    
    # 9. API Reference (SUMMARIZED)
    api_ref = _build_api_summary(project)
    if api_ref:
        sections.append("\n## API Summary\n")
        sections.append(api_ref)
        sections.append("\n*For detailed API documentation, see the [full API reference](docs/API.md).*\n")
    
    # 10. Dependencies
    dependencies = _build_dependencies(project)
    if dependencies:
        sections.append("\n## Dependencies\n")
        sections.append(dependencies)
    
    # 11. Footer
    footer = _build_footer()
    sections.append("\n" + footer)
    
    return "\n".join(sections)


def build_project_summary(project: ProjectInfo) -> str:
    """
    Build a plain text summary of the project for overview generation.
    
    Creates a structured description of the project including languages,
    files, functions/classes, and dependencies.
    
    Args:
        project: ProjectInfo object
        
    Returns:
        Plain text project summary
    """
    lines = []
    
    lines.append(f"Project: {project.name}")
    lines.append(f"Languages: {', '.join(project.languages)}")
    lines.append(f"Total files: {len(project.files)}")
    
    # List files and their units (limit to 15 files)
    lines.append("\nFiles and components:")
    for i, file_info in enumerate(project.files[:15]):
        rel_path = Path(file_info.path).relative_to(project.root)
        lines.append(f"- {rel_path}:")
        for unit in file_info.units[:5]:  # Limit units per file
            lines.append(f"  - {unit.name} ({unit.kind})")
    
    if len(project.files) > 15:
        lines.append(f"... and {len(project.files) - 15} more files")
    
    # Dependencies
    if project.dependencies:
        lines.append("\nDependencies:")
        for lang, deps in project.dependencies.items():
            lines.append(f"- {lang}: {', '.join(deps[:10])}")
            if len(deps) > 10:
                lines.append(f"  ... and {len(deps) - 10} more")
    
    return "\n".join(lines)


def _build_features(project: ProjectInfo) -> str:
    """Build features section from project components."""
    features = []
    
    # Analyze project to extract key features
    if "python" in project.languages:
        features.append("🐍 **Python Implementation** - Modular Python codebase with clean architecture")
    if "javascript" in project.languages:
        features.append("🟨 **JavaScript/Node.js** - Modern JavaScript with async/await support")
    if "java" in project.languages:
        features.append("☕ **Java Implementation** - Object-oriented design with strong typing")
    
    # Check for common patterns
    has_classes = any(any(u.kind == "class" for u in f.units) for f in project.files)
    if has_classes:
        features.append("📦 **Object-Oriented Design** - Well-structured classes and interfaces")
    
    # Check for utilities
    util_files = [f for f in project.files if "util" in f.path.lower() or "helper" in f.path.lower()]
    if util_files:
        features.append("🛠️ **Utility Functions** - Reusable helper functions and utilities")
    
    # Multi-language if applicable
    if len(project.languages) > 1:
        features.append(f"🌐 **Multi-Language Support** - Codebase spans {', '.join(project.languages)}")
    
    if features:
        return "\n".join(f"- {feat}" for feat in features) + "\n"
    return ""


def _build_quick_start(project: ProjectInfo) -> str:
    """Build quick start section with minimal setup."""
    lines = []
    
    # Python quick start
    if "python" in project.languages:
        lines.append("### Python\n")
        lines.append("```bash")
        lines.append("# Clone and setup")
        lines.append("pip install -r requirements.txt\n")
        
        # Find a main file or common module
        main_file = next((f for f in project.files if "main" in f.path.lower()), None)
        if main_file:
            rel_path = Path(main_file.path).relative_to(project.root)
            lines.append(f"# Run")
            lines.append(f"python {rel_path}")
        else:
            # Show import example
            first_file = next((f for f in project.files if f.language == "python" and f.units), None)
            if first_file and first_file.units:
                module_name = Path(first_file.path).stem
                unit = first_file.units[0]
                lines.append(f"# Import and use")
                lines.append(f"from {module_name} import {unit.name}")
        
        lines.append("```\n")
    
    # JavaScript quick start
    if "javascript" in project.languages:
        lines.append("### JavaScript\n")
        lines.append("```bash")
        lines.append("# Install dependencies")
        lines.append("npm install\n")
        lines.append("# Run")
        lines.append("npm start")
        lines.append("```\n")
    
    # Java quick start
    if "java" in project.languages:
        lines.append("### Java\n")
        lines.append("```bash")
        lines.append("# Build")
        lines.append("mvn clean install\n")
        lines.append("# Run")
        lines.append("mvn exec:java")
        lines.append("```\n")
    
    return "\n".join(lines) if lines else ""


def _format_title(name: str) -> str:
    """Convert directory name to title case."""
    return name.replace("_", " ").replace("-", " ").title()


def _build_badges(languages: List[str]) -> str:
    """Build language badges."""
    badges = []
    for lang in languages:
        if lang in LANGUAGE_CONFIG:
            badges.append(LANGUAGE_CONFIG[lang]["badge"])
    return " ".join(badges)


def _build_installation(project: ProjectInfo) -> str:
    """Build installation instructions based on detected dependencies."""
    sections = []
    
    if "python" in project.dependencies:
        sections.append("### Python\n")
        sections.append("```bash\npip install -r requirements.txt\n```\n")
    
    if "javascript" in project.dependencies:
        sections.append("### JavaScript/Node.js\n")
        sections.append("```bash\nnpm install\n# or\nyarn install\n```\n")
    
    if "java" in project.dependencies:
        sections.append("### Java\n")
        sections.append("```bash\nmvn install\n# or\ngradle build\n```\n")
    
    return "\n".join(sections) if sections else ""


def _build_dependencies(project: ProjectInfo) -> str:
    """Build dependencies section."""
    if not project.dependencies:
        return ""
    
    lines = []
    
    for lang, deps in project.dependencies.items():
        lang_name = LANGUAGE_CONFIG.get(lang, {}).get("name", lang.title())
        lines.append(f"### {lang_name}\n")
        
        # Format as bullet list
        for dep in deps[:20]:  # Limit to 20 deps
            lines.append(f"- `{dep}`")
        
        if len(deps) > 20:
            lines.append(f"- ... and {len(deps) - 20} more\n")
        else:
            lines.append("")
    
    return "\n".join(lines)


def _build_structure(project: ProjectInfo) -> str:
    """Build ASCII file tree structure."""
    # Group files by directory
    root_path = Path(project.root)
    tree_lines = [f"{project.name}/"]
    
    # Build directory tree
    dirs: Dict[str, List[str]] = {}
    for file_info in project.files:
        file_path = Path(file_info.path)
        rel_path = file_path.relative_to(root_path)
        
        parent = str(rel_path.parent)
        if parent == ".":
            parent = ""
        
        if parent not in dirs:
            dirs[parent] = []
        dirs[parent].append(rel_path.name)
    
    # Sort and format
    sorted_dirs = sorted(dirs.items())
    
    for i, (dir_path, files) in enumerate(sorted_dirs):
        if dir_path:
            # Add directory
            depth = len(Path(dir_path).parts)
            prefix = "│   " * (depth - 1) + "├── "
            tree_lines.append(f"{prefix}{Path(dir_path).name}/")
        
        # Add files
        for j, filename in enumerate(sorted(files)):
            if dir_path:
                depth = len(Path(dir_path).parts)
                prefix = "│   " * depth + "├── "
            else:
                prefix = "├── "
            
            # Use └── for last item
            if i == len(sorted_dirs) - 1 and j == len(files) - 1:
                prefix = prefix.replace("├──", "└──")
            
            tree_lines.append(f"{prefix}{filename}")
    
    return "\n".join(tree_lines)


def _build_api_summary(project: ProjectInfo) -> str:
    """Build summarized API reference with key functions/classes only."""
    # Group files by language
    files_by_lang: Dict[str, List[FileInfo]] = {}
    for file_info in project.files:
        lang = file_info.language
        if lang not in files_by_lang:
            files_by_lang[lang] = []
        files_by_lang[lang].append(file_info)
    
    sections = []
    root_path = Path(project.root)
    
    # Process each language
    for lang in sorted(files_by_lang.keys()):
        lang_config = LANGUAGE_CONFIG.get(lang, {"icon": "📄", "name": lang.title()})
        sections.append(f"### {lang_config['icon']} {lang_config['name']}\n")
        
        # Collect main classes and public functions only
        main_units = []
        for file_info in files_by_lang[lang]:
            for unit in file_info.units:
                # Include classes and top-level functions, skip private methods
                if unit.kind == "class" or (unit.kind == "function" and not unit.name.startswith("_")):
                    main_units.append((file_info, unit))
        
        # Limit to most important units (max 10 per language)
        main_units = main_units[:10]
        
        if not main_units:
            sections.append("_No public API to document._\n")
            continue
        
        # Build summary table
        sections.append("| Name | Type | Description |")
        sections.append("|------|------|-------------|")
        
        for file_info, unit in main_units:
            rel_path = Path(file_info.path).relative_to(root_path)
            # Extract first line of documentation as summary
            doc_summary = "_No description_"
            if unit.generated_doc:
                first_line = unit.generated_doc.strip().split("\n")[0]
                doc_summary = first_line[:80] + ("..." if len(first_line) > 80 else "")
            
            sections.append(f"| `{unit.name}` | {unit.kind} | {doc_summary} |")
        
        if len([u for f in files_by_lang[lang] for u in f.units]) > 10:
            remaining = len([u for f in files_by_lang[lang] for u in f.units]) - 10
            sections.append(f"\n*... and {remaining} more items*\n")
        sections.append("")
    
    return "\n".join(sections)


def _build_usage_examples(project: ProjectInfo) -> str:
    """Build usage section with actual code examples."""
    lines = []
    
    # Python examples
    if "python" in project.languages:
        python_files = [f for f in project.files if f.language == "python" and f.units]
        if python_files:
            lines.append("### Python\n")
            
            # Find a good example function or class
            example_file = python_files[0]
            example_units = [u for u in example_file.units if not u.name.startswith("_")][:2]
            
            if example_units:
                lines.append("```python")
                module_name = Path(example_file.path).stem
                
                # Show imports
                imports = [u.name for u in example_units]
                lines.append(f"from {module_name} import {', '.join(imports)}\n")
                
                # Show usage for first unit
                unit = example_units[0]
                if unit.kind == "class":
                    lines.append(f"# Create an instance")
                    lines.append(f"obj = {unit.name}()")
                    lines.append(f"# Use the class")
                    lines.append(f"# obj.method_name()")
                elif unit.kind == "function":
                    lines.append(f"# Call the function")
                    lines.append(f"result = {unit.name}()")
                    lines.append(f"print(result)")
                
                lines.append("```\n")
    
    # JavaScript examples
    if "javascript" in project.languages:
        js_files = [f for f in project.files if f.language == "javascript" and f.units]
        if js_files:
            lines.append("### JavaScript\n")
            
            example_file = js_files[0]
            example_units = [u for u in example_file.units if not u.name.startswith("_")][:2]
            
            if example_units:
                lines.append("```javascript")
                module_name = Path(example_file.path).stem
                
                # Show imports
                imports = [u.name for u in example_units]
                lines.append(f"const {{ {', '.join(imports)} }} = require('./{module_name}');\n")
                
                # Show usage
                unit = example_units[0]
                if unit.kind == "class":
                    lines.append(f"// Create an instance")
                    lines.append(f"const obj = new {unit.name}();")
                elif unit.kind == "function":
                    lines.append(f"// Call the function")
                    lines.append(f"const result = {unit.name}();")
                    lines.append(f"console.log(result);")
                
                lines.append("```\n")
    
    # Java examples
    if "java" in project.languages:
        java_files = [f for f in project.files if f.language == "java" and f.units]
        if java_files:
            lines.append("### Java\n")
            
            example_file = java_files[0]
            example_classes = [u for u in example_file.units if u.kind == "class"][:1]
            
            if example_classes:
                lines.append("```java")
                class_unit = example_classes[0]
                lines.append(f"// Create an instance")
                lines.append(f"{class_unit.name} obj = new {class_unit.name}();\n")
                lines.append(f"// Use the class methods")
                lines.append(f"// obj.methodName();")
                lines.append("```\n")
    
    return "\n".join(lines) if lines else ""


def _build_footer() -> str:
    """Build generation metadata footer."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        "---\n\n"
        f"*Documentation generated by [slm_docgen](https://github.com/your-repo/slm_docgen) "
        f"on {timestamp}*\n"
    )
