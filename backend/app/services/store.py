from typing import Dict, List, Optional
from app.models.schema import Document, Chunk, Candidate


class MemoryStore:
    """MVP in-memory store. Replace with PostgreSQL/SQL in production."""

    def __init__(self):
        self.documents: Dict[str, Document] = {}
        self.chunks: Dict[str, Chunk] = {}
        self.candidates: Dict[str, Candidate] = {}

    def save_document(self, doc: Document):
        self.documents[doc.id] = doc

    def get_document(self, doc_id: str) -> Optional[Document]:
        return self.documents.get(doc_id)

    def save_chunks(self, chunks: List[Chunk]):
        for c in chunks:
            self.chunks[c.id] = c

    def get_document_chunks(self, doc_id: str) -> List[Chunk]:
        return sorted(
            [c for c in self.chunks.values() if c.document_id == doc_id],
            key=lambda x: x.chunk_index,
        )

    def save_candidates(self, candidates: List[Candidate]):
        for c in candidates:
            self.candidates[c.id] = c

    def get_document_candidates(self, doc_id: str) -> List[Candidate]:
        return [c for c in self.candidates.values() if c.document_id == doc_id]

    def get_candidate(self, cand_id: str) -> Optional[Candidate]:
        return self.candidates.get(cand_id)

    def update_candidate_status(self, cand_id: str, status: str):
        if cand_id in self.candidates:
            self.candidates[cand_id].status = status


store = MemoryStore()
