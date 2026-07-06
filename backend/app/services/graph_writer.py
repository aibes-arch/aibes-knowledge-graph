import json
from typing import Dict, List, Any
from neo4j import GraphDatabase
from app.core.config import Settings
from app.models.schema import Candidate


class GraphWriter:
    def __init__(self, settings: Settings):
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

    def close(self):
        self.driver.close()

    def ensure_indexes(self):
        with self.driver.session() as session:
            session.run("CREATE INDEX entity_name_type IF NOT EXISTS FOR (n:Entity) ON (n.name, n.type)")
            session.run("CREATE INDEX entity_type IF NOT EXISTS FOR (n:Entity) ON (n.type)")
            session.run("CREATE INDEX doc_id IF NOT EXISTS FOR (d:Document) ON (d.id)")

    def write_candidates(self, document_id: str, candidates: List[Candidate]):
        with self.driver.session() as session:
            session.execute_write(self._merge_document, document_id)
            for cand in candidates:
                if cand.status == "error":
                    continue
                entities = cand.entity_json.get("entities", [])
                relations = cand.relation_json.get("relations", [])
                for ent in entities:
                    session.execute_write(self._merge_entity, ent, document_id)
                for rel in relations:
                    session.execute_write(self._merge_relation, rel, document_id)
                # Link document to entities mentioned
                for ent in entities:
                    session.execute_write(
                        self._merge_document_mention, document_id, ent.get("name"), ent.get("type")
                    )

    @staticmethod
    def _merge_document(tx, document_id: str):
        query = """
        MERGE (d:Document {id: $document_id})
        SET d.updatedAt = datetime()
        RETURN d
        """
        tx.run(query, document_id=document_id)

    @staticmethod
    def _merge_entity(tx, entity: Dict[str, Any], document_id: str):
        query = """
        MERGE (n:Entity {name: $name, type: $type})
        SET n += $properties
        SET n.confidence = $confidence,
            n.evidence = $evidence,
            n.updatedAt = datetime()
        RETURN n
        """
        tx.run(
            query,
            name=entity.get("name", ""),
            type=entity.get("type", ""),
            properties=entity.get("properties", {}),
            confidence=entity.get("confidence", 0.0),
            evidence=entity.get("evidence", ""),
        )

    @staticmethod
    def _merge_relation(tx, rel: Dict[str, Any], document_id: str):
        query = """
        MATCH (a:Entity {name: $source})
        MATCH (b:Entity {name: $target})
        MERGE (a)-[r:RELATED {type: $type}]->(b)
        SET r += $properties
        SET r.confidence = $confidence,
            r.evidence = $evidence,
            r.updatedAt = datetime()
        RETURN r
        """
        tx.run(
            query,
            source=rel.get("source", ""),
            target=rel.get("target", ""),
            type=rel.get("type", ""),
            properties=rel.get("properties", {}),
            confidence=rel.get("confidence", 0.0),
            evidence=rel.get("evidence", ""),
        )

    @staticmethod
    def _merge_document_mention(tx, document_id: str, entity_name: str, entity_type: str):
        query = """
        MATCH (d:Document {id: $document_id})
        MATCH (e:Entity {name: $entity_name, type: $entity_type})
        MERGE (d)-[m:MENTIONS]->(e)
        SET m.updatedAt = datetime()
        RETURN m
        """
        tx.run(
            query,
            document_id=document_id,
            entity_name=entity_name,
            entity_type=entity_type,
        )

    def search_nodes(self, keyword: str, limit: int = 50):
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (n:Entity)
                WHERE n.name CONTAINS $keyword OR n.evidence CONTAINS $keyword
                RETURN n {.*} AS node
                LIMIT $limit
                """,
                keyword=keyword,
                limit=limit,
            )
            return [record["node"] for record in result]

    def get_neighbors(self, name: str, type_: str, depth: int = 2):
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH path = (n:Entity {name: $name, type: $type})-[:RELATED|MENTIONS*1..%d]-(m)
                RETURN [x IN nodes(path) | x {.*}] AS nodes,
                       [r IN relationships(path) | {source: startNode(r).name, target: endNode(r).name, type: r.type, properties: r {.*}}] AS rels
                LIMIT 100
                """ % depth,
                name=name,
                type=type_,
            )
            return [
                {"nodes": record["nodes"], "relationships": record["rels"]}
                for record in result
            ]

    def get_graph(self, limit: int = 300):
        with self.driver.session() as session:
            nodes_result = session.run(
                """
                MATCH (n:Entity)
                RETURN n {.*} AS node
                LIMIT $limit
                """,
                limit=limit,
            )
            rels_result = session.run(
                """
                MATCH (a:Entity)-[r:RELATED]->(b:Entity)
                RETURN {source: a.name, sourceType: a.type, target: b.name, targetType: b.type, type: r.type, properties: r {.*}} AS rel
                LIMIT $limit
                """,
                limit=limit,
            )
            nodes = [r["node"] for r in nodes_result]
            links = [r["rel"] for r in rels_result]
            return {"nodes": nodes, "links": links}

    def get_statistics(self):
        with self.driver.session() as session:
            node_count = session.run(
                "MATCH (n:Entity) RETURN count(n) AS c"
            ).single()["c"]
            rel_count = session.run(
                "MATCH ()-[r:RELATED]->() RETURN count(r) AS c"
            ).single()["c"]
            doc_count = session.run(
                "MATCH (d:Document) RETURN count(d) AS c"
            ).single()["c"]
            return {
                "entity_count": node_count,
                "relation_count": rel_count,
                "document_count": doc_count,
            }
