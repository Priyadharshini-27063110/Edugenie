# EduGenie

EduGenie is a lightweight learning companion for clear explanations, topic quizzes, study summaries, learning paths, and personalized next steps. The interface is served directly by FastAPI; no frontend build step is needed.

## Run locally

```bash
python -m pip install -r requirements.txt
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000`. Without an API key, the app runs in local mode with built-in example answers and study content.

## Optional AI provider

Set an OpenAI-compatible API key to enable generated explanations, quizzes, summaries, learning paths, and recommendations:

```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_MODEL="gpt-4o-mini"
# Optional, for an OpenAI-compatible provider:
export OPENAI_BASE_URL="https://your-provider.example/v1"
uvicorn main:app --reload
```

The key stays on the server and is never sent to the browser. If the provider is unavailable, EduGenie falls back to its local responses.

## API

- `POST /api/ask` with `{"question":"Which is the largest ocean?"}`
- `POST /api/quiz` with `{"topic":"The Pythagorean theorem","count":5}`
- `POST /api/learning-path` with `{"topic":"SQL","weeks":4}`
- `POST /api/summarize` with `{"text":"..."}`
- `POST /api/recommend` with `{"topic":"SQL","level":"new","goal":"Query a database"}`
- `GET /api/health` reports whether the app is in `local` or `cloud` mode.

Interactive API documentation is available at `/docs` while the server is running.