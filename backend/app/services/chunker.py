import re
from typing import List
from app.models.schema import Chunk


class TextChunker:
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, document_id: str, text: str, page_no: int = 1) -> List[Chunk]:
        # Split by sentences first, then merge into chunks
        sentences = re.split(r"(?<=[。！？.!?])\s+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        chunks = []
        current = []
        current_len = 0
        idx = 0

        for sent in sentences:
            sent_len = len(sent)
            if current_len + sent_len > self.chunk_size and current:
                content = "".join(current)
                chunks.append(
                    Chunk(
                        document_id=document_id,
                        chunk_index=idx,
                        content=content,
                        page_no=page_no,
                        token_count=len(content),
                    )
                )
                idx += 1
                # overlap
                overlap = []
                overlap_len = 0
                for s in reversed(current):
                    if overlap_len + len(s) > self.chunk_overlap:
                        break
                    overlap.insert(0, s)
                    overlap_len += len(s)
                current = overlap
                current_len = overlap_len
            current.append(sent)
            current_len += sent_len

        if current:
            content = "".join(current)
            chunks.append(
                Chunk(
                    document_id=document_id,
                    chunk_index=idx,
                    content=content,
                    page_no=page_no,
                    token_count=len(content),
                )
            )
        return chunks
