#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
community/server.py · 本地儿童作品社区服务（本地文件存储）

- 提供 JSON API：发布 / 浏览 / 点赞 / 切换公开私有
- 提供可独立打开的社区画廊页（GET /）：展示公开作品、发布表单、点赞、私有/分享开关
- 本地优先：数据全部走 community/store.py（community/data/works.json），不联网

运行：
    python community/server.py --port 8090
演示：
    浏览器打开 http://localhost:8090/
"""

import argparse
import json
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import store  # noqa: E402

PORT = 8090


# --------------------------------------------------------------------------
# 画廊页（内嵌，单文件即可演示）
# --------------------------------------------------------------------------
GALLERY_HTML = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI造物 · 儿童作品社区</title>
<style>
  :root{--bg:#fdf6ec;--card:#fff;--accent:#ff8a3d;--ink:#3a2e25;--muted:#8a7a6d;}
  *{box-sizing:border-box} body{margin:0;font-family:-apple-system,"PingFang SC",sans-serif;
    background:var(--bg);color:var(--ink);padding:24px}
  h1{font-size:22px;margin:0 0 4px} .sub{color:var(--muted);margin:0 0 20px;font-size:13px}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:16px}
  .card{background:var(--card);border-radius:16px;padding:14px;box-shadow:0 4px 14px rgba(0,0,0,.06)}
  .thumb{height:120px;border-radius:12px;display:flex;align-items:center;justify-content:center;
    font-size:40px;color:#fff;text-shadow:0 2px 6px rgba(0,0,0,.25)}
  .title{font-weight:600;margin:10px 0 2px} .author{color:var(--muted);font-size:12px}
  .row{display:flex;justify-content:space-between;align-items:center;margin-top:10px}
  .like{background:var(--accent);color:#fff;border:0;border-radius:20px;padding:6px 12px;
    cursor:pointer;font-size:13px}
  .badge{font-size:11px;padding:2px 8px;border-radius:10px;background:#eee;color:#666}
  .pub{background:#e6f7ec;color:#1f9d55}
  .priv{background:#fdeaea;color:#c0392b}
  form{background:var(--card);border-radius:16px;padding:16px;margin-bottom:22px;
    box-shadow:0 4px 14px rgba(0,0,0,.06)}
  input,textarea{width:100%;padding:8px;margin:6px 0;border:1px solid #e2d8cc;border-radius:8px;
    font-size:14px} textarea{height:70px} .btn{background:var(--ink);color:#fff;border:0;
    border-radius:8px;padding:10px 16px;cursor:pointer} label{font-size:13px;color:var(--muted)}
</style></head>
<body>
<h1>🎨 AI造物 · 儿童作品社区</h1>
<p class="sub">把你的机器人伙伴分享出来，给同龄人的创造点个赞 —— 社区，本身就是激发创造的地方。</p>

<form id="pub"><b>发布我的作品</b>
  <input id="title" placeholder="给作品起个名字，比如「会保护我的小恐龙」">
  <input id="author" placeholder="你的昵称（建议不用真名）">
  <textarea id="contract" placeholder='设计契约 JSON，例如 {"ip_id":"flying-cat", ...}'></textarea>
  <label><input type="checkbox" id="public"> 分享到社区（取消勾选=仅自己保存，私有）</label><br>
  <button class="btn" type="submit">发布</button>
</form>

<h2 style="font-size:16px">社区画廊 · 大家一起点赞</h2>
<div class="grid" id="gallery"><p class="sub">加载中…</p></div>

<script>
const API="";
let owner=localStorage.getItem("kidcomm-owner");
if(!owner){owner=crypto.randomUUID()+crypto.randomUUID();localStorage.setItem("kidcomm-owner",owner);}
const headers={"Content-Type":"application/json","X-Owner-Token":owner};
function esc(s){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
function color(s){return /^#[0-9a-fA-F]{6}$/.test(s)?s:"#cccccc";}

async function load(){
  const r=await fetch(API+"/api/works"); const pub=await r.json();
  const own=await (await fetch(API+"/api/mine",{headers})).json();
  const owned=new Set(own.map(w=>w.id));
  const d=[...new Map([...pub,...own].map(w=>[w.id,w])).values()];
  const g=document.getElementById("gallery"); g.innerHTML="";
  if(!d.length){g.innerHTML='<p class="sub">还没有公开作品，快来发布第一个吧！</p>';return;}
  d.forEach(w=>{
    const c=document.createElement("div"); c.className="card";
    c.innerHTML=`<div class="thumb" style="background:${color(w.color)}">🤖</div>
      <div class="title">${esc(w.title)}</div><div class="author">by ${esc(w.author)}</div>
      <div class="row"><span class="badge ${w.public?'pub':'priv'}">${w.public?'分享中':'私有'}</span>
      <button class="like">❤️ ${Number(w.likes)||0}</button></div>`;
    c.querySelector(".like").onclick=()=>like(w.id);
    if(owned.has(w.id)){
      const toggle=document.createElement("button");
      toggle.textContent=w.public?"仅自己保存":"分享到社区";
      toggle.onclick=async()=>{
        const result=await fetch(API+"/api/works/"+w.id+"/privacy",{method:"POST",headers,body:JSON.stringify({public:!w.public})});
        if(!result.ok){alert("无法修改作品");return;}load();
      };
      c.appendChild(toggle);
    }
    g.appendChild(c);
  });
}
async function like(id){ await fetch(API+"/api/works/"+id+"/like",{method:"POST",
  headers,body:JSON.stringify({liker:"guest"})}); load(); }
document.getElementById("pub").onsubmit=async e=>{
  e.preventDefault();
  let contract; try{contract=JSON.parse(document.getElementById("contract").value||"{}");}
  catch{alert("契约 JSON 格式不对");return;}
  const result=await fetch(API+"/api/works",{method:"POST",headers,
    body:JSON.stringify({title:document.getElementById("title").value,
      author:document.getElementById("author").value,
      public:document.getElementById("public").checked,contract})});
  if(!result.ok){alert("保存失败，请检查设计契约。原内容已保留。");return;}
  document.getElementById("contract").value=""; load();
};
load();
</script></body></html>"""


# --------------------------------------------------------------------------
# 请求处理
# --------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Owner-Token")

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._cors()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body_json(self):
        ln = int(self.headers.get("Content-Length", 0))
        if not 0 <= ln <= 1_000_000:
            raise ValueError("request too large")
        if not ln:
            return {}
        try:
            value = json.loads(self.rfile.read(ln).decode("utf-8"))
            if not isinstance(value, dict):
                raise ValueError("request must be object")
            return value
        except Exception as exc:
            raise ValueError("invalid JSON") from exc

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path == "/design":
            html = (HERE.parent / "web-preview/index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html)
            return
        if self.path == "/api/mine":
            try:
                return self._json(store.list_owned(self.headers.get("X-Owner-Token")))
            except PermissionError:
                return self._json({"error":"需要作品管理凭证"}, 403)
        if self.path == "/" or self.path == "/index.html":
            html = GALLERY_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
            return
        if self.path == "/api/works":
            return self._json(store.list_public())
        if self.path == "/api/stats":
            return self._json(store.stats())
        self._json({"error": "not found"}, 404)

    def do_POST(self):
        try:
            self._post()
        except PermissionError:
            self._json({"error":"无权访问这个作品"}, 403)
        except (ValueError, TypeError, KeyError):
            self._json({"error":"请求或设计契约不合法"}, 400)

    def _post(self):
        if self.path == "/api/works":
            d = self._body_json()
            token = self.headers.get("X-Owner-Token")
            store.owner_id(token)
            if not isinstance(d.get("public", False), bool):
                raise ValueError("public must be boolean")
            w = store.publish(
                contract=d.get("contract", {}),
                title=d.get("title", ""),
                author=d.get("author", ""),
                public=d.get("public", False),
                owner_token=token,
                tags=d.get("tags", []),
            )
            return self._json(w, 201)
        # /api/works/<id>/like  or  /api/works/<id>/privacy
        parts = self.path.strip("/").split("/")
        if len(parts) == 4 and parts[0] == "api" and parts[1] == "works":
            wid, action = parts[2], parts[3]
            d = self._body_json()
            if action == "like":
                token = self.headers.get("X-Owner-Token")
                w = store.like(wid, store.owner_id(token) if token else "guest")
                return self._json(w or {"error": "not found"}, 200 if w else 404)
            if action == "privacy":
                w = store.set_privacy(wid, d.get("public", False), self.headers.get("X-Owner-Token"))
                return self._json(w or {"error": "not found"}, 200 if w else 404)
        self._json({"error": "not found"}, 404)

    def log_message(self, *a):
        pass  # 安静


def main():
    ap = argparse.ArgumentParser(description="儿童作品社区服务")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"[community] 儿童作品社区已启动: http://localhost:{args.port}/")
    if not args.no_browser:
        try:
            import webbrowser
            webbrowser.open(f"http://localhost:{args.port}/")
        except Exception:
            pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()
