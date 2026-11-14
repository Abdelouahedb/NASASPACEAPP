"""Shared settings for the NABD pipeline (NISAR L-band, Morocco)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
WEB = ROOT / "web"
WEB_DATA = WEB / "data"

# Two zones of one water system: the reservoir (supply) and the irrigated plain it feeds (demand).
ZONES = {
    "massira": {
        "name": "Barrage Al Massira",
        "kind": "lake",
        # Dam wall 32.475 N, 7.638 W; the lake winds ~40 km east along the Oum Er-Rbia.
        "bbox": (-7.70, 32.38, -7.35, 32.55),     # west, south, east, north
        "pixel_m": 20.0,
        "crs": "EPSG:32629",
    },
    "doukkala": {
        "name": "Périmètre irrigué des Doukkala",
        "kind": "fields",
        # Sidi Bennour / Zemamra / Ouled Frej irrigated plain, fed by Oum Er-Rbia releases.
        "bbox": (-8.75, 32.55, -8.25, 32.95),
        "pixel_m": 40.0,                          # 40 m = more radar looks, steadier per-field signal
        "crs": "EPSG:32629",
    },
}


def zone_paths(zone: str) -> dict:
    return {
        "raw": DATA / "raw" / zone,
        "work": DATA / "work" / zone,
        "granules": DATA / f"granules_{zone}.csv",
        "layers": WEB_DATA / "layers" / zone,
        "json": DATA / "work" / f"{zone}.json",
    }


# NISAR collection (Provisional L-band GCOV, released 20 July 2026)
GCOV_SHORT_NAME = "NISAR_L2_GCOV_PROVISIONAL_V1"
GCOV_CONCEPT_ID = "C2854338529-ASF"
GCOV_VARIABLES = [
    "/science/LSAR/GCOV/grids/frequencyA/HHHH",
    "/science/LSAR/GCOV/grids/frequencyA/HVHV",
]

# --- water (lake zone)
SPECKLE_WINDOW = 5            # Lee filter window (pixels)
MIN_WATER_PIXELS = 25         # drop specks smaller than this (25 px = 1 ha at 20 m)
HV_THRESHOLD_RANGE = (-32.0, -18.0)   # clamp for the automatic (Otsu) HV threshold, dB
HH_THRESHOLD_RANGE = (-26.0, -12.0)   # clamp for the automatic (Otsu) HH threshold, dB
MIN_COVERAGE = 0.90           # dates covering less of the zone are flagged "partial"

# --- fields (agricultural zone), all in dB on the per-pixel time series of one orbit track
FIELD_RULES = {
    "water_hv_max": -24.0,     # mean HV below this and HH below -16 -> open water
    "urban_hh_min": -4.0,      # mean HH above this -> buildings (strong double bounce)
    "tree_hv_min": -15.5,      # mean HV above this and steady -> orchards / trees
    "tree_std_max": 1.2,
    "crop_range_min": 3.0,     # HV p90-p10 above this ...
    "crop_peak_min": -17.0,    # ... and HV peak above this -> crop grew (irrigated in a dry summer)
    "green_hv_min": -17.0,     # per date: HV above this on farmland -> vegetation present
}
