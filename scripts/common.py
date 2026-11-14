"""Helpers shared by 03_lake.py and 04_fields.py."""
import base64
import math
import re
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from rasterio.enums import Resampling
from rasterio.transform import from_bounds, from_origin
from rasterio.warp import reproject, transform_bounds
from scipy import ndimage

import config as C

NAME_RE = re.compile(r"GCOV_(\d{3})_(\d{3})_([AD])_(\d{3})_.*?_(\d{8})T(\d{6})_")


class Grid:
    """Common analysis grid (UTM) + display grid (lat/lon) for one zone."""

    def __init__(self, zone: str):
        z = C.ZONES[zone]
        self.zone, self.bbox, self.crs, self.p = zone, z["bbox"], z["crs"], z["pixel_m"]
        w, s, e, n = transform_bounds("EPSG:4326", self.crs, *self.bbox, densify_pts=21)
        p = self.p
        w, s = math.floor(w / p) * p, math.floor(s / p) * p
        e, n = math.ceil(e / p) * p, math.ceil(n / p) * p
        self.W, self.H = int((e - w) / p), int((n - s) / p)
        self.T = from_origin(w, n, p, p)
        bw, bs, be, bn = self.bbox
        lat0 = math.radians((bs + bn) / 2)
        self.dW = int(round((be - bw) * 111320 * math.cos(lat0) / p))
        self.dH = int(round((bn - bs) * 110950 / p))
        self.dT = from_bounds(bw, bs, be, bn, self.dW, self.dH)
        self.px_km2 = p * p / 1e6

    def to_grid(self, path, band=1):
        out = np.full((self.H, self.W), np.nan, dtype="float32")
        with rasterio.open(path) as src:
            arr = src.read(band).astype("float32")
            if src.nodata is not None and not np.isnan(src.nodata):
                arr[arr == src.nodata] = np.nan
            arr[arr <= 0] = np.nan
            reproject(arr, out, src_transform=src.transform, src_crs=src.crs,
                      dst_transform=self.T, dst_crs=self.crs, src_nodata=np.nan,
                      dst_nodata=np.nan, resampling=Resampling.average)
        return out

    def to_display(self, arr, resampling=Resampling.nearest):
        out = np.full((self.dH, self.dW), np.nan, dtype="float32")
        reproject(arr.astype("float32"), out, src_transform=self.T, src_crs=self.crs,
                  dst_transform=self.dT, dst_crs="EPSG:4326", src_nodata=np.nan,
                  dst_nodata=np.nan, resampling=resampling)
        return out

    def save_tif(self, path, arr, dtype="uint8"):
        with rasterio.open(path, "w", driver="GTiff", height=self.H, width=self.W, count=1,
                           dtype=dtype, crs=self.crs, transform=self.T, compress="deflate") as d:
            d.write(arr.astype(dtype), 1)

    @property
    def leaflet_bounds(self):
        w, s, e, n = self.bbox
        return [[s, w], [n, e]]


def find_pols(folder: Path):
    """{'HH': (path, band), 'HV': (path, band)} from Harmony or stream outputs."""
    found = {}
    keys = (("HH", "HHHH"), ("HV", "HVHV"))
    for tif in sorted(folder.glob("*.tif")):
        for pol, key in keys:
            if key in tif.name.upper() and pol not in found:
                found[pol] = (tif, 1)
        if len(found) < 2:
            with rasterio.open(tif) as src:
                for b, desc in enumerate(src.descriptions or [], start=1):
                    for pol, key in keys:
                        if key in (desc or "").upper() and pol not in found:
                            found[pol] = (tif, b)
    return found


def parse_granule(name):
    m = NAME_RE.search(name)
    if not m:
        return None
    cyc, trk, d, frame, ymd, hms = m.groups()
    return {"cycle": cyc, "track": trk, "frame": frame,
            "direction": "ascending" if d == "A" else "descending",
            "date": f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:]}", "time_utc": f"{hms[:2]}:{hms[2:4]}"}


def scenes(zone):
    """Yield (info, folder, pols) for every downloaded date of a zone, sorted by date."""
    raw = C.zone_paths(zone)["raw"]
    out = []
    for folder in sorted(raw.iterdir()) if raw.exists() else []:
        info = parse_granule(folder.name) if folder.is_dir() else None
        pols = find_pols(folder) if info else {}
        if info and "HH" in pols and "HV" in pols:
            info["granule"] = folder.name.removeprefix("DEMO_")
            info["demo"] = folder.name.startswith("DEMO_")
            out.append((info, folder, pols))
        elif folder.is_dir():
            print(f"skip {folder.name}: HH/HV not found")
    out.sort(key=lambda t: (t[0]["date"], t[0]["time_utc"]))
    return out


def lee_filter(img, size):
    valid = np.isfinite(img)
    x = np.where(valid, img, 0.0)
    cnt = ndimage.uniform_filter(valid.astype("float32"), size)
    cnt[cnt == 0] = np.nan
    mean = ndimage.uniform_filter(x, size) / cnt
    sq = ndimage.uniform_filter(x * x, size) / cnt
    var = np.maximum(sq - mean * mean, 0)
    noise = np.nanmean(var[valid]) if valid.any() else 0
    w = var / (var + noise + 1e-12)
    out = mean + w * (x - mean)
    out[~valid] = np.nan
    return out


def db(x):
    with np.errstate(divide="ignore", invalid="ignore"):
        return 10 * np.log10(x)


def scale(x, lo, hi):
    return np.clip((x - lo) / (hi - lo), 0, 1)


def save_rgba(path, rgba):
    img = Image.fromarray(rgba, "RGBA")
    if str(path).endswith(".webp"):
        img.save(path, "WEBP", quality=72, method=5)     # radar texture: lossy is ~15x smaller
    else:
        img.save(path, optimize=True)


def radar_rgba(grid, hh_db, hv_db):
    """False colour: R = HH, G = HV (vegetation), B = HH/HV ratio. Water is near black."""
    hh, hv = grid.to_display(hh_db), grid.to_display(hv_db)
    valid = np.isfinite(hh) & np.isfinite(hv)
    rgba = np.zeros((grid.dH, grid.dW, 4), np.uint8)
    for i, ch in enumerate((scale(hh, -22, -2), scale(hv, -30, -10), scale(hh - hv, 2, 14))):
        rgba[..., i] = np.nan_to_num(ch * 255).astype(np.uint8)
    rgba[..., 3] = np.where(valid, 255, 0)
    return rgba


def encode_cube(grid, stack_db, target_w=180, lo=-35.0, hi=0.0):
    """Downsample a (T, H, W) dB stack on the ANALYSIS grid to ~target_w px wide uint8, in the
    lat/lon display orientation, so the browser can map a click to a pixel and 'play' it.
    255 = no data. Returns dict with base64 bytes (date-major, then rows, then columns)."""
    stack_db = np.stack([grid.to_display(a, Resampling.average) for a in stack_db])
    t, h, w = stack_db.shape
    f = max(1, int(round(w / target_w)))
    h2, w2 = h // f, w // f
    s = stack_db[:, :h2 * f, :w2 * f].reshape(t, h2, f, w2, f)
    with np.errstate(invalid="ignore"):
        m = np.nanmean(np.nanmean(s, axis=4), axis=2)
    q =np.where(np.isfinite(m), np.clip((m - lo) / (hi - lo) * 254, 0, 254), 255).astype(np.uint8)
    return {"w": int(w2), "h": int(h2), "t": int(t), "lo": lo, "hi": hi,
            "b64": base64.b64encode(q.tobytes()).decode()}
