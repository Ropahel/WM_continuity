# Format des données brutes

Ce document définit le contrat logique initial. Il ne fixe volontairement pas
la résolution, le mode couleur, la qualité JPEG ni le transport du plugin.
Ces choix seront indiqués dans la configuration de collecte et les métadonnées
du run.

## Cycle de vie d'une session et d'un run

Une **session** correspond à un lancement du collecteur. Son dossier contient
un `session.json` et un sous-dossier par tentative de conduite. Un **run**
commence lorsque la voiture est prête à partir après une commande explicite de
départ ou de reset ; il se termine à l'arrivée, à un reset/redémarrage demandé
ou à un abandon explicite.

Utiliser des commandes explicites du collecteur pour démarrer, terminer,
réinitialiser ou abandonner, sauf si le plugin Openplanet fournit un événement
fiable. Ne pas déduire la fin d'un run de la seule vitesse. Un reset termine
le run courant ; le suivant ne commence que lorsque la voiture est de nouveau
prête. Une fermeture inattendue laisse le run incomplet : il ne doit pas être
marqué comme terminé normalement.

Chaque session et run reçoit un UUID unique. `session.json` et `run.json`
enregistrent, selon le cas :

- la version du schéma et les identifiants ;
- les heures UTC de début et de fin, pour consultation humaine ;
- l'état (`recording`, `completed`, `reset`, `aborted` ou `interrupted`) et la
  raison de fin ;
- le circuit et le mode s'ils sont connus, la source des commandes, les
  versions du collecteur et du plugin ;
- les configurations de capture, télémétrie, actions et synchronisation ;
- l'état d'exécution courant et la provenance des transitions lorsqu'ils sont
  conservés dans `events.parquet` ;
- les unités source de chaque mesure et la convention du steering ;
- la résolution, le mode couleur et la qualité JPEG lorsqu'ils seront fixés.

Les heures UTC sont uniquement descriptives. L'ordre des événements et leur
alignement reposent sur des horodatages monotones locaux.

## Arborescence des enregistrements

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
    │   └── frames/
    │       ├── 000000.jpg
    │       └── ...
    └── run_<uuid>/
        └── ...
```

La racine du collecteur est configurable et peut être située hors du dépôt
Git. Les noms d'images utilisent un `frame_idx` local croissant ; aucun numéro
de frame du jeu n'est nécessaire. Si les JPEG sont regroupés dans des archives
ou blocs plus tard, conserver les mêmes identifiants et horodatages logiques.

## Horloges et index d'événements

Pour chaque événement, enregistrer un horodatage monotone local obtenu à partir
de l'horloge de performance Python (par exemple `time.perf_counter_ns()`). Il
sert à mesurer les durées et l'ordre ; ce n'est pas une date civile et il n'a
pas besoin d'être synchronisé avec Trackmania. Les heures UTC de début et de
fin sont conservées dans les fichiers JSON pour le contexte humain.

Chaque flux a son index croissant (`frame_idx`, `telemetry_idx`,
`action_idx`). Si Openplanet ne fournit pas d'heure ni de numéro de frame,
omettre cette information ou la stocker comme valeur nulle ; ne pas l'inventer.
Un timestamp de télémétrie pris à la réception indique l'heure de réception,
pas nécessairement l'instant exact où le jeu a échantillonné la mesure.

Les transitions d'état et les commandes de cycle de vie sont enregistrées dans
`events.parquet` à la racine de la session, séparément des mesures périodiques.
L'état représente ce que le collecteur sait et autorise, pas une preuve que la
voiture bouge réellement.
Valeurs prévues : `UNKNOWN` (état non confirmé, plugin déconnecté ou mesures
périmées), `READY` (jeu connecté et voiture prête, aucun run actif), `RUNNING`,
`RESETTING`, `FINISHED` et `ABORTED`. Chaque transition conserve son origine :
`user`, `plugin` ou `timeout`.

Au premier jalon, l'utilisateur confirme explicitement le début, la fin, le
reset ou l'abandon depuis le collecteur. Un événement du plugin ne remplace ce
contrôle qu'après vérification de sa fiabilité. Un reset ferme le run courant ;
après confirmation que la voiture est prête, un nouveau run commence avec un
nouvel identifiant. Une perte de connexion ou des mesures périmées font passer
l'état à `UNKNOWN` et ne doivent pas être interprétées automatiquement comme
une arrivée ou un reset.

Le collecteur n'autorise les sorties de la policy qu'en état `RUNNING` avec
une télémétrie fraîche. Dans les autres états il désactive l'émission d'actions
du modèle, neutralise le contrôleur si possible et exige une confirmation
avant de reprendre. Le seuil de fraîcheur et le mécanisme de neutralisation
seront configurés avec l'adaptateur de jeu.

## Fichiers de chaque run

### `frames.parquet`

Une ligne par tentative de capture :

| Champ | Type | Signification |
| --- | --- | --- |
| `run_id` | string | UUID du run parent |
| `frame_idx` | int64 | Index local d'image croissant |
| `t_capture_ns` | int64 | Horodatage monotone local de capture |
| `image_path` | string nullable | Chemin relatif au dossier du run |
| `width` | int32 | Largeur de l'image si la capture réussit |
| `height` | int32 | Hauteur de l'image si la capture réussit |
| `capture_ok` | bool | Indique si l'image a été enregistrée |

Ne pas stocker les octets de l'image dans cette table : placer les fichiers
dans `frames/`. Enregistrer les paramètres d'encodage dans `run.json`. Le
format initial est JPEG, mais résolution, mode couleur et qualité restent à
déterminer.

### `telemetry.parquet`

Une ligne par mesure reçue du plugin, sans rééchantillonnage à la fréquence
des images :

| Champ | Type | Signification |
| --- | --- | --- |
| `run_id` | string | UUID du run parent |
| `telemetry_idx` | int64 | Index local de mesure croissant |
| `t_receive_ns` | int64 | Horodatage monotone local de réception |
| `speed` | float32 nullable | Vitesse dans l'unité source documentée du plugin |
| `steer` | float32 nullable | Valeur de steering observée/rapportée par le plugin |
| `gas` | float32 nullable | Valeur de gas observée/rapportée par le plugin |
| `brake` | float32 nullable | Valeur de brake observée/rapportée par le plugin |
| `gear` | int16 nullable | Rapport indiqué par le plugin |
| `rpm` | float32 nullable | Régime moteur dans l'unité source documentée |
| `valid` | bool | Indique si la mesure est valide pour la suite |

Une valeur nulle signifie « indisponible » ou « non fournie » ; ne pas la
remplacer par zéro. Documenter les unités source dans `run.json` et ne
convertir vers des unités communes que dans une étape de traitement versionnée.
Si Openplanet peut lire les contrôles physiques, conserver steer, gas et brake
comme mesures observées dans ce flux, avec la provenance notée dans
`run.json`. Elles ne sont pas équivalentes aux commandes émises par le
collecteur.

### `actions.parquet`

Une ligne par mise à jour de commande envoyée par le collecteur :

| Champ | Type | Signification |
| --- | --- | --- |
| `run_id` | string | UUID du run parent |
| `action_idx` | int64 | Index local de commande croissant |
| `t_issue_ns` | int64 | Heure monotone locale d'émission |
| `t_effective_ns` | int64 nullable | Heure d'application, seulement si mesurable |
| `steer` | float32 | Commande de steering envoyée |
| `gas` | float32 | Commande de gas envoyée |
| `brake` | float32 | Commande de brake envoyée |
| `source` | string | `manual`, `script` ou `policy` |

Pour l'instant, une commande est considérée active jusqu'à l'émission de la
suivante. Conserver chaque mise à jour dans le fichier brut. Une transition
dérivée doit tenir compte de toutes les commandes émises entre deux
observations ; elle ne doit pas en choisir une arbitrairement s'il y en a
plusieurs. Ne pas renseigner `t_effective_ns` avec l'heure d'émission sauf si
le jeu confirme réellement l'application à cet instant.

Les actions de cette table sont celles émises vers le jeu. Si le plugin permet
de lire la manette physique, ces valeurs observées sont consignées dans la
télémétrie et ne remplacent pas les actions émises. Cela permet de distinguer
les cibles d'imitation des commandes réellement produites par la policy. Si la
lecture des entrées physiques n'est pas disponible, enregistrer au minimum
les actions envoyées par le collecteur avec leur `source`.

### `events.parquet`

Une ligne par transition d'état de run ou commande de cycle de vie pour toute
la session, pas une ligne par image :

| Champ | Type | Signification |
|---|---|---|
| `run_id` | string nullable | UUID du run concerné ; nul avant son démarrage |
| `event_idx` | int64 | Index local d'événement croissant |
| `t_event_ns` | int64 | Horodatage monotone local de l'événement |
| `event_type` | string | Par exemple `run_started`, `run_finished`, `reset_requested`, `reset_completed`, `run_aborted`, `state_unknown` |
| `state` | string | État après transition : `UNKNOWN`, `READY`, `RUNNING`, `RESETTING`, `FINISHED` ou `ABORTED` |
| `source` | string | `user`, `plugin` ou `timeout` |
| `details_json` | nullable string | Détails optionnels sérialisés en JSON |

`run.json` conserve aussi l'état final et la raison de fermeture. Le journal
d'événements permet de reconstruire les transitions et leur origine ; il
n'infère pas une arrivée depuis une vitesse nulle ou une absence d'image.

## Synchronisation et fenêtres d'entraînement

Les images, la télémétrie et les actions sont enregistrées indépendamment, à
leurs fréquences natives. Pour un timestamp d'image, la politique initiale du
dataset dérivé sélectionne la mesure de télémétrie la plus proche, dans une
tolérance configurable (exemple initial : 50 ms). Si aucune mesure ne respecte
la tolérance, la mesure est déclarée indisponible ou l'exemple est écarté ; ne
pas forcer un appariement. Conserver les timestamps bruts afin de pouvoir
tester ultérieurement une autre politique.

Le dataset brut stocke les événements, pas des fenêtres glissantes dupliquées.
Un exemple dérivé ancré à l'instant `t` peut être construit à partir de :

- l'historique d'images et de télémétrie se terminant en `t`, sans observation
  future ;
- toutes les mises à jour d'action pertinentes pendant l'intervalle suivant ;
- la fenêtre d'observations suivante, encodée pour calculer la cible latente.

L'encodeur de l'état courant ne doit voir que sa fenêtre passée ou courante.
La fenêtre future ne sert qu'au calcul de la cible et des losses pendant
l'entraînement.

## Parquet et interruptions

PyArrow définit les schémas de tables canoniques dans
`src/wm_continuity/data/schema.py`. Garder les noms et types stables au sein
d'une version de schéma. Écrire les événements par lots pour éviter de garder
un run complet en mémoire et fermer les writers proprement à la fin du run.

Un processus interrompu alors qu'un writer Parquet est ouvert peut laisser un
fichier sans footer valide. Au prochain lancement du collecteur, marquer ce
run comme incomplet et ne pas considérer ses fichiers valides sans contrôle
de récupération. Si la récupération des derniers événements tamponnés devient
nécessaire, ajouter ultérieurement des segments de taille bornée ; ne pas
prétendre qu'un fichier Parquet ouvert résiste à un crash.

Les fichiers bruts sont la source de vérité. Alignement, transformations
d'image, masquage de télémétrie, normalisation et affectation aux ensembles
d'entraînement/validation/test appartiennent à une configuration de
traitement versionnée et ne doivent pas écraser les enregistrements bruts.
Séparer les données par run entier pour éviter les fuites entre frames voisines.
