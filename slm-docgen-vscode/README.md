# SLM DocGen - VS Code Extension

AI-powered code documentation generator using fine-tuned language models, integrated directly into VS Code.

## Features

- **📝 Document Functions/Classes**: Generate documentation for individual code units at cursor position
- **📄 Document Files**: Automatically document all functions and classes in a file
- **📦 Document Workspace**: Batch process multiple files with comprehensive README generation
- **👁️ Preview Before Apply**: Review changes in diff view before modifying files
- **⚡ CodeLens Quick Actions**: Inline "Document this" buttons above undocumented code
- **📊 Status Integration**: Real-time server status in status bar
- **🔧 Auto-Managed Server**: Extension handles Python server lifecycle automatically

## Supported Languages

- Python (Google-style docstrings)
- Java (Javadoc)
- JavaScript/TypeScript (JSDoc)

## Requirements

- VS Code 1.85.0 or higher
- Python 3.8+ installed and accessible
- slm_docgen server with model adapters (from parent project)

## Installation

1. Install the extension from `.vsix` file or VS Code Marketplace (when published)
2. Extension will auto-start the documentation server on first use
3. Configure model adapter path in settings if needed

## Usage

### Document Function/Class at Cursor
1. Place cursor inside a function or class
2. Open Command Palette (`Cmd+Shift+P` / `Ctrl+Shift+P`)
3. Run: `SLM DocGen: Document Function/Class at Cursor`
4. Review diff and approve changes

### Document Current File
1. Open a Python, Java, or JavaScript/TypeScript file
2. Right-click in editor → `Document Current File`
3. Or use Command Palette: `SLM DocGen: Document Current File`
4. Review and apply changes

### Document Workspace
1. Open Command Palette
2. Run: `SLM DocGen: Document Workspace`
3. Select files to document
4. Wait for batch processing to complete
5. Review generated README

### Using CodeLens
- Look for "📝 Document this" above functions/classes
- Click to generate documentation instantly

## Extension Settings

- `slm-docgen.serverPort`: Port for documentation server (default: 8000)
- `slm-docgen.autoStartServer`: Auto-start server on activation (default: true)
- `slm-docgen.pythonPath`: Path to Python executable (default: python3)
- `slm-docgen.adapterPath`: Path to model adapters (auto-detected if empty)
- `slm-docgen.enable4bit`: Enable 4-bit quantization (default: true)
- `slm-docgen.enableCodeLens`: Show quick action buttons (default: true)
- `slm-docgen.maxFiles`: Max files for workspace documentation (default: 50)

## Development

```bash
# Install dependencies
npm install

# Compile
npm run compile

# Watch mode
npm run watch

# Package extension
npm run package

# Create .vsix
vsce package
```

## Troubleshooting

### Server not starting
- Check Python path in settings  
- Verify model adapters are available
- Check Output panel: View → Output → SLM DocGen

### Documentation quality issues
- Ensure model adapters are properly fine-tuned
- Check server logs for generation errors

## License

MIT

## Credits

Built on top of the slm_docgen project using fine-tuned Qwen2.5-Coder-1.5B-Instruct.
