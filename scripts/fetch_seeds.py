"""Fetch and pin the public dataset rows that seed the eval cases.

Sources (both on the Hugging Face Hub, read via the datasets-server API):
- dipenbhuva/home-diy-repair-qa    (plumbing_repair rows)
- ctgadget/nyc_311_service_requests (PLUMBING / WATER LEAK rows)

Output: data/seeds/*.json (committed, so judges never need network access).
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path

SEEDS_DIR = Path(__file__).resolve().parent.parent / "data" / "seeds"
BASE = "https://datasets-server.huggingface.co"


def get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "seed-fetcher/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def save(name: str, payload: dict) -> None:
    rows = [{"row_idx": r["row_idx"], **r["row"]} for r in payload.get("rows", [])]
    out = SEEDS_DIR / name
    out.write_text(json.dumps({"num_rows_total": payload.get("num_rows_total"),
                               "rows": rows}, indent=1))
    print(f"saved {out.name}: {len(rows)} rows (of {payload.get('num_rows_total')} matching)")


def main() -> None:
    SEEDS_DIR.mkdir(parents=True, exist_ok=True)

    ds = urllib.parse.quote("dipenbhuva/home-diy-repair-qa", safe="")
    where = urllib.parse.quote("\"category\"='plumbing_repair'", safe="")
    save("diyqa_plumbing.json",
         get(f"{BASE}/filter?dataset={ds}&config=default&split=train&where={where}&offset=0&length=40"))

    ds = urllib.parse.quote("ctgadget/nyc_311_service_requests", safe="")
    for query, name in [("PLUMBING", "nyc311_plumbing.json"), ("LEAK", "nyc311_leak.json")]:
        save(name,
             get(f"{BASE}/search?dataset={ds}&config=default&split=train&query={query}&offset=0&length=30"))


if __name__ == "__main__":
    main()
