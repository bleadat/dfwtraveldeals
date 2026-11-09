#!/usr/bin/env python3
"""Build the public board.json for DFWTravelDeals.com.

Input: an ArtifactData export folder (the `out_dir` layout):
    EXPORT/deals/<id>.json    flight + hotel packages from DFW
    EXPORT/cruises/<id>.json  cruise sailings from Galveston
    EXPORT/meta/site.json     board metadata (blocked titles, spotlight, updatedOn, ...)
The `signups` collection is never read.

Output: OUT_FILE, UTF-8 JSON (one value per line) with only the fields the page renders,
after applying the owner's removals (meta.blocked), so that list is never published.

Non-ASCII text (·, á, –, curly quotes) is written as the characters themselves, never as
\\u escapes: the tool that uploads the file to Google Drive turns \\u escapes into characters,
which changes the bytes and breaks the checksum. Text is cleaned first so every character
can be copied exactly: invisible characters are dropped and odd spaces become plain spaces.

Prints one line:  name=board-YYYY-MM-DD-HHMM-<sha8>.json deals=N cruises=N bytes=N
The <sha8> is the first 8 hex digits of the file's sha256. The GitHub Action
rejects any Drive file whose content doesn't match the sha8 in its name.

Usage: python3 build_board.py EXPORT_DIR OUT_FILE
"""
import datetime
import hashlib
import json
import pathlib
import re
import sys
import unicodedata
from zoneinfo import ZoneInfo

DEAL_FIELDS = [
    "title", "kind", "destination", "boardLabel", "country", "region", "tripType",
    "originCode", "destCode", "compareDest", "nights", "price", "priceMax", "priceNote",
    "includes", "perks", "caveat", "stars", "adultsOnly", "travelStart", "travelEnd",
    "fixedDates", "travelLabel", "bookBy", "provider", "url", "affiliateUrl", "sponsored",
    "photoKey", "foundOn", "checkedOn",
]
CRUISE_FIELDS = [
    "title", "line", "ship", "nights", "region", "departPort", "ports", "sailDate", "returnDate",
    "price", "wasPrice", "cabin", "priceNote", "perks", "bookBy", "provider", "url",
    "affiliateUrl", "sponsored", "caveat", "photoKey", "foundOn", "checkedOn",
]
META_FIELDS = ["updatedOn", "updatedAt", "nextRefresh", "sources", "dealCount", "cruiseCount", "spotlight"]
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,99}$")


def clean_text(s):
    """NFC-normalize, drop invisible format characters, and turn control characters and
    unusual spaces into plain spaces, so the file holds only characters that copy exactly."""
    out = []
    for ch in unicodedata.normalize("NFC", s):
        cat = unicodedata.category(ch)
        if cat == "Cf":  # zero-width spaces and joiners, soft hyphens, direction marks
            continue
        if cat in ("Cc", "Zl", "Zp") or (cat == "Zs" and ch != " "):
            out.append(" ")
        elif 0xD800 <= ord(ch) <= 0xDFFF:  # lone surrogate: can't be written as UTF-8
            continue
        else:
            out.append(ch)
    return "".join(out)


def clean(val):
    if isinstance(val, str):
        return clean_text(val)
    if isinstance(val, list):
        return [clean(v) for v in val]
    if isinstance(val, dict):
        return {clean_text(str(k)): clean(v) for k, v in val.items()}
    return val


def load_dir(path):
    rows = []
    for f in sorted(path.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and ID_RE.match(f.stem):
            rows.append((f.stem, data))
    return rows


def pick(doc_id, data, fields):
    out = {"id": doc_id}
    for key in fields:
        val = data.get(key)
        if val is None or val == "" or val == [] or val is False and key == "sponsored":
            continue
        out[key] = clean(val)
    return out


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src = pathlib.Path(sys.argv[1])
    dest = pathlib.Path(sys.argv[2])

    meta_raw = {}
    meta_file = src / "meta" / "site.json"
    if meta_file.exists():
        meta_raw = json.loads(meta_file.read_text(encoding="utf-8"))

    blocked = [t.strip().lower() for t in meta_raw.get("blocked") or [] if isinstance(t, str) and len(t.strip()) >= 3]

    def visible(data):
        title = (str(data.get("title") or "") + " " + str(data.get("ship") or "")).lower()
        return bool(title.strip()) and not any(b in title for b in blocked)

    deals = [pick(i, d, DEAL_FIELDS) for i, d in load_dir(src / "deals") if visible(d)]
    cruises = [pick(i, d, CRUISE_FIELDS) for i, d in load_dir(src / "cruises") if visible(d)]
    if not deals and not cruises:
        sys.exit("No deals or cruises found under " + str(src) + "; nothing written.")

    meta = {k: clean(meta_raw[k]) for k in META_FIELDS if k in meta_raw}
    now = datetime.datetime.now(ZoneInfo("America/Chicago"))
    board = {
        "version": 1,
        "generatedAt": now.isoformat(timespec="seconds"),
        "meta": meta,
        "deals": deals,
        "cruises": cruises,
    }
    # One value per line keeps every line short, so the file can be read and copied exactly.
    raw = json.dumps(board, ensure_ascii=False, indent=1, sort_keys=True).encode("utf-8")
    if b"\\u" in raw.replace(b"\\\\", b""):
        sys.exit("The board still has a \\u escape; nothing written.")
    dest.write_bytes(raw)
    sha8 = hashlib.sha256(raw).hexdigest()[:8]
    name = "board-" + now.strftime("%Y-%m-%d-%H%M") + "-" + sha8 + ".json"
    print("name=" + name, "deals=" + str(len(deals)), "cruises=" + str(len(cruises)), "bytes=" + str(len(raw)))


if __name__ == "__main__":
    main()
