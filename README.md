# NACDS TSE 2026 — RoboPharma Touch Kiosk

An offline HTML version of `NACDS_PPT_2026_Interactive.pptx` for the 55" LG Android
touch panel (55TR3DK-BM). Video backgrounds play and loop inside the slide, which is
the thing PowerPoint for Android cannot do.

**The deck's own artwork is the interface.** No arrows, no progress dots, no home
button, no "touch to explore" banner. Invisible tap targets sit exactly on the buttons
that are already drawn into the slides — the `OVERVIEW / STATIONS / AXONA` pill, the
ten station pills, the numbered floor markers, the station strip, and
`← BACK TO STATIONS OVERVIEW`. On screen it looks precisely like the PowerPoint.

---

## What's in here

```
index.html      the entire app — markup, styles, logic and all 181 tap targets
                in one self-contained file. Nothing else is required to boot.
slides/         28 slide images at 3840 × 2160
                  .jpg = normal slides
                  .png = the 8 video slides (transparent, layered over video)
video/          station-NN.mp4  — 8 backgrounds, H.264 1080p, audio stripped
                poster-NN.jpg   — first frame, shown while the video buffers
rebuild.py      regenerates index.html from slides-data.js (see "Editing")
slides-data.js  the editable tap-target source
slides.json     same data, formatted for reading
```

Slides 29–31 of the original (the hidden Axona health-systems slides) are not included,
matching how the deck presents today.

`fonts/` and `_previous-build-index.html.bak` are leftovers from the earlier build and
are no longer referenced. Safe to delete.

---

## Why the previous version wouldn't load

It kept its slide data in a separate `slides-data.js` and pulled it in with
`<script src="...">`. Android treats **every `file://` document as its own origin**, so
that request was blocked, `SLIDE_DATA` came back undefined, and the app died before it
drew anything — a blank screen.

This build inlines everything into `index.html`. There is no second code file to block.

If the artwork still can't be read, the deck now says so on screen with the exact path
it tried and how to fix it, instead of showing nothing.

---

## Deploying to the kiosk

**Use Fully Kiosk Browser.** Stock Chrome for Android won't reliably grant access to
local files and won't stay full-screen. The free tier covers everything needed here.

1. Copy the whole `capsa-kiosk` folder to the device — `/sdcard/capsa-kiosk/`.
2. Install **Fully Kiosk Browser** from the Play Store.
3. In Fully Kiosk settings:
   - **Start URL** → `file:///sdcard/capsa-kiosk/index.html`
   - **Web Content Settings** → *Local File Access* ON, *Autoplay Video* ON
   - **Device Management** → *Keep Screen On* ON
   - **Advanced Web Settings** → *Hardware Acceleration* ON
   - **Kiosk Mode** → ON, set a PIN
4. Restart Fully Kiosk.

**If local files still give you trouble**, serve the folder instead — the panel is on
wifi. Any web host or a laptop on the same network works, and it sidesteps Android file
permissions completely. Point the Start URL at the http address.

### Testing on your Mac

```bash
python3 -m http.server 8777
```

Then open <http://localhost:8777>. Resize the window — the deck letterboxes to any
aspect ratio.

---

## How it behaves

**Tap a button** — every hyperlink from the PowerPoint works: the nav pill, the ten
station pills and the ten floor markers on the hub, the station strip, and the back link.

**Tap anywhere else → next slide.** This is deliberate. PowerPoint advances on any click
that isn't a hyperlink, and the deck depends on it: slides 2–9 and 21–28 carry *only* the
three nav pills, so without it there'd be no way to read the deck in order. The last
slide wraps back to the title.

**Idle reset** — after 3 minutes with no touch, the deck quietly returns to the title
slide. Nothing animates, nothing flashes; it's just ready for the next visitor. There is
no auto-advancing attract loop — use `NACDS_PPT_2026_Auto.mp4` if you want an unattended
video loop on a second screen.

**Keyboard** (handy when testing): arrows / space to move, `Home` for the title, `f` for
full-screen.

---

## Tuning

Add to the URL — no file editing needed:

| Parameter | Default | What it does |
|---|---|---|
| `?idle=300` | `180` | Seconds of no touch before returning to the title |
| `?debug` | off | Lights every tap target in orange — use this to check alignment on the actual panel |

Or edit the `CFG` block near the top of the `<script>` in `index.html`.

---

## Editing

**Tap targets** live in `slides-data.js`. Coordinates are percentages of the slide —
`x`, `y`, `w`, `h` — and `to` is the destination slide number. After editing:

```bash
python3 rebuild.py
```

That regenerates `index.html` with the new data inlined. Load with `?debug` to check
your work.

**A slide's design changed** → re-export that slide from PowerPoint at 3840 × 2160
(File → Export → PNG → Save Every Slide), rename to `slide-NN.png`, drop it into
`slides/`, and update that slide's `img` extension in `slides-data.js`, then rebuild.

> **Do not overwrite** `slide-11, 12, 15, 16, 17, 18, 19, 20`. Those are the transparent
> video overlays — a flat PowerPoint export would paint over the video and you'd lose
> the motion.

**A video changed** → encode H.264, no audio, and replace `station-NN.mp4`:

```bash
ffmpeg -i in.mp4 -an -c:v libx264 -profile:v main -pix_fmt yuv420p -crf 21 -movflags +faststart station-NN.mp4
```

---

## Notes

- Only **one** `<video>` element exists at a time; its source is swapped on navigation.
  Android caps how many hardware decoders can run at once, and the earlier build created
  all eight up front — over the limit on this class of panel.
- Videos are muted with the audio tracks stripped. Browsers refuse autoplay on anything
  with sound, and a show floor doesn't want it.
- Nothing is gated behind a full preload. Slide 1 draws as soon as it decodes and the
  rest warm in the background, so one slow asset can't wedge the kiosk.
- Source videos are 1080p and upscale to the 4K panel. Re-encoding to 4K would have
  quadrupled the file size without adding real detail.
- Total footprint is about 76 MB.
