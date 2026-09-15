# AllanClear

A private RAG chatbot that answers questions about Allan Gray investments, grounded in Allan Gray's published articles and fund fact sheets.

## Language

### Sources

**Article**:
A text article scraped from the "latest insights" section of allangray.co.za. Videos and podcasts on the same site are not Articles.
_Avoid_: post, blog, page

**Fund Fact Sheet**:
A PDF published by Allan Gray describing one fund (performance, fees, allocation). Converted to Markdown and split by section before ingestion.
_Avoid_: factsheet, fund PDF, fund doc

**Chunk**:
One embedded unit of text from an Article or Fund Fact Sheet, stored as a vector with its metadata. A Chunk's `source_type` is either `article` or `fund_fact_sheet`.
_Avoid_: document, passage, vector

**Source**:
The Article or Fund Fact Sheet that a retrieved Chunk came from, shown to the user as a citation under the answer.
_Avoid_: reference, link

### Conversation

**Persona**:
The response style the user picks: just the answer, explain simply, give me detail, or Eminem (explicit, in-character delivery of the same facts). Changes the system prompt, not the retrieval.
_Avoid_: mode, tone, style

**Query Rewrite**:
Turning the latest user message into a standalone question using the conversation so far, before retrieval. Only happens from the second user message onward.
_Avoid_: reformulation, condensing

### Access

**Access Code**:
The single shared secret that gates the deployed app. There are no user accounts; whoever has the code is a user.
_Avoid_: password, token, API key, login
