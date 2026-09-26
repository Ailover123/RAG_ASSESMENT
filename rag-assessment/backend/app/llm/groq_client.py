from typing import Dict, Generator, List, Optional

from app.config import settings
from app.llm.prompt_templates import build_rag_prompt


DEFAULT_MODEL = "openai/gpt-oss-120b"


class GroqClient:
    """Wrapper client for interacting with Groq LLM API with streaming support."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize Groq client.

        Args:
            api_key: Groq API key (defaults to settings.GROQ_API_KEY).
            model: Target model identifier (defaults to settings.GROQ_MODEL).
        """
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.GROQ_MODEL or DEFAULT_MODEL

        if not self.api_key:
            raise ValueError(
                "GROQ_API_KEY is not configured. Set it in the environment or .env file."
            )

        try:
            import groq
            from groq import Groq
        except ImportError as exc:
            raise RuntimeError(
                "The groq Python package is not installed. Install backend requirements first."
            ) from exc

        self.client = Groq(api_key=self.api_key)
        self._auth_error = getattr(groq, "AuthenticationError", ())
        self._rate_limit_error = getattr(groq, "RateLimitError", ())

    def _completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 1024,
        stream: bool = False,
    ):
        try:
            return self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
            )
        except self._auth_error as exc:
            raise RuntimeError(
                "Groq authentication failed. Check that GROQ_API_KEY is valid."
            ) from exc
        except self._rate_limit_error as exc:
            raise RuntimeError(
                "Groq rate limit exceeded. Please retry after the limit resets."
            ) from exc
        except Exception as exc:
            raise RuntimeError(f"Groq API request failed: {exc}") from exc

    def generate(
        self,
        query: str,
        retrieved_chunks: List[dict],
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> str:
        """
        Generate a non-streaming RAG response from retrieved context chunks.

        Args:
            query: User question.
            retrieved_chunks: Retrieved context chunks with text/source/page fields.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in response.

        Returns:
            str: Full generated response text.
        """
        messages = build_rag_prompt(query, retrieved_chunks)
        response = self._completion(messages, temperature, max_tokens)
        try:
            return response.choices[0].message.content or ""
        except (AttributeError, IndexError) as exc:
            raise RuntimeError("Groq API returned an unexpected response shape.") from exc

    def generate_stream(
        self,
        query: str,
        retrieved_chunks: List[dict],
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> Generator[str, None, None]:
        """Stream a RAG response, yielding text deltas as they arrive."""
        messages = build_rag_prompt(query, retrieved_chunks)
        stream = self._completion(messages, temperature, max_tokens, stream=True)
        try:
            for event in stream:
                delta = event.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as exc:
            raise RuntimeError(f"Groq API streaming failed: {exc}") from exc

    def generate_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> str:
        """Compatibility helper for callers that already built chat messages."""
        response = self._completion(messages, temperature, max_tokens)
        try:
            return response.choices[0].message.content or ""
        except (AttributeError, IndexError) as exc:
            raise RuntimeError("Groq API returned an unexpected response shape.") from exc
