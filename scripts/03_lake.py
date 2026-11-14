"""Step 3 - the reservoir: water maps, lake area per date, web layers.

For every date:
  1. resample HH and HV onto one common UTM grid (so dates line up)
  2. Lee speckle filter, gamma0 power -> dB
  3. threshold dark backscatter. For Al Massira, use fixed thresholds and a reservoir boundary
  4. clean the mask, keep water bodies >= 0.25 km2, measure the area
Then a water-occurrence map, a first-vs-last change map, and data/work/massira.json

    python scripts/03_lake.py --zone massira
"""
import argparse
import json

import numpy as np
from skimage.filters import threshold_otsu
from skimage.morphology import remove_small_holes, remove_small_objects
from scipy import ndimage
from rasterio.features import geometry_mask
from rasterio.transform import rowcol
from rasterio.warp import transform, transform_geom

import config as C
from common import Grid, db, encode_cube, lee_filter, radar_rgba, save_rgba, scenes


def otsu_clamped(values, lo, hi):
    v = values[np.isfinite(values)]
    v = v[(v > -45) & (v < 10)]
    if v.size < 1000:
        return (lo + hi) / 2
    return float(np.clip(threshold_otsu(v), lo, hi))


def drop_small(mask, fn, n_px):
    """scikit-image >= 0.26 uses max_size; older versions use min_size / area_threshold."""
    try:
        return fn(mask, max_size=n_px - 1)
    except TypeError:
        kw = "min_size" if fn is remove_small_objects else "area_threshold"
        return fn(mask, **{kw: n_px})


def classify_water(hh_db, hv_db):
    t_hv = otsu_clamped(hv_db, *C.HV_THRESHOLD_RANGE)
    t_hh = otsu_clamped(hh_db, *C.HH_THRESHOLD_RANGE)
    valid = np.isfinite(hh_db) & np.isfinite(hv_db)
    # Water = dark in HV and HH. Very dark HV alone also counts (wind can brighten HH).
    water = valid & (((hv_db < t_hv) & (hh_db < t_hh)) | (hv_db < t_hv - 4))
    water = ndimage.binary_opening(water, iterations=1)
    water = drop_small(water, remove_small_objects, C.MIN_WATER_PIXELS)
    water = drop_small(water, remove_small_holes, C.MIN_WATER_PIXELS)
    return water & valid, valid, t_hh, t_hv


def lake_only(water, px_km2, min_km2=0.25):
    lab, n = ndimage.label(water)
    if n == 0:
        return water
    sizes = ndimage.sum(water, lab, index=np.arange(1, n + 1))
    keep = np.zeros(n + 1, bool)
    keep[1:] = sizes * px_km2 >= min_km2
    return keep[lab]


THRESHOLD_OFFSETS_DB = (-0.5, -0.25, 0.0, 0.25, 0.5)


def reservoir_window(grid, settings):
    vertices = settings["water_boundary"]
    polygon = {"type": "Polygon", "coordinates": [[*vertices, vertices[0]]]}
    projected = transform_geom("EPSG:4326", grid.crs, polygon)
    window = geometry_mask([projected], out_shape=(grid.H, grid.W), transform=grid.T, invert=True)
    lon, lat = settings["water_seed"]
    x, y = transform("EPSG:4326", grid.crs, [lon], [lat])
    return window, rowcol(grid.T, x[0], y[0])


def seeded_water(hh_db, hv_db, valid, window, seed, thresholds):
    hh_max, hv_max = thresholds
    water = valid & window & (hh_db < hh_max) & (hv_db < hv_max)
    water = ndimage.binary_opening(water)
    labels, _ = ndimage.label(water)
    reservoir = labels[seed]
    if reservoir == 0:
        return None
    return drop_small(labels == reservoir, remove_small_holes, C.MIN_WATER_PIXELS) & valid & window


def mask_rgba(grid, mask, color, alpha):
    m = grid.to_display(mask.astype("float32")) > 0.5
    rgba = np.zeros((grid.dH, grid.dW, 4), np.uint8)
    rgba[m] = (*color, alpha)
    return rgba


def occurrence_rgba(grid, freq):
    f = grid.to_display(freq)
    stops = np.array([[254, 240, 138], [74, 222, 128], [34, 211, 238], [37, 99, 235], [30, 27, 120]], float)
    t = np.clip(np.nan_to_num(f), 0, 1) * (len(stops) - 1)
    i = np.minimum(t.astype(int), len(stops) - 2)
    frac = (t - i)[..., None]
    rgba = np.zeros((grid.dH, grid.dW, 4), np.uint8)
    rgba[..., :3] = (stops[i] * (1 - frac) + stops[i + 1] * frac).astype(np.uint8)
    rgba[..., 3] = np.where(np.isfinite(f) & (f > 0), 220, 0)
    return rgba


def change_rgba(grid, first, last):
    a = grid.to_display(first.astype("float32")) > 0.5
    b = grid.to_display(last.astype("float32")) > 0.5
    rgba = np.zeros((grid.dH, grid.dW, 4), np.uint8)
    rgba[a & b] = (37, 99, 235, 150)       # stayed water
    rgba[a & ~b] = (249, 115, 22, 240)     # lost: shoreline retreat
    rgba[~a & b] = (34, 211, 238, 240)     # gained
    return rgba


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zone", default="massira")
    zone = ap.parse_args().zone
    paths, grid = C.zone_paths(zone), Grid(zone)
    for k in ("layers", "work"):
        paths[k].mkdir(parents=True, exist_ok=True)
    items = scenes(zone)
    if not items:
        print(f"No data in {paths['raw']}. Run 02_download.py --zone {zone} (or 00_make_demo.py).")
        return

    expected = set()
    settings = C.ZONES[zone]
    constrained = "water_boundary" in settings
    if constrained:
        window, seed = reservoir_window(grid, settings)
    records, masks, hv_stack = [], [], []
    areas_by_threshold = {}
    for info, _, pols in items:
        hh_db = db(lee_filter(grid.to_grid(*pols["HH"]), C.SPECKLE_WINDOW))
        hv_db = db(lee_filter(grid.to_grid(*pols["HV"]), C.SPECKLE_WINDOW))
        if constrained and not info["demo"]:
            valid = np.isfinite(hh_db) & np.isfinite(hv_db)
            t_hh, t_hv = settings["water_thresholds_db"]
            lake = seeded_water(hh_db, hv_db, valid, window, seed, (t_hh, t_hv))
            cov = float(valid[window].mean())
            if lake is None or cov < C.MIN_COVERAGE:
                print(f"Skip {info['date']}: low coverage or reservoir core unavailable.")
                continue
            valid &= window
        else:
            water, valid, t_hh, t_hv = classify_water(hh_db, hv_db)
            lake = lake_only(water, grid.px_km2)
            cov = float(valid.mean())
        key = f"{info['date']}_{info['track']}"
        expected.update((f"radar_{key}.webp", f"water_{key}.png"))
        save_rgba(paths["layers"] / f"radar_{key}.webp", radar_rgba(grid, hh_db, hv_db))
        save_rgba(paths["layers"] / f"water_{key}.png", mask_rgba(grid, lake, (56, 189, 248), 200))
        grid.save_tif(paths["work"] / f"water_{key}.tif", lake)
        rec = {**info, "key": key, "coverage": round(cov, 3), "partial": cov < C.MIN_COVERAGE,
               "lake_km2": round(float(lake.sum() * grid.px_km2), 2),
               "thr_hh_db": round(t_hh, 1), "thr_hv_db": round(t_hv, 1),
               "radar": f"data/layers/{zone}/radar_{key}.webp",
               "water": f"data/layers/{zone}/water_{key}.png"}
        if constrained and not info["demo"]:
            areas = {}
            for offset in THRESHOLD_OFFSETS_DB:
                candidate = lake if offset == 0 else seeded_water(
                    hh_db, hv_db, valid, window, seed, (t_hh + offset, t_hv + offset))
                if candidate is not None:
                    areas[offset] = float(candidate.sum() * grid.px_km2)
            areas_by_threshold[key] = areas
        records.append(rec)
        masks.append((rec, lake, valid))
        hv_stack.append(hv_db)
        print(f"{info['date']} trk {info['track']}: lake {rec['lake_km2']:6.2f} km2 | thr HV {t_hv:.1f} "
              f"HH {t_hh:.1f} dB | coverage {cov:.0%}{'  PARTIAL' if rec['partial'] else ''}")

    if not masks:
        raise SystemExit("No usable reservoir acquisitions")
    full = [m for m in masks if not m[0]["partial"]] or masks
    with np.errstate(invalid="ignore"):
        freq = (np.stack([m for _, m, _ in full]).sum(0) /
                np.stack([v for _, _, v in full]).sum(0).astype("float32"))
    save_rgba(paths["layers"] / "occurrence.png", occurrence_rgba(grid, freq))
    first, last = full[0], full[-1]
    shared = first[2] & last[2]
    before, after = first[1] & shared, last[1] & shared
    save_rgba(paths["layers"] / "change.png", change_rgba(grid, before, after))
    lost = float((before & ~after).sum() * grid.px_km2)
    gained = float((~before & after).sum() * grid.px_km2)

    out = {
        "zone": zone, "name": C.ZONES[zone]["name"], "kind": "lake",
        "bounds": grid.leaflet_bounds, "pixel_m": grid.p,
        "demo": any(i["demo"] for i, _, _ in items),
        "dates": records,
        "change": {"from": first[0]["key"], "to": last[0]["key"], "lost_km2": round(lost, 2),
                   "gained_km2": round(gained, 2), "image": f"data/layers/{zone}/change.png"},
        "occurrence": f"data/layers/{zone}/occurrence.png",
        "cube": {**encode_cube(grid, np.stack(hv_stack)), "keys": [r["key"] for r in records]},
    }
    first_areas = areas_by_threshold.get(first[0]["key"], {})
    last_areas = areas_by_threshold.get(last[0]["key"], {})
    shared_offsets = first_areas.keys() & last_areas.keys()
    if len(shared_offsets) > 1 and first[0]["key"] != last[0]["key"]:
        changes = [last_areas[d] - first_areas[d] for d in shared_offsets]
        out["change"]["sensitivity"] = {
            "net_change_km2": [round(min(changes), 2), round(max(changes), 2)],
            "offsets_db": sorted(shared_offsets),
        }
    paths["json"].write_text(json.dumps(out), encoding="utf-8")
    expected.update(("change.png", "occurrence.png"))
    for pattern in ("radar_*.webp", "water_*.png"):
        for layer in paths["layers"].glob(pattern):
            if layer.name not in expected:
                layer.unlink()
    print(f"\n{len(records)} dates. {first[0]['key']} -> {last[0]['key']}: -{lost:.2f} / +{gained:.2f} km2")
    print("Next: python scripts/05_export.py")


if __name__ == "__main__":
    main()
