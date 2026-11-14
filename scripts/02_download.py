"""Step 2 - download ONLY the zone window of each NISAR GCOV granule.

A full GCOV file is 5-7.5 GB. We only need a box of a few tens of km, so we never
download the whole file. Two methods:

  harmony (default)  NASA's Harmony service crops on the server and sends
                     small GeoTIFFs (a few MB per date).
  stream             Opens the .h5 over HTTPS and reads only the bytes of the
                     box (h5py + fsspec). Use it if Harmony is slow or fails.

Needs a free NASA Earthdata Login. Put it in ~/.netrc (Windows: %USERPROFILE%\\_netrc):

    machine urs.earthdata.nasa.gov login YOUR_USERNAME password YOUR_PASSWORD

Usage:
    python scripts/02_download.py --zone massira               # all granules
    python scripts/02_download.py --zone doukkala --track 044  # one orbit track only
    python scripts/02_download.py --zone massira --method stream
    python scripts/02_download.py --zone massira --limit 3     # quick test
"""
import argparse
import csv
import sys
import traceback

import numpy as np

from config import GCOV_CONCEPT_ID, GCOV_VARIABLES, ZONES, zone_paths

ZONE = "massira"
AOI_BBOX = ZONES[ZONE]["bbox"]
RAW = zone_paths(ZONE)["raw"]


def load_granules(track=None, limit=None):
    with open(zone_paths(ZONE)["granules"]) as f:
        rows = list(csv.DictReader(f))
    if track:
        rows = [r for r in rows if r["track"] == track]
    if limit:
        rows = rows[:limit]
    return rows


def already_done(name):
    d = RAW / name
    return d.exists() and len(list(d.glob("*.tif"))) >= len(GCOV_VARIABLES)


# --------------------------------------------------------------------------- Harmony
def download_harmony(rows):
    from harmony import BBox, Client, Collection, Request

    client = Client()  # reads ~/.netrc (or EDL_USERNAME / EDL_PASSWORD env vars)
    w, s, e, n = AOI_BBOX
    jobs = []
    for r in rows:
        req = Request(
            collection=Collection(id=GCOV_CONCEPT_ID),
            granule_name=[r["granule"]],
            spatial=BBox(w, s, e, n),
            variables=GCOV_VARIABLES,
            format="image/tiff",
        )
        if not req.is_valid():
            print("  invalid request:", req.error_messages())
            continue
        job_id = client.submit(req)
        print(f"  submitted {r['date']} track {r['track']} -> job {job_id}")
        jobs.append((r, job_id))

    failed = []
    for r, job_id in jobs:
        out = RAW / r["granule"]
        out.mkdir(parents=True, exist_ok=True)
        try:
            client.wait_for_processing(job_id, show_progress=True)
            files = [f.result() for f in client.download_all(job_id, directory=str(out), overwrite=True)]
            print(f"  {r['date']}: {len(files)} file(s) -> {out}")
        except Exception as exc:  # noqa: BLE001
            print(f"  {r['date']}: Harmony failed ({exc})")
            failed.append(r)
    return failed


# --------------------------------------------------------------------------- Streaming
def _find(h5, suffix):
    hits = []
    h5.visit(lambda k: hits.append(k) if k.endswith(suffix) else None)
    return hits[0] if hits else None


def download_stream(rows):
    import earthaccess
    import h5py
    import rasterio
    from pyproj import Transformer
    from rasterio.transform import from_origin

    earthaccess.login(strategy="netrc")
    fs = earthaccess.get_fsspec_https_session()
    failed = []
    for r in rows:
        out = RAW / r["granule"]
        out.mkdir(parents=True, exist_ok=True)
        try:
            print(f"  streaming {r['date']} track {r['track']} ...")
            with fs.open(r["h5_url"], cache_type="background", block_size=8 * 1024 * 1024) as fo, \
                    h5py.File(fo, "r") as h5:
                grid = "science/LSAR/GCOV/grids/frequencyA"
                x = h5[f"{grid}/xCoordinates"][:]
                y = h5[f"{grid}/yCoordinates"][:]
                proj = h5[f"{grid}/projection"]
                epsg = int(proj.attrs.get("epsg_code", proj[()] if proj.shape == () else 0))
                tr = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
                w, s, e, n = AOI_BBOX
                xs, ys = tr.transform([w, e, w, e], [s, s, n, n])
                xi = np.where((x >= min(xs)) & (x <= max(xs)))[0]
                yi = np.where((y >= min(ys)) & (y <= max(ys)))[0]
                if len(xi) == 0 or len(yi) == 0:
                    raise RuntimeError("granule does not overlap the AOI")
                x0, x1, y0, y1 = xi[0], xi[-1] + 1, yi[0], yi[-1] + 1
                dx = float(x[1] - x[0])
                dy = float(y[1] - y[0])          # negative (north-up)
                transform = from_origin(x[x0] - dx / 2, y[y0] - dy / 2, dx, -dy)
                for var in GCOV_VARIABLES:
                    pol = var.rsplit("/", 1)[-1]
                    if var.lstrip("/") not in h5:
                        print(f"    {pol} not in this product, skipped")
                        continue
                    arr = h5[var.lstrip("/")][y0:y1, x0:x1].astype("float32")
                    with rasterio.open(out / f"{r['granule']}_{pol}.tif", "w", driver="GTiff",
                                       height=arr.shape[0], width=arr.shape[1], count=1,
                                       dtype="float32", crs=f"EPSG:{epsg}", transform=transform,
                                       nodata=np.nan, compress="deflate") as dst:
                        dst.write(arr, 1)
                        dst.set_band_description(1, pol)
                print(f"    ok ({y1 - y0} x {x1 - x0} px)")
        except Exception:  # noqa: BLE001
            traceback.print_exc()
            failed.append(r)
    return failed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zone", choices=list(ZONES), default="massira")
    ap.add_argument("--method", choices=["harmony", "stream"], default="harmony")
    ap.add_argument("--track")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    global ZONE, AOI_BBOX, RAW
    ZONE, AOI_BBOX, RAW = args.zone, ZONES[args.zone]["bbox"], zone_paths(args.zone)["raw"]

    rows = [r for r in load_granules(args.track, args.limit) if not already_done(r["granule"])]
    print(f"{len(rows)} granule(s) to download with {args.method}")
    if not rows:
        return
    failed = download_harmony(rows) if args.method == "harmony" else download_stream(rows)
    if failed and args.method == "harmony":
        print(f"\n{len(failed)} failed with Harmony, retrying by streaming ...")
        failed = download_stream(failed)
    if failed:
        print("\nStill failed:", ", ".join(r["date"] for r in failed))
        sys.exit(1)
    nxt = "03_lake.py" if ZONES[ZONE]["kind"] == "lake" else "04_fields.py"
    print(f"\nDone. Next: python scripts/{nxt} --zone {ZONE}")


if __name__ == "__main__":
    main()
