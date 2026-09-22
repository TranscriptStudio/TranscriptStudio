# TranscriptAudio - Roadmap Traitement Audio (post-commit UI Waveform)

## Objectif
Découper le développement en petits commits cohérents, faciles à tester et à revert.

---

# Commit 1 - Suppression du panneau Réglages

## Objectif
Afficher les options de traitement en permanence dans la fenêtre principale.

## Actions

- Supprimer le bouton « Réglages ».
- Supprimer la zone masquée/affichée associée.
- Ajouter un panneau fixe en bas de l'interface.
- Vérifier que le redimensionnement de la fenêtre reste correct.

## Tests

- Ouverture d'un fichier.
- Vérification du redimensionnement.
- Vérification de la persistance des contrôles.

---

# Commit 2 - Modèle de données TraitementsAudio

## Objectif
Centraliser les paramètres futurs dans une structure unique.

## Actions

Créer une classe de configuration :

- trim_start_enabled
- trim_start_time
- trim_end_enabled
- trim_end_time
- silence_enabled
- silence_threshold_db
- silence_min_duration
- speed_enabled
- speed_percent

## Tests

- Chargement des valeurs par défaut.
- Modification depuis l'UI.

---

# Commit 3 - UI Découpe avant

## Objectif
Ajouter l'option de découpe avant.

## Actions

Ajouter sur une même ligne :

- Checkbox Découpe avant
- TextBox temps début

Comportement :

- La TextBox est désactivée tant que la case n'est pas cochée.
- Activation automatique lors du cochage.
- Synchronisation bidirectionnelle avec la valeur interne.

## Tests

- Cocher / décocher.
- Modifier le temps.

---

# Commit 4 - UI Découpe après

## Objectif
Ajouter l'option de découpe après.

## Actions

Même principe que la découpe avant.

Ligne finale :

[ ] Découpe avant   [temps]
[ ] Découpe après   [temps]

## Tests

- Synchronisation.
- Validation des valeurs.

---

# Commit 5 - Marqueur graphique Début

## Objectif
Afficher la poignée de découpe début.

## Actions

Dans WaveformWidget :

- Dessiner un triangle bleu.
- Dessiner une barre verticale.
- Dessiner la zone supprimée en transparence.

Zone estompée :

0 -------------- trim_start

## Tests

- Différents niveaux de zoom.
- Différentes durées audio.

---

# Commit 6 - Marqueur graphique Fin

## Objectif
Afficher la poignée de découpe fin.

## Actions

- Triangle inversé.
- Barre verticale.
- Zone estompée après le marqueur.

## Tests

- Zoom.
- Déplacement.

---

# Commit 7 - Déplacement souris des poignées

## Objectif
Rendre les poignées manipulables.

## Actions

Ajouter :

- Hit test poignée début.
- Hit test poignée fin.
- Curseur SizeHorCursor.

Règle :

- Le drag n'est possible que sur les poignées.
- Le clic waveform continue de contrôler la lecture.

## Tests

- Déplacement début.
- Déplacement fin.
- Conflit avec curseur lecture.

---

# Commit 8 - Synchronisation poignées / TextBox

## Objectif
Synchronisation bidirectionnelle.

## Actions

Poignée -> TextBox

TextBox -> Poignée

Validation :

- début < fin
- valeurs dans la durée du média

## Tests

- Cas limites.
- Modification rapide.

---

# Commit 9 - Gestion visuelle des conflits

## Objectif
Gérer les positions proches du curseur de lecture.

## Actions

- Priorité de sélection aux poignées.
- Zone de capture plus large.
- Affichage de survol.

## Tests

- Poignée et lecture au même endroit.
- Fort zoom.

---

# Commit 10 - UI Suppression des silences

## Objectif
Ajouter les paramètres de suppression des silences.

## Actions

Ligne unique :

[ ] Suppression silences
Seuil dB [textbox]
Durée mini [textbox]

Comportement :

- Champs activés uniquement si coché.

## Tests

- Activation / désactivation.
- Validation numérique.

---

# Commit 11 - Service Détection des silences

## Objectif
Préparer la logique audio.

## Actions

Créer :

SilenceDetectionService

Fonctions :

- détection segments silencieux
- seuil dB
- durée minimale

Sans modifier encore le fichier audio.

## Tests

- Logs de détection.
- Vérification manuelle.

---

# Commit 12 - UI Accélération audio

## Objectif
Ajouter le panneau d'accélération.

## Actions

Afficher :

- Checkbox Accélérer
- Slider 0 à 100 %
- Barre couleur fixe derrière le slider
- Zone ratio

Couleurs :

- Vert -> 0 à 50 %
- Orange -> intermédiaire
- Rouge -> 100 %

## Tests

- Fluidité du slider.
- Affichage du ratio.

---

# Commit 13 - Conversion pourcentage -> ratio

## Objectif
Définir la règle de calcul.

## Exemple

0 %  = x1.00
50 % = x1.50
100 % = x2.00

## Tests

- Cohérence affichage.
- Valeurs limites.

---

# Commit 14 - Architecture du pipeline traitement

## Objectif
Préparer l'exécution future.

## Actions

Créer :

AudioProcessingPipeline

Étapes :

1. Découpe début
2. Découpe fin
3. Suppression silences
4. Accélération

Sans traitement réel.

## Tests

- Vérifier l'enchaînement.
- Vérifier les paramètres transmis.

---

# Commit 15 - Traitement réel Découpe

## Objectif
Créer le premier traitement fonctionnel.

## Actions

Implémenter :

- trim start
- trim end

sur le WAV de travail.

## Tests

- Validation durée.
- Contrôle des exports.

---

# Commit 16 - Nettoyage et stabilisation

## Actions

- Revue UI.
- Revue signaux Qt.
- Revue performances zoom.
- Revue interactions poignées.
- Documentation technique.

## Résultat attendu

Interface complète prête avant implémentation avancée des traitements audio.
