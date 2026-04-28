# Retrieval layer and summary index

This retrieval module now supports both online recall and offline summary indexing.

## Vector retriever

This retrieval module supports three modes (in order of preference):

- sentence-transformers + faiss (recommended for quality + speed)
- sklearn TF-IDF + NearestNeighbors (fallback)
- simple substring scoring (last-resort builtin)

Install optional deps (recommended):

```bash
pip install -r backend/requirements.optional.txt
```

The semantic retriever now persists its built index under `.opencode_index/semantic/` and reuses it across process restarts when possible.

Quick smoke test (from repo root):

```bash
python -c "from backend.agent.tools.context_retrieval_step2 import retrieve_precise_context; print(retrieve_precise_context({'repo_path':'testcode','points':['calculator multiply'],'top_k':5}))"
```

If you prefer a persistent vector DB (Qdrant/Weaviate), consider adapting `SemanticRetriever` to build and persist indices there instead of in-memory FAISS.

## Summary index skeleton

The offline summary index builder writes directory summaries and file summaries under `.opencode_index`:

- `dirs/<relative-dir>/summary.json`
- `files/<relative-file>/file_summary.json`
- `manifest.json`

Build it from repo root:

```bash
python -m backend.agent.tools.retrieval.index_builder .
```

The current Step2 flow does not yet consume the summary index automatically; the next step is to prefer these precomputed summaries before falling back to live AST parsing.
