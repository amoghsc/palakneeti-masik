# पालकनीती मासिक — build tool

Turns a month's articles from palakneeti.in into:

- an **A4 PDF** for printing and for the WhatsApp broadcast
- a **Canva file** (`.pptx`) if anyone wants to hand-tweak the layout
- a **mobile web version**, published to a link you can share

Nobody needs to install anything. It runs on GitHub.

---

## Every month: how to make the new issue

### 1. Check what's published

Go to the **Actions** tab → **Preview a month** → **Run workflow**.
Type the month as `2026-09` and press the green button.

A minute later, open the finished run. It lists every article it can see for
that month. A full issue is usually 5–7 articles — if it shows two, the month
is still being published, so wait.

### 2. Build it

**Actions** → **Build issue** → **Run workflow**, then:

| Field | What to pick |
|---|---|
| **Month** | `2026-09` |
| **Page layout** | `classic` (single column, like the printed issues) · `editorial` (deeper green, left-aligned titles) · `twocol` (two columns) |
| **Cover page** | `title` puts the magazine name and month on the cover · `blank` leaves it empty for your own artwork |
| **Publish the mobile web version** | leave ticked |

Press **Run workflow**. It takes about three minutes.

### 3. Collect the files

Open the finished run. At the bottom under **Artifacts** there is a zip with
the **PDF** and the **Canva file**. Download, check it, send it out.

### 4. The web version publishes itself

It appears on the site within a minute or two, and the month is added to the
front page automatically. That is the link to put in the WhatsApp broadcast.

---

## If something looks wrong

**"No category found for this month"** — nothing is published for that month
yet, or its category on the site is named unusually. Run *Preview a month*
first; it says the same thing more clearly.

**Fewer articles than expected** — the tool only picks up posts filed under
that month's category *and* `masik-article`. Khelghar posts and announcements
are deliberately left out. If a magazine article is missing, check its
categories on the site and re-run.

**"Could not extract the editable layout"** — a warning, not a failure. The
PDF and the web version are fine; only the Canva file was skipped because
Chrome hiccuped. Re-run if you actually need the `.pptx`.

**A page looks too empty at the end of an article** — the build already tries
four levels of tightening and keeps the one that reads best. If it is still
awkward, that article is genuinely an awkward length; adding an image usually
fixes it.

**You want to change the cover, colours or the masthead names** — those live in
`pipeline/issues.py`. Everything else is derived automatically.

---

## One-time setup

1. Create the repository on GitHub and push this folder to it.
2. **Settings → Actions → General → Workflow permissions** → choose
   **Read and write permissions**. Without this the tool cannot publish the web
   version.
3. **Settings → Pages** → Source: **Deploy from a branch** → branch `main`,
   folder **`/docs`**. Save.
4. Invite the editorial team as collaborators so they can press the buttons.

> **The repository has to be public** for the free GitHub Pages site. That is
> fine here — every article is already public on palakneeti.in. If you would
> rather keep it private, Pages needs a paid GitHub plan; the PDF still works
> either way, it is just the web link that stops publishing.

---

## What is in here

```
pipeline/          the build itself
  issues.py        month names, palettes, masthead, per-issue overrides
  fetchparse.py    pulls the articles from the WordPress API and structures them
  gen.py           lays out the A4 pages (three styles)
  autofit.py       picks how tightly to set each article
  topptx.py        rebuilds the layout as an editable Canva/PowerPoint file
  web.py           builds the mobile web version
  mksite.py        adds the month to the published site
  build.sh         runs the whole PDF build
docs/              the published site (the tool writes here)
.github/workflows/ the two buttons in the Actions tab
```

A month needs no code change: the tool works out the Marathi and English month
names from `2026-09`, and finds the WordPress category by name.

## Running it on your own machine

Only needed for development.

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
cd pipeline
./.venv/bin/python fetchparse.py 2026-09
./build.sh 2026-09          # needs Google Chrome installed
./.venv/bin/python web.py 2026-09
```

## Fonts

**Mukta** (SIL Open Font License) is bundled in `pipeline/build/fonts/` — the
same face the printed issues use. The web version also loads **Tiro Devanagari
Marathi** from Google Fonts for titles.

## A note on what has been tested

The pipeline itself has been run end to end many times, and the exact sequence
of commands in the workflow was rehearsed locally against a clean copy of this
repository for three different months.

**The GitHub Actions workflows themselves have not yet run on GitHub** — that
could not be tested without pushing the repo. Both files are valid YAML and the
steps are the ones that were rehearsed, but expect to fix a small thing on the
first run. The two most likely spots are the Chrome step (there is an install
fallback if the runner image ever drops it) and the push in the publish step,
which needs the write permission in setup step 2 above.
