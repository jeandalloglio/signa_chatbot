import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .rag import RAG

app = FastAPI(title="Chatbot SIGNA")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

rag = RAG()

HTML_PAGE = """
<!DOCTYPE html>
<html lang="pt">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Chatbot SIGNA</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, 'Helvetica Neue', Arial, sans-serif; margin: 0; padding: 0; background: #f7f7f7; }
    header { padding: 16px 20px; background: #0f172a; color: white; }
    main { max-width: 920px; margin: 20px auto; background: white; padding: 16px; border-radius: 12px; box-shadow: 0 6px 20px rgba(0,0,0,.06); }
    .log { height: 56vh; overflow-y: auto; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; }
    .bubble { margin: 10px 0; padding: 12px 14px; border-radius: 10px; line-height: 1.4; }
    .user { background: #e0f2fe; }
    .bot { background: #f1f5f9; }
    form { display: flex; gap: 8px; margin-top: 10px; }
    input[type=text] { flex: 1; padding: 12px; border: 1px solid #cbd5e1; border-radius: 10px; }
    button { background: #0ea5e9; border: 0; color: white; padding: 12px 18px; border-radius: 10px; cursor: pointer; }
    .sources { font-size: 12px; color: #475569; margin-top: 8px; }
    a { color: #0ea5e9; text-decoration: none; }
  </style>
</head>
<body>
<header><strong>Chatbot SIGNA</strong></header>
<main>
  <div class="log" id="log"></div>
  <form id="frm">
    <input type="text" id="q" placeholder="Faça a sua pergunta sobre a SIGNA." autocomplete="off" />
    <button type="submit">Perguntar</button>
  </form>
</main>
<script>
  const log = document.getElementById('log');
  const frm = document.getElementById('frm');
  const q = document.getElementById('q');

  function addBubble(text, who) {
    const div = document.createElement('div');
    div.className = 'bubble ' + who;
    div.innerHTML = text;
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
  }

  frm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const question = q.value.trim();
    if (!question) return;
    addBubble(question, 'user');
    q.value = '';
    addBubble('Pensando', 'bot');
    const resp = await fetch('/ask', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({question}) });
    const data = await resp.json();
    log.lastChild.remove(); // remove "Pensando"
    const srcs = (data.sources || []).map(u => `<a href="${u}" target="_blank">${u}</a>`).join('<br/>');
    addBubble(`${data.answer}<div class="sources"><strong>Fontes</strong><br/>${srcs}</div>`, 'bot');
  });
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def home():
    return HTML_PAGE

@app.post("/ask")
async def ask(payload: dict):
    question = payload.get("question", "")
    result = await rag.answer(question)
    return JSONResponse(result)
