"""Model metadata and token accounting helpers."""

MAX_TOOL_ROUNDS = 8

CONTEXT_WINDOWS = {
    "kimi-k3": 200_000,
    "kimi-k2-thinking": 200_000,
    "kimi-k2.5": 200_000,
    "kimi-k2.6": 200_000,
    "kimi-k2.7-code": 200_000,
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "gpt-4-turbo": 128_000,
    "o1": 128_000,
    "o1-preview": 128_000,
    "o3-mini": 200_000,
    "deepseek-chat": 64_000,
    "deepseek-reasoner": 64_000,
    "llama-3.3-70b-versatile": 8_192,
    "llama-3.1-8b-instant": 8_192,
    "mixtral-8x7b-32768": 32_768,
    "anthropic.claude-3-5-sonnet-20241022-v2:0": 200_000,
    "anthropic.claude-3-haiku-20240307-v1:0": 200_000,
    "anthropic.claude-3-opus-20240229-v1:0": 200_000,
    "meta.llama3-70b-instruct-v1:0": 8_192,
    "meta.llama3-8b-instruct-v1:0": 8_192,
    "mistral.mistral-large-2402-v1:0": 32_768,
    "amazon.titan-text-express-v1": 8_000,
    "amazon.titan-text-lite-v1": 4_000,
    "qwen-max": 32_768,
    "qwen-plus": 32_768,
    "qwen-turbo": 8_192,
    "llama3.2": 8_192,
    "llama3.1": 8_192,
    "mistral": 8_192,
}

PRICING = {
    "kimi-k3": {"input": 0.71, "output": 2.94, "provider": "moonshot"},
    "kimi-k2-thinking": {"input": 0.71, "output": 2.94, "provider": "moonshot"},
    "kimi-k2.5": {"input": 0.72, "output": 3.60, "provider": "moonshot"},
    "kimi-k2.6": {"input": 0.72, "output": 3.60, "provider": "moonshot"},
    "kimi-k2.7-code": {"input": 0.72, "output": 3.60, "provider": "moonshot"},
    "gpt-4o": {"input": 2.50, "output": 10.00, "provider": "openai"},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60, "provider": "openai"},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00, "provider": "openai"},
    "o1": {"input": 15.00, "output": 60.00, "provider": "openai"},
    "o3-mini": {"input": 1.10, "output": 4.40, "provider": "openai"},
    "deepseek-chat": {"input": 0.14, "output": 0.28, "provider": "deepseek"},
    "deepseek-reasoner": {"input": 0.55, "output": 2.19, "provider": "deepseek"},
    "llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79, "provider": "groq"},
    "llama-3.1-8b-instant": {"input": 0.05, "output": 0.08, "provider": "groq"},
    "mixtral-8x7b-32768": {"input": 0.24, "output": 0.24, "provider": "groq"},
    "anthropic.claude-3-5-sonnet-20241022-v2:0": {"input": 3.00, "output": 15.00, "provider": "bedrock"},
    "anthropic.claude-3-haiku-20240307-v1:0": {"input": 0.25, "output": 1.25, "provider": "bedrock"},
    "anthropic.claude-3-opus-20240229-v1:0": {"input": 15.00, "output": 75.00, "provider": "bedrock"},
    "meta.llama3-70b-instruct-v1:0": {"input": 0.72, "output": 0.72, "provider": "bedrock"},
    "meta.llama3-8b-instruct-v1:0": {"input": 0.22, "output": 0.22, "provider": "bedrock"},
    "mistral.mistral-large-2402-v1:0": {"input": 4.00, "output": 12.00, "provider": "bedrock"},
    "amazon.titan-text-express-v1": {"input": 0.20, "output": 0.60, "provider": "bedrock"},
    "amazon.titan-text-lite-v1": {"input": 0.15, "output": 0.20, "provider": "bedrock"},
    "qwen-max": {"input": 0.72, "output": 1.44, "provider": "qwen"},
    "qwen-plus": {"input": 0.36, "output": 0.72, "provider": "qwen"},
    "qwen-turbo": {"input": 0.072, "output": 0.072, "provider": "qwen"},
    "llama3.2": {"input": 0.0, "output": 0.0, "provider": "ollama"},
    "llama3.1": {"input": 0.0, "output": 0.0, "provider": "ollama"},
    "mistral": {"input": 0.0, "output": 0.0, "provider": "ollama"},
}


def get_pricing(model_id: str) -> dict:
    """Get pricing for a model. Falls back to generic lookup or defaults."""
    if not model_id:
        return {"input": 0.0, "output": 0.0, "provider": "unknown"}

    if model_id in PRICING:
        return PRICING[model_id]

    for key, price in PRICING.items():
        if key in model_id or model_id in key:
            return price

    return {"input": 0.0, "output": 0.0, "provider": "unknown"}


def get_context_window(model_id: str) -> int:
    """Get context window size for a model. Defaults to 8192 if unknown."""
    if not model_id:
        return 8_192

    if model_id in CONTEXT_WINDOWS:
        return CONTEXT_WINDOWS[model_id]

    for key, window in CONTEXT_WINDOWS.items():
        if key in model_id or model_id in key:
            return window

    return 8_192


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return len(text) // 4
