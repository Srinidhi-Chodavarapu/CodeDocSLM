"""
Model loading and inference module.

Handles loading the fine-tuned Qwen2.5-Coder-1.5B-Instruct model with LoRA adapters
and generating documentation for code snippets.
"""

import time
import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# System prompts for different languages
SYSTEM_PROMPTS = {
    "python": (
        "You are a Python documentation assistant. Given Python source code, "
        "generate accurate, well-structured documentation following the specified style. "
        "Include a concise summary, parameter descriptions with types where inferable, "
        "and return value descriptions. Be precise and factual. "
        "Format output as plain text without markdown code blocks."
    ),
    "java": (
        "You are a Java documentation assistant. Given Java source code, generate "
        "accurate Javadoc-style documentation. Include a concise summary, @param tags for "
        "all parameters, @return tag if applicable, and @throws if exceptions are declared. "
        "Be precise and factual. Format output as plain text content only (no /** */ wrapper), "
        "with one blank line between the summary and tags. Keep formatting clean and compact."
    ),
    "javascript": (
        "You are a JavaScript documentation assistant. Given JavaScript or "
        "TypeScript source code, generate accurate JSDoc-style documentation. Include a "
        "concise summary, @param tags with types, and @returns tag where applicable. "
        "Be precise and factual. Format output as plain text content only (no /** */ wrapper), "
        "with one blank line between the summary and tags. Keep formatting clean and compact."
    ),
}

# Global model and tokenizer singletons
_model = None
_tokenizer = None
_adapter_dir = None


def load_model(adapter_dir: str, load_in_4bit: bool = True) -> Tuple[object, object]:
    """
    Load the fine-tuned model with LoRA adapters.
    
    Attempts to load using Unsloth first for optimized inference, falls back to
    standard transformers + PEFT if Unsloth is not available.
    
    Args:
        adapter_dir: Path to the directory containing LoRA adapters
        load_in_4bit: Whether to load the model in 4-bit quantization mode
        
    Returns:
        Tuple of (model, tokenizer)
        
    Raises:
        ValueError: If adapter directory doesn't exist or is missing required files
        RuntimeError: If model loading fails
    """
    global _model, _tokenizer, _adapter_dir
    
    # Return cached model if already loaded with same config
    if _model is not None and _tokenizer is not None and _adapter_dir == adapter_dir:
        logger.info("Using cached model instance")
        return _model, _tokenizer
    
    adapter_path = Path(adapter_dir)
    if not adapter_path.exists():
        raise ValueError(f"Adapter directory not found: {adapter_dir}")
    
    required_files = ["adapter_config.json", "adapter_model.safetensors"]
    for file in required_files:
        if not (adapter_path / file).exists():
            raise ValueError(f"Missing required adapter file: {file}")
    
    logger.info(f"Loading model from {adapter_dir} (4-bit: {load_in_4bit})")
    
    # Try loading with Unsloth first
    try:
        from unsloth import FastLanguageModel
        
        logger.info("Loading model with Unsloth...")
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=str(adapter_path),
            max_seq_length=2048,
            dtype=None,  # Auto-detect
            load_in_4bit=load_in_4bit,
        )
        FastLanguageModel.for_inference(model)  # Enable inference mode
        logger.info("Model loaded successfully with Unsloth")
        
    except ImportError:
        logger.warning("Unsloth not available, falling back to transformers + PEFT")
        
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
            from peft import PeftModel
            import torch
            
            # Read adapter config to get base model name
            import json
            adapter_config_path = adapter_path / "adapter_config.json"
            if not adapter_config_path.exists():
                raise ValueError(f"adapter_config.json not found in {adapter_path}")
            
            with open(adapter_config_path, "r") as f:
                adapter_config = json.load(f)
            
            if adapter_config is None:
                raise ValueError("Failed to parse adapter_config.json")
            
            base_model_name = adapter_config.get("base_model_name_or_path")
            if not base_model_name:
                logger.warning("base_model_name_or_path not found in adapter_config.json, using default")
                base_model_name = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
            
            # Detect platform and available devices
            import platform
            is_mac = platform.system() == "Darwin"
            has_mps = torch.backends.mps.is_available() if hasattr(torch.backends, "mps") else False
            has_cuda = torch.cuda.is_available()
            
            # Handle Mac-specific issues
            if is_mac:
                # On Mac, bitsandbytes doesn't work, so force disable 4-bit
                if load_in_4bit:
                    logger.warning(
                        "⚠️  4-bit quantization (bitsandbytes) is not supported on Mac. "
                        "Falling back to full precision (float16)."
                    )
                    load_in_4bit = False
                
                # If base model is a bnb-4bit variant, switch to non-quantized version
                if "bnb-4bit" in base_model_name:
                    original_name = base_model_name
                    if "unsloth" in base_model_name:
                        base_model_name = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
                    logger.warning(
                        f"⚠️  Replacing 4-bit base model '{original_name}' "
                        f"with non-quantized '{base_model_name}' for Mac compatibility."
                    )
            
            logger.info(f"Loading base model: {base_model_name}")
            
            # Configure quantization if requested
            if load_in_4bit:
                try:
                    quantization_config = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=torch.float16,
                        bnb_4bit_use_double_quant=True,
                        bnb_4bit_quant_type="nf4",
                    )
                except Exception as e:
                    logger.warning(
                        f"4-bit quantization failed: {e}\n"
                        "Try: pip install bitsandbytes>=0.46.1\n"
                        "Or use --no-4bit flag for full precision"
                    )
                    raise RuntimeError(
                        "4-bit quantization requires bitsandbytes. "
                        "Install with: pip install bitsandbytes>=0.46.1 "
                        "or use --no-4bit flag"
                    ) from e
            else:
                quantization_config = None
            
            # Log device info
            if has_cuda:
                logger.info(f"Using device: CUDA (GPU)")
            elif has_mps:
                logger.info(f"Using device: MPS (Apple Silicon GPU)")
            else:
                logger.info(f"Using device: CPU")
                logger.warning("⚠️  CPU inference is 5-10× slower than GPU. Consider using a machine with CUDA GPU for faster processing.")
            
            # Load base model
            model = AutoModelForCausalLM.from_pretrained(
                base_model_name,
                quantization_config=quantization_config,
                device_map="auto",
                torch_dtype=torch.float16 if not load_in_4bit else None,
                trust_remote_code=True,
            )
            
            # Load tokenizer
            tokenizer = AutoTokenizer.from_pretrained(
                base_model_name,
                trust_remote_code=True,
            )
            
            # Load LoRA adapters
            logger.info("Loading LoRA adapters...")
            model = PeftModel.from_pretrained(model, str(adapter_path))
            model.eval()  # Set to eval mode
            
            logger.info("Model loaded successfully with transformers + PEFT")
            
        except Exception as e:
            raise RuntimeError(f"Failed to load model: {str(e)}") from e
    
    except Exception as e:
        raise RuntimeError(f"Failed to load model with Unsloth: {str(e)}") from e
    
    # Set pad token if not set
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # Cache the model
    _model = model
    _tokenizer = tokenizer
    _adapter_dir = adapter_dir
    
    return model, tokenizer


def generate_doc(
    code: str,
    language: str,
    style: Optional[str] = None,
    max_new_tokens: int = 128,
    model=None,
    tokenizer=None,
) -> Tuple[str, float]:
    """
    Generate documentation for a code snippet.
    
    Args:
        code: Source code to document
        language: Programming language (python, java, javascript)
        style: Documentation style (google, numpy, javadoc, jsdoc) - auto-detected if None
        max_new_tokens: Maximum tokens to generate
        model: Model instance (uses global if None)
        tokenizer: Tokenizer instance (uses global if None)
        
    Returns:
        Tuple of (generated_documentation, latency_seconds)
        
    Raises:
        ValueError: If language is not supported or model not loaded
    """
    global _model, _tokenizer
    
    # Use global model if not provided
    if model is None:
        model = _model
    if tokenizer is None:
        tokenizer = _tokenizer
    
    if model is None or tokenizer is None:
        raise ValueError("Model not loaded. Call load_model() first.")
    
    # Normalize language
    language = language.lower()
    if language not in SYSTEM_PROMPTS:
        raise ValueError(f"Unsupported language: {language}. Must be one of {list(SYSTEM_PROMPTS.keys())}")
    
    # Auto-detect style if not provided
    if style is None:
        style_map = {
            "python": "Google",
            "java": "Javadoc",
            "javascript": "JSDoc",
        }
        style = style_map.get(language, "Standard")
    
    # Map language to file extension for syntax highlighting
    lang_ext = {
        "python": "python",
        "java": "java",
        "javascript": "javascript",
    }
    lang = lang_ext.get(language, language)
    
    # Build chat messages
    messages = [
        {"role": "system", "content": SYSTEM_PROMPTS[language]},
        {
            "role": "user",
            "content": (
                f"Language: {lang}\n"
                f"Documentation style: {style}\n\n"
                f"```{lang}\n{code}\n```\n\n"
                f"Generate documentation for the above code."
            ),
        },
    ]
    
    # Apply chat template
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    
    # Tokenize
    import torch
    device = next(model.parameters()).device
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    
    # Generate
    start_time = time.time()
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            max_length=None,
            temperature=0.1,
            do_sample=True,
            repetition_penalty=1.1,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id,
            early_stopping=True,
        )
    
    latency = time.time() - start_time
    
    # Decode output - only decode the generated tokens, not the input
    input_length = inputs['input_ids'].shape[1]
    generated_tokens = outputs[0][input_length:]
    generated_doc = tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()
    
    # Clean up any remaining special tokens (Qwen-specific)
    generated_doc = generated_doc.replace("<|im_end|>", "").strip()
    generated_doc = generated_doc.replace("<|im_start|>", "").strip()
    
    return generated_doc, latency


def generate_overview(
    project_summary: str,
    max_new_tokens: int = 250,
    model=None,
    tokenizer=None,
) -> Tuple[str, float]:
    """
    Generate a narrative overview for an entire project.
    
    Args:
        project_summary: Structured text description of the project
        max_new_tokens: Maximum tokens to generate
        model: Model instance (uses global if None)
        tokenizer: Tokenizer instance (uses global if None)
        
    Returns:
        Tuple of (generated_overview, latency_seconds)
        
    Raises:
        ValueError: If model not loaded
    """
    global _model, _tokenizer
    
    # Use global model if not provided
    if model is None:
        model = _model
    if tokenizer is None:
        tokenizer = _tokenizer
    
    if model is None or tokenizer is None:
        raise ValueError("Model not loaded. Call load_model() first.")
    
    # Build chat messages with narrative focus
    system_prompt = (
        "You are a technical writer creating engaging project documentation. "
        "Given a summary of a software project's structure and components, "
        "write a compelling overview that explains what the project does, why it exists, "
        "and what problems it solves. Describe the key features and technical approach. "
        "Write 2-3 informative paragraphs that would help developers quickly understand "
        "the project's purpose and value. Be specific and avoid generic filler text."
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                f"Project summary:\n{project_summary}\n\n"
                f"Generate a professional overview paragraph for this project's README."
            ),
        },
    ]
    
    # Apply chat template
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    
    # Tokenize
    import torch
    device = next(model.parameters()).device
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    
    # Generate
    start_time = time.time()
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            max_length=None,
            temperature=0.3,  # Slightly more creative for overview
            do_sample=True,
            repetition_penalty=1.1,
            pad_token_id=tokenizer.eos_token_id,
        )
    
    latency = time.time() - start_time
    
    # Decode output - only decode the generated tokens, not the input
    input_length = inputs['input_ids'].shape[1]
    generated_tokens = outputs[0][input_length:]
    overview = tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()
    
    # Clean up remaining special tokens
    overview = overview.replace("<|im_end|>", "").strip()
    overview = overview.replace("<|im_start|>", "").strip()
    
    return overview, latency
