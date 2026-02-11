from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.auth import is_read_authenticated_request

router = APIRouter()


@router.get("/logs", response_class=HTMLResponse)
async def logs_view(request: Request) -> Response:
    if not is_read_authenticated_request(request):
        return RedirectResponse(url="/login", status_code=303)

    html = """<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Pixie Audit Logs</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f3ef;
      --panel: #ffffff;
      --ink: #1f1d1b;
      --muted: #6b6460;
      --accent: #c45a2a;
      --assistant: #2f6f7b;
      --user: #9a3e6e;
      --summary: #2e6b3f;
      --system: #5b5b73;
      --border: #e5ddd6;
      --shadow: 0 10px 30px rgba(21, 16, 12, 0.08);
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Space Grotesk", "Avenir Next", "Segoe UI", sans-serif;
      background: radial-gradient(circle at top left, #fff8f0 0%, #f3efe9 40%, #efe7df 100%);
      color: var(--ink);
    }

    .app {
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      padding: 24px;
      gap: 16px;
    }

    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px 20px;
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 18px;
      box-shadow: var(--shadow);
    }

    header h1 {
      margin: 0;
      font-size: 20px;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }

    header .subtitle {
      color: var(--muted);
      font-size: 13px;
    }

    .layout {
      flex: 1;
      display: grid;
      grid-template-columns: 320px 1fr;
      gap: 16px;
    }

    .panel {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 18px;
      box-shadow: var(--shadow);
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }

    .sidebar {
      min-height: 0;
    }

    .filters {
      padding: 16px;
      border-bottom: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .filters label {
      font-size: 12px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    .filters input {
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 10px 12px;
      font-size: 14px;
      font-family: inherit;
      background: #fffaf6;
    }

    .filters button {
      border: none;
      background: var(--accent);
      color: #fff;
      padding: 10px 12px;
      border-radius: 10px;
      cursor: pointer;
      font-weight: 600;
      letter-spacing: 0.02em;
    }

    .conversation-list {
      overflow: auto;
      padding: 8px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .conversation {
      padding: 12px;
      border-radius: 12px;
      border: 1px solid transparent;
      background: #fffaf6;
      cursor: pointer;
      display: flex;
      flex-direction: column;
      gap: 4px;
      transition: transform 0.2s ease, border-color 0.2s ease;
    }

    .conversation:hover {
      transform: translateY(-1px);
      border-color: var(--accent);
    }

    .conversation.active {
      border-color: var(--accent);
      background: #fff3ea;
    }

    .conversation .title {
      font-weight: 600;
      font-size: 14px;
    }

    .conversation .meta {
      font-size: 12px;
      color: var(--muted);
    }

    .main {
      min-height: 0;
    }

    .main-header {
      padding: 16px;
      border-bottom: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .main-header .title {
      font-weight: 600;
      font-size: 16px;
    }

    .main-header .meta {
      font-size: 12px;
      color: var(--muted);
    }

    .messages {
      flex: 1;
      overflow: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .message {
      padding: 12px 14px;
      border-radius: 14px;
      background: #fffaf6;
      border: 1px solid var(--border);
      display: grid;
      gap: 8px;
    }

    .message .meta {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 12px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }

    .message .role {
      font-weight: 700;
    }

    .message .content {
      white-space: pre-wrap;
      line-height: 1.4;
      font-size: 14px;
    }

    .role-assistant .role { color: var(--assistant); }
    .role-user .role { color: var(--user); }
    .role-summary .role { color: var(--summary); }
    .role-system .role { color: var(--system); }

    .empty {
      color: var(--muted);
      font-size: 14px;
      text-align: center;
      padding: 24px;
    }

    @media (max-width: 900px) {
      .layout {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <div class="app">
    <header>
      <div>
        <h1>Pixie Audit</h1>
        <div class="subtitle">Conversaties en logs in een overzicht</div>
      </div>
      <div class="subtitle" id="status">Laden...</div>
    </header>

    <section class="layout">
      <aside class="panel sidebar">
        <div class="filters">
          <label for="server-location">Location (server filter)</label>
          <input id="server-location" type="text" placeholder="Bijv. Antwerpen" />
          <label for="server-from">Vanaf (server filter)</label>
          <input id="server-from" type="datetime-local" />
          <label for="server-to">Tot (server filter)</label>
          <input id="server-to" type="datetime-local" />
          <label for="filter">Zoek lokaal in lijst</label>
          <input id="filter" type="text" placeholder="Zoek op profiel of conversation id" />
          <button id="refresh" type="button">Ververs lijst</button>
        </div>
        <div class="conversation-list" id="conversation-list"></div>
      </aside>

      <main class="panel main">
        <div class="main-header">
          <div class="title" id="conversation-title">Selecteer een conversatie</div>
          <div class="meta" id="conversation-meta">Klik links om de messages te laden.</div>
        </div>
        <div class="messages" id="messages"></div>
      </main>
    </section>
  </div>

  <script>
    const state = {
      conversations: [],
      selectedId: null,
    };

    const listEl = document.getElementById("conversation-list");
    const serverLocationEl = document.getElementById("server-location");
    const serverFromEl = document.getElementById("server-from");
    const serverToEl = document.getElementById("server-to");
    const filterEl = document.getElementById("filter");
    const statusEl = document.getElementById("status");
    const messagesEl = document.getElementById("messages");
    const titleEl = document.getElementById("conversation-title");
    const metaEl = document.getElementById("conversation-meta");

    const formatter = new Intl.DateTimeFormat("nl-BE", {
      dateStyle: "medium",
      timeStyle: "short",
    });

    function formatTime(value) {
      if (!value) return "-";
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return value;
      return formatter.format(date);
    }

    function setStatus(text) {
      statusEl.textContent = text;
    }

    function localDateTimeToIso(value) {
      if (!value) return null;
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return null;
      return date.toISOString();
    }

    function conversationsUrl() {
      const params = new URLSearchParams({ limit: "200" });
      const location = serverLocationEl.value.trim();
      if (location) params.set("location", location);

      const fromIso = localDateTimeToIso(serverFromEl.value);
      if (fromIso) params.set("from", fromIso);

      const toIso = localDateTimeToIso(serverToEl.value);
      if (toIso) params.set("to", toIso);

      return `/conversations?${params.toString()}`;
    }

    function renderList() {
      listEl.innerHTML = "";
      const query = filterEl.value.trim().toLowerCase();
      const filtered = state.conversations.filter((item) => {
        if (!query) return true;
        return (
          item.id.toLowerCase().includes(query) ||
          (item.profile || "").toLowerCase().includes(query)
        );
      });

      if (!filtered.length) {
        const empty = document.createElement("div");
        empty.className = "empty";
        empty.textContent = "Geen conversaties gevonden.";
        listEl.appendChild(empty);
        return;
      }

      filtered.forEach((conv) => {
        const row = document.createElement("div");
        row.className = "conversation" + (conv.id === state.selectedId ? " active" : "");
        row.addEventListener("click", () => selectConversation(conv));

        const title = document.createElement("div");
        title.className = "title";
        title.textContent = conv.profile || "(geen profiel)";

        const meta = document.createElement("div");
        meta.className = "meta";
        meta.textContent = `${formatTime(conv.started_at)} -> ${formatTime(conv.ended_at)}`;

        const id = document.createElement("div");
        id.className = "meta";
        id.textContent = conv.id;

        row.appendChild(title);
        row.appendChild(meta);
        row.appendChild(id);
        listEl.appendChild(row);
      });
    }

    function setConversationHeader(conv) {
      if (!conv) {
        titleEl.textContent = "Selecteer een conversatie";
        metaEl.textContent = "Klik links om de messages te laden.";
        return;
      }
      titleEl.textContent = conv.profile || "(geen profiel)";
      metaEl.textContent = `${conv.id} - ${formatTime(conv.started_at)} -> ${formatTime(conv.ended_at)}`;
    }

    function renderMessages(messages) {
      messagesEl.innerHTML = "";
      if (!messages.length) {
        const empty = document.createElement("div");
        empty.className = "empty";
        empty.textContent = "Geen messages voor deze conversatie.";
        messagesEl.appendChild(empty);
        return;
      }

      messages.forEach((message) => {
        const wrapper = document.createElement("div");
        const role = message.role || "unknown";
        wrapper.className = `message role-${role}`;

        const meta = document.createElement("div");
        meta.className = "meta";

        const roleEl = document.createElement("span");
        roleEl.className = "role";
        roleEl.textContent = role;

        const timeEl = document.createElement("span");
        timeEl.textContent = formatTime(message.created_at);

        meta.appendChild(roleEl);
        meta.appendChild(timeEl);

        const content = document.createElement("div");
        content.className = "content";
        content.textContent = message.content || "";

        wrapper.appendChild(meta);
        wrapper.appendChild(content);
        messagesEl.appendChild(wrapper);
      });
    }

    async function loadConversations() {
      setStatus("Lijst laden...");
      try {
        const response = await fetch(conversationsUrl());
        if (!response.ok) {
          throw new Error(`Server status ${response.status}`);
        }
        const data = await response.json();
        state.conversations = data || [];
        if (state.selectedId && !state.conversations.some((item) => item.id === state.selectedId)) {
          state.selectedId = null;
          setConversationHeader(null);
          renderMessages([]);
        }
        renderList();
        setStatus(`${state.conversations.length} conversaties geladen`);
      } catch (error) {
        console.error(error);
        setStatus("Laden mislukt");
        listEl.innerHTML = "";
        const empty = document.createElement("div");
        empty.className = "empty";
        empty.textContent = "Fout bij laden van conversaties.";
        listEl.appendChild(empty);
      }
    }

    async function selectConversation(conv) {
      state.selectedId = conv.id;
      renderList();
      setConversationHeader(conv);
      renderMessages([]);

      const loading = document.createElement("div");
      loading.className = "empty";
      loading.textContent = "Messages laden...";
      messagesEl.appendChild(loading);

      try {
        const response = await fetch(`/conversations/${encodeURIComponent(conv.id)}/messages`);
        if (!response.ok) {
          throw new Error(`Server status ${response.status}`);
        }
        const data = await response.json();
        renderMessages(data || []);
      } catch (error) {
        console.error(error);
        renderMessages([]);
      }
    }

    function loadConversationsOnEnter(event) {
      if (event.key !== "Enter") return;
      event.preventDefault();
      loadConversations();
    }

    document.getElementById("refresh").addEventListener("click", loadConversations);
    filterEl.addEventListener("input", renderList);
    serverLocationEl.addEventListener("keydown", loadConversationsOnEnter);
    serverFromEl.addEventListener("keydown", loadConversationsOnEnter);
    serverToEl.addEventListener("keydown", loadConversationsOnEnter);

    loadConversations();
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html)
