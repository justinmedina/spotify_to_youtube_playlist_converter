# main.py
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from database import Base, engine
import models  # registers tables

from spotify_auth import router as spotify_auth_router
from google_auth import router as google_auth_router
from routes import router as app_router

app = FastAPI(title="Spotify->YT")

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

app.include_router(spotify_auth_router, prefix="/auth/spotify", tags=["spotify-auth"])
app.include_router(google_auth_router, prefix="/auth/google", tags=["google-auth"])
app.include_router(app_router, tags=["app"])


@app.get("/", response_class=HTMLResponse)
def home():
    return """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Spotify → YouTube</title>
  <style>
    :root{
      --bg: #0b0f19;
      --card: rgba(255,255,255,0.06);
      --border: rgba(255,255,255,0.10);
      --text: rgba(255,255,255,0.92);
      --muted: rgba(255,255,255,0.65);
      --accent: #7c3aed;
      --accent2: #22c55e;
      --danger: #ef4444;
    }
    body{
      margin:0;
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial;
      background: radial-gradient(1200px 800px at 30% 20%, rgba(124,58,237,0.22), transparent 60%),
                  radial-gradient(900px 700px at 80% 40%, rgba(34,197,94,0.18), transparent 55%),
                  var(--bg);
      color: var(--text);
    }
    .wrap{
      max-width: 980px;
      margin: 0 auto;
      padding: 28px 18px 60px;
    }
    .top{
      display:flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
      margin-bottom: 16px;
    }
    .title{
      display:flex;
      flex-direction: column;
      gap: 6px;
    }
    h1{
      font-size: 28px;
      margin:0;
      letter-spacing: -0.02em;
    }
    .subtitle{
      color: var(--muted);
      font-size: 14px;
      margin:0;
    }
    .pill{
      display:inline-flex;
      align-items:center;
      gap:8px;
      padding: 10px 12px;
      border: 1px solid var(--border);
      border-radius: 999px;
      background: rgba(255,255,255,0.04);
      color: var(--muted);
      font-size: 13px;
    }
    .grid{
      display:grid;
      grid-template-columns: 1fr;
      gap: 14px;
      margin-top: 18px;
    }
    @media (min-width: 900px){
      .grid{
        grid-template-columns: 1fr 1fr;
      }
    }
    .card{
      border: 1px solid var(--border);
      background: var(--card);
      border-radius: 18px;
      padding: 16px;
      backdrop-filter: blur(10px);
      box-shadow: 0 12px 30px rgba(0,0,0,0.30);
    }
    .card h3{
      margin:0 0 10px 0;
      font-size: 16px;
    }
    .row{
      display:flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
    }
    .input{
      flex:1;
      min-width: 220px;
      padding: 10px 12px;
      border-radius: 12px;
      border: 1px solid var(--border);
      background: rgba(0,0,0,0.25);
      color: var(--text);
      outline: none;
    }
    .input.small{
      min-width: 120px;
      width: 120px;
      flex: 0 0 auto;
    }
    .btn{
      border: 1px solid var(--border);
      background: rgba(255,255,255,0.06);
      color: var(--text);
      padding: 10px 12px;
      border-radius: 12px;
      cursor: pointer;
      font-weight: 600;
      transition: transform 0.05s ease, background 0.15s ease;
    }
    .btn:hover{
      background: rgba(255,255,255,0.10);
    }
    .btn:active{
      transform: translateY(1px);
    }
    .btn.primary{
      border-color: rgba(124,58,237,0.45);
      background: rgba(124,58,237,0.18);
    }
    .btn.green{
      border-color: rgba(34,197,94,0.45);
      background: rgba(34,197,94,0.18);
    }
    .btn.red{
      border-color: rgba(239,68,68,0.45);
      background: rgba(239,68,68,0.18);
    }
    .muted{
      color: var(--muted);
      font-size: 13px;
      margin-top: 8px;
      line-height: 1.35;
    }
    .footerRow{
      display:flex;
      justify-content: space-between;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
      margin-top: 14px;
    }
    pre{
      margin: 0;
      border-radius: 16px;
      border: 1px solid var(--border);
      background: rgba(0,0,0,0.35);
      padding: 14px;
      overflow:auto;
      max-height: 340px;
      color: rgba(255,255,255,0.88);
      font-size: 12.5px;
      line-height: 1.35;
    }
    .label{
      display:flex;
      gap: 8px;
      align-items:center;
      user-select:none;
      color: var(--muted);
      font-size: 13px;
    }
    a{
      color: rgba(255,255,255,0.92);
      text-decoration: none;
      border-bottom: 1px dashed rgba(255,255,255,0.35);
    }
    a:hover{
      border-bottom-color: rgba(255,255,255,0.75);
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="top">
      <div class="title">
        <h1>Spotify → YouTube Playlist Converter</h1>
        <p class="subtitle">One-tab dashboard. Auth, sync, transfer, debug.</p>
      </div>
      <div class="pill">⚠️ Tip: YouTube search eats quota fast — transfer in small batches (10–20)</div>
    </div>

    <div class="grid">
      <div class="card">
        <h3>1) Auth</h3>
        <div class="row">
          <button class="btn primary" onclick="go('/auth/spotify/login')">Login Spotify</button>
          <button class="btn green" onclick="go('/auth/google/login')">Login Google</button>
          <button class="btn" onclick="refreshStatus()">Refresh Status</button>
          <button class="btn" onclick="go('/docs')">Open /docs</button>
        </div>
        <div class="muted">
          After signing in, come back here and run sync + transfer.
        </div>
      </div>

      <div class="card">
        <h3>2) Sync Spotify liked songs → DB</h3>
        <div class="row">
          <input id="syncLimit" class="input small" type="number" value="200" min="1" />
          <button class="btn primary" onclick="syncLiked()">Sync liked songs</button>
        </div>
        <div class="muted">
          This downloads liked songs in pages of 50 and stores them in SQLite (<code>songs.db</code>).
        </div>
      </div>

      <div class="card">
        <h3>3) Transfer → YouTube playlist</h3>
        <div class="row">
          <input id="plTitle" class="input" type="text" value="Spotify Liked Songs" />
        </div>
        <div class="row" style="margin-top:10px;">
          <input id="transferLimit" class="input small" type="number" value="10" min="1" />
          <label class="label">
            <input id="newPlaylist" type="checkbox" />
            New playlist
          </label>
          <button class="btn green" onclick="transfer()">Transfer</button>
        </div>
        <div class="muted">
          Uses your saved playlist_id by default so you can run this multiple times and it keeps appending.
        </div>
      </div>

      <div class="card">
        <h3>4) Debug</h3>
        <div class="row">
          <button class="btn" onclick="refreshStatus()">Status counts</button>
          <button class="btn red" onclick="loadFailed()">Show failed (last 10)</button>
        </div>
        <div class="muted">
          If you see <code>quotaExceeded</code>, just wait for reset or lower batch size.
        </div>
      </div>
    </div>

    <div class="footerRow">
      <h3 style="margin: 0;">Output</h3>
      <span class="muted">API: <a href="/health">/health</a></span>
    </div>

    <div class="card" style="margin-top: 12px;">
      <pre id="out">{}</pre>
    </div>
  </div>

<script>
  function setOut(obj) {
    document.getElementById('out').textContent =
      typeof obj === 'string' ? obj : JSON.stringify(obj, null, 2);
  }

  function go(path) {
    window.location.href = path;
  }

  async function callJson(url, opts={}) {
    const res = await fetch(url, opts);
    const text = await res.text();
    try { return { ok: res.ok, status: res.status, data: JSON.parse(text) }; }
    catch { return { ok: res.ok, status: res.status, data: text }; }
  }

  async function refreshStatus() {
    const r = await callJson('/tracks/status_counts');
    setOut(r);
  }

  async function syncLiked() {
    const limit = document.getElementById('syncLimit').value || 200;
    const r = await callJson(`/spotify/sync_liked?limit=${encodeURIComponent(limit)}`);
    setOut(r);
    await refreshStatus();
  }

  async function transfer() {
    const title = document.getElementById('plTitle').value || 'Spotify Liked Songs';
    const limit = document.getElementById('transferLimit').value || 10;
    const np = document.getElementById('newPlaylist').checked;

    const url = `/transfer/youtube?playlist_title=${encodeURIComponent(title)}&limit=${encodeURIComponent(limit)}&new_playlist=${np}`;
    const r = await callJson(url, { method: 'POST' });
    setOut(r);
    await refreshStatus();
  }

  async function loadFailed() {
    const r = await callJson('/tracks/failed?limit=10');
    setOut(r);
  }

  refreshStatus();
</script>

</body>
</html>
"""


@app.get("/health")
def health():
    return {"ok": True}

