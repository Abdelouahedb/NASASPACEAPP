# Analyse des ressources du défi « Dancing with the SARs »

Vérifié le 14 novembre 2026. ★★★ = indispensable pour NABD.

## Ressources NASA

| Ressource | À quoi elle sert | Pour NABD |
|---|---|---|
| **NISAR Data User Guide** (nisar-docs.asf.alaska.edu) ★★★ | Documentation officielle : produits, accès, outils, tutoriels | Source des chemins HDF5 GCOV, de la méthode Harmony et de l'accès par earthaccess |
| **ASF Vertex** (search.asf.alaska.edu) ★★★ | Recherche visuelle des images radar sur une carte | Vérifier la couverture d'une zone et voir les aperçus PNG |
| **NASA Earthdata Search** ★★ | Recherche + téléchargement avec découpe (Harmony) en GeoTIFF | Alternative manuelle à `02_download.py` |
| **Intro au SAR** (Earthdata) ★★ | Fréquences, polarisations, mécanismes de rétrodiffusion | Explique pourquoi l'eau est sombre et la végétation brille en HV : base du pitch |
| **Intro à la télédétection** ★ | Résolutions, capteurs passifs et actifs | Pour la partie « pourquoi le radar » |
| **ARSET** ★★ | Formations en ligne, dont un cours NISAR en 2 parties (juillet 2026) | Partie 2 : accès aux données, asf_search, Earthdata Search |
| **NISAR StoryMaps** ★ | Histoires interactives : inondations, feux, subsidence, nappes de pétrole, glaciers | Modèle de narration ; « NISAR GCOV in ArcGIS Pro 3.7 » (juillet 2026) |
| **Livres blancs « Applications »** ★ | Fiches de 2 pages par usage sociétal | Arguments d'impact (eau, agriculture) pour le jury |
| **Cartes postales UAVSAR** ★ | Compositions colorées radar aéroporté | Inspiration pour la palette couleur HH/HV |

### Points techniques retenus
- **Produit GCOV** (radar géocodé, corrigé du relief) : couches `/science/LSAR/GCOV/grids/frequencyA/HHHH` et `HVHV`, valeurs de puissance gamma0, projection UTM, pixels de 10 à 20 m (fréquence A, terres émergées).
- **Taille** : un fichier GCOV complet pèse **5,7 à 7,5 Go**. Il faut donc découper : Harmony (côté NASA) ou lecture partielle en streaming.
- **Collection** : `NISAR_L2_GCOV_PROVISIONAL_V1` (identifiant `C2854338529-ASF`), produits provisoires publiés le 20 juillet 2026, retraitement en cours jusqu'à fin 2026.
- **Couverture vérifiée** : Al Massira 29 dates (orbites 044, 095, 023 ; du 17 juin au 18 oct. 2026), Doukkala 19 dates utilisables, Tadla 38, Souss 27, et des interférogrammes (GUNW) disponibles.
- **Piège** : certains produits sont `NASV` (seulement VV en fréquence B, 80 m), sans HH ni HV en fréquence A. `01_search.py` les écarte.
- **Connexion** : rechercher dans le catalogue est libre, mais télécharger demande un compte Earthdata Login (gratuit).

## Ressources des agences partenaires

| Ressource | Usage | Pour NABD |
|---|---|---|
| **Tutoriel SAR Python de l'ASC/CSA** (GitHub, FR/EN) | Afficher des images RADARSAT en Python (GDAL, cartopy) et dans QGIS | Bon pour apprendre ; pas de détection d'eau ni de changement |
| **RADARSAT Constellation (RCM)** | Radar bande C canadien, données ouvertes | Possible comparaison bande C / bande L |
| **RADARSAT-1** | Archive 1995–2013, licence ouverte | Contexte historique |
| **SAOCOM (CONAE, Argentine)** | Radar bande L comme NISAR, inscription requise | Deuxième source bande L ; demande une inscription manuelle |

## Idées écartées et pourquoi
- **Subsidence du Souss (InSAR)** : environ 0 à 20 mm/an selon une étude AGU 2022 sur 2003–2010, soit quelques mm en 4 mois. C'est sous le bruit d'un interférogramme. À reprendre quand NISAR aura 1 à 2 ans de données.
- **Dunes de Merzouga (décalages GOFF)** : en 4 mois, le déplacement est inférieur à un pixel.
- **Reconstruction d'Al Haouz** : signal faible, montagnes (ombres radar), validation difficile.
