"""Loopback-only display of actual QEMU scanout and symbolic input requests."""
import json
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import queue
import re
import secrets
import threading

PAGE='''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Sony A7 IV 6.02 · QEMU</title>
<style>*{box-sizing:border-box}body{margin:0;background:#111318;color:#eef1f7;font:15px system-ui,sans-serif}main{max-width:1060px;margin:30px auto;padding:0 24px}header{display:flex;align-items:center;gap:14px;margin-bottom:20px}h1{font-size:24px;margin:0}small{color:#ffb764;background:#332719;padding:6px 10px;border-radius:6px}.layout{display:flex;gap:28px;align-items:center;flex-wrap:wrap}.screen{width:640px;max-width:100%;height:auto;border:1px solid #3b3f48;border-radius:8px;background:#000}.controls{width:250px}button{border:1px solid #484f5f;border-radius:8px;background:#242936;color:#fff;min-height:48px;font:600 15px system-ui;cursor:pointer}button:hover{background:#3a4254}button:active{background:#985000}button:disabled{opacity:.4;cursor:wait}.pad{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:18px 0}.pad button{font-size:21px}.wide{display:flex;gap:8px}.wide button{flex:1}p{line-height:1.7;color:#aeb6c7}.status{color:#9ae6af}footer{border-top:1px solid #343843;margin-top:26px;padding-top:12px;color:#aeb6c7;font-size:13px}#stop{min-height:34px;margin-top:16px;color:#c2c9d6;font-size:13px}</style>
<style>.layout{display:grid;grid-template-columns:minmax(0,640px)250px}.screen{width:100%}@media(max-width:800px){.layout{grid-template-columns:minmax(0,1fr)210px;gap:16px}.controls{width:210px}}@media(max-width:580px){.layout{grid-template-columns:1fr}.controls{width:100%;max-width:360px}}</style>
<main><header><h1>Sony A7 IV <span style="color:#9aa5b8">6.02</span></h1><small>原厂界面 · 拍摄链路调试中</small></header>
<div class="layout"><img class="screen" id="frame" width="640" height="480" alt="QEMU 当前实际画面"><div class="controls"><div class="status" id="state">连接中…</div><p>方向键导航，Enter 确认。<br>Esc 或 M 返回上层。<br>重启将自动重做初始设置。</p><div class="pad"><span></span><button data-key="UP">↑</button><span></span><button data-key="LEFT">←</button><button data-key="ENTER" style="font-size:15px">确认</button><button data-key="RIGHT">→</button><span></span><button data-key="DOWN">↓</button><span></span></div><div class="wide"><button data-key="MENU">MENU / 返回</button><button id="snapshot">保存截图</button></div><div class="wide" style="margin-top:12px"><button data-key="RESTART">重新启动</button><button id="stop">停止虚拟机</button></div></div></div>
<div style="margin-top:18px;display:flex;gap:8px;flex-wrap:wrap"><button data-key="HALF">半按测试</button><button data-key="SHUTTER">快门测试</button><button data-key="PLAY">回放</button><button data-key="FN">Fn</button><button data-key="DISP">DISP</button><button data-key="DELETE">删除 / C2</button></div>
<footer>画面直接来自 QEMU 和原厂固件。实时取景和照片生成尚未实现；快门测试发送原厂按键事件。带卡配置使用卡槽 2 的 64 MiB 虚拟卡，可进入原厂空卡回放页。重新启动会重设语言、日期和省电选项，并清空虚拟卡及个人设置。</footer></main>
<script>const base=location.pathname,frame=document.querySelector('#frame'),state=document.querySelector('#state');let busy=false,stopped=false;
function refresh(){if(stopped)return;frame.src=base+'frame.png?t='+Date.now();fetch(base+'status.json',{cache:'no-store'}).then(r=>r.json()).then(s=>{state.textContent=s.status;});}
async function action(key){if(busy||stopped)return;busy=true;document.querySelectorAll('[data-key]').forEach(b=>b.disabled=true);try{const r=await fetch(base+'action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key})});const v=await r.json();if(!r.ok)throw Error(v.error);if(key==='STOP'){stopped=true;state.textContent='虚拟机已停止';}else refresh();}catch(e){state.textContent=e.message;}finally{busy=false;document.querySelectorAll('[data-key]').forEach(b=>b.disabled=false);}}
document.querySelectorAll('[data-key]').forEach(b=>b.onclick=()=>action(b.dataset.key));document.querySelector('#stop').onclick=()=>action('STOP');document.querySelector('#snapshot').onclick=()=>{const link=document.createElement('a');link.href=base+'frame.png';link.download='a7m4-qemu.png';link.click();};
document.addEventListener('keydown',e=>{const key={ArrowUp:'UP',ArrowDown:'DOWN',ArrowLeft:'LEFT',ArrowRight:'RIGHT',Enter:'ENTER',Escape:'MENU',m:'MENU',M:'MENU'}[e.key];if(key){e.preventDefault();if(!e.repeat)action(key);}});refresh();setInterval(refresh,500);</script></html>'''

class Panel:
    def __init__(self,port,initial,token=None):
        self.frame=initial;self.status='原厂界面已显示；取景和照片保存尚未实现';self.actions=queue.Queue(maxsize=8)
        if token is not None and not re.fullmatch(r'[A-Za-z0-9_-]{24,64}',token):raise ValueError('Invalid local panel token')
        self.token=token or secrets.token_urlsafe(24);self.prefix='/'+self.token+'/'
        owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def respond(self,status,body,mime):
                self.send_response(status);self.send_header('Content-Type',mime)
                self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store')
                self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer')
                try:self.end_headers();self.wfile.write(body)
                except (BrokenPipeError,ConnectionResetError):pass
            def do_GET(self):
                path=self.path.split('?',1)[0]
                if not path.startswith(owner.prefix):return self.respond(404,b'Not found','text/plain')
                suffix=path[len(owner.prefix):]
                if suffix=='':return self.respond(200,PAGE.encode(),'text/html; charset=utf-8')
                if suffix=='frame.png':return self.respond(200,owner.frame,'image/png')
                if suffix=='status.json':return self.respond(200,json.dumps({'status':owner.status}).encode(),'application/json')
                return self.respond(404,b'Not found','text/plain')
            def do_POST(self):
                try:
                    if self.path!=owner.prefix+'action':raise ValueError('Unknown endpoint')
                    origin=self.headers.get('Origin')
                    if origin and origin not in {f'http://localhost:{port}',f'http://127.0.0.1:{port}'}:raise ValueError('Invalid origin')
                    length=int(self.headers.get('Content-Length','0'))
                    if not 1<=length<=128:raise ValueError('Invalid length')
                    key=json.loads(self.rfile.read(length)).get('key')
                    if key not in {'MENU','UP','DOWN','LEFT','RIGHT','ENTER','DELETE','HALF','SHUTTER','PLAY','FN','DISP','STOP','RESTART'}:raise ValueError('Unknown key')
                    event=threading.Event();result={}
                    owner.actions.put_nowait((key,event,result))
                    if not event.wait(160 if key=='RESTART' else 20):raise TimeoutError('虚拟机响应超时')
                    if 'error' in result:raise RuntimeError(result['error'])
                    self.respond(200,b'{"ok":true}','application/json')
                except Exception as error:
                    self.respond(400,json.dumps({'error':str(error)},ensure_ascii=False).encode(),'application/json; charset=utf-8')
        self.server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://localhost:{port}'+self.prefix
    def close(self):self.server.shutdown();self.server.server_close()

