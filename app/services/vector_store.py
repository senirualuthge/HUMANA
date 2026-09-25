"""
humana/app/services/vector_store.py
Chroma-backed vector store service.
Each tenant gets their own Chroma collection: humana_{business_id}
"""
from __future__ import annotations

import uuid
from typing import List, Optional, Tuple

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)
settings = get_settings()


def _get_client() -> chromadb.Client:
    if settings.chroma_host:
        return chromadb.HttpClient(host=settings.chroma_host)
    return chromadb.PersistentClient(
        path=settings.chroma_path,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def _collection_name(business_id: str) -> str:
    # Chroma collection names: only alphanumeric + underscore, 3–63 chars
    safe = business_id.replace("-", "_")[:50]
    return f"humana_{safe}"


class VectorStoreService:
    def __init__(self):
        self._client = _get_client()
        # Lazy embedding function — initialised on first use
        self._ef = None

    def _get_ef(self):
        if self._ef is None:
            if settings.embedding_provider == "openai":
                self._ef = chromadb.utils.embedding_functions.OpenAIEmbeddingFunction(
                    api_key=settings.openai_api_key,
                    model_name=settings.embedding_model,
                )
            else:
                self._ef = chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=settings.embedding_model
                )
        return self._ef

    def _collection(self, business_id: str):
        return self._client.get_or_create_collection(
            name=_collection_name(business_id),
            embedding_function=self._get_ef(),
            metadata={"hnsw:space": "cosine"},
        )

    # ── Ingest ────────────────────────────────────────────────────────────────
    def upsert_chunks(
        self,
        business_id: str,
        chunks: List[str],
        source_name: str,
        doc_id: str,
    ) -> int:
        col = self._collection(business_id)
        ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
        metadatas = [{"source": source_name, "doc_id": doc_id, "chunk_index": i}
                     for i in range(len(chunks))]
        col.upsert(documents=chunks, ids=ids, metadatas=metadatas)
        log.info("chunks_upserted", business_id=business_id,
                 doc_id=doc_id, count=len(chunks))
        return len(chunks)

    # ── Query ─────────────────────────────────────────────────────────────────
    def query(
        self,
        business_id: str,
        query_text: str,
        top_k: Optional[int] = None,
    ) -> List[Tuple[str, float, dict]]:
        """
        Returns list of (document_text, distance, metadata).
        Lower distance = more similar for cosine.
        """
        k = top_k or settings.top_k_retrieval
        col = self._collection(business_id)
        count = col.count()
        if count == 0:
            return []
        k = min(k, count)
        results = col.query(query_texts=[query_text], n_results=k)
        docs = results["documents"][0]
        distances = results["distances"][0]
        metas = results["metadatas"][0]
        # Filter by similarity threshold (chroma cosine distance: 0=identical, 2=opposite)
        threshold = settings.similarity_threshold * 2  # convert to distance scale
        filtered = [
            (doc, dist, meta)
            for doc, dist, meta in zip(docs, distances, metas)
            if dist <= threshold
        ]
        return filtered

    # ── Delete ────────────────────────────────────────────────────────────────
    def delete_collection(self, business_id: str) -> bool:
        name = _collection_name(business_id)
        try:
            self._client.delete_collection(name)
            log.info("collection_deleted", business_id=business_id, name=name)
            return True
        except Exception as exc:
            log.warning("collection_delete_failed", error=str(exc))
            return False

    def delete_doc(self, business_id: str, doc_id: str) -> int:
        col = self._collection(business_id)
        existing = col.get(where={"doc_id": doc_id})
        ids = existing["ids"]
        if ids:
            col.delete(ids=ids)
        return len(ids)

    def collection_count(self, business_id: str) -> int:
        try:
            return self._collection(business_id).count()
        except Exception:
            return 0


# Global singleton
vector_store = VectorStoreService()
