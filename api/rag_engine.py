"""
RAG Engine — Vercel serverless compatible.
Writes vector_store.json to /tmp (only writable path on Vercel).
Knowledge base .txt files are read from api/knowledge_base/ (deployed with code).
"""
import json
import glob
import logging
from pathlib import Path
from typing import List, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# On Vercel, __file__ is inside /var/task/api/
_API_DIR = Path(__file__).parent
KNOWLEDGE_BASE_DIR = _API_DIR / "knowledge_base"

# /tmp is the only writable directory on Vercel Lambda
VECTOR_STORE_PATH = Path("/tmp/vector_store.json")

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHUNK_SIZE = 600
CHUNK_OVERLAP = 100


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
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
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


class RAGEngine:
    def __init__(self):
        self._model: SentenceTransformer | None = None
        self._store: List[dict] = []

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            logger.info("Loading embedding model: %s", EMBEDDING_MODEL)
            self._model = SentenceTransformer(EMBEDDING_MODEL)
        return self._model

    def ingest_knowledge_base(self, force_reingest: bool = False) -> int:
        if not force_reingest and VECTOR_STORE_PATH.exists():
            logger.info("Loading vector store from /tmp")
            with open(VECTOR_STORE_PATH, "r", encoding="utf-8") as f:
                self._store = json.load(f)
            return len(self._store)

        model = self._get_model()
        txt_files = sorted(glob.glob(str(KNOWLEDGE_BASE_DIR / "*.txt")))
        if not txt_files:
            logger.warning("No .txt files found in: %s", KNOWLEDGE_BASE_DIR)
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

        logger.info("Embedding %d chunks...", len(all_chunks))
        embeddings = model.encode(all_chunks, batch_size=32, show_progress_bar=False)

        self._store = [
            {"text": text, "source": source, "embedding": emb.tolist()}
            for text, source, emb in zip(all_chunks, all_sources, embeddings)
        ]

        with open(VECTOR_STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(self._store, f)

        logger.info("Ingestion complete: %d chunks", len(self._store))
        return len(self._store)

    def _ensure_loaded(self):
        if not self._store:
            self.ingest_knowledge_base()

    def retrieve(self, query: str, n_results: int = 6) -> List[Tuple[str, str, float]]:
        self._ensure_loaded()
        model = self._get_model()
        query_emb = model.encode([query])[0]
        scores = [
            (item["text"], item["source"],
             _cosine_similarity(query_emb, np.array(item["embedding"])))
            for item in self._store
        ]
        scores.sort(key=lambda x: x[2], reverse=True)
        return scores[:n_results]

    def get_context_for_query(self, query: str, n_results: int = 6) -> str:
        chunks = self.retrieve(query, n_results=n_results)
        parts = [f"[Source: {source}]\n{text}" for text, source, _ in chunks]
        return "\n\n---\n\n".join(parts)

    def count(self) -> int:
        self._ensure_loaded()
        return len(self._store)


_rag_engine: RAGEngine | None = None


def get_rag_engine() -> RAGEngine:
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine
