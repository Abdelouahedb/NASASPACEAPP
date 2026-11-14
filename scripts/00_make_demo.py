"""Optional - SYNTHETIC test data, so the pipeline and the app can be tested
before the real NISAR files are downloaded.

One fake HH/HV GeoTIFF pair per real granule date in data/granules_<zone>.csv:
  massira  - a made-up winding lake whose size follows the official fill rate
  doukkala - made-up parcels: irrigated crops that grow and get harvested,
             fallow land, orchards, villages
Folders are prefixed DEMO_ and the app shows a "demo data" banner.
Delete data/raw/<zone>/DEMO_* once you have real data.

    python scripts/00_make_demo.py              # both zones
    python scripts/00_make_demo.py --zone doukkala
"""
import argparse
import csv
from datetime import date

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.transform import from_origin
from scipy import ndimage

import config as C

P = 20.0  # native NISAR GCOV pixel


def native_grid(zone):
    tr = Transformer.from_crs("EPSG:4326", C.ZONES[zone]["crs"], always_xy=True)
    w, s, e, n = C.ZONES[zone]["bbox"]
    xs, ys = tr.transform([w, e, w, e], [s, s, n, n])
    x0, x1, y0, y1 = min(xs) - 400, max(xs) + 400, min(ys) - 400, max(ys) + 400
    W, H = int((x1 - x0) / P), int((y1 - y0) / P)
    gx, gy = np.meshgrid(x0 + (np.arange(W) + 0.5) * P, y1 - (np.arange(H) + 0.5) * P)
    return tr, x0, y1, W, H, gx, gy


def smooth_noise(rng, shape, sigma, amp):
    f = ndimage.gaussian_filter(rng.standard_normal(shape), sigma)
    return f / f.std() * amp


def speckle(rng, power, looks=4):
    return (power * rng.gamma(looks, 1 / looks, power.shape)).astype("float32")


def write_pair(zone, g, hh, hv, x0, y1):
    off = {"044": 7, "095": 13, "023": 3}.get(g["track"], 0)
    out = C.zone_paths(zone)["raw"] / f"DEMO_{g['granule']}"
    out.mkdir(parents=True, exist_ok=True)
    for pol, arr in (("HHHH", hh), ("HVHV", hv)):
        with rasterio.open(out / f"{g['granule']}_{pol}.tif", "w", driver="GTiff", height=arr.shape[0],
                           width=arr.shape[1], count=1, dtype="float32", crs=C.ZONES[zone]["crs"],
                           transform=from_origin(x0 + off, y1 - off, P, P), nodata=np.nan,
                           compress="deflate") as dst:
            dst.write(arr, 1)
            dst.set_band_description(1, pol)


def granules(zone):
    with open(C.zone_paths(zone)["granules"]) as f:
        return list(csv.DictReader(f))


# ------------------------------------------------------------------ lake
def demo_lake():
    rng = np.random.default_rng(42)
    tr, x0, y1, W, H, gx, gy = native_grid("massira")
    river = [(-7.6375, 32.4753), (-7.615, 32.462), (-7.585, 32.452), (-7.555, 32.441), (-7.525, 32.447),
             (-7.495, 32.437), (-7.465, 32.428), (-7.435, 32.432), (-7.405, 32.421), (-7.37, 32.415)]
    rx, ry = tr.transform(*zip(*river))
    line = np.zeros((H, W), bool)
    for (ax, ay), (bx, by) in zip(zip(rx, ry), list(zip(rx, ry))[1:]):
        for t in np.linspace(0, 1, 800):
            r, c = int((y1 - (ay + t * (by - ay))) / P), int((ax + t * (bx - ax) - x0) / P)
            if 0 <= r < H and 0 <= c < W:
                line[r, c] = True
    dist = ndimage.distance_transform_edt(~line) * P
    terrain = (0.0012 * np.clip(gx - rx[0], 0, None) + 0.016 * dist
               + smooth_noise(rng, (H, W), 30, 7) + smooth_noise(rng, (H, W), 8, 2.5))
    terrain[gx < rx[0] - 300] += 200
    valley = dist < 9000
    zsorted = np.sort(terrain[valley].ravel())
    texture = smooth_noise(rng, (H, W), 6, 1.6)
    ponds = (smooth_noise(rng, (H, W), 2, 1) > 3.2) & ~valley

    with open(C.DATA / "official_fill.csv", encoding="utf-8") as f:
        off = [(date.fromisoformat(r["date"]).toordinal(), float(r["fill_pct"])) for r in csv.DictReader(f)]
    for i, g in enumerate(granules("massira")):
        fill = float(np.interp(date.fromisoformat(g["date"]).toordinal(), *zip(*off)))
        area = 140 * (fill / 100) ** 0.6                       # ~140 km2 when full
        water = (terrain < zsorted[int(area * 1e6 / P ** 2)]) | ponds
        windy = i % 7 == 3
        hh = speckle(rng, 10 ** (np.where(water, -21 + (6 if windy else 0), -9 + texture) / 10))
        hv = speckle(rng, 10 ** (np.where(water, -29 + (2 if windy else 0), -16 + 0.8 * texture) / 10))
        if g["track"] == "023":
            hh[:, int(W * 0.96):] = hv[:, int(W * 0.96):] = np.nan
        if g["date"] == "2026-07-09":
            hh[:, int(W * 0.55):] = hv[:, int(W * 0.55):] = np.nan
        write_pair("massira", g, hh, hv, x0, y1)
        print(f"DEMO massira {g['date']} trk {g['track']}: fill {fill:5.2f}% -> lake {area:5.1f} km2")


# ------------------------------------------------------------------ fields
def demo_fields():
    rng = np.random.default_rng(7)
    tr, x0, y1, W, H, gx, gy = native_grid("doukkala")
    ang = np.radians(14)
    u = gx * np.cos(ang) + gy * np.sin(ang)
    v = -gx * np.sin(ang) + gy * np.cos(ang)
    pid = np.floor(u / 380).astype(np.int64) * 100003 + np.floor(v / 240).astype(np.int64)
    uniq, inv = np.unique(pid, return_inverse=True)
    inv = inv.reshape(H, W)
    n = uniq.size
    # irrigated perimeter = a big blob in the south-east of the box (the canal-served plain)
    cx, cy = gx.mean() + 6000, gy.mean() - 3000
    perim = ((gx - cx) / 19000) ** 2 + ((gy - cy) / 14000) ** 2 + smooth_noise(rng, (H, W), 60, 0.15) < 1
    pin = ndimage.mean(perim, inv, index=np.arange(n)) > 0.5
    r = rng.random(n)
    pclass = np.where(pin, np.select([r < 0.42, r < 0.52], [4, 3], 5),
                      np.select([r < 0.06, r < 0.10], [4, 3], 5))
    peak = rng.normal(225, 28, n)                                 # day of year of crop peak (Jul-Sep)
    width = rng.uniform(18, 32, n)
    moist = rng.normal(0, 1.2, n)
    cls = pclass[inv]
    villages = np.zeros((H, W), bool)
    for _ in range(14):
        vx, vy, rad = rng.uniform(gx.min(), gx.max()), rng.uniform(gy.min(), gy.max()), rng.uniform(250, 600)
        villages |= (gx - vx) ** 2 + (gy - vy) ** 2 < rad ** 2
    cls[villages] = 2
    cls[np.abs((gy - cy) - 0.35 * (gx - cx) + 2500) < 45] = 1     # a straight irrigation canal

    for g in granules("doukkala"):
        doy = date.fromisoformat(g["date"]).timetuple().tm_yday
        growth = np.exp(-((doy - peak) / width) ** 2)[inv]
        hv_db = np.select([cls == 1, cls == 2, cls == 3, cls == 4],
                          [-28.0, -11.0, -13.2, -21 + 9.5 * growth], default=-22.0 + 0.8 * moist[inv])
        hh_db = np.select([cls == 1, cls == 2, cls == 3, cls == 4],
                          [-21.0, -1.0, -8.0, -12 + 4.5 * growth], default=-12.5 + 1.2 * moist[inv])
        write_pair("doukkala", g, speckle(rng, 10 ** (hh_db / 10)), speckle(rng, 10 ** (hv_db / 10)), x0, y1)
        print(f"DEMO doukkala {g['date']} trk {g['track']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zone", choices=list(C.ZONES))
    z = ap.parse_args().zone
    if z in (None, "massira"):
        demo_lake()
    if z in (None, "doukkala"):
        demo_fields()


if __name__ == "__main__":
    main()
