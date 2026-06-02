from __future__ import annotations

from typing import Any

from app.chain.runnable import Runnable
from app.schemas import (
    LLMRunnerOutput,
    PromptBuilderInput,
    PromptBuilderOutput,
    ResponseParserOutput,
)


DEFAULT_MODEL_NAME = "HuggingFaceTB/SmolLM2-135M-Instruct"


class PromptBuilder(Runnable[PromptBuilderInput, PromptBuilderOutput]):
    """Builds the instruction prompt that is sent to Oraklet."""

    def invoke(self, input_data: PromptBuilderInput) -> PromptBuilderOutput:
        stats_text = self._format_stats(input_data.stats)
        prompt = f"""
Du är Oraklet, en försiktig dataassistent för ett FastAPI-projekt i KK2.
Svara på svenska om användaren frågar på svenska, annars på samma språk som frågan.
Använd bara statistiken nedan. Om statistiken inte räcker ska du säga det tydligt.

Dataset-statistik:
{stats_text}

Fråga:
{input_data.question}

Svar:
""".strip()

        return PromptBuilderOutput(prompt=prompt)

    @staticmethod
    def _format_stats(stats: dict[str, dict[str, Any]]) -> str:
        if not stats:
            return "Ingen statistik finns tillgänglig."

        lines: list[str] = []
        for column, metrics in stats.items():
            metric_parts = [
                f"{metric}={value}"
                for metric, value in metrics.items()
                if value != ""
            ]
            lines.append(f"- {column}: {', '.join(metric_parts)}")

        return "\n".join(lines)


class LLMRunner(Runnable[PromptBuilderOutput, LLMRunnerOutput]):
    """Temporary fake LLM runner.

    The real SmolLM integration can replace this class without changing the
    prompt builder, parser, endpoint, or tests around the chain shape.
    """

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME) -> None:
        self.model_name = model_name

    def invoke(self, input_data: PromptBuilderOutput) -> LLMRunnerOutput:
        return LLMRunnerOutput(
            raw_text=(
                f"{input_data.prompt}\n"
                "Det här är ett testsvar från den mockade SmolLM-köraren. "
                "Byt ut LLMRunner mot transformers.pipeline när basflödet fungerar."
            )
        )


class ResponseParser(Runnable[LLMRunnerOutput, ResponseParserOutput]):
    """Extracts a clean answer from the model output."""

    def invoke(self, input_data: LLMRunnerOutput) -> ResponseParserOutput:
        raw_text = input_data.raw_text.strip()
        if not raw_text:
            raise ValueError("The model returned an empty answer.")

        answer = raw_text.rsplit("Svar:", maxsplit=1)[-1].strip()
        if not answer:
            raise ValueError("The model returned an empty answer.")

        return ResponseParserOutput(answer=answer)
