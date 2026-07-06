from fastapi import APIRouter, Depends
from app.models.schema import DomainSchema
from app.services.extractor import DEFAULT_SCHEMA

router = APIRouter(prefix="/schema", tags=["schema"])


@router.get("/default")
def get_default_schema():
    return DEFAULT_SCHEMA.model_dump(by_alias=True)


@router.post("")
def create_schema(schema: DomainSchema):
    # In MVP just echo back; in production persist to DB.
    return {"message": "Schema received", "schema": schema.model_dump(by_alias=True)}
