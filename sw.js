/* NACDS TSE 2026 kiosk — offline cache.
 *
 * The panel can't read local files, so the deck is served over HTTPS. That
 * would normally leave it hostage to trade-show wifi. This caches the whole
 * deck (~76 MB) into the device's own storage; after that the network is only
 * a formality.
 *
 * Two different strategies, deliberately:
 *
 *   - index.html / sw.js  -> NETWORK FIRST, falling back to cache.
 *     These change whenever the deck is edited. Cache-first here means a panel
 *     that has already cached the deck never sees an update again, which is a
 *     nasty way to find out at a show. Online, it always gets the current
 *     build; offline, it falls back to the stored copy.
 *
 *   - slides / video      -> CACHE FIRST.
 *     These are big and effectively immutable. Serving them from disk is the
 *     whole point. Replacing an image means giving it a new name, or bumping
 *     CACHE below.
 */
var CACHE = 'nacds-kiosk-v4';   // v4: navigation pills restored

var SHELL = ['./', './index.html', './slides/slide-01.jpg'];

self.addEventListener('install', function(e){
  self.skipWaiting();
  e.waitUntil(
    caches.open(CACHE).then(function(c){ return c.addAll(SHELL); })
                      .catch(function(){})
  );
});

self.addEventListener('activate', function(e){
  e.waitUntil(
    caches.keys().then(function(keys){
      return Promise.all(keys.map(function(k){
        return k === CACHE ? null : caches.delete(k);
      }));
    }).then(function(){ return self.clients.claim(); })
  );
});

function isDocument(req){
  if (req.mode === 'navigate') return true;
  var u = new URL(req.url);
  return /\/$|index\.html$|\.js$/.test(u.pathname);
}

self.addEventListener('fetch', function(e){
  if (e.request.method !== 'GET') return;

  if (isDocument(e.request)){
    // network first
    e.respondWith(
      fetch(e.request).then(function(res){
        if (res && res.status === 200 && res.type === 'basic'){
          var copy = res.clone();
          caches.open(CACHE).then(function(c){ c.put(e.request, copy); });
        }
        return res;
      }).catch(function(){
        return caches.match(e.request).then(function(hit){
          return hit || caches.match('./index.html');
        });
      })
    );
    return;
  }

  // cache first for everything heavy
  e.respondWith(
    caches.match(e.request).then(function(hit){
      if (hit) return hit;
      return fetch(e.request).then(function(res){
        if (res && res.status === 200 && res.type === 'basic'){
          var copy = res.clone();
          caches.open(CACHE).then(function(c){ c.put(e.request, copy); });
        }
        return res;
      });
    })
  );
});

/* The page sends the full asset list once it has booted. Fetch them one at a
   time -- a parallel burst of eight videos will stall a weak connection and
   trip request timeouts. Progress is reported back for the ?cache readout. */
self.addEventListener('message', function(e){
  var msg = e.data || {};
  if (msg.type !== 'PRECACHE' || !msg.urls) return;

  e.waitUntil(caches.open(CACHE).then(function(c){
    var urls = msg.urls, i = 0, stored = 0;

    function report(done){
      self.clients.matchAll().then(function(cs){
        cs.forEach(function(cl){
          cl.postMessage({type:'PRECACHE_PROGRESS', done:stored, total:urls.length, finished:!!done});
        });
      });
    }

    function step(){
      if (i >= urls.length){ report(true); return Promise.resolve(); }
      var u = urls[i++];
      return c.match(u).then(function(hit){
        if (hit){ stored++; report(); return step(); }
        return fetch(u, {cache:'no-cache'})
          .then(function(res){
            if (res && res.status === 200) return c.put(u, res.clone());
          })
          .then(function(){ stored++; report(); return step(); })
          .catch(function(){ return step(); });   // one bad asset must not stop the run
      });
    }
    return step();
  }));
});
