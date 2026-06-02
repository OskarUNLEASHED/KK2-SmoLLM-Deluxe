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
    assert "mean=8.3" in prompt.prompt
    assert "Svar:" in prompt.prompt


def test_fake_llm_runner_returns_raw_text() -> None:
    output = LLMRunner().invoke(PromptBuilderOutput(prompt="Prompt text\nSvar:"))

    assert "testsvar" in output.raw_text
    assert "Prompt text" in output.raw_text


def test_response_parser_strips_prompt_echo() -> None:
    parsed = ResponseParser().invoke(
        LLMRunnerOutput(raw_text="Prompt text\nSvar:\nMalmö has the highest mean.")
    )

    assert parsed.answer == "Malmö has the highest mean."


def test_full_chain_uses_pipe_operator() -> None:
    chain = build_oraklet_chain()

    result = chain.invoke(
        PromptBuilderInput(
            question="Summarize the dataset.",
            stats={"value": {"count": 2, "mean": 10}},
        )
    )

    assert result.answer
    assert "testsvar" in result.answer
