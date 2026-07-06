from fastapi import APIRouter, Depends, Query
from app.core.config import Settings, get_settings
from app.services.graph_writer import GraphWriter

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/statistics")
def graph_statistics(settings: Settings = Depends(get_settings)):
    writer = GraphWriter(settings)
    stats = writer.get_statistics()
    writer.close()
    return stats


@router.get("/search")
def search_nodes(
    keyword: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=200),
    settings: Settings = Depends(get_settings),
):
    writer = GraphWriter(settings)
    nodes = writer.search_nodes(keyword, limit)
    writer.close()
    return {"nodes": nodes}


@router.get("/neighbors")
def get_neighbors(
    name: str = Query(...),
    type: str = Query(...),
    depth: int = Query(2, ge=1, le=4),
    settings: Settings = Depends(get_settings),
):
    writer = GraphWriter(settings)
    result = writer.get_neighbors(name, type, depth)
    writer.close()
    return result


@router.get("/full")
def get_full_graph(
    limit: int = Query(300, ge=1, le=1000),
    settings: Settings = Depends(get_settings),
):
    writer = GraphWriter(settings)
    graph = writer.get_graph(limit)
    writer.close()
    return graph
