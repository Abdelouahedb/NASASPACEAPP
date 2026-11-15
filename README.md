# NABD (نبض) — The Pulse of Morocco's Water

> **NASA Space Apps Challenge · Track: *Dancing with the SARs***  
> Monitoring reservoir supply and agricultural demand using **NASA-ISRO SAR (NISAR)** L-band Radar.

---

## 📌 Executive Summary

**NABD** (*"Pulse"* in Arabic — **نبض**) connects space radar technology directly to national water security. Focusing on the hyper-critical water basin of Morocco, NABD monitors the end-to-end water cycle: from **reservoir storage (supply)** down to **field-level crop irrigation (demand)**.

| Component | Target Area | Role in System | Radar Observation |
| :--- | :--- | :--- | :--- |
| **Al Massira Reservoir** | Settat / Rehamna (`32.47°N, -7.64°W`) | **Supply** | Water surface area evolution across satellite passes vs. national dam fill levels. |
| **Doukkala Plain** | Sidi Bennour / Zemamra (`32.75°N, -8.50°W`) | **Demand** | Crop canopy growth dynamics in hyper-arid summer conditions to identify active irrigation. |

In addition to visual Earth observation, NABD introduces an innovative **Data Sonification mode ("Écouter la Terre")**, translating radar backscatter time series into traditional Moroccan musical scales (Hijaz mode & Darbouka rhythm).

---

## 🗺️ System Architecture & Workflow Diagrams

### End-to-End Data Pipeline Architecture

```mermaid
flowchart TD
    subgraph Data_Acquisition["1. Satellite & Catalog Acquisition"]
        A1["NASA CMR Catalog API"] -->|01_search.py| B1["granules_zone.csv"]
        B1 -->|02_download.py| C1["NASA Harmony Subset / HDF5 Stream"]
        C1 --> D1[("Raw GeoTIFF / HDF5 Granules")]
    end

    subgraph Analytics_Engine["2. SAR Processing & Scientific Analytics"]
        D1 --> E1["Standardized UTM Reprojection"]
        E1 --> E2["5x5 Lee Speckle Filter & dB Conversion"]

        E2 --> F1["Reservoir Processing (03_lake.py)"]
        F1 --> G1["Adaptive Dual Otsu Thresholding (HV & HH)"]
        G1 --> H1["Morphology & Lake Polygon Filtering"]
        H1 --> I1["Lake Extent Time Series & Occurrence Maps"]

        E2 --> F2["Agricultural Plain Processing (04_fields.py)"]
        F2 --> G2["Single-Orbit Multi-Temporal Stacking"]
        G2 --> H2["Growth Dynamic Metrics (P90 - P10)"]
        H2 --> I2["5-Class Land Cover & Irrigation Phenology"]
    end

    subgraph Synthesis_Web["3. Basin Accounting & Web Presentation"]
        I1 --> J["05_export.py Aggregator"]
        I2 --> J
        K[("official_fill.csv Ground Truth")] --> J
        J --> L[("web/data/data.js")]
        L --> M["Interactive Leaflet Map"]
        L --> N["Time-Series Charts (Chart.js)"]
        L --> O["Water Balance Accounting Card"]
        L --> P["Web Audio Sonification ('Écouter la Terre')"]
    end

    style Data_Acquisition fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#fff
    style Analytics_Engine fill:#0f172a,stroke:#10b981,stroke-width:2px,color:#fff
    style Synthesis_Web fill:#18181b,stroke:#f59e0b,stroke-width:2px,color:#fff
```

### Reservoir Water Extraction Pipeline (Al Massira)

```mermaid
flowchart LR
    InSAR["NISAR L2 GCOV (HH/HV)"] --> Reproj["Grid Align (EPSG:32629)"]
    Reproj --> Speckle["Lee Filter (5x5)"]
    Speckle --> Log["dB Conversion"]
    Log --> Otsu["Dual Otsu Thresholding<br/>(HV & HH)"]
    Otsu --> Morph["Morphological Clean<br/>(Opening + Size Filter >= 25px)"]
    Morph --> Contig["Lake Filter (>= 0.25 km²)"]
    Contig --> Metric["Lake Area (km²) & WebP Mask"]

    style InSAR fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#fff
    style Otsu fill:#1e3a5f,stroke:#38bdf8,stroke-width:2px,color:#fff
    style Metric fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#fff
```

### Agricultural Parcel Phenology & Irrigation Classifier (Doukkala)

```mermaid
flowchart TD
    TS["Multi-Temporal Radar Cube (Track-specific)"] --> Stats["Calculate Temporal Statistics<br/>(Mean, Std, P10, P90)"]
    
    Stats --> Q1{"Is (P90 - P10) >= 4.5 dB<br/>AND P90 >= -18.5 dB?"}
    Q1 -- Yes --> C4["Active Irrigated Crop<br/>(Canopy growth during dry summer)"]
    Q1 -- No --> Q2{"Is Mean HH >= -4 dB?"}
    
    Q2 -- Yes --> C2["Urban / Built-up<br/>(Double-bounce corner scattering)"]
    Q2 -- No --> Q3{"Is Mean HV >= -15.5 dB<br/>AND Std HV <= 1.2 dB?"}
    
    Q3 -- Yes --> C3["Orchard / Tree Canopy<br/>(Permanent dense volume scattering)"]
    Q3 -- No --> Q4{"Is Mean HV <= -24 dB<br/>AND Mean HH <= -16 dB?"}
    
    Q4 -- Yes --> C1["Open Water Body<br/>(Specular reflection)"]
    Q4 -- No --> C5["Bare Soil / Fallow"]

    style C4 fill:#365314,stroke:#a3e635,stroke-width:2px,color:#fff
    style C1 fill:#1e3a8a,stroke:#60a5fa,stroke-width:2px,color:#fff
    style C3 fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#fff
    style C2 fill:#374151,stroke:#9ca3af,stroke-width:2px,color:#fff
    style C5 fill:#451a03,stroke:#d97706,stroke-width:2px,color:#fff
```

---

## 🛰️ Theoretical Background & Scientific Methods

NISAR (NASA-ISRO Synthetic Aperture Radar) operates in the **L-band (~24 cm wavelength)**, which penetrates dry soil, clouds, weather cover, and dense vegetation canopies more effectively than shorter optical or C-band wavelengths. NABD processes **NISAR Level-2 GCOV (Geocoded Polarimetric Covariance)** data (`HH` and `HV` polarization backscatter).

### 1. Water Surface Detection (Reservoir Supply)
* **Pre-processing:** Reprojection to a standardized metric UTM grid (`EPSG:32629`, 20 m resolution) and Lee Speckle Filtering ($5 \times 5$ window) to suppress SAR granular speckle noise.
* **Conversion to dB:** Linear power $\gamma^0$ converted via:
  $$\gamma^0_{\text{dB}} = 10 \cdot \log_{10}(\gamma^0)$$
* **Adaptive Dual-Polarization Otsu Thresholding:**
  Water acts as a specular reflector (smooth surface reflecting radar signals away from satellite sensors), resulting in low backscatter:
  $$\text{Water} = \left( \gamma^0_{\text{HV}} < T_{\text{HV}} \land \gamma^0_{\text{HH}} < T_{\text{HH}} \right) \lor \left( \gamma^0_{\text{HV}} < T_{\text{HV}} - 4\,\text{dB} \right)$$
  *Automatic threshold boundaries:* $T_{\text{HV}} \in [-32, -18]\,\text{dB}$ and $T_{\text{HH}} \in [-26, -12]\,\text{dB}$.
* **Morphological Cleaning & Filtering:** Binary opening followed by small hole/object suppression ($<25$ pixels / $1\text{ ha}$) and contiguous water body filtering ($>0.25\text{ km}^2$).
* **Water Occurrence & Dynamics:** Multi-temporal tracking reveals baseline water reserves vs. seasonal shoreline recession.

### 2. Crop Growth & Irrigation Mapping (Agricultural Demand)
* **Single-Orbit Invariant Geometry:** All time-series observations are constrained to single orbital tracks (e.g., Track `044`) to eliminate incidence angle variations.
* **Summer Growth Inversion:** Summer in Doukkala is dry and cloud-free with near-zero precipitation. Any systematic rise in cross-polarization backscatter ($\gamma^0_{\text{HV}}$) signifies volume scattering from developing plant stems and foliage—providing clear evidence of irrigation:
  $$\Delta \gamma^0_{\text{HV}} = P_{90}(\gamma^0_{\text{HV}}) - P_{10}(\gamma^0_{\text{HV}}) \ge 4.5\,\text{dB} \quad \text{and} \quad P_{90} \ge -18.5\,\text{dB}$$
* **Multi-Class Land Surface Classification:**
  1. **Water:** Mean $\gamma^0_{\text{HV}} \le -24\,\text{dB}$ and $\gamma^0_{\text{HH}} \le -16\,\text{dB}$.
  2. **Urban / Built-up:** High double-bounce corner reflection (Mean $\gamma^0_{\text{HH}} \ge -4\,\text{dB}$).
  3. **Perennial Trees / Orchards:** Constant high volume scattering ($\mu_{\text{HV}} \ge -15.5\,\text{dB}$ with $\sigma_{\text{HV}} \le 1.2\,\text{dB}$).
  4. **Active Summer Crops (Irrigated):** Dynamic backscatter swing exceeding vegetative growth thresholds.
  5. **Bare Soil / Fallow:** Low backscatter variations throughout the season.

### 3. Integrated Basin Water Balance
Correlating satellite-measured water surface contraction ($\Delta A_{\text{lake}}$) with official dam volume discharge records ($\Delta V_{\text{official}}$ in $\text{Mm}^3$) and active irrigated acreage ($\text{km}^2$), offering policymakers a transparent water budget accounting framework.

---

## 🗂️ Project Repository Structure

```text
nisar-surface-change/
├── data/
│   ├── granules_massira.csv    # CMR query catalog entries for Al Massira
│   ├── granules_doukkala.csv   # CMR query catalog entries for Doukkala
│   ├── official_fill.csv       # Ground truth dam reservoir fill rates & volumes
│   ├── raw/                    # Downloaded / clipped GeoTIFF radar granules
│   └── work/                   # Intermediate analytical cubes and JSON outputs
├── scripts/
│   ├── config.py               # Coordinates, bounding boxes, thresholds & parameters
│   ├── common.py               # Projections, speckle filters (Lee), display encoders
│   ├── 00_make_demo.py         # Synthetic SAR scene generator for off-line evaluation
│   ├── 01_search.py            # NASA CMR API discovery client for NISAR scenes
│   ├── 02_download.py          # NASA Harmony bounding-box subsetter / HDF5 streamer
│   ├── 03_lake.py              # Surface water extraction pipeline (Otsu + morphology)
│   ├── 04_fields.py            # Temporal variance analysis for crop classification
│   └── 05_export.py            # Aggregator compiling outputs into web/data/data.js
├── web/
│   ├── index.html              # Interactive Dashboard (Leaflet + Chart.js + Web Audio)
│   ├── data/                   # Packaged dataset & raster overlays (WebP/PNG)
│   └── vendor/                 # Leaflet GIS vendor styles & scripts
├── app_demo.py                 # Streamlit exploration prototype
├── requirements.txt            # Python dependencies
└── RESSOURCES.md               # NASA Space Apps resource survey & documentation
```

---

## 🚀 Getting Started

### 1. Prerequisites & Environment Setup
Clone the repository and configure your Python virtual environment:

```bash
# Clone the repository
git clone https://github.com/your-username/nisar-surface-change.git
cd nisar-surface-change

# Set up virtual environment
python -m venv .venv

# Activate environment
# On Linux / macOS:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install required dependencies
pip install -r requirements.txt
```

### 2. NASA Earthdata Credentials
Accessing raw NISAR granules requires an approved [NASA Earthdata Login](https://urs.earthdata.nasa.gov/users/new).

Create or update your `~/.netrc` (or `%USERPROFILE%\_netrc` on Windows):
```text
machine urs.earthdata.nasa.gov login <YOUR_USERNAME> password <YOUR_PASSWORD>
```
*(This credential file is strictly personal and excluded via `.gitignore`.)*

---

## ⚙️ Running the Full End-to-End Pipeline

```bash
# Step 0: (Optional) Generate mock synthetic radar data to test offline
python scripts/00_make_demo.py

# Step 1: Query NASA CMR catalog for available NISAR granules
python scripts/01_search.py --zone massira
python scripts/01_search.py --zone doukkala

# Step 2: Download clipped spatial bounding boxes (spatially subset via NASA Harmony)
python scripts/02_download.py --zone massira
python scripts/02_download.py --zone doukkala --track 044

# Step 3: Extract reservoir water extent & compute surface timeseries
python scripts/03_lake.py --zone massira

# Step 4: Classify irrigated agriculture & crop calendars
python scripts/04_fields.py --zone doukkala

# Step 5: Package metrics and layers for the web UI
python scripts/05_export.py
```

---

## 🌐 Web Visualization & Interactive Exploration

Launch the local web server to explore the application:

```bash
python -m http.server -d web 8000
```
Open your browser at **`http://localhost:8000`**.

### Dashboard Features:
* **Interactive Spatio-Temporal Maps:** Switch seamlessly between Al Massira lake contours and Doukkala agricultural parcels.
* **Dual Layer Overlay:** Inspect calibrated radar amplitude (false color `HH`/`HV`) and automated classification masks.
* **Time-Series Charts:** Track water surface area fluctuations juxtaposed with official dam telemetry.
* **Audio Sonification ("Écouter la Terre"):** Click anywhere on the map to sonify the local SAR backscatter signature into microtonal musical rhythms.

---

## ⚖️ Scientific Considerations & Disclaimers

1. **Provisional NISAR Data:** Data products correspond to early provisional calibration releases (mid-to-late 2026).
2. **Wind Roughness Effects on Water:** High surface wind can increase SAR surface roughness and backscatter on water. NABD prioritizes `HV` polarization, which maintains superior contrast against wind-roughened open water.
3. **Indirect Irrigation Proxy:** Summer active vegetative growth strongly implies irrigation during dry Mediterranean summers, serving as an operational proxy rather than a direct meter reading.
4. **Water Budget Approximations:** Surface area-to-volume approximations omit localized evaporation dynamics, inter-basin transfers, and municipal drinking water abstractions.

---

## 📜 License & Acknowledgments
Developed for the **NASA Space Apps Challenge 2026**.  
Satellite data courtesy of **NASA / ISRO** distributed via **ASF DAAC**. Built using open-source geospatial tools: Rasterio, Scikit-Image, SciPy, Leaflet, and Chart.js.
