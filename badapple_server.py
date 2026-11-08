#!/usr/bin/env python3
"""
Bad Apple → 0/1 đơn giản
GET /read:
  - Gặp 0 → {"value":"00000000"}
  - Gặp 1 → {"value":"10000000"}
  - Tự sang số tiếp theo
"""

import http.server
import socketserver
import threading
import json
import os
from urllib.parse import urlparse

PORT = int(os.environ.get("PORT", 8080))
DATA_FILE = os.path.join(os.path.dirname(__file__), "badapple_16x16-1.txt")

class State:
    def __init__(self):
        self.lock = threading.Lock()
        self.playing = False
        self.index = 0               # vị trí hiện tại trong chuỗi 0/1
        self.data = ""               # toàn bộ 0/1 nối liền

    def load_data(self):
        print("Loading data...")
        with open(DATA_FILE, "r") as f:
            # bỏ hết xuống dòng, chỉ giữ 0 và 1
            self.data = f.read().replace("\n", "").replace(" ", "")
        print(f"Loaded {len(self.data)} bits")

    def get_next(self):
        with self.lock:
            if not self.data:
                return "00000000"

            bit = self.data[self.index]

            if self.playing:
                self.index = (self.index + 1) % len(self.data)

            if bit == "1":
                return "10000000"
            else:
                return "00000000"

    def get_status(self):
        with self.lock:
            return {
                "index": self.index,
                "total": len(self.data),
                "playing": self.playing,
                "current": self.data[self.index] if self.data else "0"
            }

    def start(self):
        with self.lock:
            self.playing = True

    def stop(self):
        with self.lock:
            self.playing = False

    def reset(self):
        with self.lock:
            self.index = 0
            self.playing = False

state = State()

CONTROL_HTML = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bad Apple 0/1</title>
<style>
  :root {
    --bg: #0d1117; --card: #161b22; --border: #30363d;
    --text: #e6edf3; --muted: #8b949e;
    --green: #3fb950; --red: #f85149; --blue: #58a6ff;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: var(--bg); color: var(--text);
    min-height: 100vh; display: flex; flex-direction: column;
    align-items: center; padding: 24px 16px;
  }
  h1 { font-size: 1.5rem; margin-bottom: 6px; }
  .sub { color: var(--muted); font-size: 0.9rem; margin-bottom: 24px; }
  .card {
    background: var(--card); border: 1px solid var(--border);
    border-radius: 12px; padding: 24px; width: 100%; max-width: 400px;
  }
  .info { text-align: center; margin-bottom: 20px; }
  .big { font-size: 2.2rem; font-weight: 700; }
  .status { margin-top: 8px; font-size: 1rem; }
  .status.playing { color: var(--green); }
  .status.stopped { color: var(--red); }
  .btns { display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; margin-top: 16px; }
  button {
    border: none; border-radius: 8px; padding: 12px 26px;
    font-size: 1rem; font-weight: 600; cursor: pointer;
  }
  #btn-start { background: var(--green); color: #000; }
  #btn-stop  { background: var(--red); color: #fff; }
  #btn-reset { background: var(--border); color: var(--text); }
  .links { margin-top: 20px; font-size: 0.85rem; color: var(--muted); text-align: center; }
  .links code { background: #21262d; padding: 2px 6px; border-radius: 4px; color: var(--blue); }
</style>
</head>
<body>
  <h1>Bad Apple 0 → 1</h1>
  <p class="sub">0 = 00000000 &nbsp;|&nbsp; 1 = 10000000</p>

  <div class="card">
    <div class="info">
      <div class="big"><span id="cur">0</span> / <span id="total">0</span></div>
      <div id="status" class="status stopped">● STOPPED</div>
      <div style="margin-top:6px;color:var(--muted)">Hiện tại: <b id="bit">0</b></div>
    </div>

    <div class="btns">
      <button id="btn-start" onclick="doStart()">▶ Start</button>
      <button id="btn-stop"  onclick="doStop()">■ Stop</button>
      <button id="btn-reset" onclick="doReset()">↺ Reset</button>
    </div>
  </div>

  <div class="links">
    Transmitter: <code id="read-url"></code>
  </div>

<script>
async function fetchStatus() {
  try {
    const r = await fetch('/status');
    const j = await r.json();
    document.getElementById('cur').textContent = j.index;
    document.getElementById('total').textContent = j.total;
    document.getElementById('bit').textContent = j.current;
    const st = document.getElementById('status');
    if (j.playing) {
      st.textContent = '● PLAYING';
      st.className = 'status playing';
    } else {
      st.textContent = '● STOPPED';
      st.className = 'status stopped';
    }
  } catch(e) {}
}

async function doStart()  { await fetch('/start',  {method:'POST'}); fetchStatus(); }
async function doStop()   { await fetch('/stop',   {method:'POST'}); fetchStatus(); }
async function doReset()  { await fetch('/reset',  {method:'POST'}); fetchStatus(); }

document.getElementById('read-url').textContent = location.origin + '/read';
setInterval(fetchStatus, 300);
fetchStatus();
</script>
</body>
</html>
"""

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {args[0]}")

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/" or path == "/control":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(CONTROL_HTML.encode("utf-8"))

        elif path == "/read":
            value = state.get_next()
            payload = json.dumps({"value": value}, separators=(",", ":"))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(payload.encode("utf-8"))

        elif path == "/status":
            data = json.dumps(state.get_status())
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data.encode("utf-8"))

        else:
            self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/start":
            state.start()
            self._ok()
        elif path == "/stop":
            state.stop()
            self._ok()
        elif path == "/reset":
            state.reset()
            self._ok()
        else:
            self.send_error(404)

    def _ok(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b"ok")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

def main():
    state.load_data()
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Server running on port {PORT}")
        httpd.serve_forever()

if __name__ == "__main__":
    main()
