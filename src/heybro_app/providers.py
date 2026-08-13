"""Provider configuration."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ProviderConfig:
    name: str
    base_url: str
    model: str
    api_key_env: str
    supports_reasoning: bool = False
    reasoning_param: Optional[str] = None
    supports_streaming: bool = True
    system_role: str = "system"
    is_bedrock: bool = False


PROVIDERS = {
    "moonshot": ProviderConfig(
        name="Moonshot (Kimi)",
        base_url="https://api.moonshot.cn/v1",
        model="kimi-k3",
        api_key_env="MOONSHOT_API_KEY",
        supports_reasoning=True,
        reasoning_param="reasoning_effort",
    ),
    "openai": ProviderConfig(
        name="OpenAI",
        base_url="https://api.openai.com/v1",
        model="gpt-4o",
        api_key_env="OPENAI_API_KEY",
        supports_reasoning=True,
        reasoning_param="reasoning_effort",
    ),
    "deepseek": ProviderConfig(
        name="DeepSeek",
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        api_key_env="DEEPSEEK_API_KEY",
        supports_reasoning=True,
        reasoning_param="reasoning_effort",
    ),
    "groq": ProviderConfig(
        name="Groq",
        base_url="https://api.groq.com/openai/v1",
        model="llama-3.3-70b-versatile",
        api_key_env="GROQ_API_KEY",
    ),
    "ollama": ProviderConfig(
        name="Ollama (Local)",
        base_url="http://localhost:11434/v1",
        model="llama3.2",
        api_key_env="OLLAMA_API_KEY",
    ),
    "qwen": ProviderConfig(
        name="Alibaba Qwen",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model="qwen-max",
        api_key_env="DASHSCOPE_API_KEY",
    ),
    "bedrock": ProviderConfig(
        name="AWS Bedrock",
        base_url="",
        model="moonshot.kimi-k2-thinking",
        api_key_env="AWS_ACCESS_KEY_ID",
        is_bedrock=True,
    ),
    "bedrock-mantle": ProviderConfig(
        name="AWS Bedrock",
        base_url="https://bedrock-mantle.us-east-1.api.aws/v1",
        model="moonshot.kimi-k2-thinking",
        api_key_env="AI_API_KEY",
    ),
    "custom": ProviderConfig(
        name="Custom",
        base_url="",
        model="",
        api_key_env="AI_API_KEY",
    ),
}

