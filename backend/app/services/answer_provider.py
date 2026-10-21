"""Answer-generation providers.

The mock provider deliberately reuses retrieved text instead of inventing facts.
A real AI provider can implement the same interface in a later stage.
"""

from collections.abc import Sequence
from typing import Protocol

from app.services.retrieval import SearchResult


class AnswerProvider(Protocol):
    """Interface implemented by answer-generation providers."""

    def generate_answer(self, question: str, passages: Sequence[SearchResult]) -> str:
        """Generate an answer grounded in the supplied passages."""


class MockAnswerProvider:
    """Return retrieved evidence verbatim without external API calls."""

    def generate_answer(self, question: str, passages: Sequence[SearchResult]) -> str:
        """Present the matched passages as evidence, without claiming to summarize them."""
        del question  # The mock provider does not interpret or infer an answer.
        evidence = [
            f'- From "{passage.filename}", page {passage.page_number}:\n  {passage.text.strip()}'
            for passage in passages
        ]
        return "Relevant evidence found in your documents:\n\n" + "\n\n".join(evidence)
