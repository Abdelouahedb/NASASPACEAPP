# NABD نبض — le pouls de l'eau du Maroc

NASA Space Apps Challenge 2026 · défi **Dancing with the SARs**

NABD suit l'eau d'un système marocain du barrage jusqu'aux champs avec le radar **NISAR** (NASA–ISRO, bande L) :

| Zone | Rôle | Ce que mesure le radar |
|---|---|---|
| **Barrage Al Massira** (Settat) | l'offre | surface du lac à chaque passage, comparée au taux de remplissage officiel |
| **Périmètre des Doukkala** (Sidi Bennour) | la demande | parcelles qui poussent pendant l'été sec, donc irriguées, et leur calendrier |

Avec en plus le mode « écouter la Terre » : on clique sur un point de la carte et sa série radar devient une mélodie (gamme Hijaz, rythme de darbouka).

## Données et démonstration

Le tableau de bord inclut quatre acquisitions NISAR L2 GCOV provisoires de la même orbite ascendante (044, trame 018), les 17 juin, 23 juillet, 28 août et 15 octobre 2026. Les bandes HH et HV de chaque acquisition ont été découpées par Harmony pour Al Massira et les Doukkala. Le lien « Source NASA de ce passage » affiche la fiche du produit.

Activez « Synchroniser barrage et champs » pour suivre la même acquisition dans les deux zones. « Écouter le duo » anime leur chronologie et joue deux voix, le lac à gauche et le signal de végétation des champs à droite. Chaque série est normalisée indépendamment. Les accords comparent la chronologie de deux indicateurs et ne mesurent pas les lâchers d'eau.

À Al Massira, le masque retient l'eau sombre reliée à un point au cœur du réservoir dans une limite tracée à la main. Les seuils fixes sont −15 dB (HH) et −24 dB (HV). Dans les Doukkala, les classes reposent sur les pixels observés à chaque date et sur des règles radar exploratoires. L'irrigation par parcelle demande une validation indépendante.

## Installation (une fois)

```bash
python -m venv .venv && source .venv/bin/activate      # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

Compte NASA gratuit : <https://urs.earthdata.nasa.gov/users/new>, puis créez le fichier `~/.netrc`
(Windows : `%USERPROFILE%\_netrc`) avec cette ligne :

```
machine urs.earthdata.nasa.gov login VOTRE_NOM password VOTRE_MOT_DE_PASSE
```

Ce fichier reste sur votre ordinateur. Ne le mettez jamais sur GitHub (il est déjà dans `.gitignore`).

## Lancer le pipeline

```bash
# 1. Lister les images NISAR (sans connexion). Les listes du 14/11/2026 sont déjà dans data/
python scripts/01_search.py --zone massira
python scripts/01_search.py --zone doukkala

# 2. Télécharger uniquement la fenêtre utile (quelques Mo par date au lieu de 6 Go)
python scripts/02_download.py --zone massira --limit 2          # test rapide d'abord
python scripts/02_download.py --zone massira
python scripts/02_download.py --zone doukkala --track 044
#    (si Harmony échoue : ajoutez --method stream)

# 3-5. Traiter et exporter vers l'application
rm -rf data/raw/*/DEMO_*                 # supprimer les données de démonstration
python scripts/03_lake.py --zone massira
python scripts/04_fields.py --zone doukkala
python scripts/05_export.py

# Voir l'application
python -m http.server -d web 8000         # puis http://localhost:8000
```

Pas encore de données ? `python scripts/00_make_demo.py` crée des images **synthétiques** pour tester
toute la chaîne. L'application affiche alors un bandeau « données de démonstration ».

## Ce qu'il y a dans le dossier

```
scripts/config.py        zones, collection NISAR, seuils
scripts/01_search.py     catalogue NASA (CMR) -> data/granules_<zone>.csv
scripts/02_download.py   Harmony (découpe côté NASA) ou lecture HDF5 en streaming
scripts/03_lake.py       eau : filtre de Lee, seuil d'Otsu HV/HH, surface, cartes
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
