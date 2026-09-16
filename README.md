# AllanClear

AllanClear is a RAG (Retrieval-Augmented Generation) chatbot that answers questions about Allan Gray investments, grounded in Allan Gray's own published articles and fund fact sheets.

> This is an educational/demo project and is not affiliated with, endorsed by, or associated with Allan Gray Investment Management in any way.

<!-- TODO: add a screenshot or GIF of the chat UI here -->
<!-- ![AllanClear chat UI](docs/screenshot.png) -->

## How it works

AllanClear retrieves relevant source material before generating an answer, rather than relying on the LLM's own knowledge.

1. **Scrape** — [scraper.py](rag-app/src/rag_app/pipeline/scraper.py) crawls the allangray.co.za sitemap for articles and writes one JSON file per article to `rag-app/data/articles/`.
2. **Chunk, embed & store** — [article_ingest.py](rag-app/src/rag_app/pipeline/article_ingest.py) splits articles into overlapping chunks (1950 chars, 300 overlap) with LangChain's `RecursiveCharacterTextSplitter`, prepends title/author/date/category to each chunk, embeds with OpenAI's `text-embedding-3-small`, and upserts to a Pinecone index. [pdf_ingest.py](rag-app/src/rag_app/pipeline/pdf_ingest.py) does the same for fund fact sheets (Docling PDF → Markdown, split by section, Claude contextual description, embed, upsert). Chunk ids are deterministic, so re-running overwrites rather than duplicates.
3. **Query** — on each user message, [search.py](rag-app/src/rag_app/search.py) embeds the query, retrieves the top 20 candidates from Pinecone plus a fund-fact-sheet-only top 10 and, for each fund named in the query (detected against a fixed alias table in [funds.py](rag-app/src/rag_app/funds.py)), a fund-filtered top 3, caps article chunks at two per article, scores the union with Pinecone's hosted `bge-reranker-v2-m3` reranker and fuses the two rankings (reciprocal rank fusion) to keep the best 10 (up to 20 when the query names several funds). If the rerank call fails, the dense order is used as-is.
4. **Respond** — [server.py](rag-app/src/rag_app/server.py) streams a response from Claude (Anthropic) back to the client over Server-Sent Events, followed by the sources the answer actually drew on (the model reports which numbered context entries it used; that line is stripped before display).

**Multi-turn query rewrite** — when a conversation has more than one turn, the backend first rewrites the latest user message into a standalone query (via an LLM call over the last few turns) before running retrieval, so follow-up questions ("what about the second one?") and complaints ("you ignored me") resolve to what the user actually asked, without the user restating context. If the rewrite call fails, the raw message is used.

**Observability** — LLM and retrieval calls are instrumented with OpenInference and traced via Arize, so a full request (rewrite → retrieval → generation) can be inspected end to end. Enabled only when the Arize keys are set.

**Access** — the app is private. Every API request must carry a single shared access code as a bearer token; the frontend asks for it once and remembers it. There are no user accounts. See [Deployment](#deployment).

## Tech stack

**Backend** — Python, FastAPI, Poetry, Anthropic SDK, OpenAI SDK (embeddings only), Pinecone, LangChain text splitters, Docling (PDF parsing), Arize/OpenInference (observability)

**Frontend** — React 19, TypeScript, Vite, Tailwind CSS, shadcn/ui, [@assistant-ui/react](https://github.com/assistant-ui/assistant-ui) (chat UI framework), Zustand (session persistence)

## Getting started

### Prerequisites
- Python 3.12–3.13, with [Poetry](https://python-poetry.org/) installed
- Node.js 20+
- API keys for OpenAI, Pinecone, and Anthropic

### Backend

```bash
cd rag-app
poetry install --with pipeline      # --with pipeline adds the scraper/PDF deps (docling is large)
cp .env.example .env                # then fill in the keys; APP_ACCESS_CODE can be anything locally

eval $(poetry env activate)
PYTHONPATH=src python -m uvicorn rag_app.server:app --reload   # runs on :8000
```

### Frontend

```bash
cd rag-client
npm install
npm run dev   # runs on :5173 and proxies /chat and /auth to :8000
```

Open `http://localhost:5173`, enter the access code from your `.env`, and start chatting.

### Refreshing the index

Run from `rag-app/` with the venv active. A full refresh takes about 45 minutes, almost all of it the polite 2-second scrape delay.

```bash
PYTHONPATH=src python -m rag_app.pipeline.scraper                    # 1. scrape ~1300 articles to data/articles/
PYTHONPATH=src python -m rag_app.pipeline.article_ingest --wipe      # 2. chunk, embed, WIPE the index, upsert articles
PYTHONPATH=src python -m rag_app.pipeline.pdf_ingest --upsert        # 3. re-upsert the committed fact-sheet chunks
```

Step 2 empties the index before upserting, so run step 3 straight after. Drop `--wipe` to upsert on top of the existing vectors instead (safe, because chunk ids are deterministic). To rebuild fact sheets from new PDFs, drop them in `data/fund_fact_sheets/` and run `pdf_ingest.py --convert --split --describe --upsert`.

## Deployment

The app deploys as one container: FastAPI serves both the API and the built React app from the same origin, so there is no CORS and one URL. The [Dockerfile](Dockerfile) builds the frontend in a Node stage and installs only the serving dependencies in a slim Python stage. It's set up for [Railway](https://railway.app) but any Docker host works.

1. Create a Railway project from this GitHub repo. It detects the root `Dockerfile` automatically.
2. Set these variables in the service's settings:

   | Variable | Purpose |
   |---|---|
   | `ANTHROPIC_API_KEY` | chat, query rewrite, fact-sheet descriptions |
   | `OPENAI_API_KEY` | query embeddings |
   | `PINECONE_API_KEY`, `PINECONE_INDEX_NAME` | retrieval |
   | `APP_ACCESS_CODE` | the shared access code. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(24))"`. The server refuses to start without it. |
   | `ARIZE_SPACE_ID`, `ARIZE_API_KEY` | optional, observability |

   Railway sets `PORT` itself. Do not set `STATIC_DIR`; the Dockerfile does.
3. Deploy, open the generated URL, and confirm `/health` returns `{"status":"ok"}`.
4. Send the URL and the access code to whoever should have access. To revoke or rotate, change `APP_ACCESS_CODE` and redeploy.

To test the image locally:

```bash
docker build -t allanclear .
docker run --rm -p 8000:8000 --env-file rag-app/.env allanclear
```

## Known limitations

- Access control is a single shared code, not per-user accounts. Anyone with the code is a user.
- No automated test suite is configured yet.
