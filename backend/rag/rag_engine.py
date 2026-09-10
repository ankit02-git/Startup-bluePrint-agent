"""
RAG Engine — pure-Python vector store using sentence-transformers + cosine similarity.
No native build dependencies (no ChromaDB, no HNSWLIB).
Embeddings are persisted to disk as a JSON file for reuse across restarts.
"""
import json
import glob
import logging
import math
from pathlib import Path
from typing import List, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

KNOWLEDGE_BASE_DIR = Path(__file__).parent.parent / "knowledge_base"
VECTOR_STORE_PATH = Path(__file__).parent.parent / "vector_store.json"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHUNK_SIZE = 600      # words per chunk
CHUNK_OVERLAP = 100   # overlapping words between chunks


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping word-level chunks."""
    words = text.split()
    chunks: List[str] = []
    step = chunk_size - overlap
    for i in range(0, len(words), step):
        chunk = " ".join(words[i: i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
        if i + chunk_size >= len(words):
            break
    return chunks


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two 1-D vectors."""
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


class RAGEngine:
    """
    Lightweight in-process vector store.
    - Embeds all knowledge base chunks on first run and saves to disk.
    - On subsequent runs, loads from disk (fast restart).
    - Retrieval: brute-force cosine similarity (fast enough for <5000 chunks).
    """

    def __init__(self):
        self._model: SentenceTransformer | None = None
        # Each entry: {"text": str, "source": str, "embedding": List[float]}
        self._store: List[dict] = []

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            logger.info("Loading embedding model: %s", EMBEDDING_MODEL)
            self._model = SentenceTransformer(EMBEDDING_MODEL)
        return self._model

    def ingest_knowledge_base(self, force_reingest: bool = False) -> int:
        """
        Load all .txt files from the knowledge base, embed them, and persist.
        If the vector store already exists on disk and force_reingest=False, loads from disk.
        """
        if not force_reingest and VECTOR_STORE_PATH.exists():
            logger.info("Loading existing vector store from disk: %s", VECTOR_STORE_PATH)
            with open(VECTOR_STORE_PATH, "r", encoding="utf-8") as f:
                self._store = json.load(f)
            logger.info("Loaded %d chunks from disk.", len(self._store))
            return len(self._store)

        model = self._get_model()
        txt_files = sorted(glob.glob(str(KNOWLEDGE_BASE_DIR / "*.txt")))
        if not txt_files:
            logger.warning("No .txt files found in knowledge base: %s", KNOWLEDGE_BASE_DIR)
            return 0

        all_chunks: List[str] = []
        all_sources: List[str] = []

        for filepath in txt_files:
            source_name = Path(filepath).stem
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            chunks = chunk_text(content)
            all_chunks.extend(chunks)
            all_sources.extend([source_name] * len(chunks))
            logger.info("  %s → %d chunks", source_name, len(chunks))

        logger.info("Embedding %d total chunks...", len(all_chunks))
        embeddings = model.encode(all_chunks, batch_size=64, show_progress_bar=True)

        self._store = [
            {
                "text": text,
                "source": source,
                "embedding": emb.tolist(),
            }
            for text, source, emb in zip(all_chunks, all_sources, embeddings)
        ]

        logger.info("Saving vector store to %s", VECTOR_STORE_PATH)
        with open(VECTOR_STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(self._store, f)

        logger.info("Ingestion complete: %d chunks indexed.", len(self._store))
        return len(self._store)

    def _ensure_loaded(self):
        if not self._store:
            self.ingest_knowledge_base()

    def retrieve(self, query: str, n_results: int = 6) -> List[Tuple[str, str, float]]:
        """
        Retrieve top-n most similar chunks for the query.
        Returns list of (text, source, similarity_score) sorted by score descending.
        """
        self._ensure_loaded()
        model = self._get_model()

        query_emb = model.encode([query])[0]

        scores = [
            (
                item["text"],
                item["source"],
                _cosine_similarity(query_emb, np.array(item["embedding"])),
            )
            for item in self._store
        ]
        scores.sort(key=lambda x: x[2], reverse=True)
        return scores[:n_results]

    def get_context_for_query(self, query: str, n_results: int = 6) -> str:
        """Build a formatted context string from retrieved chunks."""
        chunks = self.retrieve(query, n_results=n_results)
        parts = [f"[Source: {source}]\n{text}" for text, source, _ in chunks]
        return "\n\n---\n\n".join(parts)

    def count(self) -> int:
        return len(self._store)


# ── singleton ──────────────────────────────────────────────────────────────────
_rag_engine: RAGEngine | None = None


def get_rag_engine() -> RAGEngine:
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine
