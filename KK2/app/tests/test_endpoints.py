import pytest
from fastapi.testclient import TestClient

from app.chain.steps import LLMRunner
from app.config import get_settings
from app.data import clear_dataset
from app.main import app
from app.schemas import LLMRunnerOutput, PromptBuilderOutput


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_dataset() -> None:
    clear_dataset()
    yield
    clear_dataset()


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_valid_csv_returns_metadata() -> None:
    response = client.post(
        "/data/upload",
        files={"file": ("weather.csv", b"city,temp_c\nMalmo,8.3\nLund,7.9\n")},
    )

    assert response.status_code == 200
    assert response.json()["rows"] == 2
    assert response.json()["columns"] == ["city", "temp_c"]


def test_upload_rejects_non_csv_file() -> None:
    response = client.post(
        "/data/upload",
        files={"file": ("weather.txt", b"city,temp_c\nMalmo,8.3\n")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only CSV files are accepted."


def test_upload_rejects_empty_csv() -> None:
    response = client.post(
        "/data/upload",
        files={"file": ("empty.csv", b"")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "The uploaded CSV file is empty."


def test_upload_rejects_csv_that_is_too_large(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "max_upload_size_bytes", 12)

    response = client.post(
        "/data/upload",
        files={"file": ("big.csv", b"city,temp_c\nMalmo,8.3\n")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "The uploaded CSV file is too large. Max size is 12 bytes."


def test_upload_rejects_bad_encoding() -> None:
    response = client.post(
        "/data/upload",
        files={"file": ("broken.csv", b"\xff\xfe\x00\x00")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "The uploaded CSV file could not be decoded as text."


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
    client.post(
        "/data/upload",
        files={"file": ("weather.csv", b"city,temp_c\nMalmo,8.3\nLund,7.9\n")},
    )

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
    client.post(
        "/data/upload",
        files={"file": ("weather.csv", b"city,temp_c\nMalmo,8.3\nLund,7.9\n")},
    )

    response = client.post("/ai/ask", json={"question": "Which city is warmest?"})

    assert response.status_code == 502
    assert response.json()["detail"] == "SmolLM took longer than 30 seconds to answer."


def test_ask_answers_direct_stats_question_without_llm() -> None:
    client.post(
        "/data/upload",
        files={"file": ("sales.csv", b"Sales,Region\n10,North\n42.5,South\n")},
    )

    response = client.post("/ai/ask", json={"question": "What is the highest sale value?"})

    assert response.status_code == 200
    assert response.json() == {
        "question": "What is the highest sale value?",
        "answer": "Sales max is 42.50.",
        "model": "HuggingFaceTB/SmolLM2-360M-Instruct",
    }
