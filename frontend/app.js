const API_BASE = "http://localhost:8000";

let currentDocId = null;
let simulation = null;
let allNodes = [];
let allLinks = [];

const typeColors = {
  Equipment: "#e53935",
  Subsystem: "#d81b60",
  Component: "#8e24aa",
  Fault: "#fb8c00",
  Symptom: "#fdd835",
  Cause: "#43a047",
  Solution: "#1e88e5",
  Procedure: "#00acc1",
  Tool: "#6d4c41",
  SparePart: "#78909c",
  Supplier: "#26a69a",
  Document: "#5e35b1",
  Person: "#ec407a",
  Record: "#8d6e63",
};

function color(type) {
  return typeColors[type] || "#607d8b";
}

function setStatus(msg) {
  document.getElementById("pipeline-status").textContent = msg;
}

async function api(path, opts = {}) {
  const res = await fetch(`${API_BASE}${path}`, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// Upload
document.getElementById("btn-upload").addEventListener("click", async () => {
  const input = document.getElementById("file-input");
  if (!input.files.length) return alert("请选择文件");
  const form = new FormData();
  form.append("file", input.files[0]);
  setStatus("正在上传...");
  const data = await api("/documents/upload", { method: "POST", body: form });
  currentDocId = data.document_id;
  setStatus(`上传成功：${data.filename}\nID: ${currentDocId}`);
  document.getElementById("btn-parse").disabled = false;
});

// Parse
document.getElementById("btn-parse").addEventListener("click", async () => {
  if (!currentDocId) return;
  setStatus("正在解析...");
  const data = await api(`/documents/${currentDocId}/parse`, { method: "POST" });
  setStatus(`解析完成：文本长度 ${data.text_length}，切块 ${data.chunks}`);
  document.getElementById("btn-extract").disabled = false;
});

// Extract
document.getElementById("btn-extract").addEventListener("click", async () => {
  if (!currentDocId) return;
  setStatus("正在使用 LLM 抽取实体关系，请稍候...");
  const data = await api(`/documents/${currentDocId}/extract`, { method: "POST" });
  setStatus(`抽取完成：候选数 ${data.candidates}`);
  document.getElementById("btn-write").disabled = false;
});

// Write graph
document.getElementById("btn-write").addEventListener("click", async () => {
  if (!currentDocId) return;
  setStatus("正在写入 Neo4j...");
  const data = await api(`/documents/${currentDocId}/write-graph`, { method: "POST" });
  setStatus(`图谱写入完成：${data.status}`);
  loadStats();
  loadFullGraph();
});

// Search
document.getElementById("btn-search").addEventListener("click", async () => {
  const kw = document.getElementById("search-input").value.trim();
  if (!kw) return;
  const data = await api(`/graph/search?keyword=${encodeURIComponent(kw)}`);
  renderSearchNodes(data.nodes);
});

document.getElementById("btn-load-full").addEventListener("click", loadFullGraph);

// Chat
document.getElementById("btn-chat").addEventListener("click", async () => {
  const input = document.getElementById("chat-input");
  const q = input.value.trim();
  if (!q) return;
  appendChat("user", q);
  input.value = "";
  try {
    const data = await api("/rag/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q }),
    });
    appendChat("bot", data.answer);
  } catch (e) {
    appendChat("bot", "出错：" + e.message);
  }
});

function appendChat(role, text) {
  const box = document.getElementById("chat-history");
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = (role === "user" ? "你：" : "AI：") + text;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

async function loadStats() {
  try {
    const data = await api("/graph/statistics");
    document.getElementById("stats").innerHTML =
      `实体数：${data.entity_count}<br/>关系数：${data.relation_count}<br/>文档数：${data.document_count}`;
  } catch (e) {
    console.error(e);
  }
}

function renderSearchNodes(nodes) {
  const container = d3.select("#graph-svg");
  container.selectAll("*").remove();
  if (!nodes.length) {
    container.append("text").attr("x", 100).attr("y", 100).text("未找到节点");
    return;
  }
  // Render as simple list with click to expand neighbors
  const g = container.append("g").attr("transform", "translate(20,30)");
  g.append("text").attr("font-weight", "bold").text(`找到 ${nodes.length} 个节点：`);
  nodes.forEach((n, i) => {
    const row = g.append("g").attr("transform", `translate(0, ${(i + 1) * 28})`).style("cursor", "pointer");
    row.append("circle").attr("r", 8).attr("fill", color(n.type));
    row.append("text").attr("x", 18).attr("dy", 4).text(`${n.name} (${n.type})`);
    row.on("click", () => loadNeighbors(n.name, n.type));
  });
}

async function loadNeighbors(name, type) {
  const data = await api(`/graph/neighbors?name=${encodeURIComponent(name)}&type=${encodeURIComponent(type)}`);
  const nodes = new Map();
  const links = [];
  data.forEach((path) => {
    path.nodes.forEach((n) => nodes.set(`${n.name}|${n.type}`, n));
    path.relationships.forEach((r) => links.push(r));
  });
  renderGraph(Array.from(nodes.values()), links);
  document.getElementById("node-detail").textContent = JSON.stringify(data, null, 2);
}

async function loadFullGraph() {
  const data = await api("/graph/full");
  renderGraph(data.nodes, data.links);
}

function renderGraph(nodes, links) {
  allNodes = nodes;
  allLinks = links;
  const svg = d3.select("#graph-svg");
  svg.selectAll("*").remove();
  const width = svg.node().parentElement.clientWidth;
  const height = svg.node().parentElement.clientHeight;
  svg.attr("viewBox", [0, 0, width, height]);

  const g = svg.append("g");
  const zoom = d3.zoom().on("zoom", (e) => g.attr("transform", e.transform));
  svg.call(zoom);

  const nodeById = new Map(nodes.map((n) => [`${n.name}|${n.type}`, n]));
  const validLinks = links.filter(
    (l) => nodeById.has(`${l.source}|${l.sourceType || ""}`) && nodeById.has(`${l.target}|${l.targetType || ""}`)
  );

  simulation = d3
    .forceSimulation(nodes)
    .force("link", d3.forceLink(validLinks).id((d) => `${d.name}|${d.type}`).distance(120))
    .force("charge", d3.forceManyBody().strength(-400))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collide", d3.forceCollide().radius(35));

  const link = g
    .append("g")
    .attr("class", "links")
    .selectAll("line")
    .data(validLinks)
    .join("line")
    .attr("class", "link")
    .attr("stroke-width", 1.5);

  const linkLabel = g
    .append("g")
    .selectAll("text")
    .data(validLinks)
    .join("text")
    .attr("class", "link-label")
    .text((d) => d.type);

  const node = g
    .append("g")
    .attr("class", "nodes")
    .selectAll("g")
    .data(nodes)
    .join("g")
    .attr("class", "node")
    .call(d3.drag().on("start", dragstarted).on("drag", dragged).on("end", dragended));

  node.append("circle").attr("r", 18).attr("fill", (d) => color(d.type));
  node
    .append("text")
    .attr("dy", 32)
    .text((d) => d.name.length > 8 ? d.name.slice(0, 8) + "..." : d.name);

  node.on("click", (e, d) => {
    document.getElementById("node-detail").textContent = JSON.stringify(d, null, 2);
  });

  simulation.on("tick", () => {
    link
      .attr("x1", (d) => d.source.x)
      .attr("y1", (d) => d.source.y)
      .attr("x2", (d) => d.target.x)
      .attr("y2", (d) => d.target.y);

    linkLabel
      .attr("x", (d) => (d.source.x + d.target.x) / 2)
      .attr("y", (d) => (d.source.y + d.target.y) / 2);

    node.attr("transform", (d) => `translate(${d.x},${d.y})`);
  });

  updateLegend();
}

function updateLegend() {
  const legend = document.getElementById("legend");
  const types = [...new Set(allNodes.map((n) => n.type))];
  legend.innerHTML =
    "<strong>图例</strong><br/>" +
    types
      .map((t) => `<span style="color:${color(t)}">●</span> ${t}`)
      .join("<br/>");
}

function dragstarted(event, d) {
  if (!event.active) simulation.alphaTarget(0.3).restart();
  d.fx = d.x;
  d.fy = d.y;
}
function dragged(event, d) {
  d.fx = event.x;
  d.fy = event.y;
}
function dragended(event, d) {
  if (!event.active) simulation.alphaTarget(0);
  d.fx = null;
  d.fy = null;
}

loadStats();
