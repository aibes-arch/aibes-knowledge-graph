import os
import shutil
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from app.core.config import Settings, get_settings
from app.models.schema import Document, Chunk
from app.services.document_parser import DocumentParser
from app.services.chunker import TextChunker
from app.services.extractor import KnowledgeExtractor
from app.services.graph_writer import GraphWriter
from app.services.store import store
from app.core.llm import LLMClient

router = APIRouter(prefix="/documents", tags=["documents"])


def save_upload(file: UploadFile, upload_dir: str) -> str:
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return file_path


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
):
    file_type = DocumentParser.detect_type(file.filename)
    if file_type == "unknown":
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Use PDF, Word, Markdown, or TXT.",
        )
    file_path = save_upload(file, settings.upload_dir)
    doc = Document(
        filename=file.filename,
        file_type=file_type,
        status="uploaded",
        storage_path=file_path,
    )
    store.save_document(doc)
    return {"document_id": doc.id, "filename": doc.filename, "status": doc.status}


@router.post("/{doc_id}/parse")
async def parse_document(doc_id: str):
    doc = store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    full_text, pages = DocumentParser.parse(doc.storage_path, doc.file_type)
    doc.status = "parsed"
    store.save_document(doc)

    chunker = TextChunker()
    all_chunks: List[Chunk] = []
    for page in pages:
        chunks = chunker.chunk(doc_id, page["text"], page.get("page_no", 1))
        all_chunks.extend(chunks)
    store.save_chunks(all_chunks)

    return {
        "document_id": doc_id,
        "status": doc.status,
        "text_length": len(full_text),
        "chunks": len(all_chunks),
    }


@router.post("/{doc_id}/extract")
async def extract_document(doc_id: str, settings: Settings = Depends(get_settings)):
    doc = store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    chunks = store.get_document_chunks(doc_id)
    if not chunks:
        raise HTTPException(status_code=400, detail="Document not parsed yet")

    llm = LLMClient(settings)
    extractor = KnowledgeExtractor(llm, mock=settings.mock_llm)
    candidates = extractor.extract_chunks(chunks)
    store.save_candidates(candidates)
    doc.status = "extracted"
    store.save_document(doc)

    return {
        "document_id": doc_id,
        "status": doc.status,
        "candidates": len(candidates),
    }


@router.post("/{doc_id}/write-graph")
async def write_graph(doc_id: str, settings: Settings = Depends(get_settings)):
    doc = store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    candidates = store.get_document_candidates(doc_id)
    if not candidates:
        raise HTTPException(status_code=400, detail="No extraction candidates")

    writer = GraphWriter(settings)
    writer.ensure_indexes()
    writer.write_candidates(doc_id, candidates)
    writer.close()

    doc.status = "graph_written"
    store.save_document(doc)
    return {"document_id": doc_id, "status": doc.status}


@router.get("/{doc_id}")
async def get_document(doc_id: str):
    doc = store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc.model_dump()


@router.get("/{doc_id}/candidates")
async def get_candidates(doc_id: str):
    return [c.model_dump() for c in store.get_document_candidates(doc_id)]
