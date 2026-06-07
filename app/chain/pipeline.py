from app.chain.runnable import Runnable
from app.chain.steps import DEFAULT_MODEL_NAME, LLMRunner, PromptBuilder, ResponseParser
from app.schemas import PromptBuilderInput, ResponseParserOutput


def build_oraklet_chain(
    llm_runner: LLMRunner | None = None,
) -> Runnable[PromptBuilderInput, ResponseParserOutput]:
    return PromptBuilder() | (llm_runner or LLMRunner()) | ResponseParser()


oraklet = build_oraklet_chain()

MODEL_NAME = DEFAULT_MODEL_NAME
