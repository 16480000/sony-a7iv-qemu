"""Loopback-only display of actual QEMU scanout and symbolic input requests.

The page can also take a local video as a client-side virtual sensor input:
the browser uploads it to this loopback service, FFmpeg transcodes it to a
browser-playable H.264 file, and the canvas composites the QEMU OSD over it.
This is an emulator display layer, not original camera ISP/sensor output.
"""
import json, os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs
import queue
import re
import secrets
import subprocess
import threading

PAGE='''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Sony A7 IV 6.02 · QEMU</title>
<style>*{box-sizing:border-box}body{margin:0;background:#111318;color:#eef1f7;font:15px system-ui,sans-serif}main{max-width:1060px;margin:30px auto;padding:0 24px}header{display:flex;align-items:center;gap:14px;margin-bottom:20px}h1{font-size:24px;margin:0}small{color:#ffb764;background:#332719;padding:6px 10px;border-radius:6px}.layout{display:flex;gap:28px;align-items:center;flex-wrap:wrap}.screen{width:640px;max-width:100%;height:auto;border:1px solid #3b3f48;border-radius:8px;background:#000;display:block}.controls{width:250px}button{border:1px solid #484f5f;border-radius:8px;background:#242936;color:#fff;min-height:48px;font:600 15px system-ui;cursor:pointer}button:hover{background:#3a4254}button:active{background:#985000}button:disabled{opacity:.4;cursor:wait}.pad{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:18px 0}.pad button{font-size:21px}.wide{display:flex;gap:8px}.wide button{flex:1}.wide select{border:1px solid #484f5f;border-radius:8px;background:#242936;color:#fff;min-height:48px;font:14px system-ui;padding:0 6px}p{line-height:1.7;color:#aeb6c7}.status{color:#9ae6af}footer{border-top:1px solid #343843;margin-top:26px;padding-top:12px;color:#aeb6c7;font-size:13px}#stop{min-height:34px;margin-top:16px;color:#c2c9d6;font-size:13px}#videoState{margin-top:12px;font-size:13px;line-height:1.5}.screenWrap{position:relative;line-height:0}.playOverlay{display:none;position:absolute;inset:0;pointer-events:none;color:#fff;font:13px system-ui,sans-serif;line-height:1.4}.playOverlay.show{display:block}.playBar{position:absolute;left:0;right:0;display:flex;align-items:center;gap:12px;padding:10px 14px;background:linear-gradient(180deg,rgba(0,0,0,.78),rgba(0,0,0,.55))}.playTop{top:0;justify-content:space-between}.playBottom{bottom:0;justify-content:space-between;background:linear-gradient(0deg,rgba(0,0,0,.82),rgba(0,0,0,.55));pointer-events:auto}.playLabel{color:#ffb764;font-weight:700}.playBottom button{min-height:32px;padding:4px 12px;font-size:13px;pointer-events:auto}</style>
<style>.layout{display:grid;grid-template-columns:minmax(0,640px)250px}.screen{width:100%}@media(max-width:800px){.layout{grid-template-columns:minmax(0,1fr)210px;gap:16px}.controls{width:210px}}@media(max-width:580px){.layout{grid-template-columns:1fr}.controls{width:100%;max-width:360px}}</style>
<main><header><h1>Sony A7 IV <span style="color:#9aa5b8">6.02</span></h1><small>网页视频合成 · 非原厂 ISP</small></header>
<div class="layout"><div class="screenWrap"><canvas class="screen" id="screen" width="640" height="480"></canvas><img id="frame" alt="" style="display:none"><video id="videoEl" muted loop playsinline style="display:none"></video><div class="playOverlay" id="playOverlay"><div class="playBar playTop"><span class="playLabel">▶ 回放</span><span>DSC00001.JPG</span><span>1/1 · JPEG</span></div><div class="playBar playBottom"><button id="playBack">MENU 返回</button><span>虚拟照片回放 · 非原厂解码</span></div></div></div><div class="controls"><div class="status" id="state">连接中…</div><p>方向键导航，Enter 确认。<br>Esc 或 M 返回上层。<br>选择本地视频后会立即合成到原厂 OSD 下方。<br>回放为网页虚拟照片层；固件反馈音来自原厂注册表/请求。<br>下方网页快门音仅作试听，与固件路径无关。</p><div class="pad"><span></span><button data-key="UP">↑</button><span></span><button data-key="LEFT">←</button><button data-key="ENTER" style="font-size:15px">确认</button><button data-key="RIGHT">→</button><span></span><button data-key="DOWN">↓</button><span></span></div><div class="wide"><button data-key="MENU">MENU / 返回</button><button id="snapshot">保存合成画面</button></div><div class="wide" style="margin-top:12px"><button data-key="RESTART">重新启动</button><button id="stop">停止虚拟机</button></div><div class="wide" style="margin-top:12px"><button id="pickVideo">选择视频</button><select id="fit"><option value="contain">适应</option><option value="cover">填充</option></select></div><div class="wide" style="margin-top:8px"><button id="sound">开启声音</button><button id="sysSound">网页合成音：关</button></div><div style="margin-top:14px;font-size:13px;color:#aeb6c7">固件反馈音（原厂音效表 / AP 请求）</div><div class="wide" style="margin-top:6px"><button id="fwSound">固件音：开</button><button id="fwReplay" style="flex:0 0 72px">重放</button></div><div class="wide" style="margin-top:6px"><select id="fwRate" style="flex:0 0 154px"><option value="auto">固件头自动（48/16 千赫）</option><option value="8">8 千赫</option><option value="16">16 千赫</option><option value="24">24 千赫</option><option value="32">32 千赫</option><option value="48">48 千赫</option></select><span style="font-size:12px;color:#aeb6c7;align-self:center">原厂音效资源</span></div><div class="wide" style="margin-top:6px"><select id="cpShutter" style="flex:1"><option value="silent">快门音：电子快门静音（原厂）</option><option value="mechanical">快门音：机械 Ka+Sha</option><option value="kasha">快门音：试听 Kasha（虚拟 CP）</option><option value="continuous">快门音：Kasha 连续（虚拟 CP）</option></select><button id="cpFocus" style="flex:0 0 86px">对焦音：开</button></div><div style="margin-top:2px;font-size:12px;color:#aeb6c7">A7 IV 电子快门原厂无提示音；机械/试听选项仅用于虚拟 CP 测试。</div><div class="status" id="fwState" style="margin-top:6px">等待固件音效…</div><div style="margin-top:2px;font-size:12px;color:#aeb6c7" id="fwLog">—</div><div style="margin-top:14px;font-size:13px;color:#aeb6c7">旧实验：网页快门音（与固件反馈无关）</div><div class="wide" style="margin-top:6px"><select id="shutterSound" style="flex:1"><option value="synth">合成哔声</option><option value="ka8">原厂候选 · 8 千赫（实验）</option><option value="ka16">原厂候选 · 16 千赫（实验）</option><option value="kasha8">Kasha 候选 · 8 千赫（实验）</option><option value="custom">自定义文件</option><option value="off">静音</option></select><button id="testShutterSound" style="flex:0 0 64px">试听</button></div><div class="wide" style="margin-top:6px"><button id="pickShutterSound">选择自定义快门音</button></div><div class="status" id="shutterState" style="margin-top:6px">快门音：合成哔声</div><div style="margin-top:2px;font-size:12px"><a href="sounds/shutter-ka-sha-8k.wav" download style="color:#9ae6af">下载 8k 候选</a> · <a href="sounds/shutter-ka-sha-16k.wav" download style="color:#9ae6af">下载 16k 候选</a></div><input id="shutterFile" type="file" accept="audio/*" hidden><div class="status" id="videoState">未选择视频</div><input id="videoFile" type="file" accept="video/*" hidden></div></div>
<div style="margin-top:18px;display:flex;gap:8px;flex-wrap:wrap"><button data-key="HALF">半按测试</button><button data-key="SHUTTER">原厂快门</button><button id="shutter">网页拍照</button><button id="playPhoto">回放</button><button data-key="FN">Fn</button><button data-key="DISP">DISP</button><button data-key="DELETE">删除 / C2</button></div>
<footer>画面中的原厂 OSD 来自 QEMU。视频由浏览器直接解码并与 OSD 合成；它不是原厂 ISP/传感器输出。视频会先上传到本机回环服务，再由本机 FFmpeg 转成 H.264 后播放。“保存合成画面”保存当前视频+OSD 的 JPEG。原厂按键仍通过右侧/下方按钮发送。回放画面/JPEG 列表是网页虚拟层；JPEG 本身已真实写入虚拟卡。扬声器中的“固件反馈音”有两条来源：原厂 AP 确实发出的 adf_sys_request（显示为 AP），以及缺失 CP 的虚拟化触发（半按/快门/菜单等，显示为虚拟 CP 注册表）。两条都读取固件描述符/注册表指向的 SysSound.bin 资源；原厂 CP/AIP 的解码与触发逻辑尚未执行，采样率是宿主渲染参数，因此资源和注册表/描述符来自固件，音色与 CP 触发时序仍是近似。网页不具备、也不会执行真机固件刷写；旧实验的网页候选只在本页播放，与固件反馈音无关。新的固件反馈音按每个 SysSound 条目跳过一个 1 字节头后渲染，不再使用“每 32 字节块切分”：原厂 CP/AIP 解码器仍未执行，音色与采样率是宿主近似，但注册表、描述符与音效字节都来自 guest 固件。</footer></main>
<script>const base=location.pathname,frame=document.querySelector('#frame'),screen=document.querySelector('#screen'),ctx=screen.getContext('2d'),state=document.querySelector('#state'),video=document.querySelector('#videoEl'),videoState=document.querySelector('#videoState'),fileInput=document.querySelector('#videoFile'),fit=document.querySelector('#fit'),sound=document.querySelector('#sound'),playOverlay=document.querySelector('#playOverlay'),sysSoundBtn=document.querySelector('#sysSound'),shutterSel=document.querySelector('#shutterSound'),shutterState=document.querySelector('#shutterState'),shutterFileInput=document.querySelector('#shutterFile');let busy=false,stopped=false,uiReady=false,photoView=false,photoBusy=false,lastPhoto=null;
frame.onload=()=>{uiReady=true;};
function setPhotoView(on){photoView=on;playOverlay.classList.toggle('show',on);document.querySelector('#playPhoto').textContent=on?'返回取景':'回放';}
function closePhotoView(){if(!photoView)return;setPhotoView(false);videoState.textContent='已回到取景';}
function openPhotoView(){setPhotoView(true);videoState.textContent='网页照片回放（虚拟回放层；原厂 JPEG 解码未建模）';}
let audioCtx=null,sysSoundOn=false;
function ensureAudio(){try{if(!audioCtx)audioCtx=new(window.AudioContext||window.webkitAudioContext)();if(audioCtx.state==='suspended')audioCtx.resume();return audioCtx;}catch(e){return null;}}
function sysBeep(kind){if(!sysSoundOn)return;const ac=ensureAudio();if(!ac)return;const t=ac.currentTime,o=ac.createOscillator(),g=ac.createGain();const tone={move:[1900,.035],select:[1250,.055],menu:[820,.06],shutter:[520,.16],error:[300,.12]}[kind]||[1000,.05];o.type=kind==='shutter'?'square':'sine';o.frequency.setValueAtTime(tone[0],t);o.frequency.exponentialRampToValueAtTime(Math.max(100,tone[0]*(kind==='shutter'?.55:.82)),t+tone[1]);g.gain.setValueAtTime(kind==='shutter'?.09:.05,t);g.gain.exponentialRampToValueAtTime(.0001,t+tone[1]);o.connect(g);g.connect(ac.destination);o.start(t);o.stop(t+tone[1]+.02);}
function actionSound(key){if(['UP','DOWN','LEFT','RIGHT'].includes(key))sysBeep('move');else if(['ENTER','FN','DISP','HALF'].includes(key))sysBeep('select');else if(['MENU','DELETE'].includes(key))sysBeep('menu');else if(key==='SHUTTER')sysBeep('shutter');}
let fwSoundOn=true,fwSeq=0,fwLast=null,fwRate='auto',fwPollBusy=false,fwCount=0;
window.__fw={seq:0,last:null,plays:0,events:[],errors:[]};
const fwState=document.querySelector('#fwState'),fwLog=document.querySelector('#fwLog'),fwRateSel=document.querySelector('#fwRate');
function fwB64(b64){const bin=atob(b64),bytes=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)bytes[i]=bin.charCodeAt(i);return bytes.buffer;}
async function playFwSound(e){if(!e)return;const ac=ensureAudio();if(!ac){fwState.textContent='浏览器不支持音频';return;}const rateKey=fwRate==='auto'?null:String(fwRate);const wav=rateKey?e['wav'+rateKey]:e.wav;if(!wav){fwState.textContent='固件音 #'+(e.seq||'?')+' 无法读取：'+(e.error||'无数据');return;}try{const buf=await ac.decodeAudioData(fwB64(wav).slice(0));if(ac.state==='suspended')await ac.resume();const src=ac.createBufferSource(),g=ac.createGain();g.gain.value=.9;src.buffer=buf;src.connect(g);g.connect(ac.destination);src.start();fwCount++;window.__fw.plays=fwCount;window.__fw.ctx=ac.state;const playRate=rateKey?Number(rateKey)*1000:(Number(e.rate)||48000);const ms=e.samples?Math.round(e.samples/playRate*1000):Math.round((e.duration||0)*1000);window.__fw.last={seq:e.seq,sound_id:e.sound_id,name:e.name,source:e.source,rate:playRate,duration:ms/1000};fwState.textContent='固件音 #'+e.seq+' · '+(e.name||('音效 '+e.sound_id))+' · '+(playRate/1000)+' 千赫 · '+ms+' ms';}catch(err){window.__fw.errors.push(err.message);fwState.textContent='固件音播放失败：'+err.message;}}
async function pollFwSounds(){if(fwPollBusy)return;fwPollBusy=true;try{const r=await fetch(base+'fw-sounds.json?since='+fwSeq,{cache:'no-store'});if(!r.ok)return;const j=await r.json();for(const e of (j.events||[])){fwSeq=Math.max(fwSeq,Number(e.seq)||0);fwLast=e;window.__fw.seq=fwSeq;window.__fw.last={seq:e.seq,sound_id:e.sound_id,name:e.name,source:e.source,rate:e.rate,duration:e.duration};window.__fw.events.push({seq:e.seq,sound_id:e.sound_id,name:e.name,source:e.source});if(window.__fw.events.length>50)window.__fw.events.shift();if(e.error){fwState.textContent='固件音 #'+(e.seq||'?')+'：'+e.error;fwLog.textContent='adf_sys_request 已到达，但音效资源读取失败';continue;}fwLog.textContent='来源='+(e.source==='ap'?'AP 固件请求':'虚拟 CP 音效表')+' · 类型='+e.kind+' 选项='+e.option+' 音效ID='+e.sound_id+' 参数=0x'+(Number(e.param)>>>0).toString(16)+' 地址=0x'+Number(e.addr).toString(16)+' 长度='+e.len+' 音量='+e.volume+' 头=0x'+(Number(e.header)||0).toString(16)+' 自动率='+(Number(e.rate)/1000)+' 千赫';if(fwSoundOn)playFwSound(e);else fwState.textContent='已收到固件音 #'+e.seq+'（固件音关闭）';}}catch(_){}finally{fwPollBusy=false;}}
setInterval(pollFwSounds,350);pollFwSounds();
document.addEventListener('pointerdown',()=>{ensureAudio();if(fwLast&&fwSoundOn)setTimeout(()=>playFwSound(fwLast),80);},{once:true});
const SHUTTER_FILES={ka8:'sounds/shutter-ka-sha-8k.wav',ka16:'sounds/shutter-ka-sha-16k.wav',kasha8:'sounds/shutter-kasha-8k.wav'};
const shutterLabels={synth:'合成哔声',ka8:'原厂候选 8 千赫（实验解包）',ka16:'原厂候选 16 千赫（实验解包）',kasha8:'Kasha 候选 8 千赫（实验解包）',custom:'自定义文件',off:'静音'};
let shutterMode='synth',customShutterBuffer=null,shutterSource=null;
const shutterCache={};
window.__shutter={mode:'synth',plays:0,cached:[],error:null};
function updateShutterState(extra){shutterState.textContent='快门音：'+(shutterLabels[shutterMode]||shutterMode)+(extra?' · '+extra:'');}
async function loadShutterBuffer(mode){if(shutterCache[mode])return shutterCache[mode];const ac=ensureAudio();if(!ac)throw new Error('音频上下文不可用');const r=await fetch(base+SHUTTER_FILES[mode],{cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status);const ab=await r.arrayBuffer();const buf=await ac.decodeAudioData(ab);shutterCache[mode]=buf;window.__shutter.cached.push(mode);return buf;}
async function playShutterSound(){if(shutterMode==='off')return;if(shutterMode==='synth'){sysBeep('shutter');window.__shutter.plays+=1;return;}let buf=null;try{if(shutterMode==='custom'){if(!customShutterBuffer){shutterState.textContent='请先选择自定义快门音';sysBeep('shutter');return;}buf=customShutterBuffer;}else{buf=await loadShutterBuffer(shutterMode);}}catch(e){window.__shutter.error=e.message;shutterState.textContent='快门音加载失败：'+e.message;sysBeep('shutter');return;}const ac=ensureAudio();if(!ac||!buf)return;try{if(shutterSource){try{shutterSource.stop();}catch(_){}}const src=ac.createBufferSource(),g=ac.createGain();src.buffer=buf;g.gain.value=.85;src.connect(g);g.connect(ac.destination);src.start();shutterSource=src;window.__shutter.plays+=1;updateShutterState(buf.duration.toFixed(3)+'s');}catch(e){window.__shutter.error=e.message;shutterState.textContent='快门音播放失败：'+e.message;}}
async function restoreShutter(){let saved='synth';try{saved=localStorage.getItem('a7m4-shutter-mode')||'synth';}catch(e){}if(!document.querySelector('#shutterSound option[value="'+saved+'"]'))saved='synth';shutterMode=saved;shutterSel.value=saved;window.__shutter.mode=saved;let data=null;try{data=localStorage.getItem('a7m4-shutter-custom');}catch(e){}if(data){try{const ab=await(await fetch(data)).arrayBuffer();const ac=ensureAudio();customShutterBuffer=await ac.decodeAudioData(ab);}catch(e){}}if(saved==='custom'&&!customShutterBuffer)shutterState.textContent='自定义快门音需重新选择文件';else updateShutterState();}
function refresh(){if(stopped)return;frame.src=base+'frame.png?t='+Date.now();fetch(base+'status.json',{cache:'no-store'}).then(r=>r.json()).then(s=>{state.textContent=s.status;}).catch(()=>{});}
function draw(){ctx.globalCompositeOperation='source-over';ctx.fillStyle='#000';ctx.fillRect(0,0,640,480);if(photoView&&lastPhoto&&lastPhoto.complete&&lastPhoto.naturalWidth){ctx.drawImage(lastPhoto,0,0,640,480);}else{if(video.readyState>=2&&video.videoWidth){const vw=video.videoWidth,vh=video.videoHeight;const cover=fit.value==='cover';const scale=cover?Math.max(640/vw,480/vh):Math.min(640/vw,480/vh);const dw=vw*scale,dh=vh*scale;ctx.drawImage(video,(640-dw)/2,(480-dh)/2,dw,dh);}if(uiReady&&frame.complete&&frame.naturalWidth){ctx.globalCompositeOperation='screen';ctx.drawImage(frame,0,0,640,480);ctx.globalCompositeOperation='source-over';}}requestAnimationFrame(draw);}
async function action(key){if(busy||stopped)return;if(photoView&&key==='MENU'){closePhotoView();sysBeep('menu');return;}actionSound(key);busy=true;document.querySelectorAll('[data-key]').forEach(b=>b.disabled=true);try{const r=await fetch(base+'action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key})});const v=await r.json();if(!r.ok)throw Error(v.error);if(key==='STOP'){stopped=true;state.textContent='虚拟机已停止';}else refresh();}catch(e){state.textContent=e.message;}finally{busy=false;document.querySelectorAll('[data-key]').forEach(b=>b.disabled=false);}}
document.querySelectorAll('[data-key]').forEach(b=>b.onclick=()=>action(b.dataset.key));document.querySelector('#stop').onclick=()=>action('STOP');
document.querySelector('#snapshot').onclick=()=>{const a=document.createElement('a');a.href=screen.toDataURL('image/jpeg',0.92);a.download='a7m4-web.jpg';a.click();};
document.querySelector('#shutter').onclick=capturePhoto;document.querySelector('#playPhoto').onclick=togglePlay;document.querySelector('#playBack').onclick=()=>togglePlay();
async function capturePhoto(){if(photoBusy)return;if(!(video.readyState>=2&&video.videoWidth)){videoState.textContent='请先选择视频';return;}playShutterSound();const pc=document.createElement('canvas');pc.width=640;pc.height=480;const c=pc.getContext('2d');c.fillStyle='#000';c.fillRect(0,0,640,480);const vw=video.videoWidth,vh=video.videoHeight;const cover=fit.value==='cover';const scale=cover?Math.max(640/vw,480/vh):Math.min(640/vw,480/vh);const dw=vw*scale,dh=vh*scale;c.drawImage(video,(640-dw)/2,(480-dh)/2,dw,dh);let q=0.9,url=pc.toDataURL('image/jpeg',q),bin=atob(url.split(',')[1]),bytes=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)bytes[i]=bin.charCodeAt(i);while(bytes.length>65536&&q>0.4){q-=0.1;url=pc.toDataURL('image/jpeg',q);bin=atob(url.split(',')[1]);bytes=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)bytes[i]=bin.charCodeAt(i);}if(bytes.length>65536){videoState.textContent='照片 JPEG 超过 64 KiB';return;}const padded=new Uint8Array(65536);padded.set(bytes);lastPhoto=new Image();lastPhoto.src=url;photoBusy=true;videoState.textContent='上传并写入虚拟卡…';try{const r=await fetch(base+'photo-upload',{method:'POST',headers:{'Content-Type':'image/jpeg'},body:padded});const j=await r.json();if(!r.ok)throw Error(j.error||('HTTP '+r.status));videoState.textContent='已写入虚拟卡；点回放查看照片';setPhotoView(false);}catch(e){videoState.textContent='拍摄失败：'+e.message;}finally{photoBusy=false;}}
async function togglePlay(){if(photoBusy)return;if(photoView){closePhotoView();sysBeep('menu');return;}if(!lastPhoto){videoState.textContent='还没有照片，请先按快门';return;}openPhotoView();sysBeep('select');}
document.querySelector('#pickVideo').onclick=()=>fileInput.click();
shutterSel.onchange=async()=>{shutterMode=shutterSel.value;window.__shutter.mode=shutterMode;window.__shutter.error=null;try{localStorage.setItem('a7m4-shutter-mode',shutterMode);}catch(e){}updateShutterState();if(shutterMode==='custom'&&!customShutterBuffer){shutterFileInput.click();return;}await playShutterSound();};
document.querySelector('#testShutterSound').onclick=()=>playShutterSound();
document.querySelector('#pickShutterSound').onclick=()=>shutterFileInput.click();
shutterFileInput.onchange=async()=>{const f=shutterFileInput.files[0];if(!f)return;try{const ac=ensureAudio();const ab=await f.arrayBuffer();const buf=await ac.decodeAudioData(ab.slice(0));customShutterBuffer=buf;shutterMode='custom';shutterSel.value='custom';window.__shutter.mode='custom';try{localStorage.setItem('a7m4-shutter-mode','custom');if(f.size<=3*1024*1024){const rd=new FileReader();rd.onload=()=>{try{localStorage.setItem('a7m4-shutter-custom',rd.result);}catch(e){}};rd.readAsDataURL(f);}}catch(e){}shutterState.textContent='已加载自定义快门音：'+f.name;playShutterSound();}catch(e){window.__shutter.error=e.message;shutterState.textContent='音频解码失败：'+e.message;}};
document.querySelector('#sysSound').onclick=()=>{sysSoundOn=!sysSoundOn;sysSoundBtn.textContent='网页合成音：'+(sysSoundOn?'开':'关');if(sysSoundOn)sysBeep('select');};
document.querySelector('#fwSound').onclick=()=>{fwSoundOn=!fwSoundOn;document.querySelector('#fwSound').textContent='固件音：'+(fwSoundOn?'开':'关');if(fwSoundOn&&fwLast)playFwSound(fwLast);};
document.querySelector('#fwReplay').onclick=()=>{if(fwLast)playFwSound(fwLast);else fwState.textContent='还没有收到固件音效';};
fwRateSel.onchange=()=>{fwRate=fwRateSel.value;if(fwLast)playFwSound(fwLast);};
const cpShutter=document.querySelector('#cpShutter'),cpFocus=document.querySelector('#cpFocus');let cpFocusOn=true;
async function saveCpConfig(){try{await fetch(base+'cp-config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({shutter:cpShutter.value,focus:cpFocusOn})});}catch(e){fwState.textContent='虚拟 CP设置失败：'+e.message;}}
cpShutter.onchange=saveCpConfig;
cpFocus.onclick=()=>{cpFocusOn=!cpFocusOn;cpFocus.textContent='对焦音：'+(cpFocusOn?'开':'关');saveCpConfig();};
document.querySelector('#sound').onclick=async()=>{if(!video.src)return;if(video.muted){video.muted=false;try{await video.play();}catch(e){video.muted=true;videoState.textContent='浏览器阻止了有声播放，请再点一次声音';}sound.textContent=video.muted?'开启声音':'关闭声音';}else{video.muted=true;sound.textContent='开启声音';}};
fileInput.onchange=async()=>{const f=fileInput.files[0];if(!f)return;videoState.textContent='上传并转码中…';try{const r=await fetch(base+'video-upload',{method:'POST',headers:{'Content-Type':'application/octet-stream'},body:f});const j=await r.json();if(!r.ok)throw Error(j.error||('HTTP '+r.status));video.src=base+'video.mp4?v='+Date.now();video.muted=false;try{await video.play();sound.textContent='关闭声音';}catch(e){video.muted=true;try{await video.play();}catch(_){}sound.textContent='开启声音';}setPhotoView(false);videoState.textContent='当前视频：'+f.name;}catch(e){videoState.textContent='视频处理失败：'+e.message;}};
document.addEventListener('keydown',e=>{const key={ArrowUp:'UP',ArrowDown:'DOWN',ArrowLeft:'LEFT',ArrowRight:'RIGHT',Enter:'ENTER',Escape:'MENU',m:'MENU',M:'MENU'}[e.key];if(key){e.preventDefault();if(!e.repeat)action(key);}});
restoreShutter();refresh();setInterval(refresh,500);requestAnimationFrame(draw);</script></html>'''

FFMPEG=os.environ.get('A7M4_FFMPEG','/mnt/c/Users/16483/AppData/Local/Microsoft/WinGet/Links/ffmpeg.exe')
VIDEO_SRC='/mnt/d/TMP/a7m4-web-video-source'
VIDEO_SRC_WIN='D:/TMP/a7m4-web-video-source'
VIDEO_TMP='/mnt/d/TMP/a7m4-web-video.part.mp4'
VIDEO_TMP_WIN='D:/TMP/a7m4-web-video.part.mp4'
VIDEO_OUT='/mnt/d/TMP/a7m4-web-video.mp4'
SOUNDS_DIR=os.path.join(os.path.dirname(os.path.abspath(__file__)),'sounds')

class Panel:
    def __init__(self,port,initial,token=None):
        self.frame=initial;self.status='原厂界面已显示；网页视频输入未启用';self.actions=queue.Queue(maxsize=8)
        self.video_lock=threading.Lock()
        self.fw_events=[];self.fw_seq=0;self.fw_lock=threading.Lock()
        self.cp_config={'shutter':'silent','focus':True}
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
            def check_origin(self):
                origin=self.headers.get('Origin')
                if origin and origin not in {f'http://localhost:{port}',f'http://127.0.0.1:{port}'}:raise ValueError('Invalid origin')
            def do_GET(self):
                path=self.path.split('?',1)[0]
                if not path.startswith(owner.prefix):return self.respond(404,b'Not found','text/plain')
                suffix=path[len(owner.prefix):]
                if suffix=='':return self.respond(200,PAGE.encode(),'text/html; charset=utf-8')
                if suffix=='frame.png':return self.respond(200,owner.frame,'image/png')
                if suffix=='status.json':return self.respond(200,json.dumps({'status':owner.status}).encode(),'application/json')
                if suffix=='fw-sounds.json':
                    try:since=int(parse_qs(self.path.split('?',1)[1]).get('since',['0'])[0])
                    except (IndexError,ValueError):since=0
                    with owner.fw_lock:
                        events=[event for event in owner.fw_events if int(event.get('seq',0))>since]
                    return self.respond(200,json.dumps({'events':events,'latest':owner.fw_seq}).encode(),'application/json')
                if suffix.startswith('sounds/'):
                    name=suffix[len('sounds/'):]
                    if not re.fullmatch(r'[A-Za-z0-9._-]+\.wav',name):return self.respond(404,b'Not found','text/plain')
                    try:
                        with open(os.path.join(SOUNDS_DIR,name),'rb') as f:data=f.read()
                    except OSError:return self.respond(404,b'No sound','text/plain')
                    return self.respond(200,data,'audio/wav')
                if suffix=='video.mp4':
                    try:
                        with open(VIDEO_OUT,'rb') as f:data=f.read()
                    except OSError:return self.respond(404,b'No video','text/plain')
                    return self.respond(200,data,'video/mp4')
                return self.respond(404,b'Not found','text/plain')
            def upload_video(self):
                self.check_origin()
                length=int(self.headers.get('Content-Length','0'))
                if not 1<=length<=300*1024*1024:raise ValueError('视频大小超过 300 MiB')
                os.makedirs('/mnt/d/TMP',exist_ok=True)
                remaining=length
                with open(VIDEO_SRC,'wb') as out:
                    while remaining:
                        chunk=self.rfile.read(min(65536,remaining))
                        if not chunk:raise ValueError('上传不完整')
                        out.write(chunk);remaining-=len(chunk)
                with owner.video_lock:
                    if not os.path.isfile(FFMPEG):raise RuntimeError('FFmpeg 不可用')
                    vf='scale=640:480:force_original_aspect_ratio=decrease,scale=trunc(iw/2)*2:trunc(ih/2)*2'
                    cmd=[FFMPEG,'-y','-v','error','-i',VIDEO_SRC_WIN,'-vf',vf,'-c:v','libx264','-preset','veryfast','-crf','23','-pix_fmt','yuv420p','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-c:a','aac','-b:a','128k','-movflags','+faststart','-t','30',VIDEO_TMP_WIN]
                    result=subprocess.run(cmd,capture_output=True,timeout=300)
                    if result.returncode:raise RuntimeError((result.stderr or b'ffmpeg failed')[-900:].decode('utf-8','replace'))
                    os.replace(VIDEO_TMP,VIDEO_OUT)
                self.respond(200,json.dumps({'ok':True,'url':'video.mp4'}).encode(),'application/json')
            def guest_exec(self):
                self.check_origin()
                length=int(self.headers.get('Content-Length','0'))
                if not 1<=length<=4096:raise ValueError('guest command length invalid')
                command=self.rfile.read(length).decode('utf-8','replace').strip()
                if not command:raise ValueError('empty guest command')
                event=threading.Event();result={}
                owner.actions.put_nowait(('EXEC',event,result,command))
                if not event.wait(90):raise TimeoutError('guest command timeout')
                if 'error' in result:raise RuntimeError(result['error'])
                self.respond(200,json.dumps({'ok':True,'output':result.get('output','')},ensure_ascii=False).encode(),'application/json; charset=utf-8')
            def upload_photo(self):
                self.check_origin()
                length=int(self.headers.get('Content-Length','0'))
                if length!=65536:raise ValueError('照片长度必须为 65536 字节')
                data=bytearray();remaining=length
                while remaining:
                    chunk=self.rfile.read(min(65536,remaining))
                    if not chunk:raise ValueError('照片上传不完整')
                    data.extend(chunk);remaining-=len(chunk)
                event=threading.Event();result={}
                owner.actions.put_nowait(('PHOTO',event,result,bytes(data)))
                if not event.wait(600):raise TimeoutError('写入虚拟卡超时')
                if 'error' in result:raise RuntimeError(result['error'])
                self.respond(200,b'{"ok":true}','application/json')
            def do_POST(self):
                try:
                    path=self.path.split('?',1)[0]
                    if not path.startswith(owner.prefix):raise ValueError('Unknown endpoint')
                    suffix=path[len(owner.prefix):]
                    if suffix=='video-upload':return self.upload_video()
                    if suffix=='photo-upload':return self.upload_photo()
                    if suffix=='guest-exec':return self.guest_exec()
                    if suffix=='cp-config':
                        self.check_origin()
                        length=int(self.headers.get('Content-Length','0'))
                        if not 1<=length<=512:raise ValueError('Invalid length')
                        data=json.loads(self.rfile.read(length))
                        if data.get('shutter') in {'silent','mechanical','kasha','continuous','off'}:
                            owner.cp_config['shutter']=data['shutter']
                        elif data.get('shutter')=='electronic':
                            owner.cp_config['shutter']='silent'
                        if isinstance(data.get('focus'),bool):owner.cp_config['focus']=data['focus']
                        return self.respond(200,json.dumps(owner.cp_config).encode(),'application/json')
                    if suffix!='action':raise ValueError('Unknown endpoint')
                    self.check_origin()
                    length=int(self.headers.get('Content-Length','0'))
                    if not 1<=length<=128:raise ValueError('Invalid length')
                    key=json.loads(self.rfile.read(length)).get('key')
                    if key not in {'MENU','UP','DOWN','LEFT','RIGHT','ENTER','DELETE','HALF','SHUTTER','PLAY','FN','DISP','STOP','RESTART'}:raise ValueError('Unknown key')
                    event=threading.Event();result={}
                    owner.actions.put_nowait((key,event,result))
                    if not event.wait(240 if key=='PHOTO' else (160 if key=='RESTART' else 20)):raise TimeoutError('虚拟机响应超时')
                    if 'error' in result:raise RuntimeError(result['error'])
                    self.respond(200,b'{"ok":true}','application/json')
                except Exception as error:
                    self.respond(400,json.dumps({'error':str(error)},ensure_ascii=False).encode(),'application/json; charset=utf-8')
        self.server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://localhost:{port}'+self.prefix
    def add_fw_sound(self,event):
        """Publish one real adf_sys_request event with host-rendered WAVs."""
        with self.fw_lock:
            event=dict(event)
            event['seq']=int(event.get('seq',self.fw_seq+1))
            self.fw_seq=max(self.fw_seq,event['seq'])
            self.fw_events.append(event)
            self.fw_events=self.fw_events[-48:]
            return event['seq']
    def close(self):self.server.shutdown();self.server.server_close()
