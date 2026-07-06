from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime
from uuid import uuid4


class EntityType(BaseModel):
    label: str
    name: str
    color: Optional[str] = None


class RelationType(BaseModel):
    type: str
    from_: str = Field(..., alias="from")
    to: str

    class Config:
        populate_by_name = True


class DomainSchema(BaseModel):
    domain: str
    entities: List[EntityType]
    relations: List[RelationType]


class Entity(BaseModel):
    name: str
    type: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    evidence: str = ""
    confidence: float = 0.0


class Relation(BaseModel):
    source: str
    target: str
    type: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    evidence: str = ""
    confidence: float = 0.0


class ExtractionResult(BaseModel):
    entities: List[Entity] = Field(default_factory=list)
    relations: List[Relation] = Field(default_factory=list)


class Document(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    filename: str
    file_type: str
    domain: str = "equipment_maintenance"
    status: str = "uploaded"
    storage_path: str = ""
    created_at: datetime = Field(default_factory=datetime.now)


class Chunk(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    document_id: str
    chunk_index: int
    title: str = ""
    content: str
    page_no: Optional[int] = None
    token_count: int = 0


class Candidate(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    chunk_id: str
    document_id: str
    entity_json: Dict[str, Any] = Field(default_factory=dict)
    relation_json: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    status: str = "pending"  # pending, approved, rejected
    created_at: datetime = Field(default_factory=datetime.now)
