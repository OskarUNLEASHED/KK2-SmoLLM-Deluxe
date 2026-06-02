from app.chain.pipeline import build_oraklet_chain
from app.chain.steps import LLMRunner, PromptBuilder, ResponseParser
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
        return [{"generated_text": "Generated answer"}]

    output = LLMRunner(generator=fake_generator).invoke(
        PromptBuilderOutput(prompt="Prompt text\nSvar:")
    )

    assert output.raw_text == "Generated answer"


def test_llm_runner_rejects_empty_model_output() -> None:
    def fake_generator(*args: object, **kwargs: object) -> list[dict[str, str]]:
        return [{"generated_text": ""}]

    runner = LLMRunner(generator=fake_generator)

    try:
        runner.invoke(PromptBuilderOutput(prompt="Prompt text\nSvar:"))
    except ValueError as exc:
        assert str(exc) == "The model returned an empty answer."
    else:
        raise AssertionError("Expected ValueError for empty model output.")


def test_response_parser_strips_prompt_echo() -> None:
    parsed = ResponseParser().invoke(
        LLMRunnerOutput(raw_text="Prompt text\nSvar:\nMalmö has the highest mean.")
    )

    assert parsed.answer == "Malmö has the highest mean."


def test_response_parser_rejects_repetitive_answer() -> None:
    runner_output = LLMRunnerOutput(raw_text="Svar:\nSvergar Svergar Svergar Svergar Svergar Svergar Svergar Svergar")

    try:
        ResponseParser().invoke(runner_output)
    except ValueError as exc:
        assert str(exc) == "The model returned a repetitive answer."
    else:
        raise AssertionError("Expected ValueError for repetitive model output.")


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
