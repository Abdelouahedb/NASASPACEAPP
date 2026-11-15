# NABD نبض : l'été de feu 2026

**Le pouls des forêts, vu depuis l'espace.** NASA Space Apps Challenge 2026, défi **Dancing with the SARs**.

*English summary at the end.*

En juillet 2026, deux incendies records ont brûlé près de 1 000 km² de forêt en Espagne et en France, et le Moyen Atlas marocain a brûlé lui aussi. NABD utilise le radar **NISAR** (NASA–ISRO) pour montrer, à travers la fumée, les nuages et la nuit, où le feu est passé, avec quelle violence, et si la forêt repart.

---

## Le problème

- Pendant un grand feu, la **fumée et les nuages** cachent le sol aux satellites optiques (Landsat, Sentinel-2). Les meilleures images arrivent souvent trop tard.
- Les **bilans officiels** donnent un seul chiffre : une surface. Ils ne disent ni **où** le feu a frappé le plus fort, ni **si la forêt repart** dans les mois qui suivent.
- Les données radar sont gratuites, mais lourdes (environ 6 Go par image) et difficiles à lire pour un service forestier ou une commune.

## La solution

NABD, c'est une chaîne ouverte en **six scripts Python** et un **site web** qu'on ouvre dans n'importe quel navigateur.

1. **Chercher** les passages NISAR au-dessus de chaque feu (catalogue NASA Earthdata / ASF).
2. **Télécharger seulement la fenêtre du feu** : quelques Mo au lieu de 6 Go par image (service Harmony de la NASA).
3. **Mesurer la chute du signal radar** HV : quand une forêt brûle, le radar bande L (24 cm), qui « touche » les branches et les troncs, perd du signal.
4. **Dessiner la cicatrice**, sa **sévérité** et sa **progression**, puis suivre le **pouls** de la forêt, passage par passage.
5. **Vérifier** le résultat avec les bilans officiels et avec un deuxième produit NASA indépendant, vu par l'optique (OPERA DIST-ALERT).
6. **Raconter** le tout sur le site : on rejoue chaque passage, on clique un point de la carte et on lit son histoire.

## Résultats (vraies images NISAR 2026)

| Site | Feu | Bilan officiel | Mesuré par NISAR | Part du bilan | Confirmé par l'optique (OPERA) |
|---|---|---|---|---|---|
| **Gironde, Saumos / Le Porge** (France) | 22 juil. → 2 août 2026 | 42 000 ha | 38 643 ha | **92 %** | **82 %** |
| **Laânoussar, Sefrou** (Maroc) | 31 juil. → 7 août 2026 | 480 ha | 473 ha | **99 %** | **78 %** |
| **Ávila, Burgohondo** (Espagne) | 22 juil. → 6 août 2026 | ≈ 50 000 ha | 30 995 ha | **62 %** | **83 %** |

*Confirmé par l'optique* : part de la cicatrice radar où le produit NASA OPERA DIST-ALERT (Landsat 8/9 et Sentinel-2, images d'octobre 2026) voit aussi une perte de végétation. Les deux mesures sont indépendantes (micro-ondes contre lumière visible et infrarouge) : environ 4 pixels brûlés sur 5 vus par le radar sont confirmés.

Ávila est plus bas face au bilan officiel pour deux raisons connues : le feu sort du cadre analysé par l'est, et une grande partie a brûlé des broussailles et des prairies, que la bande L voit peu. L'optique le confirme : dans le cadre analysé, elle compte 36 838 ha de végétation perdue, contre 26 514 ha pour le radar.

## Les données de la NASA

| Données | Ce qu'on en fait | Où |
|---|---|---|
| **NISAR L2 GCOV** (bande L, HH et HV, corrigé du relief) | cicatrice, sévérité, progression, pouls | ASF DAAC, via `earthaccess` et Harmony |
| **OPERA DIST-ALERT-HLS** (NASA/JPL, Landsat + Sentinel-2) | vérification optique indépendante | LP DAAC, via `earthaccess` |
| **Blue Marble** (NASA Earth Observatory) | la Terre du globe 3D de l'intro | NASA Visible Earth |

Toutes ces données sont gratuites et ouvertes. Un compte NASA Earthdata (gratuit) suffit.

## Pour qui

- **Services forestiers et protection civile** : la cicatrice et sa sévérité sans attendre un ciel dégagé, pour prioriser les secteurs à sécuriser et à reboiser.
- **Communes et associations de reboisement** : savoir où replanter, et suivre la repousse tous les 12 jours.
- **Chercheurs, élèves, citoyens** : une méthode documentée, du code et des données ouverts.

---

## Le site

Ouvrez `web/index.html` via un petit serveur (voir *Lancer*). Le site est en **français et en anglais**.

| Partie | Ce qu'on y voit |
|---|---|
| **Intro 3D** | Le vrai lancement de NISAR : GSLV-F16, 30 juillet 2025, Sriharikota. Gros plan sur les moteurs à l'allumage, décollage, séparation des étages, ouverture de la coiffe, déploiement du bras de 9 m et de l'antenne de 12 m. Elle ne se joue qu'à la première visite et peut être passée. |
| **Mission** | Le problème, les données NASA, la solution, pour qui. |
| **Carte** | Chaque passage NISAR rejouable, couches radar / sévérité / chute du signal / progression / optique OPERA, glissière avant-après. |
| **Inspecter un point** | Un clic sur la carte : verdict en clair (« le feu est passé ici vers le… »), valeurs avant, au plus bas, aujourd'hui, petite courbe, et version sonore. |
| **Pouls** | La courbe de la cicatrice par rapport à la forêt intacte, avec trois chiffres clés : chute maximale, dernier passage, repousse depuis le creux. |
| **Chiffres** | Radar contre bilans officiels, sévérité, et accord avec l'optique OPERA. |
| **Satellite (3D)** | NISAR et sa fusée GSLV-F16 à faire tourner (la 3D démarre seulement sur demande). Le modèle détaillé de NISAR sur Sketchfab se charge seulement si on clique. |
| **Données** | Toutes les images disponibles, avec leurs dates. |

**Rapide et accessible** : l'intro passe en version légère sur les cartes graphiques modestes ; le fond 3D s'arrête pendant la lecture ; les images radar et l'historique par point ne se chargent que quand on en a besoin ; la vue 3D du satellite démarre seulement sur demande ; boutons de 44 px minimum, navigation au clavier, textes lisibles sur le fond, respect du réglage « réduire les animations ».

---

## Installation (une fois)

```bash
python -m venv .venv
.venv\Scripts\activate            # Mac/Linux : source .venv/bin/activate
pip install -r requirements.txt
```

Compte NASA gratuit : <https://urs.earthdata.nasa.gov/users/new>. Créez ensuite le fichier `_netrc`
(Windows, dans `C:\Users\VOUS\`) ou `~/.netrc` (Mac/Linux) contenant :

```
machine urs.earthdata.nasa.gov login VOTRE_NOM password VOTRE_MOT_DE_PASSE
```

**Ne publiez jamais ce fichier** : il est déjà exclu par `.gitignore`.

## Lancer

```bash
python scripts/01_search.py --zone all          # liste à jour des images NISAR
python scripts/02_download.py --zone sefrou --limit 2    # petit test d'abord
python scripts/02_download.py --zone all        # tout (seulement la fenêtre de chaque feu)
#   en cas d'échec de Harmony : ajouter --method stream
python scripts/03_fire.py --zone all            # cicatrice, sévérité, progression, pouls
python scripts/05_dist.py --zone all            # vérification optique NASA OPERA (facultatif)
python scripts/04_export.py                     # écrit web/data/data.js
python -m http.server 8000 -d web               # puis http://localhost:8000
```

Avant d'utiliser les vraies données : supprimez les dossiers `data/raw/<zone>/DEMO_*`.
Sans données, `python scripts/00_make_demo.py` crée des images **synthétiques** aux vraies dates NISAR,
pour tester la chaîne. Le site affiche alors un bandeau « démonstration ».

## Organisation du dépôt

```
scripts/
  config.py        réglages : zones, dates des feux, seuils
  common.py        outils partagés (lecture GCOV, mosaïque, filtre de Lee)
  00_make_demo.py  données synthétiques pour tester sans compte NASA
  01_search.py     recherche des passages NISAR (ASF)
  02_download.py   téléchargement des seules fenêtres utiles (Harmony)
  03_fire.py       cicatrice, sévérité, progression, pouls (GeoTIFF + JSON)
  05_dist.py       comparaison avec NASA OPERA DIST-ALERT (Landsat + Sentinel-2)
  04_export.py     regroupe tout dans web/data/data.js
web/
  index.html       le site (carte Leaflet, graphiques Chart.js)
  data/            data.js, l'historique radar par feu (cube_*.bin) et les images des passages
  intro/           l'intro 3D (three.js) et les textures de la Terre
  hangar/          la vue 3D de NISAR et de la GSLV
  vendor/          three.js et la police Archivo, copiés dans le dépôt
data/              images brutes et résultats (non publiés, voir .gitignore)
```

## Méthode (03_fire.py)

1. Chaque passage : les cadres voisins sont assemblés, puis filtre de Lee et passage en dB (HH, HV).
2. Chaque passage est calé sur la partie **non brûlée** de l'image : cela efface les jours de pluie (+2 dB d'un coup) et les sauts d'étalonnage. Un passage qui saute de plus de 3 dB est écarté.
3. Pour chaque orbite : ΔHV = médiane des passages de **10 à 120 jours après** le feu − médiane des passages des **75 jours avant**. Sur les vraies images, la chute continue de se creuser pendant 2 à 3 mois (les aiguilles tombent, les troncs sèchent) : regarder juste après le feu sous-estime beaucoup. Les orbites sont moyennées, puis la carte est lissée (45 m).
4. Brûlé = végétation avant (HV > −22 dB) **et** ΔHV < −1 dB. On ne garde que les taches **reliées au feu** : la plus grande près du point de départ, puis toutes celles à moins de 1 km (2,5 km à Ávila, coupée par le lac du Burguillo). Le **périmètre** referme les trous de moins de 200 m, comme les bilans officiels. Sévérité : faible (−1 à −2,5 dB), modérée (−2,5 à −4 dB), forte (au-delà).
5. Progression : premier passage où chaque pixel brûlé a chuté de plus de 1,5 dB.
6. Pouls : HV moyen de la cicatrice moins HV de la forêt témoin, à chaque passage. Cette différence annule la saison et l'orbite.

Les réglages sont dans `scripts/config.py`. Les résultats en GeoTIFF (`dHV_dB.tif`, `severity.tif`) sont dans `data/work/<zone>/` et s'ouvrent dans QGIS.

## Vérification optique (05_dist.py)

`05_dist.py` cherche les tuiles **OPERA DIST-ALERT** publiées après chaque feu, ne télécharge que deux couches (statut et date de la perte de végétation), les remet sur la grille du radar et calcule :

- la **part de la cicatrice radar confirmée par l'optique** ;
- la surface de végétation perdue vue par l'optique autour de la cicatrice ;
- une couche pour la carte : en cyan, radar et optique d'accord ; en magenta, ce que seule l'optique voit.

Les deux mesures sont indépendantes (micro-ondes contre lumière visible et infrarouge). Quand elles s'accordent, le résultat est solide ; là où l'optique a des nuages, le radar continue de voir.

## Ouvrir le site sur un autre PC

Il faut seulement Python (pas de compte NASA : les résultats sont déjà dans `web/data/`).

```bash
git clone <adresse du dépôt>
cd <dossier du dépôt>
python -m http.server 8000 -d web      # puis ouvrir http://localhost:8000
```

Ne pas double-cliquer sur `index.html` : ouvert comme un simple fichier, le navigateur bloque l'intro 3D et les données. Une connexion Internet est nécessaire pour le fond de carte et les graphiques.

## Mise en ligne (GitHub Pages)

Dans le dépôt sur GitHub : **Settings → Pages** → *Deploy from a branch* → choisir la branche du projet et le dossier `/ (root)`. Le fichier `index.html` à la racine redirige vers `web/`. Avec un compte gratuit, le dépôt doit être public.

## Limites (à dire au jury)

- Les produits NISAR sont **provisoires** (calibration en cours) ; la version validée ne couvre que depuis le 21/10/2026.
- Il manque des passages entre le 27/07 et le 10/08/2026 (lacune de l'instrument). C'est pour ça qu'on regarde plusieurs orbites.
- En pente forte (Moyen Atlas, Gredos), l'ombre et le repliement radar peuvent gêner. Les zones en pente sont à interpréter avec prudence.
- Le seuil de −1 dB est un choix, réglé sur les vraies images 2026 : Gironde 92 % du bilan officiel, Laânoussar 99 %.
- Ávila : le feu sort du cadre analysé par l'est (vers Madrid), et une grande partie a brûlé des broussailles et des prairies, que la bande L voit peu. Pour agrandir le cadre : changer `bbox` dans `config.py`, puis `01_search.py --zone avila` et `02_download.py --zone avila --fresh`.
- Pour OPERA, `05_dist.py` compte comme « végétation perdue » les codes de statut 2, 3, 5, 6, 7 et 8. Sur les vraies tuiles d'octobre 2026, ils donnent 78 à 83 % d'accord avec le radar, ce qui est cohérent ; ce choix reste à revérifier avec la documentation officielle du produit.

## Crédits et licences

- **Radar** : NASA/JPL–ISRO, mission NISAR, données distribuées par l'ASF DAAC.
- **OPERA DIST-ALERT** : NASA/JPL, projet OPERA, distribué par le LP DAAC.
- **Terre** : textures dérivées des images NASA *Blue Marble* (NASA Earth Observatory).
- **Fond de carte** : Esri World Imagery.
- **Bibliothèques** : [three.js](https://threejs.org) (MIT), [Leaflet](https://leafletjs.com) (BSD-2), [Chart.js](https://www.chartjs.org) (MIT), [earthaccess](https://github.com/nsidc/earthaccess) (MIT). Police [Archivo](https://github.com/Omnibus-Type/Archivo) (SIL Open Font License, voir `web/vendor/fonts/`).
- **Modèles 3D** :
  - Modèle détaillé de NISAR : « [NISAR Satellite ISRO - NASA Joint Mission](https://sketchfab.com/3d-models/nisar-satellite-isro-nasa-joint-mission-0103309668d243dbbfab3c8fc6b9683c) » par MechLab3D, **affiché depuis Sketchfab** (lecteur intégré), il n'est pas copié dans ce dépôt.
  - NISAR et la fusée GSLV de l'intro sont des modèles faits à la main pour NABD, d'après la configuration publiée par l'ISRO.
- **Chiffres officiels des feux** : voir la liste des sources en bas du site.

---

## English summary

**NABD (Arabic for "pulse")** measures the 2026 summer wildfires at Ávila (Spain), Gironde (France) and Laânoussar–Sefrou (Morocco) with **NASA–ISRO NISAR** L-band radar, which sees through smoke, cloud and night.

- **Problem**: during big fires, optical satellites are blind under smoke, and official reports give only one number (an area), not where the fire was most severe or whether the forest recovers.
- **Solution**: an open Python pipeline that downloads only each fire's window of NISAR GCOV data, maps the burn scar, severity, spread and the "pulse" (recovery) of the forest from the drop of the HV signal, cross-checks it with official figures and with NASA OPERA DIST-ALERT (Landsat + Sentinel-2), and a bilingual website to explore it.
- **Results on real 2026 NISAR data**: Gironde 92% of the official burned area, Laânoussar 99%, Ávila 62% (part of the fire lies outside the analysed frame and burned scrub and grassland, which L-band sees poorly). An independent check with NASA OPERA DIST-ALERT (Landsat + Sentinel-2) confirms 82%, 78% and 83% of the radar burn scars.
- **Website**: 3D intro of the real NISAR launch (GSLV-F16, 30 July 2025), interactive map with per-pass replay, point inspector, recovery indicators, optical cross-check, and a 3D view of NISAR and its rocket.

Run: see *Installation* and *Lancer* above (same commands). To just view the site: `python -m http.server 8000 -d web`, then open http://localhost:8000.
