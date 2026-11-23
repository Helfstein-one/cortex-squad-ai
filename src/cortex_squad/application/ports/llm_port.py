"""LLM Port interface definition."""

from typing import Any, Protocol


class LLMPort(Protocol):
    """Port for interacting with language models (local or cloud)."""

    async def generate_response(
        self,
        persona: str,
        system_prompt: str,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        **kwargs: Any,
    ) -> str:
        """Generates a text completion given the persona context."""
        ...
