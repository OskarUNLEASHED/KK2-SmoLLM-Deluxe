import logging

from fastapi import FastAPI, File, HTTPException, UploadFile

from app.chain.direct_stats import answer_direct_stats_question
from app.chain.pipeline import MODEL_NAME, oraklet
from app.data import DatasetError, get_stats, load_csv
from app.schemas import (
    AskRequest,
    AskResponse,
    ErrorResponse,
    HealthResponse,
    PromptBuilderInput,
    StatsResponse,
    UploadMetadata,
)

app = FastAPI(title="Cat Data Analyst Deluxe")
logger = logging.getLogger(__name__)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post(
    "/data/upload",
    response_model=UploadMetadata,
    responses={400: {"model": ErrorResponse}},
)
async def upload_data(file: UploadFile = File(...)) -> UploadMetadata:
    if file.filename is None or not file.filename.lower().endswith(".csv"):
        logger.warning("Rejected non-CSV upload: %s", file.filename)
        raise HTTPException(status_code=400, detail="Only CSV files are accepted.")

    try:
        metadata = load_csv(file.file)
    except DatasetError as exc:
        logger.warning("CSV upload failed for %s: %s", file.filename, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    logger.info(
        "Dataset uploaded: filename=%s rows=%s columns=%s",
        file.filename,
        metadata.rows,
        len(metadata.columns),
    )
    return metadata


@app.get(
    "/data/stats",
    response_model=StatsResponse,
    responses={404: {"model": ErrorResponse}},
)
def data_stats() -> StatsResponse:
    stats = get_stats()
    if stats is None:
        logger.warning("Stats requested before dataset upload.")
        raise HTTPException(status_code=404, detail="No dataset has been uploaded.")

    logger.info("Dataset stats requested.")
    return StatsResponse(stats)


@app.post(
    "/ai/ask",
    response_model=AskResponse,
    responses={
        400: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
)
def ask_oraklet(request: AskRequest) -> AskResponse:
    stats = get_stats()
    if stats is None:
        logger.warning("AI question received before dataset upload.")
        raise HTTPException(status_code=400, detail="Upload a dataset before asking questions.")

    direct_answer = answer_direct_stats_question(request.question, stats)
    if direct_answer is not None:
        logger.info("AI question answered directly from stats.")
        return AskResponse(
            question=request.question,
            answer=direct_answer,
            model=MODEL_NAME,
        )

    try:
        result = oraklet.invoke(
            PromptBuilderInput(question=request.question, stats=stats)
        )
    except (RuntimeError, ValueError) as exc:
        logger.error("AI chain failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    logger.info("AI question answered through the model chain.")
    return AskResponse(
        question=request.question,
        answer=result.answer,
        model=MODEL_NAME,
    )
