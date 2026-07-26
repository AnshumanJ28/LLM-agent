"""Minimal FAISS-backed lookup, same pattern as your rag-document-qa project: embed a
corpus once via build_index(), then do nearest-neighbor search at query time. Falls back
to a keyword match if faiss/sentence-transformers aren't installed, so the agent still
runs without those heavier deps."""

from src.tools.registry import register

try:
    import faiss
    from sentence_transformers import SentenceTransformer
    _HAS_DEPS = True
except ImportError:
    _HAS_DEPS = False

_INDEX = None
_MODEL = None
_DOCS = []


def build_index(docs: list):
    global _INDEX, _MODEL, _DOCS
    _DOCS = docs
    if not _HAS_DEPS:
        return
    _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = _MODEL.encode(docs, convert_to_numpy=True)
    dim = embeddings.shape[1]
    _INDEX = faiss.IndexFlatL2(dim)
    _INDEX.add(embeddings)


@register(
    name="vector_lookup",
    description="Search a document corpus for relevant passages. Input: {query: str, k: int}",
)
def vector_lookup(query: str, k: int = 3) -> str:
    if not _DOCS:
        return "No index built yet. Call build_index(docs) with your corpus first."

    if not _HAS_DEPS or _INDEX is None:
        matches = [d for d in _DOCS if any(w.lower() in d.lower() for w in query.split())][:k]
        if not matches:
            return "No keyword matches found (faiss/sentence-transformers not installed)."
        return "\n".join(f"- {m}" for m in matches)

    query_emb = _MODEL.encode([query], convert_to_numpy=True)
    _, indices = _INDEX.search(query_emb, k)
    results = [_DOCS[i] for i in indices[0] if 0 <= i < len(_DOCS)]
    return "\n".join(f"- {r}" for r in results) if results else "No matches found."
