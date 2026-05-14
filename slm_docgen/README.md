# slm_docgen

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) ![PyTorch](https://img.shields.io/badge/PyTorch-%23EE4C2C.svg?style=for-the-badge&logo=PyTorch&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)

**AI-powered code documentation generator using fine-tuned Qwen2.5-Coder-1.5B-Instruct**

A production-ready local documentation system that automatically generates high-quality docstrings for Python, Java, and JavaScript/TypeScript code using a fine-tuned small language model with LoRA adapters.

## 🌟 Features

- **Multi-language Support**: Python (Google-style), Java (Javadoc), JavaScript/TypeScript (JSDoc)
- **Local & Private**: Runs entirely on your machine - no cloud dependencies
- **Fast Inference**: Optimized with 4-bit quantization and optional Unsloth acceleration
- **Smart Parsing**: AST-based Python parsing, regex-based Java/JS extraction
- **In-place Injection**: Safely modifies source files with automatic backups
- **README Generation**: Creates comprehensive project documentation automatically
- **REST API**: FastAPI server for integration with editors and CI/CD
- **CLI Tool**: Full-featured command-line interface for batch processing

## 📋 Requirements

- Python 3.8+
- CUDA-capable GPU recommended (CPU inference supported but slower)
- 4-8GB VRAM for 4-bit quantization, 16GB+ for full precision
- Fine-tuned model adapters (see Setup)

## 🚀 Installation

### 1. Clone and Setup

```bash
cd slm_docgen
pip install -r requirements.txt
```

### 2. Obtain Model Adapters

Place your fine-tuned LoRA adapters in a directory. Default expected structure:

```
slm_docgen_final/
└── slm_docgen_adapters/
    ├── adapter_config.json
    ├── adapter_model.safetensors
    ├── tokenizer_config.json
    ├── tokenizer.json
    └── chat_template.jinja
```

Or specify a custom path with `--adapter-dir`.

### 3. Optional: Install Unsloth (for faster inference)

```bash
pip install "unsloth @ git+https://github.com/unslothai/unsloth.git"
```

If Unsloth is not available, the system automatically falls back to `transformers + PEFT`.

## 💻 Usage

### Command-Line Interface

#### Document an Entire Project

```bash
python cli.py document ./my_project
```

This will:
- Scan all Python, Java, and JavaScript files
- Generate docstrings for functions, classes, and methods
- Inject docstrings back into source files (creates `.bak` backups)
- Generate a comprehensive `README_generated.md`

#### Document a Single File

```bash
python cli.py document ./my_project/utils.py
```

#### Dry Run (Preview Changes)

```bash
python cli.py document ./my_project --dry-run
```

#### Advanced Options

```bash
python cli.py document ./my_project \
  --adapter-dir ./path/to/adapters \
  --no-4bit \
  --max-files 100 \
  --output ./DOCUMENTATION.md \
  --verbose
```

#### Show Project Statistics

```bash
python cli.py stats ./my_project
```

Displays:
- Files detected by language
- Total documentable units
- Dependencies detected
- No model loading required

### REST API Server

#### Start the Server

```bash
python cli.py serve --port 8000
```

Or run directly:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

API documentation available at: `http://localhost:8000/docs`

#### API Endpoints

**Health Check**
```bash
curl http://localhost:8000/health
```

**Generate Documentation for Code Snippet**
```bash
curl -X POST http://localhost:8000/generate/doc \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def calculate_bmi(weight, height):\n    return weight / (height ** 2)",
    "language": "python"
  }'
```

**Generate Documentation for Single File**
```bash
curl -X POST http://localhost:8000/generate/file \
  -F "file=@utils.py"
```

**Generate Documentation for Entire Project (ZIP)**
```bash
curl -X POST http://localhost:8000/generate/project \
  -F "file=@my_project.zip" \
  -F "write_back=false" \
  -o response.json
```

With `write_back=true`, returns a new ZIP with injected docstrings.

## 📁 Project Structure

```
slm_docgen/
├── app/
│   ├── __init__.py          # Package exports
│   ├── model.py             # Model loading & inference (Unsloth/PEFT)
│   ├── parser.py            # Code parsing (AST for Python, regex for Java/JS)
│   ├── injector.py          # Docstring injection into source files
│   ├── assembler.py         # README.md generation
│   └── main.py              # FastAPI server
├── cli.py                   # Command-line interface
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## 🧠 How It Works

### 1. Model Loading
- Base model: `Qwen/Qwen2.5-Coder-1.5B-Instruct`
- Loads LoRA adapters via Unsloth (optimized) or transformers+PEFT (fallback)
- Supports 4-bit quantization for reduced memory usage
- Global singleton pattern - model loaded once and reused

### 2. Code Parsing
- **Python**: Uses AST to extract functions, classes, methods with exact line numbers
- **Java**: Regex-based extraction of classes and methods with Javadoc
- **JavaScript/TypeScript**: Regex for functions, arrow functions, classes, JSDoc

Skips:
- Private/internal functions (Python `_` prefix)
- Very short functions (< 3 lines)
- Build artifacts, dependencies (`__pycache__`, `node_modules`, etc.)

### 3. Documentation Generation
Each code unit is sent to the model with:
- Language-specific system prompt
- Code snippet (truncated to 40 lines if needed)
- Chat template formatting (`<|im_start|>` tokens)

Generation parameters:
- Temperature: 0.1 (focused, deterministic)
- Max tokens: 256
- Repetition penalty: 1.1

### 4. Injection
Generated docstrings are inserted back into source files:
- **Python**: Triple-quoted strings after `def`/`class` lines
- **Java**: `/** ... */` blocks above methods
- **JavaScript**: `/** ... */` JSDoc blocks above functions

Existing docstrings are replaced, not duplicated.

### 5. README Assembly
Comprehensive README includes:
- Language badges
- AI-generated overview paragraph
- Installation instructions (detected from `requirements.txt`, `package.json`, `pom.xml`)
- ASCII file tree
- API reference with collapsible source code
- Usage examples

## 🔧 Configuration

### Environment Variables (for API server)

```bash
export ADAPTER_DIR="./slm_docgen_final/slm_docgen_adapters"
export LOAD_IN_4BIT="true"
export MAX_FILES="50"
export MAX_ZIP_MB="50"
```

### CLI Flags

```
--adapter-dir PATH        Path to LoRA adapters
--no-4bit                 Disable 4-bit quantization
--dry-run                 Preview without modifying files
--no-readme               Skip README generation
--no-inject               Skip docstring injection
--max-files N             Limit files to process
--verbose                 Show detailed progress
```

## 🛡️ Safety Features

1. **Automatic Backups**: Creates `.bak` files before modifying sources
2. **Zip Slip Protection**: Validates ZIP archives for path traversal attacks
3. **Size Limits**: Configurable limits on ZIP uploads and file counts
4. **Graceful Fallbacks**: Works without Unsloth, handles parsing errors
5. **Dry Run Mode**: Preview all changes before applying

## 📊 Performance

Typical performance on NVIDIA RTX 3090 (4-bit quantization):

- **Single function**: ~1.2s
- **100-function project**: ~2-3 minutes
- **1000-line file**: ~15-20s

CPU inference is 5-10× slower but fully supported.

## 🔍 Example Output

### Input Python Code
```python
def calculate_bmi(weight, height):
    return weight / (height ** 2)
```

### Generated Docstring
```python
def calculate_bmi(weight, height):
    """
    Calculate Body Mass Index (BMI) from weight and height.
    
    Args:
        weight: Weight in kilograms
        height: Height in meters
        
    Returns:
        float: BMI value
    """
    return weight / (height ** 2)
```

## 🤝 Integration Examples

### VS Code Extension

```javascript
const response = await fetch('http://localhost:8000/generate/doc', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    code: selectedText,
    language: 'python'
  })
});
const { documentation } = await response.json();
```

### CI/CD Pipeline

```yaml
# .github/workflows/docs.yml
- name: Generate documentation
  run: |
    pip install -r requirements.txt
    python cli.py document ./src --no-inject --output DOCS.md
    
- name: Commit updated docs
  run: |
    git add DOCS.md
    git commit -m "Auto-update documentation"
```

## 📝 Advanced Usage

### Custom Adapter Path

```bash
python cli.py document ./project --adapter-dir ~/models/custom-adapter
```

### Process Large Projects

```bash
python cli.py document ./large_project --max-files 200 --no-readme
```

### Server with Custom Config

```bash
ADAPTER_DIR=/path/to/adapters MAX_ZIP_MB=100 \
  python -m uvicorn app.main:app --port 9000
```

## 🐛 Troubleshooting

**Model loading fails**
- Ensure CUDA is available: `python -c "import torch; print(torch.cuda.is_available())"`
- Try without 4-bit: `--no-4bit`
- Check adapter files exist and are readable

**Out of memory**
- Use 4-bit quantization (default)
- Reduce batch size by processing fewer files at once
- Close other GPU applications

**Parsing errors**
- Check file encoding (UTF-8 required)
- Some complex syntax may not parse - file is skipped automatically
- Use `--verbose` to see detailed error messages

**Slow inference**
- Install Unsloth for 2-3× speedup
- Ensure GPU is being used
- For CPU: reduce `--max-files` and process in batches

## 📜 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- **Qwen Team** - [Qwen2.5-Coder](https://github.com/QwenLM/Qwen2.5-Coder)
- **Unsloth** - [Optimized inference](https://github.com/unslothai/unsloth)
- **Hugging Face** - transformers, PEFT, accelerate libraries

## 📧 Support

For issues, feature requests, or questions:
- GitHub Issues: [your-repo/slm_docgen/issues](https://github.com/your-repo/slm_docgen/issues)
- Documentation: See `/docs` endpoint when API server is running

---

