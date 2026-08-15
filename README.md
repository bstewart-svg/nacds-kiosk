# NACDS TSE 2026 — RoboPharma Touch Kiosk

## → **https://bstewart-svg.github.io/nacds-kiosk/**

Point the panel's browser at that URL. That's the whole setup.

An HTML version of `NACDS_PPT_2026_Interactive.pptx` for the 55" LG Android touch panel
(55TR3DK-BM). Video backgrounds play and loop inside the slide, which is the thing
PowerPoint for Android cannot do.

**The deck's own artwork is the interface.** No arrows, no progress dots, no home
button, no "touch to explore" banner. Invisible tap targets sit exactly on the buttons
already drawn into the slides — the `OVERVIEW / STATIONS / AXONA` pill, the ten station
pills, the numbered floor markers, the station strip, and `← BACK TO STATIONS OVERVIEW`.
On screen it looks precisely like the PowerPoint.

---

## Setting up the panel

1. Open **https://bstewart-svg.github.io/nacds-kiosk/** in the panel's browser.
2. Leave it on the title slide for about a minute on the Cradlepoint. It's downloading
   the full ~86 MB deck into the panel's own storage in the background.
3. To watch that happen, load **`…/nacds-kiosk/?cache`** instead — a readout appears at
   the bottom and turns green at `CACHED — RUNS OFFLINE (49 FILES)`. Drop the `?cache`
   afterwards; the badge is hidden on the normal URL.

Once cached, **the deck runs entirely from the panel and no longer needs the network.**
If the wifi drops mid-show it keeps working. Do step 3 during booth setup, not during a
demo.

For a locked-down full-screen experience, put that URL in **Fully Kiosk Browser** as the
Start URL and turn on *Keep Screen On*, *Autoplay Video*, *Hardware Acceleration*, and
Kiosk Mode. Not required, but it hides the Android chrome and stops visitors wandering
off into the browser.

### Why it isn't loaded from a file

It can't be. This panel refuses local files outright — Fully Kiosk with local file
access enabled still wouldn't open them, and nothing in the Android file browser opens
either. Hosting is the only route that works, which is why the service worker exists:
it gets the offline behaviour back without depending on local file access.

The site is public but carries `noindex,nofollow` plus a `robots.txt` deny, so it won't
turn up in search results.

---

## What's in here

```
index.html      the entire app — markup, styles, logic and all 181 tap targets
                in one self-contained file
sw.js           service worker; caches the deck for offline playback
slides/         31 slide images at 3840 × 2160
                  .jpg = normal slides
                  .png = the 8 video slides (transparent, layered over video)
video/          station-NN.mp4  — 8 backgrounds, H.264 1080p, audio stripped
                poster-NN.jpg   — first frame, shown while the video buffers
rebuild.py      regenerates index.html from slides-data.js
slides-data.js  the editable tap-target source
slides.json     same data, formatted for reading
```

Slides 29–31 are the Axona health-systems slides, which sit at the end of the deck.
They carry no `OVERVIEW / STATIONS / AXONA` pill in their artwork, so they have no tap
targets — visitors page through them and slide 31 wraps back to the title.

---

## How it behaves

**Tap a button** — every hyperlink from the PowerPoint works: the nav pill, the ten
station pills and ten floor markers on the hub, the station strip, and the back link.

**Tap anywhere else → next slide.** Deliberate. PowerPoint advances on any click that
isn't a hyperlink, and the deck depends on it: slides 2–9 and 21–28 carry *only* the
three nav pills, so without it there'd be no way to read the deck in order. The last
slide wraps to the title.

**Idle reset** — after 3 minutes with no touch it quietly returns to the title. Nothing
animates or flashes; it's just ready for the next visitor. There's no auto-advancing
attract loop — use `NACDS_PPT_2026_Auto.mp4` if you want an unattended video loop.

**Auto Play** — the pill centred along the bottom starts the Vimeo loop
(`vimeo.com/1218544080`) full-screen. While it runs, a replica of the
`OVERVIEW / STATIONS / AXONA` pill stays on screen so staff can break straight
into any section, plus a `■ STOP` button. Any touch anywhere also drops out into
manual control at the current slide.

The control is hidden on station pages (11–20), whose cards run to the bottom
edge with no clear space. Step back out to the hub and it returns.

> The loop streams from Vimeo, so unlike the rest of the deck **it needs a live
> connection** — it is the one thing the offline cache can't hold. If the video
> can't be reached the deck says so rather than showing a black rectangle.
> To change the video, edit `VIMEO_ID` near the bottom of the `<script>` in
> `rebuild.py` and rebuild.

**Keyboard** (for testing): arrows / space to move, `Home` for the title, `f` full-screen.

---

## URL options

| Parameter | Default | What it does |
|---|---|---|
| `?cache` | hidden | Shows the offline-download readout. Use during setup. |
| `?debug` | off | Lights every tap target in orange — checks alignment on the real panel |
| `?idle=300` | `180` | Seconds of no touch before returning to the title |

---

## Editing

Tap targets live in `slides-data.js` — coordinates are percentages of the slide
(`x`, `y`, `w`, `h`) and `to` is the destination slide. After editing:

```bash
python3 rebuild.py
git commit -am "update tap targets" && git push
```

GitHub Pages redeploys in about a minute.

`index.html` and `sw.js` are fetched **network-first**, so code and layout changes reach
a panel on its next load with nothing to remember. Slides and videos are cache-first.

> **Bump `CACHE` in `sw.js`** when you replace an image or video *under its existing
> name* — panels that already cached it will otherwise keep serving the old file
> forever. Giving the new asset a new filename avoids this entirely.

**A slide's design changed** → re-export from PowerPoint at 3840 × 2160 (File → Export →
PNG → Save Every Slide), rename to `slide-NN.png`, drop it in `slides/`, update that
slide's `img` extension in `slides-data.js`, rebuild.

> **Do not overwrite** `slide-11, 12, 15, 16, 17, 18, 19, 20`. Those are the transparent
> video overlays — a flat PowerPoint export would paint over the video and lose the motion.

**A video changed** → H.264, no audio:

```bash
ffmpeg -i in.mp4 -an -c:v libx264 -profile:v main -pix_fmt yuv420p -crf 21 -movflags +faststart station-NN.mp4
```

---

## Notes

- Only **one** `<video>` element exists at a time; its source is swapped on navigation.
  Android caps concurrent hardware decoders and the earlier build created all eight up
  front — over the limit on this panel.
- Videos are muted with audio stripped. Browsers refuse autoplay on anything with sound.
- Nothing is gated behind a full preload. Slide 1 draws as soon as it decodes and the
  rest warm in the background, so one slow asset can't wedge the kiosk.
- Source videos are 1080p and upscale to the 4K panel. Re-encoding to 4K would have
  quadrupled file size without adding real detail.
- Total footprint about 86 MB.
