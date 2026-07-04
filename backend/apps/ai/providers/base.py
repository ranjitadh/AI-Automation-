from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ProviderResponse:
    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    latency_ms: int = 0
    provider: str = ''
    error: Optional[str] = None


class BaseAIProvider(ABC):
    provider_name: str = ''

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str,
                 temperature: float = 0.3, max_tokens: int = 4096,
                 response_schema: Optional[dict] = None,
                 model: Optional[str] = None) -> ProviderResponse:
        ...

    @abstractmethod
    def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        ...

    def get_model_name(self, requested: Optional[str] = None) -> str:
        return requested or self.default_model

    @property
    @abstractmethod
    def default_model(self) -> str:
        ...
