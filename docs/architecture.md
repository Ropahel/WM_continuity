# Architecture expérimentale

Le dépôt sépare les simulateurs, la préparation des données, les sous-modèles,
les losses, l'entraînement et l'évaluation. L'objectif est de remplacer une
variante par configuration sans réécrire le dataset ni le loop d'entraînement.

## Une transition d'apprentissage

```text
historique passé o[t-L+1:t] ──> encodeur ──> z(t) ─────┐
                                                       ├─> prédicteur(z(t), a(t))
action a(t) ───────────────────────────────────────────┘             │
                                                                   z_hat(t+1)

fenêtre suivante o[t-L+2:t+1] ──> encodeur cible ──> z(t+1)
                                            loss(z_hat(t+1), z(t+1))
```

L'encodeur courant ne reçoit aucune observation postérieure à `t`. Le passage
qui produit la cible `z(t+1)` est distinct et réservé à l'entraînement. Le
prédicteur reste dans l'espace latent ; reconstruire une observation ou des
pixels n'est pas une exigence de la première baseline.

## Contrats des composants

- **Environnement** : expose reset/step, observation, espace d'action, seed et
  marqueurs de fin d'épisode. Les adaptateurs traduisent les API spécifiques
  au simulateur vers ce contrat commun.
- **Dataset d'épisodes** : conserve transitions et métadonnées brutes. Il
  produit des fenêtres temporelles à la demande et sépare les données par
  épisodes complets.
- **Encodeur** : transforme les modalités choisies (état vectoriel, images,
  ou combinaison) ainsi que leur historique en un latent de dimension connue.
- **Encodage temporel** : peut être une partie de l'encodeur ou un composant
  sélectionné indépendamment. Le choix reste expérimental.
- **Prédicteur** : reçoit le latent et l'action et renvoie une prédiction de
  latent à l'horizon spécifié.
- **Losses** : termes nommés, configurables et combinables. Toute expérience
  enregistre le nom, les paramètres et le poids de chaque terme.
- **Policy** : étape ultérieure ; elle transforme `z(t)` en action. Le premier
  objectif est le WM, pas de faire jouer une policy dès le départ.

Les formes de tenseurs doivent être documentées au contrat du modèle :
observations vectorielles `[B,T,F]`, images `[B,T,C,H,W]`, actions `[B,A]`,
latents `[B,D]`. Les composantes effectivement présentes dépendent de
l'environnement choisi.

## Variantes et reproductibilité

Un registre construit les variantes par nom et paramètres résolus depuis YAML.
Une erreur de nom ou paramètre inconnu doit être explicite. Chaque expérience
conserve les configurations résolues, les versions de dépendances utiles, les
seeds, l'environnement/version, les épisodes/splits, les architectures et les
losses.

Les sauvegardes et la commande `save_model` sont décrites dans
[checkpoints.md](./checkpoints.md). Les traces latentes sont facultatives,
activées par commande et identifiées par expérience, checkpoint, épisode et
pas de simulation.

## Ordre des expériences

1. Valider l'API et la reproductibilité de l'environnement.
2. Valider la structure des transitions et des fenêtres causales.
3. Tester les contrats et variantes de modèles sur des données synthétiques.
4. Entraîner une loss de référence et surveiller la diversité latente.
5. Modifier un seul facteur expérimental à la fois.
6. N'ajouter images, dépendances de benchmark ou policy qu'une fois la
   baseline précédente fiable.

Les anciens choix Trackmania (captures, télémétrie de véhicule, Openplanet,
pilotage) sont archivés et ne définissent plus l'architecture active.
