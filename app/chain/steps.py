from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from collections.abc import Callable
from typing import Any

from app.chain.runnable import Runnable
from app.config import get_settings
from app.schemas import (
    LLMRunnerOutput,
    PromptBuilderInput,
    PromptBuilderOutput,
    ResponseParserOutput,
)


DEFAULT_MODEL_NAME = get_settings().model_name
logger = logging.getLogger(__name__)

TextGenerator = Callable[..., list[dict[str, Any]]]


class PromptBuilder(Runnable[PromptBuilderInput, PromptBuilderOutput]):
    """Builds the instruction prompt that is sent to the data analyst model."""

    def invoke(self, input_data: PromptBuilderInput) -> PromptBuilderOutput:
        stats_text = self._format_stats(input_data.stats)
        prompt = f"""
You are Cat Data Analyst Deluxe, a careful data assistant.
Use ONLY the values in STATS.
Do not calculate new numbers.
For direct numeric questions, answer with the exact metric from STATS.
For summary questions, briefly describe the columns and the clearest patterns in STATS.
Answer in max 4 short lines.

Rules:
- average = mean
- median = 50%
- highest/largest = max
- lowest/smallest = min
- always mention column name and metric name
- do not mention raw rows because STATS does not contain raw rows
- if the needed value is missing, say: "The uploaded stats do not contain that value."

STATS:
{stats_text}

QUESTION:
{input_data.question}

ANSWER:
""".strip()

        return PromptBuilderOutput(prompt=prompt)

    @staticmethod
    def _format_stats(stats: dict[str, dict[str, Any]]) -> str:
        if not stats:
            return "No stats available."

        lines: list[str] = []
        for column, metrics in stats.items():
            metric_parts = PromptBuilder._useful_metric_parts(metrics)
            if metric_parts:
                lines.append(f"- {column}: {', '.join(metric_parts)}")

        return "\n".join(lines)

    @staticmethod
    def _useful_metric_parts(metrics: dict[str, Any]) -> list[str]:
        preferred_metrics = ("count", "mean", "50%", "min", "max", "top", "freq")
        parts: list[str] = []

        for metric in preferred_metrics:
            value = metrics.get(metric)
            if value == "" or value is None:
                continue

            parts.append(f"{metric}={PromptBuilder._format_value(value)}")

        return parts

    @staticmethod
    def _format_value(value: Any) -> str:
        if isinstance(value, float):
            return f"{value:.2f}"

        return str(value)


class LLMRunner(Runnable[PromptBuilderOutput, LLMRunnerOutput]):
    """Runs SmolLM through transformers.pipeline."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        generator: TextGenerator | None = None,
    ) -> None:
        self.model_name = model_name
        self._generator = generator

    def invoke(self, input_data: PromptBuilderOutput) -> LLMRunnerOutput:
        settings = get_settings()
        try:
            output = self._generate_with_timeout(
                prompt=input_data.prompt,
                timeout_seconds=settings.model_timeout_seconds,
                generation_kwargs={
                    "max_new_tokens": settings.max_new_tokens,
                    "do_sample": settings.do_sample,
                    "repetition_penalty": settings.repetition_penalty,
                    "no_repeat_ngram_size": settings.no_repeat_ngram_size,
                    "clean_up_tokenization_spaces": False,
                    "return_full_text": False,
                },
            )
        except RuntimeError as exc:
            logger.error("SmolLM generation failed: %s", exc)
            raise
        except Exception as exc:
            logger.error("SmolLM generation failed: %s", exc)
            raise RuntimeError("SmolLM could not generate an answer.") from exc

        raw_text = self._extract_generated_text(output)
        if not raw_text.strip():
            logger.warning("SmolLM returned an empty answer.")
            raise ValueError("The model returned an empty answer.")

        return LLMRunnerOutput(raw_text=raw_text)

    def _generate_with_timeout(
        self,
        prompt: str,
        timeout_seconds: float,
        generation_kwargs: dict[str, Any],
    ) -> list[dict[str, Any]]:
        generator = self._get_generator()
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(generator, prompt, **generation_kwargs)

        try:
            return future.result(timeout=timeout_seconds)
        except TimeoutError as exc:
            future.cancel()
            raise RuntimeError(
                f"SmolLM took longer than {timeout_seconds:g} seconds to answer."
            ) from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _get_generator(self) -> TextGenerator:
        if self._generator is None:
            from transformers import pipeline

            self._generator = pipeline(
                "text-generation",
                model=self.model_name,
            )

        return self._generator

    @staticmethod
    def _extract_generated_text(output: Any) -> str:
        if not isinstance(output, list) or not output:
            return ""

        first_result = output[0]
        if not isinstance(first_result, dict):
            return ""

        generated_text = first_result.get("generated_text", "")
        return generated_text if isinstance(generated_text, str) else ""


class ResponseParser(Runnable[LLMRunnerOutput, ResponseParserOutput]):
    """Extracts a clean answer from the model output."""

    def invoke(self, input_data: LLMRunnerOutput) -> ResponseParserOutput:
        raw_text = input_data.raw_text.strip()
        if not raw_text:
            raise ValueError("The model returned an empty answer.")

        answer = raw_text.rsplit("ANSWER:", maxsplit=1)[-1]
        answer = answer.rsplit("Svar:", maxsplit=1)[-1].strip()
        if not answer:
            raise ValueError("The model returned an empty answer.")
        if self._looks_repetitive(answer):
            raise ValueError("The model returned a repetitive answer.")

        return ResponseParserOutput(answer=answer)

    @staticmethod
    def _looks_repetitive(answer: str) -> bool:
        words = answer.replace("\n", " ").split()
        if len(words) < 8:
            return False

        unique_ratio = len(set(words)) / len(words)
        return unique_ratio < 0.35
