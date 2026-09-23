# TranscriptAudio - Roadmap Traitement Audio (post-commit UI Waveform)

## Objectif
Découper le développement en petits commits cohérents, faciles à tester et à revert.

---

# Commit 1 - Suppression du panneau Réglages 

## Objectif
Afficher les options de traitement en permanence dans la fenêtre principale.

## Actions

- [✓] Supprimer le bouton « Réglages ».
- [✓] Supprimer la zone masquée/affichée associée.
- [✓] Ajouter un panneau fixe en bas de l'interface.
- [✓] Vérifier que le redimensionnement de la fenêtre reste correct.

## Tests

- [✓] Ouverture d'un fichier.
- [✓] Vérification du redimensionnement.
- [✓] Vérification de la persistance des contrôles.

---

# Commit 2 - Modèle de données TraitementsAudio V1.1.2

## Objectif
Centraliser les paramètres futurs dans une structure unique.

## Actions

Créer une classe de configuration :

- [✓] trim_start_enabled
- [✓] trim_start_time
- [✓] trim_end_enabled
- [✓] trim_end_time
- [✓] silence_enabled
- [✓] silence_threshold_db
- [✓] silence_min_duration
- [✓] speed_enabled
- [✓] speed_percent

## Tests

- [✓] Chargement des valeurs par défaut.
- [✓] Modification depuis l'UI.

---

# Commit 3 - UI Découpe unifiée

UI Découpe unifiée
- [✓] Checkbox découpe
- [✓] Début
- [✓] Fin
- [✓] Durée conservée

---

# Commit 4 - Poignées graphiques de découpe

## Objectif

Afficher graphiquement la zone conservée.

### Actions

- [✓] Ajouter poignée début.
- [✓] Ajouter poignée fin.
- [✓] Ajouter barres verticales.
- [✓] Ajouter triangles de préhension.
- [✓] Ajouter rendu des zones supprimées.

### Résultat attendu

xxx ▼=====================▼ xxx

---

# Commit 5 - Déplacement des poignées

## Objectif

Manipuler les poignées à la souris.

### Actions

- [✓] Hit test début.
- [✓] Hit test fin.
- Curseur SizeHorCursor.
- [✓] Drag poignée début.
- [✓] Drag poignée fin.

### Synchronisation

Poignée → textbox

Textbox → poignée

---

# Commit 6 - Validation découpe V1.1.3

## Objectif

Sécuriser les saisies.

### Contraintes

- [✓] début < fin
- [✓] début ≥ 0
- [✓] fin ≤ durée audio


### Affichage

- [✓] correction automatique
- [✓] ajout poignées ouvertes ou fermées au passage sourie

---

# Commit 7 - Architecture pipeline V1.1.4

## Objectif

Préparer le moteur.

### Créer

AudioProcessingPipeline

### Ordre

1. Découpe
2. Silences
3. Accélération

- [✓] création services/audio_processing_pipeline.py
- [✓] ajout du squelette
- [✓] ajouter les traces dans l'ordre
- [✓] brancher le bouton traiter
- [✓] modifier process_audio()

Sans traitement réel.

---

# Commit 8 - UI Suppression silences

## Affichage

☑ Suppression silences

Seuil :
[-35 dB]

Durée mini :
[500 ms]

### Comportement

- [✓] Activation dynamique des champs.

---

# Commit 9a - Détection des silences V1.1.5

## Créer

- [✓] SilenceDetectionService

### Fonction

- [✓] Détecter les zones silencieuses.

### Pas encore de suppression réelle.

---

# Commit 9b - conversion audio wave


- [✓] instancier audio converti en wav
- [✓] rendu opérationnnel par utilisation SilenceDetectionService


---
# Commit 10 - UI Accélération V1.1.6

## Affichage

☑ Accélération

Slider 0 → 100 %

Barre couleur :
vert → orange → rouge

Ratio :
[1.00x]

- [✓] mise en place de l'UI pour l'accélération

---

# Commit 11 - Amélioration graphique et analyse prévisionelle globale v1.1.7

11.1 Réorganisation UI

- [✓] retrait des labels sous les checkboxes ;
- [✓] durée conservée sur la ligne Début / Fin ;
- [✓] paramètres silence sur une seule ligne ;
- [✓] ratio vitesse à droite du slider ;
- [✓] colorbar full-transparente quand désactivée ;
- [✓] labels estompés quand option inactive.
- [✓] réduire hauteur de la piste par défaut 
- [✓] augmenter la hauteur mini du panneau option

11.2 Affichage temps

- [✓] temps de saisie découpe au dixième 
- [✓] temps récapitulatifs à la seconde 

11.3 Analyse prévisionnelle

ajouter 
- [✓] Découpe : Temps supprimé / sur la même ligne que les paramètres découpe
- [✓] Silences : Nb silences détectés  et Temps total de silence, sur la même ligne que les paramètres
- [✓] Vitesse : Gain théorique, sur la même ligne que le slider
- [✓] rendre ces paramètres invisibles quand option décochée

11.4 Waveform

- [✓] passer la découpe en gris
- [✓] ajouter les silences en rouge transparent
- [✓] passer waveforme en couleur bleu par exemple (plutôt que gris actuel) et augmenter très légèrement l'épaisseur de la courbe


11.5 récap dans encart final

- [✓] ajout Durée originale format HH:MM:SS
- [✓] ajout Temps supprimé format HH:MM:SS
- [✓] ajout Durée estimée finale format HH:MM:SS

11.6 ajustement calcul silence

- [✓] réduire la plage de calcul de silence à la zone de trim si celle ci est activée
- [✓] ajustement des couleurs

---


# Commit 12 - Découpe réelle

## Objectif

Premier traitement audio réel.

### Fonction

- [✓]  trim start
- [✓]  trim end

sur WAV de travail.

---

# Commit 13 - Suppression silences réelle

## Fonction

Suppression effective des segments détectés.

---

# Commit 14 - Accélération réelle

## Fonction

Modification vitesse audio.

---

# Commit 15 - Pipeline complet

## Ordre final

1. Découpe
2. Suppression silences
3. Accélération
4. Export

---

# Commit 16 - Stabilisation

## Actions

- nettoyage UI
- optimisation waveform
- revue performances
- revue architecture
- documentation