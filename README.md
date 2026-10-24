# WM Continuity

Projet d'expérimentation sur les World Models (WM) et l'apprentissage de
représentations latentes. La première version vise des simulations courtes,
reproductibles et peu coûteuses, avant tout retour éventuel à un jeu réel.

Trackmania n'est pas une cible de développement pour cette version. Les
plugins, notes d'intégration, formats de télémétrie et prototypes Python liés
au jeu sont conservés dans [archive/trackmania/](./archive/trackmania/) pour
référence ; ils ne font pas partie du paquet actif ni de ses dépendances.

## Objectif de la première version

Construire une boucle expérimentale complète sur une simulation :

1. obtenir une séquence d'observations \(o_{t-L+1:t}\) et les actions associées ;
2. encoder uniquement le passé disponible en \(z_t\) ;
3. prédire \(z_{t+1}\) depuis \(z_t\) et l'action \(a_t\) ;
4. comparer plusieurs encodeurs, agrégateurs temporels, prédicteurs et losses ;
5. examiner les embeddings et détecter les solutions triviales ou le collapse ;
6. sauvegarder les expériences, checkpoints et, à la demande, les traces
   latentes.

L'architecture doit rester modulaire. Le premier environnement et le premier
type d'observation ne sont pas encore figés : le code devra accepter aussi
bien des vecteurs d'état que des séquences d'images, sans imposer les deux
modalités dans chaque expérience.

## Choix des environnements

Les pistes citées sont Push-T, AntMaze et CUBE. Elles ne sont pas équivalentes :

| Environnement | Intérêt expérimental | Coût / point à vérifier |
|---|---|---|
| CUBE (à préciser) | Environnement contrôlé et rapide ; bon premier test pour valider les transitions, les losses et les outils d'expérience | Déterminer s'il s'agit d'un benchmark existant ou d'un petit environnement à définir dans le dépôt |
| Push-T | Tâche visuelle de manipulation ; utile pour étudier images, séquences et représentations | Identifier l'implémentation et ses dépendances avant de les ajouter |
| AntMaze | Navigation avec dépendances à la dynamique et à la planification ; intéressant pour les données hors ligne | L'implémentation et le dataset exacts restent à choisir ; la pile peut être plus lourde |

**Progression recommandée :** commencer par un petit CUBE clairement défini et
rapide (états vectoriels pour valider la dynamique et le pipeline), puis
introduire Push-T pour les observations visuelles et temporelles. Garder
AntMaze pour une étape ultérieure, une fois le chargement de trajectoires et
l'évaluation stables. Si « CUBE » désigne un benchmark précis, confirmer son
nom et son API avant d'écrire un adaptateur.

Chaque environnement sera branché derrière une interface commune inspirée de
Gymnasium (`reset`, `step`, observation, action, fin d'épisode). Gymnasium
devient donc une dépendance de base ; les paquets spécifiques à Push-T ou
AntMaze seront ajoutés uniquement lorsque l'environnement retenu et ses
versions auront été vérifiés. Aucun environnement spécifique n'est installé
par ce changement.

## Arborescence cible

```text
WM_continuity/
├── archive/
│   └── trackmania/                 # Ancien prototype et toute sa documentation
│       ├── configs/
│       ├── docs/
│       ├── openplanet/
│       └── python/
├── configs/
│   ├── environment.yaml            # Environnement, observations et actions
│   ├── model.yaml                  # Variantes d'encodeur/prédicteur/policy
│   └── experiment.yaml             # Dataset, losses, entraînement, checkpoints
├── docs/
│   ├── architecture.md             # Architecture WM générique
│   ├── checkpoints.md              # Reprise et versions de modèles
│   └── simulators.md               # Comparaison et ajout d'environnements
├── src/
│   └── wm_continuity/
│       ├── config.py               # Chargement/validation de configuration
│       ├── cli.py                  # Commandes CLI et lancement d'expérience
│       ├── environments/
│       │   ├── base.py             # Interface commune des simulations
│       │   ├── cube.py             # Premier environnement contrôlé
│       │   ├── pusht.py            # Adaptateur Push-T (phase ultérieure)
│       │   └── antmaze.py          # Adaptateur AntMaze (phase ultérieure)
│       ├── data/
│       │   ├── trajectories.py     # Épisodes et transitions
│       │   ├── dataset.py          # Fenêtres temporelles PyTorch
│       │   └── splits.py           # Splits par épisode/trajectoire
│       ├── models/
│       │   ├── interfaces.py       # Contrats et formes de tenseurs
│       │   ├── registry.py         # Enregistrement des variantes
│       │   ├── world_model.py      # Assemblage encodeur/prédicteur
│       │   ├── encoders/           # Encodeurs image, état, temps
│       │   ├── predictors/         # Prédicteurs latents
│       │   └── policies/           # Policies (étape ultérieure)
│       ├── losses/                 # Losses sélectionnables/composables
│       ├── training/
│       │   ├── world_model.py      # Entraînement et validation du WM
│       │   ├── checkpoints.py      # Sauvegarde et reprise
│       │   └── latent_recorder.py  # Traces z(t) activées sur demande
│       └── evaluation/
│           ├── world_model.py      # Prédiction, collapse, horizons
│           └── trajectories.py     # Mesures par épisode
├── tests/
│   ├── unit/                       # Tests rapides hors simulateur
│   └── integration/                # Environnement, dataset, entraînement
├── data/                           # Données/caches, ignorés par Git
├── runs/                           # Expériences et checkpoints, ignorés
├── environment.yml                 # Environnement Conda CPU reproductible
├── pyproject.toml
└── .gitignore
```

Cette arborescence est une cible, pas une affirmation que tous les modules
sont déjà implémentés. Les fichiers Python présents dans le paquet sont encore
principalement des squelettes. Les premiers vrais modules doivent être créés
dans l'ordre indiqué par la feuille de route.

## Environnement Anaconda/Conda

Anaconda est maintenant détecté sur la machine. L'environnement du projet reste
à créer : le fichier [environment.yml](./environment.yml) en décrit la
configuration reproductible, avec Python 3.11, PyTorch CPU, Gymnasium et les
bibliothèques communes.

Depuis la racine du dépôt, dans un terminal Conda :

```powershell
conda env create -f environment.yml
conda activate wm-continuity
python -m pip install --no-deps -e .
```

La même définition peut être importée dans Anaconda Navigator, onglet
**Environments**, avec **Import** puis le fichier `environment.yml`. Dans VS
Code, choisir ensuite l'interpréteur Conda `wm-continuity` via
**Python: Select Interpreter**.

Pour mettre à jour l'environnement après modification de `environment.yml` :

```powershell
conda env update -f environment.yml --prune
```

`--prune` supprime aussi les paquets installés dans l'environnement mais qui ne
sont plus déclarés dans le fichier. Ajouter les nouvelles dépendances à
`environment.yml` avant de mettre l'environnement à jour pour garder ce fichier
comme définition de référence.

Vérifier l'interpréteur, PyTorch CPU et Gymnasium :

```powershell
python -c "import sys, torch, gymnasium; print(sys.executable); print(torch.__version__); print('CUDA disponible :', torch.cuda.is_available()); print('Gymnasium :', gymnasium.__version__)"
```

La vérification attend `CUDA disponible : False`. Ces commandes sont à lancer
explicitement par l'utilisateur après activation de l'environnement ; elles ne
sont pas exécutées automatiquement par le dépôt.

### Dépendances retenues

- `torch` : réseaux et entraînement CPU ;
- `gymnasium` : interface commune aux simulations ;
- `numpy` : observations, actions et trajectoires ;
- `PyYAML` : configurations d'expériences ;
- `tensorboard` : suivi des losses, métriques et statistiques latentes ;
- `pytest` et `ruff` : tests et qualité du code.

Les dépendances retirées du projet actif car elles venaient du prototype
Trackmania sont `mss`, `opencv-python-headless`, `Pillow`, `pyarrow` et
`vgamepad`. Elles ne sont pas remplacées automatiquement : le stockage initial
des trajectoires peut utiliser NumPy (`.npz`) et les dépendances propres à un
benchmark seront décidées après choix de son implémentation.

## Données et résultats

Les expériences portent sur des épisodes/trajectoires simulés, pas sur des runs
Trackmania. Le premier format de travail recommandé est un jeu de fichiers
NumPy par dataset ou épisode, contenant observations, actions, rewards si
disponibles, indicateurs de fin et métadonnées de l'environnement. Les exemples
d'entraînement (fenêtres glissantes) sont construits au chargement et ne sont
pas dupliqués dans les données brutes.

```text
data/
└── <environment>/
    ├── metadata.json
    └── episodes/
        ├── episode_000001.npz
        └── ...

runs/
└── <experiment_id>/
    ├── config.resolved.yaml
    ├── metrics/
    ├── checkpoints/
    └── latent_traces/              # seulement si demandé
```

Les dossiers d'expérience enregistrent l'environnement et sa version, les
modalités d'observation, l'action, les splits d'épisodes, les architectures,
les losses, les seeds et les checkpoints. Une sauvegarde de latents doit
rester facultative, activée par commande et limitée à la période demandée.
Voir [docs/checkpoints.md](./docs/checkpoints.md).

## Vérifications locales

Dans l'environnement Conda activé :

```powershell
python -m pytest -v
ruff check .
```

Les tests unitaires ne doivent pas dépendre d'un rendu graphique ni d'un
benchmark lourd. Les tests d'intégration de chaque adaptateur doivent pouvoir
être lancés séparément.

## Feuille de route exécutable

L'ordre vise à obtenir rapidement un système testable, sans commencer par les
dépendances complexes d'un environnement visuel. Chaque phase donne les
fichiers ou livrables à produire et un critère clair avant de passer à la
suivante.

### 1. Installer et valider l'environnement Conda

**À faire après installation d'Anaconda/Miniconda :**

1. Créer l'environnement avec `conda env create -f environment.yml`.
2. L'activer, installer le dépôt en mode éditable avec `python -m pip install
   --no-deps -e .`, et vérifier `sys.executable`.
3. Vérifier les imports torch/Gymnasium, la version PyTorch et
   `torch.cuda.is_available() == False`.
4. Lancer `python -m pytest -v` et `ruff check .`.

**Importance :** garantit que les résultats sont exécutés sur l'interpréteur
CPU prévu et non dans un environnement Python différent.

**Critère de sortie :** imports et versions vérifiés, CUDA indisponible, tous
les tests collectés passent. Aucune installation n'est faite par l'assistant
dans cette phase.

### 2. Choisir précisément le premier environnement

**À faire :**

1. Définir ce que signifie « CUBE » : benchmark externe (nom de paquet,
   dépôt, version, API, licence) ou petit environnement contrôlé implémenté
   dans le projet.
2. Pour Push-T/AntMaze, identifier la source exacte (paquet, version,
   dépendances, observations, espace d'action, terminaison et dataset
   disponible). Ne pas installer les trois environnements d'un coup.
3. Choisir un seul premier environnement et consigner les critères :
   installation simple, simulation rapide sur CPU, reset déterministe,
   accès aux états/actions, épisodes reproductibles et coût de rendu.
4. Mettre à jour `configs/environment.yaml` et `docs/simulators.md` avec ce
   choix et ses versions.

**Recommandation :** utiliser un CUBE minimal à états vectoriels s'il n'existe
pas de benchmark CUBE précis visé. Il permet de tester le pipeline WM sans
dépendances de rendu. Ajouter Push-T ensuite pour la modalité image ; reporter
AntMaze jusqu'à ce que datasets et transitions soient bien gérés.

**Importance :** l'interface d'observation (état ou image), l'action et la
distribution des données déterminent les premiers contrats du Dataset et du
modèle.

**Critère de sortie :** une seule simulation choisie, installée et décrite,
avec un script minimal qui réinitialise l'environnement et exécute un épisode.

### 3. Définir l'interface de simulation et le CUBE minimal

**Fichiers à créer :** `environments/base.py`, `environments/cube.py`,
`tests/unit/test_cube.py`, `tests/integration/test_environment_api.py`.

1. Définir un adaptateur indépendant du WM avec `reset(seed)`, `step(action)`
   et une description typée des observations/actions.
2. Normaliser le résultat de step sous une structure stable contenant
   observation, action appliquée, reward optionnelle, `terminated`,
   `truncated` et informations/métadonnées.
3. Si CUBE est à construire, définir une tâche minuscule déterministe : état
   vectoriel, petit nombre d'actions, transition simple, but explicite et
   limite d'épisode. Ne pas ajouter de pixels avant que la version état
   fonctionne.
4. Tester les formes/dtypes, la reproductibilité avec la même seed, les
   limites d'action, les resets et les deux causes de fin d'épisode.
5. Ajouter une commande CLI `play-random` qui exécute un épisode aléatoire,
   affiche les statistiques et termine sans lancer de modèle.

**Importance :** une simulation stable permet de tester indépendamment le
WM, la loss, le logger et le pipeline d'entraînement.

**Critère de sortie :** plusieurs épisodes se terminent, mêmes seeds = mêmes
transitions, les observations/actions satisfont le contrat, et le test
d'intégration s'exécute sans dépendance Trackmania.

### 4. Enregistrer et relire des trajectoires synthétiques

**Fichiers à créer :** `data/trajectory.py`, `data/recorder.py`,
`data/dataset.py`, `tests/unit/test_trajectory.py`,
`tests/unit/test_dataset.py`.

1. Définir un épisode comme séquences alignées de `obs_t`, `action_t`,
   `obs_tp1`, reward, flags de terminaison et numéro de pas.
2. Écrire quelques épisodes vers `.npz` plus un manifeste JSON indiquant
   environnement/version, seed, formes, dtypes et ordre des actions.
3. Implémenter chargement/validation qui rejette longueurs incohérentes,
   NaN/Inf inattendus, actions hors espace et transitions après terminaison.
4. Générer les fenêtres causales à la lecture ; ne pas sauvegarder chaque
   fenêtre glissante avec ses données dupliquées.
5. Séparer train/validation/test par épisodes complets et persister la liste
   des IDs dans la configuration résolue.

**Importance :** des données synthétiques fournissent une première preuve
reproductible et rendent les tests du WM indépendants d'un simulateur coûteux.

**Critère de sortie :** enregistrer puis relire un épisode sans perte, obtenir
des batches de formes fixes, vérifier qu'aucune fenêtre ne traverse un épisode
ni ne donne le futur à l'encodeur courant.

### 5. Poser les interfaces des modèles, avant les architectures

**Fichiers à créer :** `models/interfaces.py`, `models/registry.py`,
`models/world_model.py`, tests `test_model_contracts.py`.

1. Définir le contrat `Encoder.encode(observation_history) -> z_t`.
2. Définir `Predictor.predict_next(z_t, action_t) -> z_pred_tp1`.
3. Définir l'interface des observations multimodales : état vectoriel,
   images ou les deux ; ne pas forcer une modalité absente.
4. Fixer les tenseurs de batch : vectoriel `[B,T,F]`, image
   `[B,T,C,H,W]`, action `[B,A]` et latent `[B,D]`.
5. Créer un registre explicite de variantes sélectionnées par nom et
   paramètres YAML ; refuser les noms inconnus et les paramètres non pris en
   charge avec une erreur utile.
6. Assembler encodeur + prédicteur dans un `WorldModel` sans placer les choix
   d'architecture dans le Dataset.

**Importance :** les variantes se remplacent proprement si les dimensions et
responsabilités sont explicites avant de coder des réseaux.

**Critère de sortie :** tests de contrat validant formes, dtype, device,
latent dimension et erreurs de configuration, sans entraînement.

### 6. Créer deux modèles de référence et tester la fabrique

**Fichiers à créer :**

- `models/encoders/state_mlp.py` pour les états vectoriels ;
- `models/encoders/image_cnn.py` seulement si l'environnement initial fournit
  des images ;
- `models/encoders/temporal.py` pour l'agrégation temporelle interchangeable ;
- `models/predictors/mlp.py` pour `z_t, a_t -> z_pred_tp1` ;
- tests `test_encoder_variants.py`, `test_predictor.py`, `test_world_model.py`.

1. Commencer par un encodeur MLP d'état avec agrégation temporelle simple.
2. Ajouter une seconde variante réellement différente (par ex. GRU ou
   Transformer compact) derrière la même interface, pour prouver la
   modularité.
3. Ajouter le prédicteur latent MLP conditionné par l'action.
4. Construire les deux configurations depuis `configs/model.yaml`, exécuter un
   forward, vérifier les formes et le passage du gradient.
5. Vérifier explicitement que l'encodeur courant ne reçoit que la fenêtre
   jusqu'à `t`; l'encodage cible de `t+1` est un appel distinct réservé à la
   loss d'entraînement.

**Importance :** une architecture interchangeable est le cœur du projet ;
il faut le démontrer par des tests plutôt que par des dossiers de code seuls.

**Critère de sortie :** deux variantes instanciées par configuration
produisent les mêmes contrats de sortie et un backward PyTorch CPU réussit.

### 7. Entraîner une première loss latente et mesurer le collapse

**Fichiers à créer :** `losses/latent_prediction.py`,
`training/world_model.py`, `evaluation/world_model.py`,
`tests/unit/test_training_step.py`.

1. Implémenter une loss de référence entre le latent prédit et la cible
   latente encodée séparément.
2. Ajouter une boucle minimaliste : batch → encodeur courant → prédicteur →
   encodeur cible → loss → backward/optimizer.
3. Démarrer sur quelques épisodes synthétiques, une petite dimension latente,
   peu d'étapes et CPU ; sauvegarder config, seed et métriques.
4. Comparer contre des baselines triviales (copie de `z_t`, constante ou
   prédiction moyenne).
5. Logger loss, normes et variance des embeddings, diversité des états latents
   et erreur à un puis plusieurs pas lorsque disponible.
6. Vérifier les valeurs finies, les gradients et l'absence de dégradation
   évidente de diversité indiquant un collapse.

**Importance :** une loss faible ne prouve pas que les embeddings portent une
information utile ; les baselines et diagnostics évitent de valider un modèle
trivial.

**Critère de sortie :** l'entraînement réduit la loss de validation par rapport
aux baselines triviales sans collapse manifeste sur le petit jeu contrôlé.

### 8. Ajouter checkpoints et sauvegarde manuelle

Compléter `training/checkpoints.py` et `docs/checkpoints.md` pour l'expérience
générique : reprise périodique avec optimiseur/seed/config et sauvegarde
manuelle `save_model` en version immuable. Tester interruption/reprise et
chargement par identifiant. Les paramètres de fréquence et rétention sont
configurables ; aucun checkpoint n'est sauvegardé à chaque époque par défaut.

**Critère de sortie :** une expérience synthétique peut reprendre puis
produire une version nommée qui recharge les poids et la configuration exacts.

### 9. Enregistrer des latents uniquement sur demande

Ajouter une commande terminal pour armer un enregistrement d'un épisode et
l'arrêter automatiquement à sa fin. Sauvegarder `z_t`, pas de modèle,
provenance (encodeur/prédicteur), environnement, experiment/checkpoint IDs,
et timestamps/indices de pas dans une trace séparée. L'écriture ne bloque pas
l'entraînement ; erreur visible si la file d'écriture déborde.

**Critère de sortie :** sans commande aucune trace n'est produite ; avec
commande, une trace est alignée sur un seul épisode et reliée au modèle qui
l'a générée.

### 10. Ajouter les environnements plus riches un par un

Pour Push-T puis éventuellement AntMaze : créer un adaptateur dans
`environments/`, un fichier d'extra dépendances dédié seulement après
vérification des versions, des tests de reset/step/fin d'épisode, un exemple
de collecte et une recette de dataset/split. Comparer d'abord sur état
vectoriel si disponible, puis images. Ne pas changer en même temps
l'environnement, l'architecture et la loss.

**Critère de sortie par environnement :** installation/documentation
reproductible, collecte d'un épisode, relecture du dataset et tests
d'intégration verts avant toute expérience WM longue.

### 11. Comparer les variantes

Établir un tableau de résultats utilisant les mêmes splits d'épisodes :
variante d'encodeur, temporalité, prédicteur, sélection de modalités, loss,
seed, erreur latente et métriques de collapse. Changer un facteur par
expérience et sauvegarder les configurations résolues.

**Critère de sortie :** toute amélioration rapportée peut être reliée à une
expérience reproductible, un dataset/split et un checkpoint identifiés.

Le retour à Trackmania est une piste distincte, à reprendre seulement si les
expériences de simulation ont d'abord produit un WM et une boucle d'évaluation
fonctionnels. Les JPEG pourraient être regroupés plus tard si les mesures de
débit et de stockage le justifient.
