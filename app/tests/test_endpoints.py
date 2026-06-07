import pytest
from fastapi.testclient import TestClient

from app.chain.steps import LLMRunner
from app.config import get_settings
from app.data import clear_dataset
from app.main import app
from app.schemas import LLMRunnerOutput, PromptBuilderOutput


client = TestClient(app)


VALID_WEATHER_CSV = b"city,temp_c\nMalmo,8.3\nLund,7.9\n"
VALID_SALES_CSV = b"Sales,Region\n10,North\n42.5,South\n20,West\n"


@pytest.fixture(autouse=True)
def reset_dataset() -> None:
    clear_dataset()
    yield
    clear_dataset()


def upload_csv(
    filename: str = "weather.csv",
    content: bytes = VALID_WEATHER_CSV,
):
    return client.post(
        "/data/upload",
        files={"file": (filename, content)},
    )


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_valid_csv_returns_metadata() -> None:
    response = upload_csv()

    assert response.status_code == 200
    assert response.json()["rows"] == 2
    assert response.json()["columns"] == ["city", "temp_c"]


@pytest.mark.parametrize(
    ("filename", "content", "expected_detail"),
    [
        ("weather.txt", b"city,temp_c\nMalmo,8.3\n", "Only CSV files are accepted."),
        ("empty.csv", b"", "The uploaded CSV file is empty."),
        ("broken.csv", b"\xff\xfe\x00\x00", "The uploaded CSV file could not be decoded as text."),
    ],
)
def test_upload_rejects_invalid_files(
    filename: str,
    content: bytes,
    expected_detail: str,
) -> None:
    response = upload_csv(filename=filename, content=content)

    assert response.status_code == 400
    assert response.json()["detail"] == expected_detail


def test_upload_rejects_csv_that_is_too_large(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "max_upload_size_bytes", 12)

    response = upload_csv(filename="big.csv", content=VALID_WEATHER_CSV)

    assert response.status_code == 400
    assert response.json()["detail"] == "The uploaded CSV file is too large. Max size is 12 bytes."


def test_stats_without_dataset_returns_404() -> None:
    response = client.get("/data/stats")

    assert response.status_code == 404
    assert response.json()["detail"] == "No dataset has been uploaded."


def test_ask_without_dataset_returns_400() -> None:
    response = client.post("/ai/ask", json={"question": "What is in the data?"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Upload a dataset before asking questions."


def test_ask_uses_chain_with_mocked_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_invoke(
        self: LLMRunner,
        input_data: PromptBuilderOutput,
    ) -> LLMRunnerOutput:
        assert "temp_c" in input_data.prompt
        return LLMRunnerOutput(raw_text="Svar:\nMalmo has the highest temperature.")

    monkeypatch.setattr(LLMRunner, "invoke", fake_invoke)
    upload_csv()

    response = client.post("/ai/ask", json={"question": "Which city is warmest?"})

    assert response.status_code == 200
    assert response.json() == {
        "question": "Which city is warmest?",
        "answer": "Malmo has the highest temperature.",
        "model": "HuggingFaceTB/SmolLM2-360M-Instruct",
    }


def test_ask_returns_502_when_model_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_invoke(
        self: LLMRunner,
        input_data: PromptBuilderOutput,
    ) -> LLMRunnerOutput:
        raise RuntimeError("SmolLM took longer than 30 seconds to answer.")

    monkeypatch.setattr(LLMRunner, "invoke", fake_invoke)
    upload_csv()

    response = client.post("/ai/ask", json={"question": "Which city is warmest?"})

    assert response.status_code == 502
    assert response.json()["detail"] == "SmolLM took longer than 30 seconds to answer."


@pytest.mark.parametrize(
    ("question", "expected_answer"),
    [
        ("What is the highest sale value?", "Sales max is 42.50."),
        ("Vad är högsta sales value?", "Sales max is 42.50."),
        ("Vad är median sale value?", "Sales median is 20."),
        ("What is the medial sales value?", "Sales median is 20."),
    ],
)
def test_ask_answers_direct_stats_questions_without_llm(
    question: str,
    expected_answer: str,
) -> None:
    upload_csv(filename="sales.csv", content=VALID_SALES_CSV)

    response = client.post("/ai/ask", json={"question": question})

    assert response.status_code == 200
    assert response.json() == {
        "question": question,
        "answer": expected_answer,
        "model": "HuggingFaceTB/SmolLM2-360M-Instruct",
    }
