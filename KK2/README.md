# Cat Data Analyst Deluxe

This cat AI will read your .csv file and answer your burning questions!


## What He Does

This is a small API for uploading a dataset and asking questions about it.

The project is built around four ideas:

- `FastAPI` is the front desk
- `Pandas` reads and summarizes the CSV
- `SmolLM` answers natural language questions
- `Runnable` steps connect everything together

For simple stats questions, the app can also answer directly from Pandas without depending on the model.

The chain looks like this:

```text
PromptBuilder
     |
     v
LLMRunner
     |
     v
ResponseParser
```

Or, in the actual project style:

```python
oraklet = PromptBuilder() | LLMRunner() | ResponseParser()
```



## How to boot

From the `KK2` folder, install everything:

```powershell
uv sync
```

Then start the API:

```powershell
uv run uvicorn app.main:app --reload
```

If you want to open a simple desktop window:

```powershell
uv run ui
```

There is also a shortcut file that I thought some people might find convenient:

```text
start_server.py
```

Open it and click the green run button in DataSpell/PyCharm.

Then go here:

```text
http://127.0.0.1:8000/docs
```

Swagger is where you can test the API if, like me, you dislike writing curl by hand.



## Endpoints

The API has these endpoints:

```text
GET  /health
POST /data/upload
GET  /data/stats
POST /ai/ask
```

`/health` just checks that the app is alive.

`/data/upload` takes a CSV file.

`/data/stats` returns the Pandas `describe()` output.

`/ai/ask` takes a question and returns an answer.



## Example Spellbook

Upload a CSV:

```powershell
curl -X POST "http://127.0.0.1:8000/data/upload" -F "file=@data.csv"
```

Ask a question:

```powershell
curl -X POST "http://127.0.0.1:8000/ai/ask" `
  -H "Content-Type: application/json" `
  -d "{ \"question\": \"What is the highest sale value?\" }"
```

Example answer:

```json
{
  "question": "What is the highest sale value?",
  "answer": "Sales max is 2294600.",
  "model": "HuggingFaceTB/SmolLM2-360M-Instruct"
}
```



## Tests

Run:

```powershell
uv run pytest app/tests/ -v
```

The tests cover the endpoints, the Runnable chain, mocked model behavior, empty model answers, and a few bug fixes that appeared while building this.



## Limits

The app rejects oversized CSV files before Pandas reads them. The limit lives in `app/config.py`.

The model call also has a timeout. If SmolLM is too slow or returns empty text, the API returns an error instead of pretending it has a good answer.
