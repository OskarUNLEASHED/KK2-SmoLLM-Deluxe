import time

import pytest

from app.chain.direct_stats import answer_direct_stats_question
from app.chain.pipeline import build_oraklet_chain
from app.chain.steps import LLMRunner, PromptBuilder, ResponseParser
from app.config import get_settings
from app.schemas import LLMRunnerOutput, PromptBuilderInput, PromptBuilderOutput


def test_prompt_builder_includes_question_and_stats() -> None:
    prompt = PromptBuilder().invoke(
        PromptBuilderInput(
            question="Which city is warmest?",
            stats={"temp_c": {"mean": 8.3, "max": 12.0}},
        )
    )

    assert "Which city is warmest?" in prompt.prompt
    assert "temp_c" in prompt.prompt
    assert "mean=8.30" in prompt.prompt
    assert "ANSWER:" in prompt.prompt
    assert "average = mean" in prompt.prompt


def test_llm_runner_returns_raw_text_from_generator() -> None:
    def fake_generator(*args: object, **kwargs: object) -> list[dict[str, str]]:
        assert kwargs["return_full_text"] is False
        return [{"generated_text": "Generated answer"}]

    output = LLMRunner(generator=fake_generator).invoke(
        PromptBuilderOutput(prompt="Prompt text\nSvar:")
    )

    assert output.raw_text == "Generated answer"


def test_llm_runner_rejects_empty_model_output() -> None:
    def fake_generator(*args: object, **kwargs: object) -> list[dict[str, str]]:
        return [{"generated_text": ""}]

    runner = LLMRunner(generator=fake_generator)

    with pytest.raises(ValueError, match="The model returned an empty answer."):
        runner.invoke(PromptBuilderOutput(prompt="Prompt text\nSvar:"))


def test_llm_runner_rejects_slow_model_output(monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "model_timeout_seconds", 0.01)

    def slow_generator(*args: object, **kwargs: object) -> list[dict[str, str]]:
        time.sleep(0.05)
        return [{"generated_text": "Too late"}]

    runner = LLMRunner(generator=slow_generator)

    with pytest.raises(RuntimeError, match="longer than 0.01 seconds"):
        runner.invoke(PromptBuilderOutput(prompt="Prompt text\nSvar:"))


def test_response_parser_strips_prompt_echo() -> None:
    parsed = ResponseParser().invoke(
        LLMRunnerOutput(raw_text="Prompt text\nSvar:\nMalmö has the highest mean.")
    )

    assert parsed.answer == "Malmö has the highest mean."


def test_response_parser_rejects_repetitive_answer() -> None:
    runner_output = LLMRunnerOutput(raw_text="Svar:\nSvergar Svergar Svergar Svergar Svergar Svergar Svergar Svergar")

    with pytest.raises(ValueError, match="The model returned a repetitive answer."):
        ResponseParser().invoke(runner_output)


def test_full_chain_uses_pipe_operator() -> None:
    def fake_generator(*args: object, **kwargs: object) -> list[dict[str, str]]:
        return [{"generated_text": "Chain answer"}]

    chain = build_oraklet_chain(LLMRunner(generator=fake_generator))

    result = chain.invoke(
        PromptBuilderInput(
            question="Summarize the dataset.",
            stats={"value": {"count": 2, "mean": 10}},
        )
    )

    assert result.answer
    assert result.answer == "Chain answer"


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("What is the highest Sales value?", "Sales max is 42.50."),
        ("What is the highest sale value?", "Sales max is 42.50."),
        ("Vad är högsta sales value?", "Sales max is 42.50."),
    ],
)
def test_direct_stats_answer_handles_max_aliases(question: str, expected: str) -> None:
    answer = answer_direct_stats_question(
        question,
        {"Sales": {"count": 3.0, "mean": 20.0, "min": 10.0, "max": 42.5}},
    )

    assert answer == expected


@pytest.mark.parametrize(
    "question",
    [
        "Vad är median sale value?",
        "What is the medial sales value?",
    ],
)
def test_direct_stats_answer_handles_median_aliases(question: str) -> None:
    answer = answer_direct_stats_question(
        question,
        {"Sales": {"count": 3.0, "mean": 20.0, "50%": 25.0, "min": 10.0, "max": 42.5}},
    )

    assert answer == "Sales median is 25."


def test_direct_stats_answer_ignores_questions_without_metric() -> None:
    answer = answer_direct_stats_question(
        "Which city is warmest?",
        {"city": {"top": "Malmo", "freq": 1}, "temp_c": {"max": 12.0}},
    )

    assert answer is None


@pytest.mark.parametrize(
    "question",
    [
        "Which Region has the highest Sales value?",
        "Vilken region har högsta Sales value?",
    ],
)
def test_direct_stats_answer_ignores_row_lookup_questions(question: str) -> None:
    answer = answer_direct_stats_question(
        question,
        {"Region": {"top": "South", "freq": 1}, "Sales": {"max": 42.5}},
    )

    assert answer is None
