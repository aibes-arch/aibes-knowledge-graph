import json
from typing import List
from app.core.llm import LLMClient
from app.models.schema import (
    DomainSchema,
    ExtractionResult,
    Entity,
    Relation,
    Chunk,
    Candidate,
)


DEFAULT_SCHEMA = DomainSchema(
    domain="equipment_maintenance",
    entities=[
        {"label": "Equipment", "name": "装备"},
        {"label": "Subsystem", "name": "子系统"},
        {"label": "Component", "name": "部件"},
        {"label": "Fault", "name": "故障"},
        {"label": "Symptom", "name": "现象"},
        {"label": "Cause", "name": "原因"},
        {"label": "Solution", "name": "维修方案"},
        {"label": "Procedure", "name": "维修步骤"},
        {"label": "Tool", "name": "工具"},
        {"label": "SparePart", "name": "备件"},
        {"label": "Supplier", "name": "供应商"},
        {"label": "Document", "name": "文档"},
        {"label": "Person", "name": "专家"},
        {"label": "Record", "name": "维修记录"},
    ],
    relations=[
        {"type": "HAS_SUBSYSTEM", "from": "Equipment", "to": "Subsystem"},
        {"type": "HAS_COMPONENT", "from": "Subsystem", "to": "Component"},
        {"type": "HAS_FAULT", "from": "Component", "to": "Fault"},
        {"type": "HAS_SYMPTOM", "from": "Fault", "to": "Symptom"},
        {"type": "CAUSED_BY", "from": "Fault", "to": "Cause"},
        {"type": "SOLVED_BY", "from": "Fault", "to": "Solution"},
        {"type": "HAS_STEP", "from": "Solution", "to": "Procedure"},
        {"type": "REQUIRES_TOOL", "from": "Solution", "to": "Tool"},
        {"type": "REQUIRES_PART", "from": "Solution", "to": "SparePart"},
        {"type": "SUPPLIED_BY", "from": "SparePart", "to": "Supplier"},
        {"type": "MENTIONS", "from": "Document", "to": "Equipment"},
        {"type": "CONFIRMS", "from": "Record", "to": "Fault"},
        {"type": "PROVIDES", "from": "Person", "to": "Solution"},
    ],
)


class KnowledgeExtractor:
    def __init__(self, llm: LLMClient, schema: DomainSchema = None, mock: bool = False):
        self.llm = llm
        self.schema = schema or DEFAULT_SCHEMA
        self.mock = mock

    def _mock_extract(self, chunk_text: str) -> Candidate:
        """Heuristic mock extraction for MVP demo without paid LLM."""
        import re

        entities = []
        relations = []
        text = chunk_text

        # Simple keyword-based entity extraction (conservative demo set)
        equipment_keywords = ["主轴冷却风机", "冷却风机"]
        component_keywords = ["散热风扇", "电机轴承", "电源模块"]
        fault_keywords = ["异响", "不转", "磨损"]
        tool_keywords = ["内六角扳手", "万用表"]
        part_keywords = ["电机轴承", "散热风扇"]
        solution_keywords = ["维修方案"]

        def add_entity(name, etype):
            if not name or any(e.name == name for e in entities):
                return
            entities.append(
                Entity(name=name, type=etype, evidence=text[:120], confidence=0.85)
            )

        for kw in equipment_keywords:
            if kw in text:
                add_entity(kw, "Equipment")
        for kw in component_keywords:
            if kw in text:
                add_entity(kw, "Component")
        for kw in fault_keywords:
            if kw in text:
                add_entity(kw, "Fault")
        for kw in tool_keywords:
            if kw in text:
                add_entity(kw, "Tool")
        for kw in part_keywords:
            if kw in text:
                add_entity(kw, "SparePart")
        for kw in solution_keywords:
            if kw in text:
                add_entity(kw, "Solution")

        # Simple relations: equipment has component, fault caused_by component, solution requires tool/part
        equipment = next((e for e in entities if e.type == "Equipment"), None)
        for comp in [e for e in entities if e.type == "Component"]:
            if equipment:
                relations.append(
                    Relation(source=equipment.name, target=comp.name, type="HAS_COMPONENT", evidence=text[:120], confidence=0.8)
                )
        sentences = re.split(r"(?<=[。！？.!?])\s+", text)
        for fault in [e for e in entities if e.type == "Fault"]:
            for comp in [e for e in entities if e.type == "Component"]:
                # link component to fault only if they co-occur in a sentence
                for sent in sentences:
                    if comp.name in sent and fault.name in sent:
                        relations.append(
                            Relation(source=comp.name, target=fault.name, type="HAS_FAULT", evidence=sent, confidence=0.75)
                        )
                        break
            for sol in [e for e in entities if e.type == "Solution"]:
                for sent in sentences:
                    if fault.name in sent and sol.name in sent:
                        relations.append(
                            Relation(source=fault.name, target=sol.name, type="SOLVED_BY", evidence=sent, confidence=0.75)
                        )
                        break
        for sol in [e for e in entities if e.type == "Solution"]:
            for tool in [e for e in entities if e.type == "Tool"]:
                relations.append(
                    Relation(source=sol.name, target=tool.name, type="REQUIRES_TOOL", evidence=text[:120], confidence=0.7)
                )
            for part in [e for e in entities if e.type == "SparePart"]:
                relations.append(
                    Relation(source=sol.name, target=part.name, type="REQUIRES_PART", evidence=text[:120], confidence=0.7)
                )

        return Candidate(
            chunk_id="",
            document_id="",
            entity_json={"entities": [e.model_dump() for e in entities]},
            relation_json={"relations": [r.model_dump() for r in relations]},
            confidence=0.8,
            status="pending",
        )

    def build_prompt(self, chunk_text: str) -> str:
        entity_labels = ", ".join(e.label for e in self.schema.entities)
        relation_types = "\n".join(
            f"  {r.type}: {r.from_} -> {r.to}" for r in self.schema.relations
        )
        return f"""你是知识图谱抽取专家。请从文本中抽取实体、关系和属性。

只允许使用以下实体类型：
{entity_labels}

只允许使用以下关系类型：
{relation_types}

输出严格 JSON，格式如下：
{{
  "entities": [
    {{
      "name": "实体名称",
      "type": "实体类型",
      "properties": {{}},
      "evidence": "原文片段",
      "confidence": 0.95
    }}
  ],
  "relations": [
    {{
      "source": "源实体名称",
      "target": "目标实体名称",
      "type": "关系类型",
      "properties": {{}},
      "evidence": "原文片段",
      "confidence": 0.9
    }}
  ]
}}

如果文本中没有明显实体或关系，返回空数组。不要编造。

文本：
{chunk_text}
"""

    def extract_chunk(self, chunk: Chunk) -> Candidate:
        if self.mock:
            cand = self._mock_extract(chunk.content)
            cand.chunk_id = chunk.id
            cand.document_id = chunk.document_id
            return cand

        prompt = self.build_prompt(chunk.content)
        system = "你是一个知识图谱抽取专家，只输出合法 JSON。"
        try:
            data = self.llm.chat_completion_json(prompt, system=system)
            data = data if isinstance(data, dict) else {}
            entities = data.get("entities", []) or []
            relations = data.get("relations", []) or []
            candidate = Candidate(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                entity_json={"entities": entities},
                relation_json={"relations": relations},
                confidence=min(
                    1.0,
                    sum(e.get("confidence", 0.8) for e in entities)
                    / max(1, len(entities)),
                ),
                status="pending",
            )
            return candidate
        except Exception as e:
            return Candidate(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                entity_json={"entities": [], "error": str(e)},
                relation_json={"relations": []},
                confidence=0.0,
                status="error",
            )

    def extract_chunks(self, chunks: List[Chunk]) -> List[Candidate]:
        return [self.extract_chunk(c) for c in chunks]
