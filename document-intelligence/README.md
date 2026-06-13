# Finance Document Intelligence (RAG)

Semantic search, retrieval-augmented generation (RAG), and structured
extraction over finance documents (vendor contracts and an expense policy),
on synthetic data modeled on the Lumen company used across this repo.

## Files

- `embedder.py` — embedding backend. Primary: `sentence-transformers`
  (PyTorch). Fallback: `model2vec` (no PyTorch). The search code is
  backend-agnostic, so it also works with hosted embeddings (Voyage, OpenAI).
- `search.py` — chunks the documents, embeds them, and returns the closest
  passages to a query by cosine similarity.
- `rag.py` — RAG question answering with source citations, and structured
  extraction of key contract terms into a table.
- `docs/` — the source documents.

## Run it

```bash
pip install -r requirements.txt
python search.py        # semantic search (no API key needed)
python rag.py           # RAG + extraction (needs ANTHROPIC_API_KEY in repo-root .env)
```

## Design decisions (the "why")

- **When RAG, when not.** For a specific question over a large corpus, RAG
  wins: retrieve only the relevant passages. For extracting fields from a
  single short document, pass the whole document; retrieval there is
  unnecessary overhead. Choosing well is the skill, not using RAG by default.
- **Grounded answers.** The model answers using only retrieved context and
  cites the source document. If the context is insufficient, it says so
  instead of inventing.
- **Swappable embeddings.** Retrieval depends on an `embed()` function, not on
  a specific model, so the backend can change without touching the search.
- **Multilingual retrieval.** Uses a multilingual embedding model so a Spanish
  question retrieves the right passage from an English document, a real need in
  a LATAM finance context. An English-only model degrades on cross-lingual
  queries; this is the kind of failure an eval set is built to catch.

## Debugging note: cross-lingual retrieval

A real issue found and fixed while building this. With an English-only
embedding model, Spanish questions over English documents failed to retrieve
the right passage. For "plazo de pago de la agencia de marketing", the model
correctly refused to answer (it would not invent the figure) because the
relevant passage was never retrieved, while the full-document extraction
returned the same field correctly.

Diagnosis: the failure was in retrieval, not generation, and specifically in
cross-lingual matching (Spanish query, English corpus). Fix: a multilingual
embedding model, which matters in a LATAM finance context with mixed-language
documents. The broader lesson: a correct number can still produce a wrong
answer if retrieval misses, and you only catch this reliably with an
evaluation set, not by spot-checking. That is the motivation for the evals
and guardrails work.

## Stack
Python, sentence-transformers / PyTorch, multilingual embeddings & cosine
similarity, RAG, structured extraction, Anthropic API.
