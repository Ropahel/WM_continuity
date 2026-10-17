# WM Continuity

## Idée

On peut repérer quand on reset la run en demandant à l'utilisateur de presser une touche/faire une commande lorsqu'il est à la position de base(le strart) de la map. Comme ça à chaque fois qu'on y revient avec speed = 0, cela voudra dire qu'on a reset. C'est une options si Openplanet n'est pas capable de nous dire quand on reset et si on ne peut pas se baser sur les touches appuyé par le joueur.

Projet expérimental pour entraîner un World Model (WM) jouant à Trackmania 2020.
Le modèle apprend une dynamique dans un espace latent : l'encodeur transforme
une séquence passée d'images et de télémétrie en embedding, puis le prédicteur
apprend à prédire l'embedding suivant à partir de l'embedding courant et de
l'action appliquée. Le but principale est de construire un WM de zero, de l'entrainer sans avoir de collapse, et de voir comment gérer un frand flux de données en temps réel.

Le dépôt est au stade de la structure et du contrat de données. Un plugin
Openplanet existe pour envoyer une partie de la télémétrie. Pour l'instant,
l'information de cycle de vie confirmée est que
`VehicleState::ViewingPlayerState()` renvoie `null` lorsqu'on n'est pas dans
une map. La détection du départ, de la conduite, de l'arrivée et du reset,
la lecture des commandes physiques, l'intégration complète du collecteur
Python et l'entraînement restent à implémenter.

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
│   ├── data-format.md           # Contrat des sessions, runs et fichiers bruts
│   └── checkpoints.md           # Sauvegarde, reprise et version des modèles
├── openplanet/
│   ├── Main.as                  # Plugin Openplanet (télémétrie initiale)
│   └── info.toml                # Métadonnées du plugin
├── src/
│   ├── __init__.py
│   ├── config.py            # Chargement/validation des configurations
│   ├── cli.py               # Points d'entrée en ligne de commande
│   ├── game_io/
│   │   ├── telemetry.py     # Réception des mesures du plugin
│   │   ├── capture.py       # Capture et sauvegarde des images
│   │   ├── controller.py    # Envoi des actions au jeu
│   │   └── run_control.py   # Début, fin, reset et interruption de run
│   ├── data/
│   │   ├── schema.py        # Schémas Arrow des flux bruts
│   │   ├── recorder.py      # Écriture des fichiers d'un run
│   │   ├── reader.py        # Lecture des données brutes
│   │   └── windows.py       # Alignement et fenêtres temporelles
│   ├── models/
│   │   ├── registry.py      # Enregistrement/résolution des variantes
│   │   ├── encoders/        # Encodeurs image + télémétrie séquentielle
│   │   ├── predictors/      # Prédicteurs d'embeddings latents
│   │   └── policies/        # Politiques d'action à partir de z(t)
│   ├── losses/              # Termes de loss composables
│   ├── training/
│   │   ├── wm.py            # Entraînement conjoint encodeur/prédicteur
│   │   ├── policy.py        # Imitation ou optimisation évolutionnaire
│   │   └── checkpoints.py   # Sauvegarde et reprise des expériences
│   └── evaluation/
│       ├── world_model.py   # Évaluation de la dynamique latente
│       └── driving.py       # Évaluation en jeu
├── tests/
│   └── test_data_schema.py      # Tests du contrat des tables Arrow
├── runs/                        # Résultats d'expériences, ignorés par Git
├── pyproject.toml
└── .gitignore
```

Les dossiers de données et de résultats sont ignorés par Git. La racine réelle
des datasets est configurable dans `configs/collector.yaml` ; elle peut être un
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
    ├── events.parquet
    ├── run_<uuid>/
    │   ├── run.json
    │   ├── frames.parquet
    │   ├── telemetry.parquet
    │   ├── actions.parquet
    │   ├── latents.parquet    # optionnel, seulement si demandé
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
- `latents.parquet` n'est créé que si l'utilisateur demande explicitement
  l'enregistrement des embeddings ; la capture est limitée à un run.
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
Les sauvegardes périodiques de reprise et la promotion manuelle d'un modèle
sont décrites dans [docs/checkpoints.md](./docs/checkpoints.md).

Le collecteur utilisera un état de run explicite et hybride : commandes
utilisateur au départ, puis événements Openplanet lorsqu'ils auront été
validés. Un message frais avec `ViewingPlayerState() is null` confirme
`NOT_IN_MAP`, mais une valeur non nulle ne renseigne pas à elle seule sur le
départ, la conduite, l'arrivée ou le reset. L'absence de message indique un
problème de communication ou un état inconnu, pas `NOT_IN_MAP`. Le
contrôleur du modèle ne sera autorisé qu'en état `RUNNING` confirmé avec des
mesures fraîches ; un état inconnu ou une perte de télémétrie désactive ses
actions.

### Commandes pendant l'exécution

Une interface terminal interactive est tout à fait réalisable tant que le
collecteur tourne, mais elle doit être conçue pour ne pas bloquer la boucle qui
reçoit la télémétrie, capture les images et calcule les actions. Le lecteur du
terminal lira les commandes en parallèle et les transmettra à la boucle
principale par une file de messages. Les opérations qui touchent au modèle ou
aux fichiers — notamment `save_model` et le démarrage de l'enregistrement des
latents — seront exécutées par cette boucle à un point sûr, et non directement
depuis le thread clavier.

Commandes prévues :

- `record_latents next_run` : armer une capture de latents pour un run complet,
  du début confirmé à sa fin/reset/abandon ;
- `record_latents current_run` : commencer immédiatement si un run est déjà
  actif, en indiquant dans les métadonnées que la capture est partielle ;
- `stop_latent_recording` : arrêter avant la fin du run ;
- `save_model` : sauvegarder manuellement une version nommée du modèle courant.

Des raccourcis clavier sont également possibles. Pour le premier jalon, il est
plus fiable de commencer par les commandes textuelles dans le terminal. Des
hotkeys peuvent ensuite appeler les mêmes commandes du répartiteur, mais
nécessitent une gestion des répétitions de touches, des conflits avec le jeu,
du focus de fenêtre et éventuellement des permissions si elles sont globales
à Windows. Un raccourci ne doit jamais contourner les contrôles d'état du run
ni la neutralisation de sécurité.

## Installation (Windows, CPU)

Créer et activer un environnement virtuel :

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Cette installation ajoute les bibliothèques prévues pour le projet :
PyTorch n'est pas installé par la commande précédente, car sa source CPU doit
être sélectionnée explicitement. Installer ensuite sa roue CPU :

```powershell
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
```

`opencv-python-headless` fournit les opérations d'image sans dépendance à
l'interface graphique d'OpenCV ; `Pillow` et `mss` servent aux images et aux
captures. `PyArrow` gère les tables Parquet, `NumPy` les tableaux, `PyYAML` les
configurations, `TensorBoard` le suivi des métriques, `pytest` les tests,
`Ruff` les vérifications de code et `vgamepad` l'envoi potentiel des commandes
par manette virtuelle.

Sur Windows, `vgamepad` nécessite aussi l'installation d'un pilote de manette
virtuelle compatible (ViGEmBus). Installer le paquet Python ne suffit pas à
faire fonctionner le contrôle en jeu. Le protocole Openplanet et le contrôle
ne sont pas encore implémentés.

Pour vérifier l'installation CPU de PyTorch :

```powershell
python -c "import torch; print(torch.__version__); print('CUDA disponible :', torch.cuda.is_available())"
```

La dernière ligne doit afficher `CUDA disponible : False` pour cette
installation.

## Vérifications

Lancer les tests du contrat des données :

```powershell
python -m pytest
```

Vérifier le style avec Ruff :

```powershell
ruff check .
```

## Feuille de route détaillée

Les étapes ci-dessous sont ordonnées pour réduire les risques : valider d'abord
ce que le jeu expose, puis fiabiliser la collecte et les données, avant de
consacrer du temps au WM et à la policy. Les décisions qui restent
expérimentales doivent être enregistrées dans les configurations et les
métadonnées, pas codées en dur dans les données brutes.

### 1. Cartographier les informations accessibles avec Openplanet

ICI: uniquement sur TM. Pas de python.

- Installer Openplanet et mettre le plugin actuel dans le jeu.
- Tester dans les différents contextes de jeu la valeur de
  `VehicleState::ViewingPlayerState()` : menu, chargement, map avant départ,
  voiture en mouvement, arrivée, écran de résultat et après reset.
- Traiter comme fait confirmé uniquement ceci : si la fonction renvoie `null`,
  on n'est pas dans une map. Vérifier séparément ce que signifie un état non
  nul ; ne pas conclure automatiquement qu'un run est en cours.
- Chercher dans les APIs Openplanet/Trackmania si elles exposent des événements
  de départ, d'arrivée, de fin de map et de reset, ainsi que les commandes
  physiques de manette réellement lues par le jeu. -> modifier le plugin en conséquence et choisir les modalités de décisions.
- Vérifier les unités, la fréquence et les conditions d'indisponibilité des
  mesures déjà récupérées : vitesse, RPM, gear, position, et celles restant à
  ajouter (steer, gas, brake).

**Pourquoi c'est important :** le collecteur doit distinguer « hors map »,
« en map mais à l'arrêt », « en conduite » et « terminé » sans inventer un
événement. De plus, les actions physiques du joueur sont nécessaires comme
cibles si la première policy est entraînée par imitation.

**Résultat attendu :** une liste vérifiée des signaux et événements
disponibles, et une liste explicite de ce qui nécessitera encore une commande
manuelle.

### 2. Définir puis tester le protocole plugin ↔ Python

En gros: faire le code python qui fera la communication avec le plugin. En ajoutant tous les test necessaires, les sécurités etc...

- Choisir et documenter le transport local (le plugin actuel essaie une
  connexion TCP vers `127.0.0.1:9000`) et le format des messages.
- Définir des messages séparés ou identifiables pour télémétrie, état du jeu,
  heartbeat, événements de run et, si disponible, entrées physiques.
- Envoyer explicitement l'état `NOT_IN_MAP` lorsque
  `ViewingPlayerState()` est nul. Le script actuel n'envoie alors aucune
  télémétrie : sans message d'état ou heartbeat, Python ne peut pas savoir si
  le jeu est hors map ou si le plugin/la connexion s'est arrêté.
- Ajouter une version de protocole et des règles de reconnexion ; tester
  démarrage du jeu avant Python, redémarrage du plugin, déconnexion et
  reconnexion.
- Vérifier que les messages incomplets, répétés ou mal formés ne sont pas
  interprétés comme des mesures valides.

**Pourquoi c'est important :** un protocole explicite évite de confondre
l'absence légitime de voiture avec un défaut de communication et rend les
enregistrements analysables après coup.

**Résultat attendu :** un petit test d'intégration qui affiche côté Python des
messages valides horodatés localement et qui détecte une perte de connexion.

### 3. Implémenter le contrôleur d'état et les transitions de run

- Maintenir les états côté Python : `UNKNOWN`, `NOT_IN_MAP`, `READY`,
  `RUNNING`, `RESETTING`, `FINISHED` et `ABORTED`.
- Définir pour chaque transition son signal déclencheur et sa provenance :
  `plugin`, `user` ou `timeout`. Tant que départ, arrivée ou reset ne sont pas
  détectés de façon fiable, utiliser des commandes explicites du collecteur.
- Une valeur nulle de `ViewingPlayerState()` peut justifier `NOT_IN_MAP`, mais
  une valeur non nulle ne suffit pas à déclarer `RUNNING`.
- Ajouter un timeout de fraîcheur des messages et passer à `UNKNOWN` si le
  plugin ou les mesures cessent d'être à jour.
- N'autoriser la policy à agir que dans `RUNNING` confirmé. Dans tout autre
  état, désactiver ses commandes et neutraliser la manette virtuelle si le
  contrôleur le permet.
- À l'arrivée, au reset ou à l'abandon, fermer le run en cours ; après le
  reset, créer un nouveau run uniquement lorsque l'utilisateur ou un signal
  validé confirme que la voiture est prête.

**Pourquoi c'est important :** une classification erronée du cycle de vie
mélangerait plusieurs tentatives dans un run et pourrait laisser le modèle
envoyer des actions au mauvais moment.

**Résultat attendu :** des tests de transitions (dont perte/récupération de
connexion) et un journal d'événements permettant de reconstruire ce qui s'est
passé sans deviner à partir de la vitesse.

### 4. Terminer la première tranche de collecte de données

- Implémenter une session avec plusieurs dossiers de runs et une racine de
  stockage configurable hors du dépôt.
- Capturer les images en fichiers JPEG et enregistrer les chemins relatifs,
  index et timestamps monotones dans `frames.parquet`.
- Enregistrer séparément chaque message de télémétrie reçu, sans la
  rééchantillonner à la fréquence des images.
- Enregistrer chaque action envoyée et sa source. Si l'accès aux entrées
  physiques est confirmé, stocker ces entrées séparément des commandes émises.
- Écrire les transitions dans le journal d'événements de session et consigner
  dans `run.json` la raison de clôture et l'état final.
- Fermer proprement les fichiers Parquet et marquer les sessions interrompues
  comme incomplètes ; ne pas présenter des fichiers potentiellement tronqués
  comme des runs terminés.

**Pourquoi c'est important :** les images, les mesures et les actions ont des
fréquences différentes. Les enregistrer comme flux bruts indépendants permet
de changer plus tard la synchronisation sans refaire la collecte.

**Résultat attendu :** un run manuel complet, relisible, avec images,
télémétrie, commandes et événements conservés séparément conformément à
[docs/data-format.md](./docs/data-format.md).

### 5. Mesurer la qualité de collecte avant d'entraîner

- Enregistrer plusieurs runs couvrant départ, conduite normale, arrêt,
  arrivée, reset, abandon et, si possible, perte de connexion.
- Vérifier que les timestamps monotones avancent dans chaque flux, que les
  index sont uniques et que les images référencées existent.
- Afficher des diagnostics : fréquence observée de chaque flux, trous de
  télémétrie, délais de réception, échecs de capture et durée des runs.
- Tester l'alignement image/télémétrie par voisin le plus proche avec la
  tolérance configurée. Mesurer combien d'images ont une télémétrie associée
  avant de fixer cette tolérance.
- Vérifier les unités et la plage des signaux, notamment vitesse, steer, gas,
  brake, gear et RPM ; distinguer les contrôles lus du jeu des actions émises.

**Pourquoi c'est important :** un WM peut apprendre des timestamps décalés,
des commandes mal interprétées ou des données manquantes sans que
l'entraînement échoue explicitement.

**Résultat attendu :** un rapport de qualité par session et la confirmation
qu'un dataset peut être relu et aligné de manière reproductible.

### 6. Construire le lecteur et les fenêtres causales

- Lire les tables Arrow et les images à partir d'un dossier de run ou d'un
  manifeste de dataset.
- Construire les fenêtres passées d'images et de télémétrie à l'ancre `t`,
  ainsi que la fenêtre suivante servant à produire la cible d'embedding.
- Fournir au prédicteur la commande ou les commandes effectivement actives
  dans l'intervalle de transition, selon la convention « maintenue jusqu'à la
  suivante ».
- Permettre le masquage de composantes télémétriques et du vecteur complet sans
  modifier les données brutes.
- Affecter train/validation/test par runs entiers et enregistrer les splits.
- Ajouter des tests prouvant l'absence de données futures dans l'entrée
  courante, le respect de la tolérance temporelle, la gestion des valeurs
  manquantes et la séparation des runs.

**Pourquoi c'est important :** une fuite temporelle rendrait les résultats
artificiellement bons et invaliderait les comparaisons d'architectures.

**Résultat attendu :** des lots de données cohérents et testés, directement
utilisables par plusieurs modèles expérimentaux.

### 7. Établir une baseline de World Model

- Définir les interfaces minimales des sous-modèles et leur registre de
  variantes, puis sélectionner chaque architecture par configuration.
- Commencer par une architecture de petite taille adaptée au CPU, sans
  considérer ce premier choix comme définitif.
- Implémenter encodeur séquentiel, prédicteur latent conditionné par l'action
  et une loss de référence comparant `z_hat(t+1)` avec la cible `z(t+1)`.
- Entraîner encodeur et prédicteur conjointement ; vérifier que la cible
  future n'entre pas dans le calcul de l'embedding courant.
- Comparer à des contrôles simples (par exemple prédiction de l'embedding
  courant ou cible constante) pour vérifier que le WM apprend plus qu'une
  solution triviale.
- Suivre métriques d'entraînement et validation, et examiner la distribution
  des embeddings pour repérer un éventuel collapse.

**Pourquoi c'est important :** une baseline et des contrôles permettent de
savoir si une nouvelle architecture ou loss apporte réellement quelque chose.

**Résultat attendu :** une expérience reproductible, des métriques de
prédiction latente et un premier modèle dont le comportement est vérifié avant
d'ajouter des termes expérimentaux.

### 8. Mettre en place les checkpoints avant les longues expériences

- Implémenter la sauvegarde périodique de reprise (poids, état d'optimiseur,
  compteurs et configuration), à une cadence mesurée en étapes et configurable.
- Sauvegarder de façon atomique, tester une reprise après arrêt et choisir une
  politique de rétention qui ne supprime jamais les modèles promus.
- Ajouter pendant l'entraînement la commande terminal `save_model` pour
  nommer et conserver manuellement un instantané intéressant, sans remplacer
  une version existante.
- Enregistrer séparément les identifiants d'architecture de l'encodeur et du
  prédicteur, tout en gardant leurs poids dans le même bundle WM entraîné
  conjointement.
- Pour une policy, enregistrer le WM exact dont elle dépend et vérifier cette
  compatibilité au chargement.

**Pourquoi c'est important :** les entraînements CPU et les comparaisons
peuvent durer ; il faut pouvoir les reprendre et savoir précisément quelle
combinaison de sous-modèles a produit un résultat.

**Résultat attendu :** reprise vérifiée après interruption et bibliothèque de
modèles nommés, décrite dans [docs/checkpoints.md](./docs/checkpoints.md).

### 9. Ajouter l'enregistrement facultatif des états latents

- Implémenter les commandes `record_latents next_run`,
  `record_latents current_run` et `stop_latent_recording`.
- Ne rien écrire par défaut ; quand l'option est armée, enregistrer un run au
  maximum puis arrêter automatiquement au reset, à la fin ou à l'abandon.
- Écrire les vecteurs dans `latents.parquet` avec horodatage monotone, index,
  pas de modèle, provenance (`encoder` ou `predictor`) et identifiants exacts du
  bundle/checkpoint.
- Enregistrer dans les métadonnées les dimensions et l'ordre des coordonnées,
  la cadence, ainsi que les bornes (complètes ou partielles) de la capture.
- Tester que l'activation/désactivation terminale est traitée à un point sûr
  de la boucle et ne bloque ni la télémétrie, ni l'inférence, ni le contrôle.
- Comparer une trace latente à ses images, à la télémétrie et aux actions
  enregistrées, en séparant les embeddings recalibrés par l'encodeur des
  embeddings prédits par le WM.

**Pourquoi c'est important :** les vecteurs latents sont le résultat direct
des expériences d'architecture et de loss. Les conserver sur demande permet de
les analyser après le run sans imposer le volume de stockage et le coût
d'écriture à chaque partie.

**Résultat attendu :** une trace latente facultative, alignable et
reproductible, produite pour un seul run par commande et reliée au modèle
exact qui l'a générée.

### 10. Comparer les architectures et les losses de façon contrôlée

- Modifier un facteur à la fois : architecture d'encodeur, prédicteur,
  encodage temporel/positionnel, loss ou sélection de télémétrie.
- Pour chaque expérience, sauvegarder configuration résolue, seed, splits,
  métriques, identifiants de variantes et checkpoint.
- Comparer les expériences sur les mêmes runs de validation et contrôler
  plusieurs seeds lorsque le coût le permet.
- Mesurer explicitement le collapse et les performances à plusieurs pas
  prédits, pas seulement la loss d'un pas.

**Pourquoi c'est important :** changer simultanément le modèle, les données et
la loss ne permet pas d'attribuer une amélioration à une cause précise.

**Résultat attendu :** un tableau de comparaison permettant de retenir des
variantes sur des critères définis plutôt qu'une impression qualitative.

### 11. Entraîner d'abord une policy par imitation

- Confirmer quelles actions peuvent servir de labels : commandes manuelles
  réellement lues ou commandes manuelles envoyées via le contrôleur.
- Entraîner la policy à partir des embeddings produits par un WM identifié et
  testé.
- Évaluer sur des runs séparés et vérifier que l'état d'action et les
  commandes sont correctement alignés.

**Pourquoi c'est important :** l'imitation fournit une première policy sans
introduire immédiatement les difficultés de l'évaluation et de la récompense
en ligne.

**Résultat attendu :** une policy candidate avec des métriques reproductibles,
qui n'est pas encore autorisée à contrôler le jeu sans garde-fous.

### 12. Tester la conduite en jeu de manière progressive

- Commencer par observation seule (policy calculée mais commandes non
  appliquées), puis faire des essais courts à vitesse réduite ou dans un
  contexte contrôlé.
- Vérifier les arrêts d'urgence, la neutralisation de la manette et les
  transitions `UNKNOWN` / `NOT_IN_MAP` avant d'autoriser le contrôle.
- Journaliser état, observations, actions proposées et actions réellement
  envoyées afin de pouvoir analyser chaque échec.
- N'essayer l'optimisation génétique/RL qu'une fois la boucle de jeu et
  l'évaluation suffisamment fiables.

**Pourquoi c'est important :** une erreur de synchronisation ou d'état peut
produire des commandes inadaptées ; le contrôle réel doit être activé
progressivement et pouvoir être interrompu.

**Résultat attendu :** des runs d'évaluation réplicables et une procédure
d'arrêt sûre avant de lancer des expériences autonomes longues.

### 13. Optimiser le stockage et le débit ensuite

Garder pour le début un fichier JPEG par image et le stockage Parquet par run.
Mesurer d'abord la taille des données, le débit d'écriture et le temps de
lecture. Si le grand nombre de JPEG devient un problème, regrouper les images
en archives ou blocs sans changer leurs identifiants ni le schéma logique.

**Pourquoi c'est important :** optimiser trop tôt ajoute de la complexité au
collecteur et rend les premiers jeux de données plus difficiles à inspecter.
