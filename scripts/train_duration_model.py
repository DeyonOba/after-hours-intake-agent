"""Generate synthetic job history and train the duration-prediction model.

Ground-truth generative rule (documented in data/cases/README.md):
    duration = base_duration_min * 1.15^old_fixture * 1.10^recurring
               * 1.25^multi_fixture + N(0, 8)  [floored at 15 min]

The eval answer keys use the same rule WITHOUT noise, so the model's job is to
recover the rule from noisy history — a real (if small) ML task the agent
calls as a tool. Fixed seed => byte-identical CSV and near-identical model on
every machine.
"""
from __future__ import annotations

import csv
import json
import random
from pathlib import Path

import joblib
from sklearn.ensemble import RandomForestRegressor

ROOT = Path(__file__).resolve().parent.parent
RNG = random.Random(20260831)

N_PER_CODE = 30


def main() -> None:
    price_book = json.loads((ROOT / "data" / "price_book.json").read_text())
    items = [i for i in price_book["items"] if i["base_duration_min"] > 0]
    codes = [i["code"] for i in items]

    rows = []
    for item in items:
        for _ in range(N_PER_CODE):
            old = RNG.random() < 0.35
            rec = RNG.random() < 0.20
            multi = RNG.random() < 0.10
            dur = item["base_duration_min"] * (1.15 if old else 1) * (1.10 if rec else 1) * (1.25 if multi else 1)
            dur = max(15, dur + RNG.gauss(0, 8))
            rows.append([item["code"], int(old), int(rec), int(multi), round(dur, 1)])
    RNG.shuffle(rows)

    csv_path = ROOT / "data" / "historical_jobs.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["job_code", "old_fixture", "recurring", "multi_fixture", "duration_min"])
        w.writerows(rows)
    print(f"wrote {csv_path} ({len(rows)} rows)")

    X = [[1.0 if r[0] == c else 0.0 for c in codes] + [float(r[1]), float(r[2]), float(r[3])]
         for r in rows]
    y = [r[4] for r in rows]
    model = RandomForestRegressor(n_estimators=200, random_state=0)
    model.fit(X, y)

    # report training-rule MAE on the noise-free rule (what the eval keys use)
    base = {i["code"]: i["base_duration_min"] for i in items}
    errs = []
    for code in codes:
        for old in (0, 1):
            for rec in (0, 1):
                truth = base[code] * (1.15 if old else 1) * (1.10 if rec else 1)
                feats = [[1.0 if code == c else 0.0 for c in codes] + [float(old), float(rec), 0.0]]
                errs.append(abs(model.predict(feats)[0] - truth))
    print(f"noise-free rule MAE: {sum(errs)/len(errs):.1f} min over {len(errs)} combos")

    out = ROOT / "models"
    out.mkdir(exist_ok=True)
    joblib.dump({"model": model, "codes": codes}, out / "duration_model.joblib")
    print(f"saved {out / 'duration_model.joblib'}")


if __name__ == "__main__":
    main()
