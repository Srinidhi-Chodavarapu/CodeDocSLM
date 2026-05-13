#!/usr/bin/env python3
"""
slm_docgen CLI tool.

Command-line interface for generating documentation for code projects.
"""

import sys
import argparse
import logging
from pathlib import Path
import shutil
from typing import Optional
from tqdm import tqdm

from app import (
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
    level=logging.WARNING,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


def document_command(args):
    """Handle the 'document' command."""
    path = Path(args.path).resolve()
    
    if not path.exists():
        print(f"Error: Path not found: {path}")
        sys.exit(1)
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.INFO)
    
    # Load model
    print(f"Loading model from {args.adapter_dir}...")
    try:
        model, tokenizer = load_model(args.adapter_dir, load_in_4bit=not args.no_4bit)
        print("✓ Model loaded successfully\n")
    except Exception as e:
        print(f"Error loading model: {e}")
        sys.exit(1)
    
    # Check if it's a file or directory
    if path.is_file():
        # Document single file
        _document_file(path, model, tokenizer, args)
    else:
        # Document entire directory
        _document_directory(path, model, tokenizer, args)


def _document_file(file_path: Path, model, tokenizer, args):
    """Document a single file."""
    # Determine language
    ext = file_path.suffix.lower()
    language_map = {
        ".py": "python",
        ".java": "java",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "javascript",
        ".tsx": "javascript",
    }
    
    if ext not in language_map:
        print(f"Error: Unsupported file type: {ext}")
        sys.exit(1)
    
    language = language_map[ext]
    
    print(f"Processing {file_path.name}...")
    
    # Parse file
    try:
        file_info = parse_file(str(file_path), language)
    except Exception as e:
        print(f"Error parsing file: {e}")
        sys.exit(1)
    
    if not file_info or not file_info.units:
        print("No documentable units found in file")
        sys.exit(1)
    
    print(f"Found {len(file_info.units)} units to document\n")
    
    # Generate docs for each unit
    for unit in file_info.units:
        print(f"  Processing {unit.name} ({unit.kind})...", end=" ", flush=True)
        
        try:
            doc, latency = generate_doc(
                code=unit.code,
                language=language,
                model=model,
                tokenizer=tokenizer,
                max_new_tokens=128,
            )
            unit.generated_doc = doc
            unit.latency = latency
            print(f"✅ ({latency:.1f}s)")
        except Exception as e:
            print(f"❌ ({e})")
            continue
    
    # Create backup if not dry run
    if not args.dry_run:
        backup_path = str(file_path) + ".bak"
        shutil.copy2(file_path, backup_path)
        print(f"\n✓ Backup created: {backup_path}")
    
    # Inject docstrings
    if not args.no_inject and not args.dry_run:
        try:
            modified_source = inject_docstrings(file_info)
            
            # Write back to file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(modified_source)
            
            print(f"✓ Docstrings injected into {file_path}")
        except Exception as e:
            print(f"Error injecting docstrings: {e}")
            sys.exit(1)
    elif args.dry_run:
        print("\n[DRY RUN] Would inject docstrings into file")
    
    print(f"\n✓ Successfully documented {file_path.name}")


def _document_directory(dir_path: Path, model, tokenizer, args):
    """Document an entire directory."""
    print(f"Scanning directory: {dir_path}...")
    
    # Scan directory
    try:
        project = scan_directory(str(dir_path), max_files=args.max_files)
    except Exception as e:
        print(f"Error scanning directory: {e}")
        sys.exit(1)
    
    if not project.files:
        print("No source files found")
        sys.exit(1)
    
    print(f"Found {len(project.files)} files across {len(project.languages)} languages")
    print(f"Languages detected: {', '.join(project.languages)}\n")
    
    # Count total units
    total_units = sum(len(f.units) for f in project.files)
    print(f"Total units to document: {total_units}\n")
    
    if args.dry_run:
        print("[DRY RUN MODE] - No files will be modified\n")
    
    # Process each file
    total_latency = 0.0
    documented_count = 0
    
    for file_info in project.files:
        rel_path = Path(file_info.path).relative_to(dir_path)
        print(f"Processing {rel_path} ({len(file_info.units)} units)...")
        
        # Generate docs for each unit
        for unit in file_info.units:
            print(f"  {'✓' if args.verbose else '⋯'} {unit.name:<30}", end=" ", flush=True)
            
            try:
                doc, latency = generate_doc(
                    code=unit.code,
                    language=unit.language,
                    model=model,
                    tokenizer=tokenizer,
                    max_new_tokens=128,
                )
                unit.generated_doc = doc
                unit.latency = latency
                total_latency += latency
                documented_count += 1
                print(f"✅ ({latency:.1f}s)")
            except Exception as e:
                print(f"❌ ({e})")
                logger.warning(f"Failed to document {unit.name}: {e}")
                continue
        
        print()
    
    # Generate overview
    if not args.no_readme:
        print("Generating project overview...", end=" ", flush=True)
        try:
            project_summary = build_project_summary(project)
            overview, overview_latency = generate_overview(
                project_summary,
                model=model,
                tokenizer=tokenizer,
            )
            total_latency += overview_latency
            print(f"✅ ({overview_latency:.1f}s)\n")
        except Exception as e:
            print(f"❌ ({e})\n")
            overview = "Project overview could not be generated."
    else:
        overview = ""
    
    # Inject docstrings into files
    if not args.no_inject and not args.dry_run:
        print("Injecting docstrings into source files...")
        
        # Create backups
        for file_info in project.files:
            backup_path = file_info.path + ".bak"
            shutil.copy2(file_info.path, backup_path)
        
        print(f"✓ Created {len(project.files)} backup files (.bak)")
        
        # Inject
        try:
            modified_files = inject_project(project)
            
            # Write back
            for file_path, content in modified_files.items():
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
            
            print(f"✓ Injected docstrings into {len(modified_files)} files\n")
        except Exception as e:
            print(f"Error injecting docstrings: {e}")
            sys.exit(1)
    elif args.dry_run:
        print(f"[DRY RUN] Would inject docstrings into {len(project.files)} files\n")
    
    # Generate README
    if not args.no_readme:
        print("Generating README...", end=" ", flush=True)
        try:
            readme_content = build_readme(project, overview)
            
            if not args.dry_run:
                # Determine output path
                if args.output:
                    readme_path = Path(args.output)
                else:
                    readme_path = dir_path / "README_generated.md"
                
                with open(readme_path, "w", encoding="utf-8") as f:
                    f.write(readme_content)
                
                print(f"✅\n✓ README saved to {readme_path}\n")
            else:
                print(f"✅\n[DRY RUN] Would save README to README_generated.md\n")
        except Exception as e:
            print(f"❌ ({e})\n")
    
    # Print summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Files processed:      {len(project.files)}")
    print(f"Units documented:     {documented_count}/{total_units}")
    print(f"Total time:           {total_latency:.1f}s")
    print(f"Average per unit:     {total_latency/documented_count:.2f}s" if documented_count > 0 else "")
    print("=" * 60)
    
    if not args.dry_run:
        print("\n✓ Documentation complete! Check the .bak files if you need to revert.")
    else:
        print("\n[DRY RUN] No files were modified. Remove --dry-run to apply changes.")


def serve_command(args):
    """Handle the 'serve' command."""
    import os
    import uvicorn
    
    # Set environment variables BEFORE importing app
    # (main.py reads these on import)
    os.environ["ADAPTER_DIR"] = args.adapter_dir
    os.environ["LOAD_IN_4BIT"] = str(not args.no_4bit).lower()
    
    from app.main import app
    
    print(f"Starting slm_docgen API server...")
    print(f"Adapter directory: {args.adapter_dir}")
    print(f"Host: {args.host}:{args.port}")
    print(f"4-bit quantization: {not args.no_4bit}\n")
    print("Docs available at: http://{args.host}:{args.port}/docs\n")
    
    # Run server
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
    )


def stats_command(args):
    """Handle the 'stats' command."""
    path = Path(args.path).resolve()
    
    if not path.exists() or not path.is_dir():
        print(f"Error: Directory not found: {path}")
        sys.exit(1)
    
    print(f"Scanning directory: {path}...\n")
    
    # Scan without loading model
    try:
        project = scan_directory(str(path), max_files=args.max_files)
    except Exception as e:
        print(f"Error scanning directory: {e}")
        sys.exit(1)
    
    if not project.files:
        print("No source files found")
        sys.exit(1)
    
    # Print statistics
    print("=" * 60)
    print("PROJECT STATISTICS")
    print("=" * 60)
    print(f"Project name:         {project.name}")
    print(f"Root directory:       {project.root}")
    print(f"Total files:          {len(project.files)}")
    print(f"Languages detected:   {', '.join(project.languages)}")
    print()
    
    # Count by language
    lang_counts = {}
    for file_info in project.files:
        lang = file_info.language
        if lang not in lang_counts:
            lang_counts[lang] = {"files": 0, "units": 0}
        lang_counts[lang]["files"] += 1
        lang_counts[lang]["units"] += len(file_info.units)
    
    print("By language:")
    for lang, counts in sorted(lang_counts.items()):
        print(f"  {lang:<15} {counts['files']} files, {counts['units']} units")
    
    print()
    
    # Dependencies
    if project.dependencies:
        print("Dependencies detected:")
        for lang, deps in project.dependencies.items():
            print(f"  {lang}: {len(deps)} packages")
    
    print()
    
    # List files
    print("Files:")
    for file_info in project.files:
        rel_path = Path(file_info.path).relative_to(path)
        unit_count = len(file_info.units)
        print(f"  {str(rel_path):<50} {unit_count} units")
    
    print("=" * 60)
    
    total_units = sum(len(f.units) for f in project.files)
    print(f"\nTotal documentable units: {total_units}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="slm_docgen - AI-powered code documentation generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Document entire project
  python cli.py document ./my_project
  
  # Document single file
  python cli.py document ./my_project/main.py
  
  # Dry run (don't modify files)
  python cli.py document ./my_project --dry-run
  
  # Start API server
  python cli.py serve --port 8000
  
  # Show project statistics
  python cli.py stats ./my_project
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Document command
    doc_parser = subparsers.add_parser("document", help="Generate documentation for code")
    doc_parser.add_argument("path", help="Path to file or directory to document")
    doc_parser.add_argument(
        "--adapter-dir",
        default="./slm_docgen_final/slm_docgen_adapters",
        help="Path to LoRA adapter directory"
    )
    doc_parser.add_argument(
        "--no-4bit",
        action="store_true",
        help="Disable 4-bit quantization (use full precision)"
    )
    doc_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't modify files, just show what would be done"
    )
    doc_parser.add_argument(
        "--no-readme",
        action="store_true",
        help="Don't generate README.md"
    )
    doc_parser.add_argument(
        "--no-inject",
        action="store_true",
        help="Don't inject docstrings into source files"
    )
    doc_parser.add_argument(
        "--max-files",
        type=int,
        default=50,
        help="Maximum number of files to process"
    )
    doc_parser.add_argument(
        "--output",
        help="Output path for README (default: README_generated.md)"
    )
    doc_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed progress"
    )
    
    # Serve command
    serve_parser = subparsers.add_parser("serve", help="Start API server")
    serve_parser.add_argument(
        "--adapter-dir",
        default="./slm_docgen_final/slm_docgen_adapters",
        help="Path to LoRA adapter directory"
    )
    serve_parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to"
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to"
    )
    serve_parser.add_argument(
        "--no-4bit",
        action="store_true",
        help="Disable 4-bit quantization"
    )
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show project statistics")
    stats_parser.add_argument("path", help="Path to directory to analyze")
    stats_parser.add_argument(
        "--max-files",
        type=int,
        default=100,
        help="Maximum number of files to scan"
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Dispatch to command handler
    if args.command == "document":
        document_command(args)
    elif args.command == "serve":
        serve_command(args)
    elif args.command == "stats":
        stats_command(args)


if __name__ == "__main__":
    main()
