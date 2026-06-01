from typing import Any

from pydantic import BaseModel, Field, RootModel


class HealthResponse(BaseModel):
    status: str


class UploadMetadata(BaseModel):
    rows: int = Field(ge=0)
    columns: list[str]
    dtypes: dict[str, str]


class StatsResponse(RootModel[dict[str, dict[str, Any]]]):
    pass


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class AskResponse(BaseModel):
    question: str
    answer: str
    model: str


class ErrorResponse(BaseModel):
    detail: str


class PromptBuilderInput(BaseModel):
    question: str = Field(min_length=1)
    stats: dict[str, dict[str, Any]]


class PromptBuilderOutput(BaseModel):
    prompt: str = Field(min_length=1)


class LLMRunnerInput(BaseModel):
    prompt: str = Field(min_length=1)


class LLMRunnerOutput(BaseModel):
    raw_text: str


class ResponseParserInput(BaseModel):
    raw_text: str


class ResponseParserOutput(BaseModel):
    answer: str = Field(min_length=1)
