"""Validate Small Print scout candidate JSON files against the data contract.

Usage:  python validate.py examples/candidate-example.json [more.json ...]
Exit:   0 if every file is valid, 1 otherwise. Standard library only.
"""

import json
import re
import sys
from pathlib import Path

REQUIRED = ["source", "candidate_id", "question", "start_s", "end_s",
            "hook_line", "scores", "claims_to_verify", "status"]
SOURCE_TYPES = {"podcast_rss", "youtube"}
STATUSES = {"needs_review", "approved", "rejected", "redo_crop"}
CROP_MODES = {"track", "hold", "cut", "both", "stack", "blur_fill"}
SCORE_KEYS = ["hook", "payoff_clarity", "fact_checkable", "channel_fit"]


def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def check(doc):
    errs = []
    if not isinstance(doc, dict):
        return ["top level must be an object"]
    errs += [f"missing field: {k}" for k in REQUIRED if k not in doc]

    src = doc.get("source")
    if isinstance(src, dict):
        if src.get("type") not in SOURCE_TYPES:
            errs.append(f"source.type must be one of {sorted(SOURCE_TYPES)}")
        for k in ("show", "episode"):
            if not isinstance(src.get(k), str) or not src.get(k):
                errs.append(f"source.{k} must be a non-empty string")
        if not re.match(r"^https?://", str(src.get("url", ""))):
            errs.append("source.url must start with http:// or https://")
    elif "source" in doc:
        errs.append("source must be an object")

    if "candidate_id" in doc and not re.fullmatch(r"[a-z0-9-]+", str(doc["candidate_id"])):
        errs.append("candidate_id must be lowercase letters, digits and dashes")
    if "question" in doc and not str(doc["question"]).startswith("Why "):
        errs.append('question must start with "Why " (channel format)')

    start, end = doc.get("start_s"), doc.get("end_s")
    if "start_s" in doc and not (is_num(start) and start >= 0):
        errs.append("start_s must be a number >= 0")
    if "end_s" in doc and not (is_num(end) and end >= 0):
        errs.append("end_s must be a number >= 0")
    if is_num(start) and is_num(end) and end <= start:
        errs.append("end_s must be after start_s")

    sc = doc.get("scores")
    if isinstance(sc, dict):
        parts = []
        for k in SCORE_KEYS:
            v = sc.get(k)
            if isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 10:
                parts.append(v)
            else:
                errs.append(f"scores.{k} must be an integer 0-10")
        tot = sc.get("total")
        if not (isinstance(tot, int) and not isinstance(tot, bool) and 0 <= tot <= 40):
            errs.append("scores.total must be an integer 0-40")
        elif len(parts) == len(SCORE_KEYS) and tot != sum(parts):
            errs.append(f"scores.total is {tot} but the parts add up to {sum(parts)}")
    elif "scores" in doc:
        errs.append("scores must be an object")

    claims = doc.get("claims_to_verify")
    if "claims_to_verify" in doc and not (isinstance(claims, list) and all(isinstance(c, str) for c in claims)):
        errs.append("claims_to_verify must be a list of strings")

    if "status" in doc and doc["status"] not in STATUSES:
        errs.append(f"status must be one of {sorted(STATUSES)}")

    track = doc.get("crop_track")
    if track is not None:
        if not isinstance(track, list):
            errs.append("crop_track must be a list")
        else:
            prev_t = None
            for i, kf in enumerate(track):
                if not isinstance(kf, dict):
                    errs.append(f"crop_track[{i}] must be an object")
                    continue
                t, x = kf.get("t"), kf.get("x")
                if not is_num(t):
                    errs.append(f"crop_track[{i}].t must be a number")
                elif prev_t is not None and t < prev_t:
                    errs.append(f"crop_track[{i}].t goes backwards in time")
                else:
                    prev_t = t
                if not (isinstance(x, int) and not isinstance(x, bool) and x >= 0):
                    errs.append(f"crop_track[{i}].x must be an integer >= 0")
                if kf.get("mode") not in CROP_MODES:
                    errs.append(f"crop_track[{i}].mode must be one of {sorted(CROP_MODES)}")
    return errs


def main(paths):
    if not paths:
        print(__doc__.strip())
        return 1
    ok = True
    for p in paths:
        try:
            doc = json.loads(Path(p).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"FAIL {p}: cannot read JSON ({e})")
            ok = False
            continue
        errs = check(doc)
        if errs:
            ok = False
            print(f"FAIL {p}")
            for e in errs:
                print(f"  - {e}")
        else:
            print(f"OK   {p}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
