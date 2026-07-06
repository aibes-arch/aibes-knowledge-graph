import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import get_settings
from app.api import documents, graph, schema as schema_api, rag

settings = get_settings()
os.makedirs(settings.upload_dir, exist_ok=True)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure Neo4j indexes (best effort)
    from app.services.graph_writer import GraphWriter

    writer = GraphWriter(settings)
    try:
        writer.ensure_indexes()
    except Exception as e:
        print(f"[WARNING] Neo4j not ready, skipping index creation: {e}")
    finally:
        writer.close()
    yield
    # Shutdown


app = FastAPI(
    title=settings.app_name,
    description="面向任意行业的知识图谱自动构建与 GraphRAG 应用开发平台",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(graph.router)
app.include_router(schema_api.router)
app.include_router(rag.router)

# Serve frontend static files
frontend_dir = os.path.join(PROJECT_ROOT, "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/")
def root():
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
