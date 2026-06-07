# KK2 - Oraklet

Si no tienes ganas de mirar datos e interpretarlos, y tampoco quieres pagar tokens caros,
entonces llegaste al lugar correcto.

O si estas aqui para corregir, hola Johan.

O si estas aqui para copiar mi trabajo, no eres bienvenido D:



## Que hace

Esta es una API pequena para subir un dataset y hacer preguntas sobre el.

El proyecto esta construido alrededor de cuatro ideas:

- `FastAPI` es la recepcion
- `Pandas` lee y resume el CSV
- `SmolLM` responde preguntas en lenguaje natural
- Los pasos `Runnable` conectan todo

Para preguntas simples de estadisticas, la app tambien puede responder directamente desde Pandas sin depender del modelo.

La cadena se ve asi:

```text
PromptBuilder
     |
     v
LLMRunner
     |
     v
ResponseParser
```

O, en el estilo real del proyecto:

```python
oraklet = PromptBuilder() | LLMRunner() | ResponseParser()
```



## How to get going

Desde la carpeta `KK2`, instala todo:

```powershell
uv sync
```

Despues inicia la API:

```powershell
uv run uvicorn app.main:app --reload
```

Tambien hay un archivo de atajo que pense que algunas personas podrian encontrar conveniente:

```text
start_server.py
```

Abre ese archivo y haz click en el boton verde de DataSpell/PyCharm.

Despues entra aqui:

```text
http://127.0.0.1:8000/docs
```

Swagger es donde puedes probar la API si, como yo, no te gusta escribir curl a mano.



## Endpoints

La API tiene estos endpoints:

```text
GET  /health
POST /data/upload
GET  /data/stats
POST /ai/ask
```

`/health` solo revisa que la app este viva.

`/data/upload` recibe un archivo CSV.

`/data/stats` devuelve el resultado de Pandas `describe()`.

`/ai/ask` recibe una pregunta y devuelve una respuesta.



## Example Spellbook

Subir un CSV:

```powershell
curl -X POST "http://127.0.0.1:8000/data/upload" -F "file=@data.csv"
```

Hacer una pregunta:

```powershell
curl -X POST "http://127.0.0.1:8000/ai/ask" `
  -H "Content-Type: application/json" `
  -d "{ \"question\": \"What is the highest sale value?\" }"
```

Ejemplo de respuesta:

```json
{
  "question": "What is the highest sale value?",
  "answer": "Sales max is 2294600.",
  "model": "HuggingFaceTB/SmolLM2-360M-Instruct"
}
```



## Tests

Ejecuta:

```powershell
uv run pytest app/tests/ -v
```

Los tests cubren los endpoints, la cadena Runnable, el comportamiento del modelo mockeado, respuestas vacias del modelo y algunos bugs que aparecieron mientras construia esto.



## Limits

La app rechaza CSVs demasiado grandes antes de que Pandas los lea. El limite esta en `app/config.py`.

La llamada al modelo tambien tiene timeout. Si SmolLM tarda demasiado o devuelve texto vacio, la API responde con error en vez de fingir que tiene una respuesta buena.



---



# English Version

If you cba to look and interpret data and also don't want to pay for expensive tokens.
Then you've found the right place.

Or if you are here to grade, hello Johan.

Or if you are here to copy my work, you are not welcome D:



## What It Does

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
