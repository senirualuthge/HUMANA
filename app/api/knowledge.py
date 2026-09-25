"""
humana/app/api/knowledge.py
Knowledge Base endpoints — ingest text, upload files, wipe KB.

POST   /api/business/{id}/knowledge/text   — ingest pasted text
POST   /api/business/{id}/knowledge/file   — upload PDF/TXT/DOCX/MD
DELETE /api/business/{id}/knowledge        — wipe entire KB
GET    /api/business/{id}/knowledge/stats  — chunk count + doc list
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.customer import Customer, KnowledgeDoc
from app.models.schemas import (
    KnowledgeIngestResponse,
    KnowledgeTextInput,
    KnowledgeWipeResponse,
)
from app.services.chunker import chunk_text, parse_file
from app.services.vector_store import vector_store

log = get_logger(__name__)
router = APIRouter(prefix="/api/business", tags=["Knowledge Base"])

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


async def _get_active_customer(db: AsyncSession, business_id: str) -> Customer:
    c = await db.get(Customer, business_id)
    if not c:
        raise HTTPException(status_code=404, detail="Business not found")
    if c.status != "active":
        raise HTTPException(status_code=403, detail="Business account is not active")
    return c


# ── INGEST TEXT ───────────────────────────────────────────────────────────────
@router.post("/{business_id}/knowledge/text", response_model=KnowledgeIngestResponse)
async def ingest_text(
    business_id: str,
    body: KnowledgeTextInput,
    db: AsyncSession = Depends(get_db),
):
    await _get_active_customer(db, business_id)
    doc_id = str(uuid.uuid4())
    chunks = chunk_text(body.text)
    if not chunks:
        raise HTTPException(status_code=422, detail="No text content could be extracted")

    count = vector_store.upsert_chunks(
        business_id=business_id,
        chunks=chunks,
        source_name=body.source_name,
        doc_id=doc_id,
    )

    # Persist metadata
    doc = KnowledgeDoc(
        id=doc_id,
        customer_id=business_id,
        source_name=body.source_name,
        doc_type="text",
        chunks_ingested=count,
        char_count=len(body.text),
    )
    db.add(doc)
    log.info("kb_text_ingested", business_id=business_id, chunks=count,
             source=body.source_name)
    return KnowledgeIngestResponse(
        message=f"Successfully ingested {count} chunks from '{body.source_name}'",
        chunks_ingested=count,
        doc_id=doc_id,
        source_name=body.source_name,
    )


# ── UPLOAD FILE ───────────────────────────────────────────────────────────────
@router.post("/{business_id}/knowledge/file", response_model=KnowledgeIngestResponse)
async def ingest_file(
    business_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    await _get_active_customer(db, business_id)

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size is {MAX_FILE_SIZE // 1024 // 1024} MB",
        )

    try:
        text, doc_type = parse_file(file.filename or "upload.txt", content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    if not text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from file")

    doc_id = str(uuid.uuid4())
    chunks = chunk_text(text)
    count = vector_store.upsert_chunks(
        business_id=business_id,
        chunks=chunks,
        source_name=file.filename or "upload",
        doc_id=doc_id,
    )

    doc = KnowledgeDoc(
        id=doc_id,
        customer_id=business_id,
        source_name=file.filename or "upload",
        doc_type=doc_type,
        chunks_ingested=count,
        char_count=len(text),
    )
    db.add(doc)
    log.info("kb_file_ingested", business_id=business_id, filename=file.filename,
             type=doc_type, chunks=count)
    return KnowledgeIngestResponse(
        message=f"File '{file.filename}' ingested successfully",
        chunks_ingested=count,
        doc_id=doc_id,
        source_name=file.filename or "upload",
    )


# ── WIPE KB ───────────────────────────────────────────────────────────────────
@router.delete("/{business_id}/knowledge", response_model=KnowledgeWipeResponse)
async def wipe_knowledge_base(
    business_id: str,
    db: AsyncSession = Depends(get_db),
):
    await _get_active_customer(db, business_id)
    vector_store.delete_collection(business_id)

    # Delete all doc records
    docs = await db.execute(
        select(KnowledgeDoc).where(KnowledgeDoc.customer_id == business_id)
    )
    for doc in docs.scalars().all():
        await db.delete(doc)

    log.info("kb_wiped", business_id=business_id)
    return KnowledgeWipeResponse(
        message="Knowledge base wiped successfully", customer_id=business_id
    )


# ── STATS ─────────────────────────────────────────────────────────────────────
@router.get("/{business_id}/knowledge/stats")
async def knowledge_stats(
    business_id: str,
    db: AsyncSession = Depends(get_db),
):
    await _get_active_customer(db, business_id)
    chunk_count = vector_store.collection_count(business_id)
    docs = await db.execute(
        select(KnowledgeDoc)
        .where(KnowledgeDoc.customer_id == business_id)
        .order_by(KnowledgeDoc.created_at.desc())
    )
    doc_list = [
        {
            "id": d.id,
            "source_name": d.source_name,
            "doc_type": d.doc_type,
            "chunks_ingested": d.chunks_ingested,
            "char_count": d.char_count,
            "created_at": d.created_at.isoformat(),
        }
        for d in docs.scalars().all()
    ]
    return {
        "business_id": business_id,
        "total_chunks": chunk_count,
        "documents": doc_list,
        "document_count": len(doc_list),
    }
