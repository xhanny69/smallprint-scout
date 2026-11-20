# smallprint-scout

Research scout for **Small Print** ([youtube.com/@tinyclause](https://www.youtube.com/@tinyclause)), an English YouTube Shorts channel about weird business decisions, told as animated 3D toy-figure stories ("Why did [company] do [strange thing]?").

The animation side is already code (Remotion + three.js). The slow, manual part is research: listening to 3-hour business podcasts to find the 20 seconds worth turning into a Short. This repo is where that part gets automated.

**Status:** design phase. The data contract (`schema/`) and its validator are done; the pipeline below is milestone 1 onward.

## Pipeline

```
RSS / YouTube WebSub
        │
   watch ─► fetch ─► transcribe ─► score ─► frame ─► render ─► deliver
            yt-dlp    Whisper API    LLM     faces +   ffmpeg   Drive +
            ffmpeg    (chunked,      ranks   speaker   9:16     Slack
            16k mono  word stamps)   moments tracking
```

| Step | What it does | Done when |
|---|---|---|
| watch | Polls podcast RSS every 6 h; YouTube uploads arrive via WebSub push | New episode becomes a `jobs` row within minutes |
| fetch | Highest-res source, audio normalized to 16 kHz mono, chunks < 25 MB with overlap | Chunks cover the full episode with no gaps |
| transcribe | Whisper API with word timestamps, chunks stitched back with corrected offsets | No duplicated or dropped words at chunk joins |
| score | LLM reads sliding windows, extracts "decision moments", scores hook / payoff / fact-checkability / channel fit | ≥3 of 5 hand-picked moments land in the top 3 per golden episode |
| frame | Shot detection → face tracks → active speaker (diarization + lip motion) → crop path | Active speaker inside the crop on ≥95% of sampled frames |
| render | Crop path (stored as keyframes in the JSON) → ffmpeg 1080×1920 + rough captions | Re-render from edited keyframes without re-running detection |
| deliver | Clip, JSON, transcript excerpt and contact sheet to Drive; card to Slack | 3-hour episode → clips in Drive in < 45 min, unattended |

Every step checks the job status before running (`discovered → fetched → transcribed → scored → rendered → delivered`, or `failed`), so reruns are safe and a crash resumes where it stopped.

## Framing rules (16:9 → 9:16)

- Decisions are made **per shot** (PySceneDetect), so the virtual camera never pans across an editor's cut.
- **Dead zone:** the crop holds still while the speaker's face stays in the middle 30%.
- **Speaker change outside the crop → hard cut**, not a pan. Each framing holds at least 1.5 s.
- Both faces fit → frame both. Split-screen call → stack tiles. No face (charts, b-roll) → full frame over a blurred copy.

## Data contract

Each candidate moment is one JSON document. Schema: [`schema/candidate.schema.json`](schema/candidate.schema.json). Example: [`examples/candidate-example.json`](examples/candidate-example.json).

```
python validate.py examples/candidate-example.json
```

Standard library only, Python 3.10+. Exits 0 when the file is valid, 1 with a list of problems when it isn't.

## Channel rules the scout must follow

- Format: "Why did X do Y?" with the hook landing in the first 2 seconds.
- Every fact needs a source; unverified claims stay in `claims_to_verify`.
- Skip topics already covered on the channel (Kodak, Bertha Benz, Haier) and topics that are saturated elsewhere (Costco was dropped for that reason).
- Clips are internal reference for scripting. Nothing from a source is re-uploaded; every story is rebuilt as original animation.
