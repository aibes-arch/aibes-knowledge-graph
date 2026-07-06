from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.core.config import Settings, get_settings
from app.core.llm import LLMClient
from app.services.graph_writer import GraphWriter


class ChatRequest(BaseModel):
    question: str


router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/chat")
def chat(request: ChatRequest, settings: Settings = Depends(get_settings)):
    writer = GraphWriter(settings)
    # Extract simple keyword from question (naive approach)
    keyword = request.question.replace("?", "").replace("？", "").strip()
    nodes = writer.search_nodes(keyword, limit=10)

    # Build context from nodes and their evidence
    context_parts = []
    for n in nodes[:5]:
        context_parts.append(
            f"实体：{n.get('name')}（{n.get('type')}）\n证据：{n.get('evidence', '')}"
        )
    context = "\n\n".join(context_parts) if context_parts else "（暂无相关图谱内容）"

    prompt = f"""基于以下知识图谱信息回答问题。

知识图谱上下文：
{context}

问题：{request.question}

请用中文简洁回答，并说明回答依据。如果没有足够信息，请明确说明。"""

    llm = LLMClient(settings)
    answer = llm.chat_completion(prompt, system="你是知识图谱问答助手。")
    writer.close()
    return {
        "question": request.question,
        "answer": answer,
        "sources": [
            {"name": n.get("name"), "type": n.get("type")} for n in nodes[:5]
        ],
    }
