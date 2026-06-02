# KK2 todo / notes

Need to not overthink this. First get the boring basic version working, then fix the nice stuff after.
Writing on the train so I might miss something will refine stuff when home

## setup first 

- go into `KK2/` - done
- run `uv sync` - done
- check nothing weird happens with the deps- done
- `.env` should NOT go to git -done
- keep `.env.example` because that one is ok -done
- check gitignore ignores the example assignment + extra rules stuff -done

## start the api -done

- done: `app/main.py` already exists
- done: FastAPI app is created there
- done: `/health` exists and returns ok
- ran: 

```bash
uv run uvicorn app.main:app --reload 
```

- open `http://127.0.0.1:8000/docs` 
- if Swagger works then move tf on 

## schemas probably needed -done

Put these in `app/schemas.py`.

- upload response
- stats response
- ask request
- ask response
- stuff for chain input/output

Can rename/fix later if the names feel bad.

## csv/data stuff

Need an `app/data.py`.

- store uploaded dataframe in memory for now
- only allow csv
- load with pandas
- get rows / columns / dtypes
- make a stats helper, probably using `describe()`
- remember to handle empty csv because that will definitely happen in tests

## endpoints for data

- `POST /data/upload`
- `GET /data/stats`

Things to handle:

- no file uploaded yet
- wrong file type
- broken csv
- empty csv

Do not spend forever making perfect error messages at first. Just make them understandable.

## runnable chain stuff

Need to copy the idea from the lesson pattern.

- `Runnable`
- `RunnableSequence`
- make `|` work

Keep it simple. I only need enough for this assignment.

## fake llm first

Do this before real SmolLM or it will get annoying.

- `PromptBuilder`
- fake `LLMRunner`
- `ResponseParser`

Chain should look like:

```python
oraklet = PromptBuilder() | LLMRunner() | ResponseParser()
```

Fake runner can just return some boring text. The point is to test the flow.

## ask endpoint

Need `POST /ai/ask`.

- should fail if no dataset exists yet
- get stats/context from the current dataframe
- send question + stats into the chain
- return question, answer and model name

Rough shape:

```json
{
  "question": "...",
  "answer": "...",
  "model": "HuggingFaceTB/SmolLM2-135M-Instruct"
}
```

## tests before real model

Do these while LLM is still fake/mocked:

- health endpoint
- upload good csv
- upload bad file
- stats with no dataset
- chain parts one by one
- `/ai/ask` with mocked `LLMRunner`

This should save time later.

## extra test chilling maybe

Potential tests for fun tests to implement

- automated api tests with `TestClient`
- unit tests for the small chain parts
- integration test for upload csv -> ask question
- regression tests for bugs I fix later
- smoke test for `/health`
- empty csv upload
- broken csv upload
- weird column names in csv
- csv with only one row
- very short question to `/ai/ask`
- too long question to `/ai/ask`
- `/ai/ask` with mocked model output
- model returns empty text
- model crashes and api returns useful error
- parser removes prompt junk from model answer
- stats after uploading new csv replaces old dataset
- check response json has the expected fields, not only status code
- maybe test docs examples / curl examples if I add them
- maybe manual Swagger check before final commit

Keep tests in `app/tests/` for now 

## real SmolLM

After the fake version works, swap in:

```python
transformers.pipeline(
    "text-generation",
    model="HuggingFaceTB/SmolLM2-135M-Instruct",
)
```

Need to keep model loading separate so tests do not actually load it.

Also handle:

- empty output
- model crash / exception
- weird extra text in output

## cleanup / VG stuff maybe

If there is time:

- file size limit
- nicer csv errors
- better prompt
- parser strips prompt junk from the answer
- some logging
- type hints where missing

Not first priority unless the base version works.

## README

Needs:

- install
- run api
- run tests
- curl examples
- limitations / assumptions

ill try to keep it short

## reflektion projection injection

Stuff att nämna:

- `.env` and secrets
- upload risks
- prompt injection
- GDPR / personal data in csv files
- hallucinations
- bias
- small model limitations
- why the chain is nicer than one giant function
- biggest problem I hit and how I fixed it

## final before commit

Run:

```bash
uv run pytest app/tests/ -v
```

Sen:

- kör API 
- klicka runt i Swagger
- check git status
- make sure `.env` is not there
- make sure example assignment and extra rules are not there

Main rule: fake model first, real model after. Annars blir jag dizzy
