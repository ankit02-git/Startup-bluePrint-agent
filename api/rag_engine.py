"""
RAG Engine — Vercel serverless compatible, SLIM version.
Uses IBM watsonx.ai Embedding API instead of local sentence-transformers.
This removes the torch/sentence-transformers dependency (~2.5 GB saved).
IBM embedding model: ibm/slate-30m-english-rtrvr-v2 (available on Lite plan).
Writes vector_store.json to /tmp (only writable path on Vercel).
"""
import json
import glob
import logging
import os
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)

_API_DIR = Path(__file__).parent
KNOWLEDGE_BASE_DIR = _API_DIR / "knowledge_base"
VECTOR_STORE_PATH = Path("/tmp/vector_store.json")

# slate-30m confirmed working on IBM Cloud Lite plan
# Alternative: ibm/slate-125m-english-rtrvr-v2 (larger, more accurate)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL_ID", "ibm/slate-30m-english-rtrvr-v2")
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


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Pure-Python cosine similarity — no numpy needed."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _get_ibm_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Call IBM watsonx.ai Embedding API.
    Returns a list of embedding vectors (one per input text).
    Batches in groups of 20 to stay within API limits.
    """
    from ibm_watsonx_ai import Credentials
    from ibm_watsonx_ai.foundation_models import Embeddings

    api_key    = os.getenv("WATSONX_API_KEY", "")
    url        = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
    project_id = os.getenv("WATSONX_PROJECT_ID", "")

    if not api_key or not project_id:
        raise EnvironmentError("WATSONX_API_KEY and WATSONX_PROJECT_ID must be set.")

    credentials = Credentials(url=url, api_key=api_key)
    embedder = Embeddings(
        model_id=EMBEDDING_MODEL,
        credentials=credentials,
        project_id=project_id,
    )

    all_vectors: List[List[float]] = []
    batch_size = 20
    for i in range(0, len(texts), batch_size):
        batch = texts[i: i + batch_size]
        response = embedder.embed_documents(texts=batch)
        # response is a list of embedding vectors
        all_vectors.extend(response)

    return all_vectors


class RAGEngine:
    def __init__(self):
        self._store: List[dict] = []

    def ingest_knowledge_base(self, force_reingest: bool = False) -> int:
        if not force_reingest and VECTOR_STORE_PATH.exists():
            logger.info("Loading vector store from /tmp")
            with open(VECTOR_STORE_PATH, "r", encoding="utf-8") as f:
                self._store = json.load(f)
            logger.info("Loaded %d chunks", len(self._store))
            return len(self._store)

        txt_files = sorted(glob.glob(str(KNOWLEDGE_BASE_DIR / "*.txt")))
        if not txt_files:
            logger.warning("No .txt files in %s", KNOWLEDGE_BASE_DIR)
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
            logger.info("  %s -> %d chunks", source_name, len(chunks))

        logger.info("Requesting IBM watsonx embeddings for %d chunks...", len(all_chunks))
        embeddings = _get_ibm_embeddings(all_chunks)

        self._store = [
            {"text": text, "source": source, "embedding": emb}
            for text, source, emb in zip(all_chunks, all_sources, embeddings)
        ]

        with open(VECTOR_STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(self._store, f)

        logger.info("Ingestion complete: %d chunks indexed.", len(self._store))
        return len(self._store)

    def _ensure_loaded(self):
        if not self._store:
            self.ingest_knowledge_base()

    def retrieve(self, query: str, n_results: int = 6) -> List[Tuple[str, str, float]]:
        self._ensure_loaded()

        logger.info("Embedding query via IBM watsonx...")
        query_vec = _get_ibm_embeddings([query])[0]

        scores = [
            (item["text"], item["source"],
             _cosine_similarity(query_vec, item["embedding"]))
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
