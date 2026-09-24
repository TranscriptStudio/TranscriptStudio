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

- [✓]  Suppression effective des segments détectés.

---

# Commit 14 - Accélération réelle

## Fonction

- [✓] Modification vitesse audio.

---

# Commit 15

## 15.0 Séparation UI / Résultat Audio

- [✓] séparation UI/résultat audio

## 15a
- [✓] génération de audio_processed.wav
- [✓] calcul des statistiques réelles
- [✓] mise à jour de la ligne de résumé existante
## Commit 15b
- [✓] déplacement de category_combo
- [✓] retiré de ui/new_transcription_dialog.py
- [✓] ajouté dans ui/transcription_entry_dialog.py
- [✓] propagé via get_result()

### test
- [✓] « Nouvelle transcription » affiche maintenant Sous-répertoire du projet.
- [✓] La liste contient toujours Commun.
- [✓] La zone reste éditable.
- [✓] Elle n'apparaît plus dans NewTranscriptionDialog.
- [✓] Les parcours Direct et Prétraitement s'ouvrent toujours normalement.
- [✓] print(result) ok

## Commit 15c V1.1.8
- [✓] Corriger ProjectManager.create_project_folder()
- [✓] création du dossier projet dès l'entrée du workflow
- [✓] sauvegarde de audio_processed.wav dans ce dossier
- [✓] suppresion fichiers wav temporaires 
- [✓] récupération du fichier audion dans new_transcription _dialog (soit brut soit processé selon option)

### Tests avant de passer

1. Direct sans catégorie

- [✓] dossier YYYY-MM-DD_nom créé ;
- [✓] audio original copié ;
- [✓] NewTranscriptionDialog affiche le bon fichier.

2. Direct avec Commun

- [✓] dossier créé sous Commun;
- [✓] audio copié dedans.

3. Deux fois le même fichier

- [✓] second dossier suffixé _1;
- [✓] il reste bien dans la catégorie.

4. Prétraitement

- [✓] audio original présent dans le dossier projet ;
- [✓] après « Lancer le traitement », audio_processed.wav apparaît dans ce même dossier ;
- [✓] NewTranscriptionDialog reçoit audio_processed.wav.

- [✓] Vérification temporaire print("Audio transmis :", processed_audio_file) avant l'ouverture de NewTranscriptionDialog


## commit 16
- affichage waveform final avec options de lecture sous le résumé des infos finales
                 AudioPreprocessDialog
                         │
             ┌───────────┴────────────┐
             │                        │
     waveform originale       options traitement
             │                        │
             └───────────┬────────────┘
                         │
                  Lancer traitement
                         │
                         ▼
               audio_processed.wav
                         │
                statistiques réelles
                         │
                         ▼
              Résultat du traitement
              ┌─────────────────────┐
              │ waveform résultat   │
              └─────────────────────┘
                 ◀   ▶/⏸   ⏹
                 slider + temps
                         │
                         ▼
                    ☁ Transcrire
## 16.1

- [✓] Créer la zone Résultat sous le résumé, masquée avant le premier traitement.

## 16.2

- [✓] Ajouter une deuxième WaveformWidget pour audio_processed.wav.
- [✓] aujuster les graphismes

## 16.3


- [✓]  lecteur indépendant ;
- [✓]  lecture/pause ;
- [✓]  stop ;
- [✓]  slider et temps ;
- [✓]  curseur piloté par la lecture ;
- [✓]  corriger : échelle temporelle ;
- [✓]  corriger : positionnement/double-clic du curseur ;
- [✓]   zoom ;
- [✓]   déplacement horizontal ;
- [✓]  à améliorer : séparation visuelle Options / Résultat. 
## 16.4

À chaque nouveau traitement :

- [✓]  arrêter l'ancienne écoute ;
- [✓]  recharger audio_processed.wav ;
- [✓]  recalculer sa waveform ;
- [✓]  remettre le curseur à 0 ;
- [✓]  afficher la zone résultat.

## 16.5

 [✓] Petite adaptation de WaveformWidget pour que la waveform résultat soit neutre, sans poignées de trim ni zones de silence. Actuellement le widget recherche son parent_dialog.settings et affiche automatiquement ces overlays lorsqu'il est dans AudioPreprocessDialog.

## 16.6 ajouter des popup avec barre de chargement V1.1.9
### 16.6a
- [✓] popup de chargement initial
- [✓] indicateur indéterminé
- [✓] préparation audio dans un QThread
- [✓] ouverture du dialogue après préparation
### 16.6b 
- [✓] Découpe
- [✓] Suppression des silences
- [✓] Accélération
- [✓] Finalisation / génération du résultat

---


## commit 17 - sauvegarde et export audio

Commit 17 - Validation du prétraitement et fichier final
 
17.1 - Simplification toolbar
- [✓] supprimer Annuler les modifications
- [✓] supprimer Sauvegarder
- [✓] désactiver Transcrire avant premier traitement
- [✓] tooltip explicite sur Transcrire
 
17.2 - Validation audio
- [✓] clic Transcrire
- [✓] arrêt des lecteurs
- [✓] conversion audio_processed.wav vers format final
- [✓] conserver audio original
- [✓] conserver audio_processed.ext
- [✓] supprimer les WAV temporaires
- [✓] supprimer le audio_process.wav
- [✓] ajouter une loading page pour la conversion du fichier
 
17.3 - Abandon du prétraitement
- [✓] interception fermeture fenêtre
- [✓] arrêt des lecteurs
- [✓] suppression fichiers temporaires
- [✓] suppression audio_processed
- [✓] suppression du dossier projet provisoire
 
17.4 - Continuité workflow
- [✓] transmettre audio_processed.ext à NewTranscriptionDialog
- [✓] ne jamais transmettre audio_processed.wav temporaire
- [✓] conserver le dossier projet validé
 
17.5 - Cas particuliers
- [✓] original WAV
- [✓] formats audio compressés
- [✓] entrées vidéo
- [✓] erreur de conversion finale
- [✓] erreur de suppression Windows

# Commit 18 - Buffer de suppression des silences

## 18.1 - Modèle et UI
- [✓] ajouter silence_buffer_duration
- [✓] valeur par défaut : 0.2 s
- [✓] ajouter le champ Buffer (s)
- [✓] activation dynamique avec l'option silences

## 18.2 - Calcul des zones réellement supprimées
- [ ] conserver detected_silences comme détection brute
- [ ] conserver filtered_silences comme détection limitée au trim
- [ ] ajouter removal_silences
- [ ] appliquer le buffer aux deux extrémités
- [ ] ignorer les zones devenues nulles

## 18.3 - Analyse prévisionnelle
- [ ] nombre de silences réellement supprimés
- [ ] durée supprimée tenant compte du buffer
- [ ] durée finale estimée tenant compte du buffer

## 18.4 - Waveform
- [ ] afficher en violet uniquement removal_silences
- [ ] représentation graphique identique au traitement réel

## 18.5 - Traitement réel
- [ ] appliquer exactement le même buffer dans le pipeline
- [ ] conserver le buffer amont
- [ ] conserver le buffer aval
- [ ] buffer = 0 reproduit le comportement actuel

## 18.6 - Validation
- [ ] buffer = 0
- [ ] buffer = 0.2
- [ ] silence <= 2 × buffer
- [ ] interaction avec trim
- [ ] comparaison estimation / résultat réel


# Commit 19 - Stabilisation

## Actions

- nettoyage UI
- optimisation waveform
- revue performances
- revue architecture
- documentation