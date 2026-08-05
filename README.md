# AllanClear

AllanClear is a RAG (Retrieval-Augmented Generation) chatbot that answers questions about Allan Gray investments, grounded in Allan Gray's own published articles and fund fact sheets.

> This is an educational/demo project and is not affiliated with, endorsed by, or associated with Allan Gray Investment Management in any way.


https://github.com/user-attachments/assets/af167566-d65d-4e15-84cb-8c6611b53460


## How it works

AllanClear retrieves relevant source material before generating an answer, rather than relying on the LLM's own knowledge.

1. **Scrape** — [scraper.py](rag-app/src/rag_app/pipeline/scraper.py) crawls the allangray.co.za sitemap for articles.
2. **Chunk** — [chunker.py](rag-app/src/rag_app/pipeline/chunker.py) splits articles into overlapping chunks (1000 chars, 200 overlap) using LangChain's `RecursiveCharacterTextSplitter`.
3. **Embed & store** — [article_ingest.py](rag-app/src/rag_app/pipeline/article_ingest.py) and [pdf_ingest.py](rag-app/src/rag_app/pipeline/pdf_ingest.py) embed chunks with OpenAI's `text-embedding-3-small` and upsert them to a Pinecone vector index.
4. **Query** — on each user message, [search.py](rag-app/src/rag_app/search.py) embeds the query and retrieves the top 10 most relevant chunks from Pinecone.
5. **Respond** — [server.py](rag-app/src/rag_app/server.py) streams a response from Claude (Anthropic) back to the client over Server-Sent Events, citing the retrieved sources.

**Multi-turn query rewrite** — when a conversation has more than one turn, the backend first rewrites the latest user message into a standalone query (via an LLM call) before running retrieval, so follow-up questions ("what about the second one?") work without the user restating context.

**Observability** — LLM and retrieval calls are instrumented with OpenInference and traced via Arize, so a full request (rewrite → retrieval → generation) can be inspected end to end.

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
poetry install

# create rag-app/.env with:
# OPENAI_API_KEY=...
# PINECONE_API_KEY=...
# PINECONE_INDEX_NAME=...
# ANTHROPIC_API_KEY=...
# ARIZE_SPACE_ID=...   # optional, for observability
# ARIZE_API_KEY=...    # optional, for observability

eval $(poetry env activate)
python -m uvicorn src.rag_app.server:app --reload   # runs on :8000
```

### Frontend

```bash
cd rag-client
npm install
npm run dev   # runs on :5173
```

Open `http://localhost:5173` and start chatting. The frontend expects the backend on `http://localhost:8000`.

## Known limitations

- No automated test suite is configured yet.
