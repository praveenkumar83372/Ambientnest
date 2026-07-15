# Hana's World

A fully-animated, continuous-life daily short series (9:16, Studio Ghibli
style). No static image cards — every scene is real generated animation.
Hana is a persistent character: her memory carries forward every video,
driven by real Japan weather.

## How it fits together

```
japan_data.py      → real weather + season + daypart (Open-Meteo, no key needed)
hana_state.json     → Hana's living memory (garden, projects, savings, mood...)
hana_state.py       → read/update/save that memory
hana_story.py        → Gemini turns (state + weather) into today's story JSON
hana_animation.py   → HuggingFace Wan2.1 turns each scene into real animation
sfx_manager.py       → maps story sfx tags to your audio files
hana_assembly.py    → ffmpeg: voice (edge-tts) + sfx + captions + concat
hana_world.py        → orchestrates all of the above for one video run
.github/workflows/hana.yml → runs it 3x/day automatically
```

## One-time setup

1. **Secrets** (repo Settings → Secrets and variables → Actions):
   - `GEMINI_API_KEY` — for story generation
   - `HF_TOKEN` — HuggingFace token with inference access to the image
     and video models referenced in `hana_animation.py`

2. **Character reference image** — drop a locked design for Hana at
   `assets/character/hana_ref.png`. This is what keeps her looking the
   same across every video. Generate this once (any Ghibli-style
   text-to-image tool works), then never regenerate it — only reuse it.

3. **SFX library** — drop audio files into `assets/sfx/` matching the
   filenames listed in `sfx_manager.SFX_LIBRARY`. Run
   `python sfx_manager.py` any time to see what's still missing.

4. **Install deps locally** (optional, for testing before pushing):
   ```bash
   pip install -r requirements.txt
   sudo apt-get install ffmpeg   # or brew install ffmpeg on macOS
   ```

## Running locally

```bash
export GEMINI_API_KEY=...
export HF_TOKEN=...
python hana_world.py --slot morning
```

Output lands in `output/final/hana_YYYYMMDD_<slot>.mp4`.
`hana_state.json` is updated in place — commit it so the next run
(local or in Actions) continues her story instead of restarting it.

## Automated schedule

`.github/workflows/hana.yml` runs at 07:00 / 13:00 / 19:00 JST daily,
generates a video, uploads it as a workflow artifact, and commits the
updated `hana_state.json` back to the repo. YouTube upload is left as a
manual step (or a commented-out stub in the workflow) so you can review
each video before it goes live — wire it up once you're happy with
quality.

## Letting viewers influence Hana

Call `hana_state.queue_comment_thread(state, comment_text, author)` from
wherever you're pulling YouTube comments (a small separate script or
Action, not included yet — say the word if you want that built too),
save the state, and the next `hana_world.py` run will have Hana react to
it naturally in the story.

## Notes / things you'll want to tune

- `hana_animation.py` uses placeholder model IDs (`FLUX.1-dev` for
  keyframes, `Wan2.1-I2V-14B-720P` for animation) — swap for whatever's
  actually available/affordable on your HF inference plan.
- Captions are evenly split per scene duration, not word-timed. Fine for
  a first pass; swap in whisper-based alignment later if you want tighter sync.
- `hana_story.py`'s system prompt is the single most important tuning
  lever for tone — adjust it first if her voice ever feels off.
