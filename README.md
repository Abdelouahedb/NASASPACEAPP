Conversation Log
Do for me a Raedme file  descripe the project  and    the methods   ansd all 

I have created and updated a comprehensive README.md for the project.

Summary of What Was Documented:
Project Vision & System Overview: Detailed the NABD (نبض) water-budget framework connecting reservoir supply (Al Massira) and agricultural demand (Doukkala) using L-band NISAR data.
Scientific Methodology:
Reservoir Monitoring: Speckle suppression (Lee filter), dual-polarization (
HH
/
HV
HH/HV) dynamic Otsu thresholding, morphological refinement, and surface area calculation.
Agricultural Classification: Single-orbit track backscatter variance (
𝑃
90
−
𝑃
10
P
90
	​

−P
10
	​

), volume scattering indices, and classification rules (water, urban, orchards/trees, irrigated summer crops, fallow).
Basin Water Budgeting: Cross-referencing satellite-derived surface metrics with official ministry reservoir levels and volumes.
Repository Directory Structure: Clean architectural tree explaining scripts/, data/, web/, and root files.
Step-by-step Setup & Execution Guide: Virtual environment preparation, Earthdata credentials configuration, and execution commands from 00_make_demo.py through 05_export.py.
Interactive Visualization & Sonification: Guide to running the Leaflet/Chart.js web interface and using the "Écouter la Terre" radar sonification feature.
Scientific Limitations & Disclaimers: Proper disclosure on wind-roughened radar backscatter, early provisional NISAR release calibration, and irrigation proxy constraints.
Add  diagramme 

I have added comprehensive Mermaid architecture and workflow diagrams directly into README.md.

The diagrams included:
End-to-End System Architecture: Visualizing data discovery via NASA CMR API, data download & streaming (NASA Harmony/HDF5), SAR radar preprocessing and analytics, data aggregation, down to the interactive Leaflet/Chart.js/Web Audio dashboard.
Reservoir Surface Water Extraction Pipeline (Al Massira): Reprojection, 
5
×
5
5×5 Lee speckle filtering, power-to-dB conversion, dual Otsu thresholding (
HV
HV and 
HH
HH), morphological filtering, minimum contiguous lake size verification, and web layer output.
Agricultural Parcel Phenology & Irrigation Classifier (Doukkala): Clear decision-tree diagram explaining the time-series backscatter variance (
𝑃
90
−
𝑃
10
P
90
	​

−P
10
	​

), volume scattering, and categorization into active irrigated crops, urban areas, orchards, water bodies, and bare soil.
scripts/04_fields.py     champs : série temporelle par pixel -> classes, calendrier
scripts/05_export.py     web/data/data.js (tout ce dont l'app a besoin)
scripts/00_make_demo.py  données synthétiques de test
data/official_fill.csv   taux de remplissage officiels d'Al Massira, avec sources
web/index.html           l'application (Leaflet + Chart.js, aucun serveur nécessaire)
RESSOURCES.md            analyse des ressources du défi

```

## Mise en ligne (open source)

Créez un dépôt GitHub public, poussez le dossier, puis dans Settings → Pages choisissez la branche `main`
et le dossier `/web`. Le fond de carte satellite Esri s'affiche une fois le site en ligne.

## Limites, à dire honnêtement au jury

- Les produits NISAR sont **provisoires** (juillet 2026). Les données disponibles sur ces zones vont de juin à octobre 2026, alors que la grande remontée du barrage a eu lieu en janvier–mai 2026. Pour cette période, l'app montre les chiffres officiels.
- Du vent sur le lac peut éclaircir l'eau dans le radar. NABD utilise surtout HV, moins sensible au vent.
- « Culture active en été » signifie un signal de croissance pendant la saison sèche. C'est un fort indice d'irrigation, pas une preuve parcelle par parcelle.
- Le bilan barrage → champs donne un ordre de grandeur : le barrage sert aussi à l'eau potable, il y a de l'évaporation et des transferts entre barrages.
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
