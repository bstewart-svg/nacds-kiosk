/* NACDS TSE 2026 kiosk — offline cache.
 *
 * The panel can't read local files, so the deck is served over HTTPS. That
 * would normally leave it hostage to trade-show wifi. This caches the whole
 * deck (~76 MB) into the device's own storage on first load; after that every
 * request is served locally and the network is irrelevant.
 *
 * Bump CACHE when you change any asset, or the old copy will keep serving.
 */
var CACHE = 'nacds-kiosk-v1';

// Just the shell on install, so activation is immediate. The heavy assets are
// pulled afterwards in the background — see PRECACHE below.
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

/* Cache-first. Once an asset is stored the network is never consulted for it,
   which is the whole point on a dead or congested show-floor connection. */
self.addEventListener('fetch', function(e){
  if (e.request.method !== 'GET') return;
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
