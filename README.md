# AIBES Domain Graph Builder

面向任意行业的知识图谱自动构建与 GraphRAG 应用开发平台（MVP）。

## 第一版功能

1. 上传 PDF / Word / Markdown / TXT
2. 自动解析文本并切块
3. 使用 LLM 自动抽取实体和关系
4. 写入 Neo4j 图数据库
5. 图谱可视化 + 知识问答

## 快速开始

### 1. 启动 Neo4j

```bash
docker compose up -d neo4j
```

Neo4j Browser: http://localhost:7474 （用户名 `neo4j`，密码 `password`）

### 2. 配置 LLM

复制 `.env.example` 为 `.env`，填入你的 OpenAI-compatible API Key：

```bash
cp .env.example .env
```

示例：

```env
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-xxx
LLM_MODEL=gpt-4o-mini
```

如果暂时没有 LLM Key，可设置 `MOCK_LLM=true` 使用内置规则抽取器进行演示。

### 3. 启动后端

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

后端地址：http://localhost:8000
API 文档：http://localhost:8000/docs

### 4. 打开前端

- 方式一：直接用浏览器打开 `frontend/index.html`
- 方式二：访问后端挂载的静态页面 `http://localhost:8000/static/index.html`

## 使用流程

1. 在左侧面板选择文档并上传
2. 点击「解析文本」
3. 点击「抽取知识」（调用 LLM）
4. 点击「写入图谱」（写入 Neo4j）
5. 在中间可视化区域查看图谱，右侧进行问答

## 默认领域 Schema

本 MVP 预置「装备维修」领域 Schema，包括：

- 实体：Equipment, Subsystem, Component, Fault, Symptom, Cause, Solution, Procedure, Tool, SparePart, Supplier, Document, Person, Record
- 关系：HAS_SUBSYSTEM, HAS_COMPONENT, HAS_FAULT, HAS_SYMPTOM, CAUSED_BY, SOLVED_BY, HAS_STEP, REQUIRES_TOOL, REQUIRES_PART, SUPPLIED_BY, MENTIONS, CONFIRMS, PROVIDES

后续版本将支持自定义 Schema 配置与多领域切换。

## 文档

详细的需求分析、架构设计、数据模型、接口设计、部署指南和用户手册见 `docs/` 目录。

## 项目结构

```
.
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── documents.py
│   │   │   ├── graph.py
│   │   │   ├── rag.py
│   │   │   └── schema.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── llm.py
│   │   ├── services/
│   │   │   ├── document_parser.py
│   │   │   ├── chunker.py
│   │   │   ├── extractor.py
│   │   │   ├── graph_writer.py
│   │   │   └── store.py
│   │   └── models/
│   │       └── schema.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── index.html
│   └── app.js
├── docker-compose.yml
├── .env.example
└── README.md
```

## 后续扩展

- PostgreSQL / MinIO / Qdrant 持久化存储
- Celery + Redis 异步任务队列
- 实体对齐与去重
- 人工审核中心
- 自定义领域 Schema 编辑器
- GraphRAG 社区摘要
- 智能业务 Agent

## 技术栈

- 后端：Python FastAPI
- 图数据库：Neo4j
- 文档解析：pdfplumber / python-docx / markdown
- LLM：OpenAI-compatible API
- 前端：原生 HTML + D3.js
- 部署：Docker Compose
