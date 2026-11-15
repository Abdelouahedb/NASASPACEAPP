# NABD نبض — L'été de feu 2026

NASA Space Apps Challenge 2026 · défi **Dancing with the SARs**

En juillet 2026, deux incendies records ont brûlé près de 1 000 km² de forêt en Espagne et en France, et le Moyen Atlas marocain a brûlé lui aussi. NABD utilise le radar **NISAR** (NASA–ISRO, bande L, 24 cm) pour mesurer, à travers la fumée et la nuit :

- **où** le feu est passé : la cicatrice, pixel par pixel ;
- **avec quelle violence** : la sévérité, d'après la chute du signal HV en dB ;
- **quand** : la progression, passage par passage ;
- **et si la forêt repart** : le « pouls » de la cicatrice comparée à la forêt intacte.

Le tout est vérifié contre les bilans officiels, et on peut **écouter** chaque point de la carte.

| Site | Feu | Bilan officiel | Images NISAR GCOV (14/11/2026) |
|---|---|---|---|
| **Ávila – Burgohondo** (Espagne) | 22 juil. → 6 août 2026 | ≈ 50 000 ha (77 000 avec Madrid et Tolède) | 42 + 3 validées, depuis le 3 janv. 2026 |
| **Gironde – Saumos / Le Porge** (France) | 22 juil. → 2 août 2026 | 42 000 ha | 49 + 3 validées, depuis le 4 nov. 2025 |
| **Laânoussar – Sefrou** (Maroc) | 31 juil. → 7 août 2026 | 480 ha | ≈ 85 + 9 validées, depuis le 20 juin 2026 |

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

Ne publiez jamais ce fichier : il est déjà exclu par `.gitignore`.

## Lancer

```bash
python scripts/01_search.py --zone all          # liste à jour des images (sans connexion)
python scripts/02_download.py --zone sefrou --limit 2    # petit test d'abord
python scripts/02_download.py --zone all        # tout (seulement la fenêtre de chaque feu)
#   en cas d'échec de Harmony : ajouter --method stream
python scripts/03_fire.py --zone all            # cicatrice, sévérité, progression, pouls
python scripts/04_export.py                     # web/data/data.js
python -m http.server 8000 -d web               # puis http://localhost:8000
```

Avant d'utiliser les vraies données : supprimez les dossiers `data/raw/<zone>/DEMO_*`.
Sans données, `python scripts/00_make_demo.py` crée des images **synthétiques** aux vraies dates NISAR,
pour tester la chaîne. L'app affiche alors un bandeau « démonstration ».

## Méthode (03_fire.py)

1. Chaque passage : les cadres voisins sont assemblés, puis filtre de Lee et passage en dB (HH, HV).
2. Chaque passage est calé sur la partie **non brûlée** de l'image : cela efface les jours de pluie (+2 dB d'un coup) et les sauts d'étalonnage. Un passage qui saute de plus de 3 dB est écarté.
3. Pour chaque orbite : ΔHV = médiane des passages de **10 à 120 jours après** le feu − médiane des passages des **75 jours avant**. Sur les vraies images, la chute continue de se creuser pendant 2 à 3 mois (les aiguilles tombent, les troncs sèchent) : regarder juste après le feu sous-estime beaucoup. Les orbites sont moyennées, puis la carte est lissée (45 m).
4. Brûlé = végétation avant (HV > −22 dB) **et** ΔHV < −1 dB. On ne garde que les taches **reliées au feu** : la plus grande près du point de départ, puis toutes celles à moins de 1 km (2,5 km à Ávila, coupée par le lac du Burguillo). Le **périmètre** referme les trous de moins de 200 m, comme les bilans officiels. Sévérité : faible (−1 à −2,5 dB), modérée (−2,5 à −4 dB), forte (au-delà).
5. Progression : premier passage où chaque pixel brûlé a chuté de plus de 1,5 dB.
6. Pouls : HV moyen de la cicatrice moins HV de la forêt témoin, à chaque passage. Cette différence annule la saison et l'orbite.

Les réglages sont dans `scripts/config.py`. Les résultats en GeoTIFF (`dHV_dB.tif`, `severity.tif`) sont dans `data/work/<zone>/` et s'ouvrent dans QGIS.

## Mise en ligne

Poussez le dossier sur GitHub, puis dans **Settings → Pages**, choisissez la branche `main` et le dossier `/ (root)`. Le fichier `index.html` à la racine redirige vers `web/`.

## Limites (à dire au jury)

- Les produits NISAR sont **provisoires** (calibration en cours) ; la version validée ne couvre que depuis le 21/10/2026.
- Il manque des passages entre le 27/07 et le 10/08/2026 (lacune de l'instrument). C'est pour ça qu'on regarde plusieurs orbites.
- En pente forte (Moyen Atlas, Gredos), l'ombre et le repliement radar peuvent gêner. Les zones en pente sont à interpréter avec prudence.
- Le seuil de −1 dB est un choix, réglé sur les vraies images 2026 : Gironde 92 % du bilan officiel, Laânoussar 109 %.
- Ávila : le feu sort du cadre analysé par l'est (vers Madrid), et une grande partie a brûlé des broussailles et des prairies, que la bande L voit peu. Le radar en compte environ 60 %. Pour agrandir le cadre : changer `bbox` dans `config.py`, puis `01_search.py --zone avila` et `02_download.py --zone avila --fresh`.
