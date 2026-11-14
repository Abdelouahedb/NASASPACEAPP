"""Step 4 - the irrigated plain: which fields were growing during the dry summer?

Idea: summer 2026 (June-October) is the dry season in the Doukkala. A field whose
L-band HV backscatter RISES over the summer is growing leaves and stems; with no
rain, that growth needs irrigation. The time series of every pixel is its "rhythm".

Classes (per pixel, using the full time series of ONE orbit track so viewing
geometry is constant):
  1 water   2 built-up   3 trees/orchards   4 active crop (irrigated)   5 bare / fallow

Also: green-cover area per date, and the month each crop peaked (a crop calendar).

    python scripts/04_fields.py --zone doukkala            # picks the best track
    python scripts/04_fields.py --zone doukkala --track 044
"""
import argparse
import json
from collections import Counter

import numpy as np

import config as C
from common import Grid, db, encode_cube, lee_filter, radar_rgba, save_rgba, scenes

CLASSES = {
    1: ("water", "Eau", (37, 99, 235)),
    2: ("urban", "Bâti / villages", (226, 232, 240)),
    3: ("trees", "Arbres / vergers", (21, 128, 61)),
    4: ("crop", "Culture active (irriguée)", (163, 230, 53)),
    5: ("bare", "Sol nu / jachère", (180, 140, 90)),
}
MONTH_COLORS = {6: (250, 204, 21), 7: (251, 146, 60), 8: (239, 68, 68), 9: (168, 85, 247), 10: (59, 130, 246)}


def classify(hh, hv):
    r = C.FIELD_RULES
    valid = np.isfinite(hv).sum(0) >= max(3, hv.shape[0] // 2)
    with np.errstate(invalid="ignore"), np.errstate(all="ignore"):
        mhv, mhh, shv = np.nanmean(hv, 0), np.nanmean(hh, 0), np.nanstd(hv, 0)
        p10, p90 = np.nanpercentile(hv, 10, axis=0), np.nanpercentile(hv, 90, axis=0)
    cls = np.zeros(hv.shape[1:], np.uint8)
    cls[valid] = 5
    crop = valid & ((p90 - p10) >= r["crop_range_min"]) & (p90 >= r["crop_peak_min"])
    cls[crop] = 4
    cls[valid & (mhv >= r["tree_hv_min"]) & (shv <= r["tree_std_max"])] = 3
    cls[valid & (mhh >= r["urban_hh_min"])] = 2
    cls[valid & (mhv <= r["water_hv_max"]) & (mhh <= -16)] = 1
    return cls


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zone", default="doukkala")
    ap.add_argument("--track")
    args = ap.parse_args()
    zone = args.zone
    paths, grid = C.zone_paths(zone), Grid(zone)
    for k in ("layers", "work"):
        paths[k].mkdir(parents=True, exist_ok=True)
    for old in [*paths["layers"].glob("*.png"), *paths["layers"].glob("*.webp")]:
        old.unlink()

    items = scenes(zone)
    if not items:
        print(f"No data in {paths['raw']}. Run 02_download.py --zone {zone} (or 00_make_demo.py).")
        return
    track = args.track or Counter(i["track"] for i, _, _ in items).most_common(1)[0][0]
    items = [t for t in items if t[0]["track"] == track]
    print(f"Using track {track} ({items[0][0]['direction']}), {len(items)} dates")

    hh_s, hv_s, records = [], [], []
    for info, _, pols in items:
        hh = db(lee_filter(grid.to_grid(*pols["HH"]), C.SPECKLE_WINDOW))
        hv = db(lee_filter(grid.to_grid(*pols["HV"]), C.SPECKLE_WINDOW))
        key = f"{info['date']}_{info['track']}"
        save_rgba(paths["layers"] / f"radar_{key}.webp", radar_rgba(grid, hh, hv))
        hh_s.append(hh)
        hv_s.append(hv)
        records.append({**info, "key": key, "radar": f"data/layers/{zone}/radar_{key}.webp"})
    hh_s, hv_s = np.stack(hh_s), np.stack(hv_s)

    cls = classify(hh_s, hv_s)
    grid.save_tif(paths["work"] / "classes.tif", cls)
    farmland = (cls == 4) | (cls == 5)
    for rec, hv in zip(records, hv_s):
        green = farmland & (hv >= C.FIELD_RULES["green_hv_min"])
        rec["green_km2"] = round(float(green.sum() * grid.px_km2), 1)
        rec["coverage"] = round(float(np.isfinite(hv).mean()), 3)
        print(f"  {rec['date']}: green cover {rec['green_km2']:7.1f} km2")

    # class map
    disp = grid.to_display(cls.astype("float32"))
    rgba = np.zeros((grid.dH, grid.dW, 4), np.uint8)
    for k, (_, _, col) in CLASSES.items():
        rgba[disp == k] = (*col, 215)
    save_rgba(paths["layers"] / "classes.png", rgba)

    # crop calendar: month of peak HV for active crops
    with np.errstate(all="ignore"):
        peak_i = np.nanargmax(np.where(np.isfinite(hv_s), hv_s, -99), axis=0)
    months = np.array([int(r["date"][5:7]) for r in records])
    peak_m = np.where(cls == 4, months[peak_i], 0).astype("float32")
    pdisp = grid.to_display(peak_m)
    prgba = np.zeros((grid.dH, grid.dW, 4), np.uint8)
    for m, col in MONTH_COLORS.items():
        prgba[pdisp == m] = (*col, 225)
    save_rgba(paths["layers"] / "peak_month.png", prgba)
    peak_counts = {str(m): round(float(((peak_m == m)).sum() * grid.px_km2), 1) for m in MONTH_COLORS}

    areas = {CLASSES[k][0]: round(float((cls == k).sum() * grid.px_km2), 1) for k in CLASSES}
    out = {
        "zone": zone, "name": C.ZONES[zone]["name"], "kind": "fields",
        "bounds": grid.leaflet_bounds, "pixel_m": grid.p, "track": track,
        "direction": items[0][0]["direction"], "demo": any(i["demo"] for i, _, _ in items),
        "dates": records,
        "classes": {CLASSES[k][0]: {"label": CLASSES[k][1], "color": "#%02x%02x%02x" % CLASSES[k][2],
                                    "km2": areas[CLASSES[k][0]]} for k in CLASSES},
        "classes_image": f"data/layers/{zone}/classes.png",
        "peak_image": f"data/layers/{zone}/peak_month.png",
        "peak_km2_by_month": peak_counts,
        "month_colors": {str(m): "#%02x%02x%02x" % c for m, c in MONTH_COLORS.items()},
        "cube": {**encode_cube(grid, hv_s), "keys": [r["key"] for r in records]},
    }
    paths["json"].write_text(json.dumps(out), encoding="utf-8")
    print("\nAreas (km2):", areas)
    print("Next: python scripts/05_export.py")


if __name__ == "__main__":
    main()
