"""Step 1 - list every NISAR GCOV granule that covers a zone.

Searching NASA's catalogue does NOT need a login.
Output: data/granules_<zone>.csv

    python scripts/01_search.py --zone massira
    python scripts/01_search.py --zone doukkala
"""
import argparse
import csv
import re

import earthaccess

from config import DATA, GCOV_SHORT_NAME, ZONES, zone_paths

POL_RE = re.compile(r"_\d{4}_([A-Z]{4})_[A-Z]_\d{8}T")
NAME_RE = re.compile(
    r"NISAR_L2_PR_GCOV_(?P<cycle>\d{3})_(?P<track>\d{3})_(?P<dir>[AD])_(?P<frame>\d{3})_"
    r".*?_(?P<start>\d{8}T\d{6})_"
)


def parse_name(name: str) -> dict:
    m = NAME_RE.search(name)
    if not m:
        return {}
    s = m["start"]
    return {
        "cycle": m["cycle"],
        "track": m["track"],
        "direction": "ascending" if m["dir"] == "A" else "descending",
        "frame": m["frame"],
        "date": f"{s[0:4]}-{s[4:6]}-{s[6:8]}",
        "time_utc": f"{s[9:11]}:{s[11:13]}",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zone", choices=list(ZONES), default="massira")
    zone = ap.parse_args().zone
    results = earthaccess.search_data(
        short_name=GCOV_SHORT_NAME,
        bounding_box=ZONES[zone]["bbox"],
        count=-1,
    )
    rows, skipped = [], []
    for g in results:
        name = g["umm"]["GranuleUR"]
        info = parse_name(name)
        links = g.data_links(access="external")
        h5 = next((u for u in links if u.endswith(".h5")), "")
        size_mb = g.size() if hasattr(g, "size") else ""
        pol = POL_RE.search(name)
        pol = pol.group(1) if pol else ""
        # Frequency A must be dual-pol H (DH) or quad-pol (QP) to have both HH and HV.
        # e.g. "NASV" products only carry 80 m frequency-B VV: not usable here.
        if pol[:2] not in ("DH", "QP"):
            skipped.append(f"{info.get('date')} ({pol})")
            continue
        rows.append({"granule": name, **info, "pol": pol, "size_mb": round(float(size_mb or 0)),
                     "h5_url": h5})

    rows.sort(key=lambda r: (r.get("date", ""), r.get("time_utc", "")))
    DATA.mkdir(parents=True, exist_ok=True)
    out = zone_paths(zone)["granules"]
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["granule", "date", "time_utc", "cycle", "track",
                                          "direction", "frame", "pol", "size_mb", "h5_url"])
        w.writeheader()
        w.writerows(rows)

    print(f"{len(rows)} usable granules -> {out}")
    if skipped:
        print(f"  skipped {len(skipped)} without HH+HV at frequency A: {', '.join(skipped)}")
    by_track = {}
    for r in rows:
        by_track.setdefault(f"track {r['track']} ({r['direction']})", []).append(r["date"])
    for k, v in by_track.items():
        print(f"  {k}: {len(v)} dates, {v[0]} -> {v[-1]}")


if __name__ == "__main__":
    main()
