#!/usr/bin/env python3
"""
Generate a single self-contained index.html for the NACDS touch kiosk.

Everything the app needs to boot -- markup, styles, logic and the full slide /
hotspot table -- lives inside the one file. Nothing is fetched except the slide
images and the videos. That matters: Android treats every file:// document as
its own opaque origin, so an external <script src="slides-data.js"> gets blocked
and the previous build died before it drew anything.
"""

import json, re, os, sys

SRC = os.path.dirname(os.path.abspath(__file__))

raw = open(os.path.join(SRC, "slides-data.js")).read()
data = json.loads(re.search(r"=\s*(\{.*\})\s*;?\s*$", raw, re.S).group(1))
slides = data["slides"]

# Compact the payload: drop labels down to what the app actually uses, and round
# coordinates. Keeps the inlined table readable and small.
compact = []
for s in slides:
    e = {"n": s["n"], "img": s["img"]}
    if s.get("video"):
        e["video"] = s["video"]
    if s.get("poster"):
        e["poster"] = s["poster"]
    if s.get("title"):
        e["title"] = s["title"]
    e["h"] = [
        {
            "x": round(h["x"], 2), "y": round(h["y"], 2),
            "w": round(h["w"], 2), "hh": round(h["h"], 2),
            "to": h["to"], "l": h.get("label", ""),
        }
        for h in s["hotspots"]
    ]
    compact.append(e)

payload = json.dumps(compact, separators=(",", ":"))

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">
<meta name="mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#0d1b2a">
<meta name="robots" content="noindex,nofollow">
<title>Capsa Healthcare &mdash; RoboPharma Central Fill</title>
<style>
  *{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
  html,body{
    width:100%;height:100%;overflow:hidden;background:#000;
    -webkit-user-select:none;user-select:none;
    overscroll-behavior:none;touch-action:manipulation;
  }

  /* The deck is a fixed 16:9 canvas, letterboxed into whatever panel it lands on. */
  #stage{
    position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
    width:100vw;height:56.25vw;max-height:100vh;max-width:177.7778vh;
    background:#000;overflow:hidden;
  }

  /* One shared video element sits behind the plates. Android caps how many
     hardware decoders can exist at once; eight simultaneous <video> tags is
     over that limit on this class of panel. One is always safe. */
  #bg{
    position:absolute;inset:0;width:100%;height:100%;
    object-fit:cover;background:#0d1b2a;
    opacity:0;transition:opacity .25s linear;
  }
  #bg.on{opacity:1}

  /* Two plates, crossfaded, so a slide change never flashes black. */
  .plate{
    position:absolute;inset:0;width:100%;height:100%;
    display:block;opacity:0;transition:opacity .3s ease;
  }
  .plate.on{opacity:1}

  /* Invisible tap targets, sitting exactly on the artwork's own buttons.
     No borders, no fills, no hover states -- the deck's design is the UI. */
  #hots{position:absolute;inset:0;z-index:3}
  .hot{
    position:absolute;display:block;padding:0;border:0;
    background:transparent;cursor:pointer;
    -webkit-appearance:none;appearance:none;
  }
  body.debug .hot{background:rgba(243,156,18,.28);outline:1px solid #F39C12}

  /* Shown only if the artwork cannot be read -- turns a blank screen into
     something a person standing at the booth can act on. */
  #err{
    position:absolute;inset:0;z-index:9;display:none;
    background:#0d1b2a;color:#fff;
    font:400 clamp(13px,1.5vw,20px)/1.65 ui-monospace,Menlo,Consolas,monospace;
    padding:8vh 10vw;
  }
  #err.on{display:block}
  #err b{display:block;font-size:1.5em;margin-bottom:1em;font-weight:600}
  #err code{color:#F39C12;word-break:break-all}
  #err p{margin:.8em 0;opacity:.85}

  /* Download readout for setup day. Hidden unless the URL carries ?cache,
     so nothing shows on the floor. */
  #cache{
    position:absolute;left:50%;bottom:3vmin;transform:translateX(-50%);z-index:8;
    display:none;padding:1.1vmin 2.4vmin;border-radius:5vmin;
    background:rgba(12,22,38,.82);color:#fff;white-space:nowrap;
    font:400 1.5vmin/1 ui-monospace,Menlo,Consolas,monospace;letter-spacing:.16em;
  }
  body.cache #cache{display:block}
  #cache.done{background:rgba(22,120,60,.9)}
</style>
</head>
<body>

<div id="stage">
  <video id="bg" muted playsinline webkit-playsinline preload="none" loop></video>
  <img class="plate" id="p0" alt="">
  <img class="plate" id="p1" alt="">
  <div id="hots"></div>
  <div id="err">
    <b>The slide artwork didn't load.</b>
    <p>The page itself opened, so this is a file-access problem, not a broken deck.</p>
    <p>Tried to read: <code id="errsrc"></code></p>
    <p>Fix: open this deck in <b>Fully Kiosk Browser</b> with "Local File Access"
       enabled, or serve the folder over the network. Plain Chrome for Android
       blocks one local file from reading another.</p>
  </div>
  <div id="cache">Caching &hellip;</div>
</div>

<script>
/* ------------------------------------------------------------------ *
 * Slide + hotspot table, inlined. See README for how to edit.
 * ------------------------------------------------------------------ */
var SLIDES = __PAYLOAD__;

(function(){
"use strict";

var CFG = {
  idleSeconds: 180,  // untouched this long -> quietly return to the title
  homeSlide:   1
};

var qs = new URLSearchParams(location.search);
if (qs.has('idle')) CFG.idleSeconds = parseInt(qs.get('idle'),10) || CFG.idleSeconds;
if (qs.has('debug')) document.body.classList.add('debug');

var stage = document.getElementById('stage'),
    bg    = document.getElementById('bg'),
    hots  = document.getElementById('hots'),
    errEl = document.getElementById('err'),
    plates = [document.getElementById('p0'), document.getElementById('p1')];

var byN = {}, cur = 0, front = 0, idleTimer = null, failed = false;
SLIDES.forEach(function(s){ byN[s.n] = s; });

// Some Android WebViews ignore the muted *attribute* if it is parsed before a
// src exists, and an unmuted video is refused autoplay outright. Force it.
bg.muted = true; bg.defaultMuted = true; bg.playsInline = true;

function playBg(){
  var p = bg.play();
  if (p && p.catch) p.catch(function(){});     // poster stays if still refused
}

/* ---------- navigation ---------- */
function go(n){
  var s = byN[n];
  if (!s || n === cur) return;
  cur = n;

  // Crossfade to the other plate.
  var back = plates[front ^ 1];
  back.onload = function(){
    back.classList.add('on');
    plates[front].classList.remove('on');
    front ^= 1;
  };
  back.onerror = function(){ fail(s.img); };
  back.src = s.img;
  back.alt = s.title || ('Slide ' + n);

  // Retarget the single shared video element.
  if (s.video){
    if (bg.getAttribute('src') !== s.video){
      bg.setAttribute('src', s.video);
      if (s.poster) bg.setAttribute('poster', s.poster);
      bg.load();
      // load() interrupts an in-flight play() and Android rejects it with an
      // AbortError -- the video then sits on its poster forever, which reads
      // as "the videos don't work". Ask again once decoding is actually ready.
      bg.addEventListener('canplay', playBg, {once:true});
    }
    bg.classList.add('on');
    playBg();                                  // already-buffered case
  } else {
    bg.classList.remove('on');
    try { bg.pause(); } catch(e){}
  }

  drawHotspots(s);
}

function next(){
  // PowerPoint advances on any click that isn't a hyperlink. The deck depends
  // on it: most slides carry only the three nav pills. Wrap at the end.
  go(cur >= SLIDES.length ? 1 : cur + 1);
}

function drawHotspots(s){
  hots.textContent = '';
  var frag = document.createDocumentFragment();
  s.h.forEach(function(h){
    var b = document.createElement('button');
    b.className = 'hot';
    b.style.left   = h.x  + '%';
    b.style.top    = h.y  + '%';
    b.style.width  = h.w  + '%';
    b.style.height = h.hh + '%';
    b.setAttribute('aria-label', h.l || ('Go to slide ' + h.to));
    b.addEventListener('click', function(e){
      e.stopPropagation();
      touched();
      go(h.to);
    });
    frag.appendChild(b);
  });
  hots.appendChild(frag);
}

/* ---------- input: tap background = next, tap target = jump ---------- */
stage.addEventListener('click', function(){ touched(); next(); });

document.addEventListener('keydown', function(e){
  var k = e.key;
  if (k==='ArrowRight'||k==='PageDown'||k===' '){ touched(); next(); }
  else if (k==='ArrowLeft'||k==='PageUp'){ touched(); go(cur<=1 ? SLIDES.length : cur-1); }
  else if (k==='Home'){ touched(); go(CFG.homeSlide); }
  else if (k==='f'){ fullscreen(); }
});

document.addEventListener('contextmenu', function(e){ e.preventDefault(); });
document.addEventListener('gesturestart', function(e){ e.preventDefault(); });

/* ---------- idle reset ---------- */
function touched(){
  clearTimeout(idleTimer);
  idleTimer = setTimeout(function(){ go(CFG.homeSlide); }, CFG.idleSeconds * 1000);
}

/* ---------- fullscreen + wake lock ---------- */
function fullscreen(){
  var el = document.documentElement;
  try { (el.requestFullscreen || el.webkitRequestFullscreen || function(){}).call(el); } catch(e){}
}
document.addEventListener('touchend', fullscreen, {once:true});
document.addEventListener('click',    fullscreen, {once:true});

var lock = null;
function keepAwake(){
  if (!('wakeLock' in navigator)) return;
  navigator.wakeLock.request('screen').then(function(l){ lock = l; }).catch(function(){});
}
document.addEventListener('visibilitychange', function(){
  if (document.visibilityState === 'visible'){
    keepAwake();
    if (byN[cur] && byN[cur].video){ var p = bg.play(); if (p && p.catch) p.catch(function(){}); }
  }
});

/* ---------- failure surface ---------- */
function fail(src){
  if (failed) return;
  failed = true;
  document.getElementById('errsrc').textContent = src;
  errEl.classList.add('on');
}

/* ---------- boot ---------- *
 * Draw slide 1 the moment it decodes. Nothing is gated behind a full preload,
 * so the deck is usable immediately and a single bad asset can't wedge it.
 * The rest warm in the background, hub first.                                */
function warm(){
  var order = [2, 10, 21].concat(SLIDES.map(function(s){ return s.n; }));
  var i = 0;
  (function step(){
    if (i >= order.length) return;
    var s = byN[order[i++]];
    if (!s) return step();
    var im = new Image();
    im.onload = im.onerror = step;
    im.src = s.img;
  })();
}

/* ---------- offline cache ---------- *
 * Served over HTTPS, so a service worker can hold the whole deck in the
 * panel's own storage. After the first visit the network is only a formality.  */
function installSW(){
  if (!('serviceWorker' in navigator)) return;
  if (navigator.storage && navigator.storage.persist) navigator.storage.persist();

  var box = document.getElementById('cache');
  if (qs.has('cache')) document.body.classList.add('cache');

  navigator.serviceWorker.addEventListener('message', function(e){
    var m = e.data || {};
    if (m.type !== 'PRECACHE_PROGRESS') return;
    box.textContent = m.finished
      ? 'CACHED — RUNS OFFLINE (' + m.done + ' FILES)'
      : 'CACHING ' + m.done + ' / ' + m.total;
    if (m.finished) box.classList.add('done');
  });

  navigator.serviceWorker.register('sw.js').then(function(){
    return navigator.serviceWorker.ready;
  }).then(function(reg){
    var urls = ['./', './index.html'];
    SLIDES.forEach(function(s){
      urls.push(s.img);
      if (s.video)  urls.push(s.video);
      if (s.poster) urls.push(s.poster);
    });
    var target = reg.active || navigator.serviceWorker.controller;
    if (target) target.postMessage({type:'PRECACHE', urls:urls});
  }).catch(function(){});
}

go(CFG.homeSlide);
touched();
keepAwake();
if (window.requestIdleCallback) requestIdleCallback(warm); else setTimeout(warm, 1200);
setTimeout(installSW, 2000);   // let slide 1 paint before the bulk download starts

})();
</script>
</body>
</html>
"""

out = HTML.replace("__PAYLOAD__", payload)
dest = os.path.join(SRC, "index.html")
open(dest, "w").write(out)
print("wrote", dest, len(out), "bytes")
print("slides:", len(compact), "hotspots:", sum(len(s["h"]) for s in compact))
