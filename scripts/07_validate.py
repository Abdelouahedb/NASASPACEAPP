"""Step 7 - does the radar really see irrigated fields? Train, test, prove.

Labels come from OPTICAL data (06_fetch_hls.py), features from RADAR only:
  label 1 "green in the dry season"   : NDVI >= GREEN_NDVI on at least one clear date
  label 0 "not green all season"       : NDVI <  BARE_NDVI on every clear date
  pixels in between are left out (ambiguous), so are open water and cloudy pixels.

Model: random forest on each pixel's radar time series (HH, HV, HV-HH per date + seasonal
statistics). It is tested with SPATIAL block cross-validation (whole 2 km blocks are held
out), so neighbouring pixels of the same field never sit in both training and test sets.

Baselines on exactly the same pixels:
  rules      the hand-written rules of 04_fields.py (trees or active crop = green)
  threshold  one radar date, HV >= -17 dB (the simplest possible radar method)

Also: which dates / polarisations the model relies on (permutation importance), an
irrigated-area estimate with an error range, and an optical check of the "open water" class.

    python scripts/07_validate.py
Output: web/data/validation.js (+ map layers in web/data/layers/doukkala/)
"""
import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import accuracy_score, cohen_kappa_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import GroupKFold

import config as C
from common import Grid, save_rgba

GREEN_NDVI, BARE_NDVI = 0.40, 0.25
BLOCK_M = 2000
MAX_TRAIN = 60000
SEED = 7


def load_rules():
    spec = importlib.util.spec_from_file_location("fields", Path(__file__).with_name("04_fields.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.classify


def features(hh, hv):
    """(N, F) matrix + feature names from (T, N) radar arrays in dB."""
    T = hh.shape[0]
    ratio = hv - hh
    cols, names = [], []
    for t in range(T):
        cols += [hh[t], hv[t], ratio[t]]
        names += [f"HH t{t}", f"HV t{t}", f"HV-HH t{t}"]
    x = np.arange(T) - (T - 1) / 2
    slope = (x[:, None] * (hv - hv.mean(0))).sum(0) / max((x ** 2).sum(), 1e-9)
    stats = {"HV mean": hv.mean(0), "HV std": hv.std(0), "HV max": hv.max(0), "HV min": hv.min(0),
             "HV range": hv.max(0) - hv.min(0), "HV slope": slope, "HH mean": hh.mean(0), "HV-HH mean": ratio.mean(0)}
    for k, v in stats.items():
        cols.append(v); names.append(k)
    return np.column_stack(cols).astype("float32"), names


def metrics(y, p):
    return {"accuracy": round(float(accuracy_score(y, p)), 3), "precision": round(float(precision_score(y, p, zero_division=0)), 3),
            "recall": round(float(recall_score(y, p, zero_division=0)), 3), "f1": round(float(f1_score(y, p, zero_division=0)), 3),
            "kappa": round(float(cohen_kappa_score(y, p)), 3)}


def rgba_layer(grid, arr, colors, alpha=220):
    """arr: int classes on analysis grid (0 = transparent) -> RGBA on the display grid."""
    disp = grid.to_display(arr.astype("float32"))
    out = np.zeros((grid.dH, grid.dW, 4), np.uint8)
    for k, col in colors.items():
        out[disp == k] = (*col, alpha)
    return out


def prob_layer(grid, prob):
    disp = grid.to_display(prob.astype("float32"))
    out = np.zeros((grid.dH, grid.dW, 4), np.uint8)
    ok = np.isfinite(disp) & (disp >= 0.3)
    t = np.clip((disp - 0.3) / 0.7, 0, 1)
    lo, hi = np.array([255, 243, 191]), np.array([43, 138, 62])          # pale yellow -> green
    rgb = lo[None, None] + (hi - lo)[None, None] * t[..., None]
    out[..., :3] = np.nan_to_num(rgb).astype(np.uint8)
    out[..., 3] = np.where(ok, (120 + 120 * np.nan_to_num(t)).astype(np.uint8), 0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zone", default="doukkala")
    args = ap.parse_args()
    zone, grid, paths = args.zone, Grid(args.zone), C.zone_paths(args.zone)
    S = np.load(paths["work"] / "stack.npz")
    O = np.load(paths["work"] / "hls_ndvi.npz")
    hh, hv, rdates = S["hh"], S["hv"], [str(d) for d in S["dates"]]
    ndvi, water = O["ndvi"], O["water"]
    T, H, W = hv.shape
    print(f"Radar: {T} dates on {H}x{W} grid · optical: {len(O['dates'])} clear dates {list(map(str, O['dates']))}")

    radar_ok = (np.isfinite(hh) & np.isfinite(hv)).all(0)
    n_clear = np.isfinite(ndvi).sum(0)
    with np.errstate(all="ignore"):
        nmax = np.nanmax(np.where(np.isfinite(ndvi), ndvi, -9), 0)
        wfrac = np.nanmean(water, 0)
    opt_ok = n_clear >= min(2, ndvi.shape[0])
    is_water = opt_ok & (wfrac >= 0.5)
    label = np.full((H, W), -1, np.int8)
    label[opt_ok & ~is_water & (nmax >= GREEN_NDVI)] = 1
    label[opt_ok & ~is_water & (nmax < BARE_NDVI)] = 0
    use = radar_ok & (label >= 0)
    n1, n0 = int((label[use] == 1).sum()), int((label[use] == 0).sum())
    print(f"Labelled pixels: {use.sum():,} (green {n1:,} · not green {n0:,}); ambiguous/water/cloud left out")
    if min(n1, n0) < 200:
        raise SystemExit("Too few labelled pixels in one class; check the optical dates (06_fetch_hls.py).")

    X_all, names = features(hh[:, radar_ok], hv[:, radar_ok])
    idx_ok = np.flatnonzero(radar_ok.ravel())
    pos = {p: i for i, p in enumerate(idx_ok)}
    lab_idx = np.flatnonzero(use.ravel())
    rows = np.array([pos[p] for p in lab_idx])
    X, y = X_all[rows], label.ravel()[lab_idx].astype(int)
    r_, c_ = np.unravel_index(lab_idx, (H, W))
    bpx = max(1, int(BLOCK_M / grid.p))
    groups = (r_ // bpx) * 10000 + (c_ // bpx)

    # baselines on the same pixels
    cls = load_rules()(hh, hv)
    rules_pred = np.isin(cls.ravel()[lab_idx], (3, 4)).astype(int)
    best_t = int(np.argmin([abs(np.datetime64(rd) - np.datetime64(str(O["dates"][len(O["dates"]) // 2]))) for rd in rdates]))
    thr_pred = (hv[best_t].ravel()[lab_idx] >= C.FIELD_RULES["green_hv_min"]).astype(int)

    # spatial block cross-validation (subsample for speed, stratified by block)
    rng = np.random.default_rng(SEED)
    sub = rng.choice(len(y), size=min(MAX_TRAIN, len(y)), replace=False)
    Xs, ys, gs = X[sub], y[sub], groups[sub]
    oof = np.zeros(len(ys), int)
    fold_f1 = {"model": [], "rules": [], "threshold": []}
    gkf = GroupKFold(n_splits=5)
    imp_acc = np.zeros(len(names))
    for k, (tr, te) in enumerate(gkf.split(Xs, ys, gs)):
        m = RandomForestClassifier(n_estimators=200, min_samples_leaf=5, max_features="sqrt", class_weight="balanced",
                                   n_jobs=-1, random_state=SEED + k).fit(Xs[tr], ys[tr])
        oof[te] = m.predict(Xs[te])
        fold_f1["model"].append(f1_score(ys[te], oof[te]))
        fold_f1["rules"].append(f1_score(ys[te], rules_pred[sub][te], zero_division=0))
        fold_f1["threshold"].append(f1_score(ys[te], thr_pred[sub][te], zero_division=0))
        if k == 0:
            te_s = te[:min(4000, len(te))]
            pi = permutation_importance(m, Xs[te_s], ys[te_s], scoring="f1", n_repeats=5, random_state=SEED, n_jobs=-1)
            imp_acc = np.maximum(pi.importances_mean, 0)
        print(f"  fold {k + 1}: F1 model {fold_f1['model'][-1]:.3f} · rules {fold_f1['rules'][-1]:.3f} · threshold {fold_f1['threshold'][-1]:.3f}")

    res = {name: metrics(ys, pred) for name, pred in
           (("model", oof), ("rules", rules_pred[sub]), ("threshold", thr_pred[sub]))}
    for name in res:
        res[name]["f1_folds"] = [round(float(v), 3) for v in fold_f1[name]]
        res[name]["f1_std"] = round(float(np.std(fold_f1[name])), 3)
    cm = confusion_matrix(ys, oof, labels=[0, 1]).tolist()
    print("\nSpatial CV (out-of-fold):", json.dumps({k: {m: v[m] for m in ("f1", "precision", "recall", "kappa")} for k, v in res.items()}))

    # importance grouped by polarisation and by date
    by_pol, by_date = {"HH": 0.0, "HV": 0.0, "HV-HH": 0.0, "Seasonal stats": 0.0}, [0.0] * T
    for n_, v in zip(names, imp_acc):
        if " t" in n_:
            pol, t = n_.rsplit(" t", 1)
            by_pol[pol] += v; by_date[int(t)] += v
        else:
            by_pol["Seasonal stats"] += v
    tot = sum(by_pol.values()) or 1
    top = sorted(zip(names, imp_acc), key=lambda t: -t[1])[:8]

    # final model on all labelled pixels -> map for the whole zone
    final = RandomForestClassifier(n_estimators=300, min_samples_leaf=5, max_features="sqrt", class_weight="balanced",
                                   n_jobs=-1, random_state=SEED).fit(Xs, ys)
    prob = np.full(H * W, np.nan, "float32")
    for a in range(0, len(idx_ok), 200000):
        prob[idx_ok[a:a + 200000]] = final.predict_proba(X_all[a:a + 200000])[:, 1]
    prob = prob.reshape(H, W)
    prob[cls == 1] = np.nan                                   # open water is not a field
    green = prob >= 0.5
    raw_km2 = float(green.sum() * grid.px_km2)
    pm, rm = res["model"]["precision"], res["model"]["recall"]
    adj_km2 = raw_km2 * pm / rm if rm > 0 else raw_km2        # correct for the model's known bias
    band = [float((prob >= t).sum() * grid.px_km2) for t in (0.6, 0.4)]

    # optical check of the radar "open water" class
    w_ok = (cls == 1) & np.isfinite(wfrac)
    water_check = {"radar_water_km2": round(float((cls == 1).sum() * grid.px_km2), 1),
                   "optical_agrees_pct": round(float((wfrac[w_ok] >= 0.5).mean() * 100), 1) if w_ok.any() else None}

    # map layers
    lay = paths["layers"]
    save_rgba(lay / "model_prob.png", prob_layer(grid, prob))
    dis = np.zeros((H, W), np.uint8)
    full_pred = np.zeros(H * W, int); full_pred[idx_ok] = (np.nan_to_num(prob.ravel()[idx_ok]) >= 0.5)
    fp = full_pred.reshape(H, W)
    dis[use & (fp == 1) & (label == 1)] = 1
    dis[use & (fp == 0) & (label == 0)] = 2
    dis[use & (fp == 1) & (label == 0)] = 3
    dis[use & (fp == 0) & (label == 1)] = 4
    save_rgba(lay / "model_check.png", rgba_layer(grid, dis, {1: (43, 138, 62), 2: (206, 212, 218), 3: (232, 89, 12), 4: (112, 72, 232)}, 200))
    save_rgba(lay / "optical_labels.png", rgba_layer(grid, np.where(label == 1, 1, np.where(label == 0, 2, 0)), {1: (64, 192, 87), 2: (201, 162, 107)}, 190))

    out = {
        "zone": zone, "bounds": grid.leaflet_bounds,
        "radar_dates": rdates, "optical_dates": [str(d) for d in O["dates"]], "optical_sensors": [str(s) for s in O["sensors"]],
        "optical_clear_pct": [round(float(c) * 100, 1) for c in O["clear_frac"]],
        "labels": {"green": n1, "not_green": n0, "green_ndvi": GREEN_NDVI, "bare_ndvi": BARE_NDVI, "tested": int(len(ys))},
        "cv": {"scheme": f"5-fold spatial block CV, {BLOCK_M / 1000:.0f} km blocks", **res},
        "threshold_date": rdates[best_t], "confusion": cm,
        "importance": {"by_pol": {k: round(v / tot, 3) for k, v in by_pol.items()},
                       "by_date": [round(v / tot, 3) for v in by_date], "top": [[n_, round(float(v), 4)] for n_, v in top]},
        "area_km2": {"raw": round(raw_km2, 1), "adjusted": round(adj_km2, 1), "range": [round(min(band), 1), round(max(band), 1)]},
        "water_check": water_check,
        "layers": {"prob": f"data/layers/{zone}/model_prob.png", "check": f"data/layers/{zone}/model_check.png",
                   "labels": f"data/layers/{zone}/optical_labels.png"},
    }
    js = C.WEB_DATA / "validation.js"
    js.write_text("// generated by scripts/07_validate.py\nwindow.NABD_VAL = " + json.dumps(out) + ";\n", encoding="utf-8")
    print(f"\nIrrigated / green area (model): {raw_km2:.1f} km2 raw, {adj_km2:.1f} km2 bias-adjusted, range {min(band):.1f}-{max(band):.1f}")
    print(f"Open-water check: {water_check}")
    print(f"-> {js}")


if __name__ == "__main__":
    main()
