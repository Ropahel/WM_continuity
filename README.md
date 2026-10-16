# WM Continuity

Projet expérimental pour entraîner un World Model (WM) jouant à Trackmania 2020.
Le modèle apprend une dynamique dans un espace latent : l'encodeur transforme
une séquence passée d'images et de télémétrie en embedding, puis le prédicteur
apprend à prédire l'embedding suivant à partir de l'embedding courant et de
l'action appliquée.

Le dépôt est actuellement au stade de la structure et du contrat de données.
L'acquisition Openplanet, le contrôle du jeu et l'entraînement ne sont pas
encore implémentés.

## Objectifs et principes

- Garder les observations et les actions brutes afin de pouvoir refaire le
  prétraitement et comparer plusieurs expériences sans réenregistrer le jeu.
- Enregistrer séparément les captures, la télémétrie et les commandes : leurs
  fréquences ne sont pas nécessairement identiques.
- Horodater les événements avec une horloge monotone locale. Il n'est pas
  nécessaire de disposer du numéro de frame ou du temps de jeu Openplanet.
- Donner à l'encodeur uniquement des fenêtres d'observations passées. La
  fenêtre cible utilisée pour calculer la loss ne doit pas être accessible à
  l'encodeur qui produit l'état courant.
- Rendre les encodeurs, prédicteurs, losses, méthodes d'entraînement et
  politiques remplaçables, afin de mener des ablations et comparaisons.
- Garder les choix d'architecture, d'image, de synchronisation et de loss
  configurables plutôt que de les figer dans le schéma des données.
- Ne pas utiliser Gymnasium.

## Arborescence proposée

```text
WM_continuity/
├── configs/
│   ├── collector.yaml           # Racine de stockage et paramètres de collecte
│   ├── model.yaml               # Choix expérimentaux des sous-modèles
│   └── experiment.yaml          # Données, entraînement, losses et ablations
├── docs/
│   ├── architecture.md          # Composants et frontières expérimentales
│   └── data-format.md           # Contrat des sessions, runs et fichiers bruts
├── openplanet/
│   └── README.md                # Emplacement et protocole du plugin Openplanet
├── src/
│   └── wm_continuity/
│       ├── __init__.py
│       ├── config.py            # Chargement/validation des configurations
│       ├── cli.py               # Points d'entrée en ligne de commande
│       ├── game_io/
│       │   ├── telemetry.py     # Réception des mesures du plugin
│       │   ├── capture.py       # Capture et sauvegarde des images
│       │   ├── controller.py    # Envoi des actions au jeu
│       │   └── run_control.py   # Début, fin, reset et interruption de run
│       ├── data/
│       │   ├── schema.py        # Schémas Arrow des flux bruts
│       │   ├── recorder.py      # Écriture des fichiers d'un run
│       │   ├── reader.py        # Lecture des données brutes
│       │   └── windows.py       # Alignement et fenêtres temporelles
│       ├── models/
│       │   ├── registry.py      # Enregistrement/résolution des variantes
│       │   ├── encoders/        # Encodeurs image + télémétrie séquentielle
│       │   ├── predictors/      # Prédicteurs d'embeddings latents
│       │   └── policies/        # Politiques d'action à partir de z(t)
│       ├── losses/              # Termes de loss composables
│       ├── training/
│       │   ├── wm.py            # Entraînement conjoint encodeur/prédicteur
│       │   ├── policy.py        # Imitation ou optimisation évolutionnaire
│       │   └── checkpoints.py   # Sauvegarde et reprise des expériences
│       └── evaluation/
│           ├── world_model.py   # Évaluation de la dynamique latente
│           └── driving.py       # Évaluation en jeu
├── tests/
│   └── test_data_schema.py      # Tests du contrat des tables Arrow
├── runs/                        # Résultats d'expériences, ignorés par Git
├── data/                        # Données locales par défaut, ignorées par Git
├── pyproject.toml
└── .gitignore
```

Les répertoires `data/` et `runs/` sont ignorés par Git. La racine réelle des
datasets est configurable dans `configs/collector.yaml` ; elle peut être un
disque ou un dossier externe au dépôt, par exemple `E:\TrackmaniaDatasets`.
Le dossier des résultats d'entraînement est également configurable dans
`configs/experiment.yaml`.

## Données collectées

Une **session** correspond à une période pendant laquelle le collecteur est
lancé. Elle peut contenir plusieurs **runs** (tentatives sur un circuit).
Chaque run possède son propre répertoire et ses propres fichiers :

```text
<data_root>/
└── session_<uuid>/
    ├── session.json
    ├── run_<uuid>/
    │   ├── run.json
    │   ├── frames.parquet
    │   ├── telemetry.parquet
    │   ├── actions.parquet
    │   └── frames/
    │       ├── 000000.jpg
    │       └── ...
    └── run_<uuid>/
        └── ...
```

- `frames.parquet` indexe les images et leurs timestamps de capture ; les
  images elles-mêmes restent des fichiers JPEG séparés.
- `telemetry.parquet` contient chaque mesure reçue : vitesse, steer, gas,
  brake, gear et RPM lorsqu'ils sont fournis par le plugin.
- `actions.parquet` contient chaque commande émise. Une commande est considérée
  maintenue jusqu'à la suivante.
- `run.json` et `session.json` décrivent le contexte, la configuration, les
  unités et l'état de l'enregistrement.

Le schéma détaillé, les champs et la politique de synchronisation sont décrits
dans [docs/data-format.md](./docs/data-format.md). Le contrat Arrow initial est
défini dans [schema.py](./src/wm_continuity/data/schema.py).

Les observations brutes restent indépendantes des exemples d'entraînement.
Les fenêtres passées, l'alignement télémétrie-image (mesure la plus proche
dans une tolérance configurable) et les splits train/validation/test seront
construits lors de la préparation ou de la lecture du dataset. Les splits se
font par run entier, jamais par frame aléatoire.

## Modèle et expériences

Le WM encode une séquence passée d'images et de télémétrie en `z(t)`. Son
prédicteur reçoit `z(t)` et l'action `a(t)` pour produire `z_hat(t+1)`.
Pendant l'entraînement, l'encodeur est aussi appliqué à la fenêtre suivante
afin de construire la cible latente `z(t+1)` et calculer les losses. En jeu,
le prédicteur et la politique peuvent avancer dans l'espace latent ; l'encodeur
recalibre l'état lorsqu'une nouvelle séquence d'images et de télémétrie est
disponible.

Les variantes seront choisies par configuration et enregistrées avec les
résultats de chaque expérience. Le WM est entraîné avant la policy. La policy
pourra ensuite être entraînée par imitation ou avec une méthode évolutionnaire.
Voir [docs/architecture.md](./docs/architecture.md) pour les frontières prévues.

## Installation (Windows, CPU)

Créer et activer un environnement virtuel :

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

PyTorch est installé séparément pour sélectionner explicitement les roues CPU
et éviter une installation CUDA :

```powershell
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
```

L'envoi des actions et la réception Openplanet dépendent du protocole retenu
pour le plugin et le contrôleur. Le paquet Python `vgamepad` peut être évalué
pour le contrôle par manette virtuelle ; il nécessite également un pilote
compatible installé sur Windows. Ce choix n'est pas encore implémenté.

## Vérifications

Lancer les tests du contrat des données :

```powershell
python -m pytest
```

Vérifier le style avec Ruff :

```powershell
ruff check .
```

## État et prochaines étapes

1. Finaliser le protocole entre le plugin Openplanet et le collecteur.
2. Implémenter l'enregistrement d'une session et les transitions explicites
   début / fin / reset / abandon de run.
3. Vérifier l'alignement réel des images, mesures et commandes sur plusieurs
   runs enregistrés.
4. Construire le lecteur de données et la préparation de fenêtres causales.
5. Ajouter des variantes minimales d'encodeur, prédicteur et losses pour établir
   une baseline mesurable.
6. Entraîner et évaluer le WM avant de commencer l'entraînement de la policy.

Le regroupement éventuel des JPEG en blocs est volontairement remis à plus
tard ; il ne doit pas modifier le schéma logique ni les identifiants de frames.
