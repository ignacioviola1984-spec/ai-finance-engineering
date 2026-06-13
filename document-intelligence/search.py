"""
search.py - Busqueda semantica sobre documentos financieros (Fase 4.1).

Trocea los documentos en parrafos, los convierte en embeddings, y ante una
consulta devuelve los fragmentos mas parecidos por similitud coseno.

Conceptos: que es un embedding (texto -> vector), vector search (buscar por
cercania en ese espacio), y chunking (trocear el documento en piezas).
"""

import glob
import os

import numpy as np

from embedder import embed, backend_name

DOCS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")


def load_chunks():
    """Trocea cada documento en parrafos (chunks) con su archivo de origen."""
    chunks = []
    for path in sorted(glob.glob(os.path.join(DOCS, "*.md"))):
        name = os.path.basename(path)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        for para in text.split("\n\n"):
            p = " ".join(para.split())
            if len(p) >= 40:
                chunks.append((name, p))
    return chunks


CHUNKS = load_chunks()
_VECS = None


def _vectors():
    global _VECS
    if _VECS is None:
        _VECS = embed([c[1] for c in CHUNKS])
    return _VECS


def search(query, k=3):
    """Devuelve los k chunks mas similares a la consulta (cosine similarity)."""
    qv = embed([query])[0]
    M = _vectors()
    qn = qv / (np.linalg.norm(qv) + 1e-9)
    Mn = M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-9)
    sims = Mn @ qn
    idx = np.argsort(-sims)[:k]
    return [(CHUNKS[i][0], CHUNKS[i][1], float(sims[i])) for i in idx]


if __name__ == "__main__":
    print(f"backend: {backend_name()} | {len(CHUNKS)} chunks")
    for q in [
        "When does the cloud contract renew and what notice is required?",
        "What are the payment terms for the marketing agency?",
        "Who approves an expense over 5000 dollars?",
    ]:
        print(f"\nQ: {q}")
        for name, snip, score in search(q):
            print(f"  [{score:.3f}] {name}: {snip[:85]}...")
