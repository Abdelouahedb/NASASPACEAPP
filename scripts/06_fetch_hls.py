"""Step 6 - independent "ground truth" from optical satellites (NASA HLS).

HLS (Harmonized Landsat Sentinel-2, NASA LP DAAC) gives 30 m surface reflectance from
Landsat 8/9 and Sentinel-2. On clear days, NDVI = (NIR - red) / (NIR + red) tells us
which pixels are green. We use it ONLY to check (and train) the radar, never as a
radar input, so the comparison stays independent.

For each radar date we take the clearest HLS scene within +/- MAX_DAYS, read just the
study window (no full-tile download when possible), mask clouds/shadows with Fmask,
and resample NDVI and the HLS water flag onto the radar analysis grid.

    python scripts/06_fetch_hls.py                 # Doukkala, dates of data/work/doukkala/stack.npz
    python scripts/06_fetch_hls.py --max-days 6 --max-scenes 6

Output: data/work/doukkala/hls_ndvi.npz  (ndvi[T,H,W], water[T,H,W], dates, sensors, clear_frac)
Needs an Earthdata login in ~/.netrc (same as 02_download.py).
"""
import argparse
import datetime as dt
import os
import tempfile
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject, transform_bounds
from rasterio.windows import from_bounds as window_from_bounds

import config as C
from common import Grid

MAX_DAYS = 8
BANDS = {"HLSS30": {"red": "B04", "nir": "B8A"}, "HLSL30": {"red": "B04", "nir": "B05"}}
SCALE = 1e-4          # HLS reflectance scale factor
FILL = -9999


def gdal_env():
    """GDAL settings to read LP DAAC COGs over HTTPS with the Earthdata login in ~/.netrc."""
    jar = str(Path(tempfile.gettempdir()) / "nabd_edl_cookies.txt")
    return rasterio.Env(GDAL_HTTP_COOKIEFILE=jar, GDAL_HTTP_COOKIEJAR=jar, GDAL_HTTP_NETRC="YES",
                        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS="TIF,tif",
                        GDAL_HTTP_MAX_RETRY="4", GDAL_HTTP_RETRY_DELAY="2", VSI_CACHE="TRUE")


def band_links(granule):
    """{'red': url, 'nir': url, 'fmask': url} for one HLS granule."""
    product = "HLSS30" if ".S30." in granule["meta"]["native-id"] else "HLSL30"
    want = {**BANDS[product], "fmask": "Fmask"}
    links = [u for u in granule.data_links(access="external") if u.endswith(".tif")]
    out = {}
    for key, band in want.items():
        hit = [u for u in links if u.endswith(f".{band}.tif")]
        if hit:
            out[key] = hit[0]
    return product, out


def read_to_grid(url, grid, resampling, local_dir=None):
    """Read only the study window of a COG and resample it onto the radar grid."""
    src_path = url
    if local_dir is not None:                       # fallback: full file was downloaded
        src_path = str(Path(local_dir) / url.rsplit("/", 1)[1])
    out = np.full((grid.H, grid.W), np.nan, dtype="float32")
    with rasterio.open(src_path) as src:
        w, s, e, n = transform_bounds("EPSG:4326", src.crs, *grid.bbox, densify_pts=21)
        win = window_from_bounds(w, s, e, n, src.transform).round_offsets().round_lengths()
        win = win.intersection(rasterio.windows.Window(0, 0, src.width, src.height))
        arr = src.read(1, window=win).astype("float32")
        arr[arr == (src.nodata if src.nodata is not None else FILL)] = np.nan
        reproject(arr, out, src_transform=src.window_transform(win), src_crs=src.crs,
                  dst_transform=grid.T, dst_crs=grid.crs, src_nodata=np.nan, dst_nodata=np.nan,
                  resampling=resampling)
    return out


def fmask_flags(fm):
    """Fmask bits: 1 cloud, 2 adjacent to cloud, 3 shadow, 5 water."""
    q = np.where(np.isfinite(fm), fm, 255).astype(np.uint16)
    bad = (q == 255) | ((q >> 1) & 1).astype(bool) | ((q >> 2) & 1).astype(bool) | ((q >> 3) & 1).astype(bool)
    water = ((q >> 5) & 1).astype(bool) & ~bad
    return bad, water


def scene_on_grid(granule, grid):
    product, links = band_links(granule)
    if len(links) < 3:
        raise RuntimeError("missing bands")
    def load(local_dir=None):
        red = read_to_grid(links["red"], grid, Resampling.average, local_dir)
        nir = read_to_grid(links["nir"], grid, Resampling.average, local_dir)
        fm = read_to_grid(links["fmask"], grid, Resampling.nearest, local_dir)
        return red, nir, fm
    try:
        with gdal_env():
            red, nir, fm = load()
    except Exception as exc:  # noqa: BLE001  - streaming refused: download the 3 files instead
        import earthaccess
        print(f"    window read failed ({exc.__class__.__name__}); downloading full band files ...")
        tmp = C.zone_paths(grid.zone)["work"] / "hls_cache"
        tmp.mkdir(parents=True, exist_ok=True)
        earthaccess.download(list(links.values()), str(tmp))
        red, nir, fm = load(tmp)
    bad, water = fmask_flags(fm)
    red, nir = red * SCALE, nir * SCALE
    with np.errstate(invalid="ignore", divide="ignore"):
        ndvi = (nir - red) / (nir + red)
    ndvi[bad | ~np.isfinite(ndvi) | (red <= 0) | (nir <= 0)] = np.nan
    return product, ndvi.astype("float32"), np.where(bad, np.nan, water).astype("float32")


def main():
    import earthaccess
    ap = argparse.ArgumentParser()
    ap.add_argument("--zone", default="doukkala")
    ap.add_argument("--max-days", type=int, default=MAX_DAYS)
    ap.add_argument("--max-scenes", type=int, default=8, help="keep at most this many optical dates")
    ap.add_argument("--max-cloud", type=int, default=30, help="CMR scene cloud cover filter, %%")
    args = ap.parse_args()
    paths, grid = C.zone_paths(args.zone), Grid(args.zone)
    stack = paths["work"] / "stack.npz"
    if not stack.exists():
        raise SystemExit(f"{stack} not found: run 04_fields.py first (it saves the radar stack).")
    radar_dates = [str(d) for d in np.load(stack)["dates"]]
    t0 = dt.date.fromisoformat(radar_dates[0]) - dt.timedelta(days=args.max_days)
    t1 = dt.date.fromisoformat(radar_dates[-1]) + dt.timedelta(days=args.max_days)

    earthaccess.login(strategy="netrc")
    found = []
    for short in ("HLSS30", "HLSL30"):
        found += earthaccess.search_data(short_name=short, version="2.0", bounding_box=grid.bbox,
                                         temporal=(t0.isoformat(), t1.isoformat()),
                                         cloud_cover=(0, args.max_cloud))
    print(f"{len(found)} HLS granules {t0} → {t1} with ≤{args.max_cloud}% cloud")
    by_day = {}
    for g in found:
        day = g["umm"]["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"][:10]
        by_day.setdefault(day, []).append(g)

    # for each radar date, candidate optical days sorted by distance
    wanted = []
    for rd in radar_dates:
        r = dt.date.fromisoformat(rd)
        cands = sorted((abs((dt.date.fromisoformat(d) - r).days), d) for d in by_day
                       if abs((dt.date.fromisoformat(d) - r).days) <= args.max_days)
        wanted.append((rd, [d for _, d in cands]))

    ndvi_s, water_s, dates, sensors, clear, pairs = [], [], [], [], [], []
    used = set()
    for rd, days in wanted:
        if len(dates) >= args.max_scenes:
            break
        best = None
        for day in days:
            if day in used:
                continue
            mosaic_ndvi = np.full((grid.H, grid.W), np.nan, "float32")
            mosaic_water = mosaic_ndvi.copy()
            prods = []
            for g in by_day[day]:                    # several MGRS tiles can cover the zone
                try:
                    prod, ndvi, water = scene_on_grid(g, grid)
                except Exception as exc:  # noqa: BLE001
                    print(f"    skip {g['meta']['native-id']}: {exc}")
                    continue
                fill = ~np.isfinite(mosaic_ndvi) & np.isfinite(ndvi)
                mosaic_ndvi[fill], mosaic_water[fill] = ndvi[fill], water[fill]
                prods.append(prod)
            frac = float(np.isfinite(mosaic_ndvi).mean())
            print(f"  radar {rd}: optical {day} clear {frac:5.1%}")
            if frac >= 0.6:
                best = (day, mosaic_ndvi, mosaic_water, "+".join(sorted(set(prods))), frac)
                break
        if best:
            day, ndvi, water, prod, frac = best
            used.add(day)
            ndvi_s.append(ndvi); water_s.append(water); dates.append(day); sensors.append(prod)
            clear.append(frac); pairs.append(rd)
    if len(dates) < 2:
        raise SystemExit("Fewer than 2 usable clear optical dates: try --max-days 12 or --max-cloud 60")

    out = paths["work"] / "hls_ndvi.npz"
    np.savez_compressed(out, ndvi=np.stack(ndvi_s), water=np.stack(water_s), dates=np.array(dates),
                        sensors=np.array(sensors), clear_frac=np.array(clear), radar_pair=np.array(pairs))
    print(f"\n{len(dates)} optical dates -> {out}")
    print("Next: python scripts/07_validate.py")


if __name__ == "__main__":
    main()
