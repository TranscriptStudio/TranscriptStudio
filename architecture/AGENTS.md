# Instructions pour les agents IA - TranscriptStudio

## 1. Objet de ce document

Ce fichier définit les règles permanentes que tout agent IA intervenant sur TranscriptStudio doit respecter.

Avant toute intervention sur le projet, l'agent doit :

1. lire intégralement ce fichier ;
2. lire `PROJECT_STATE.md` ;
3. examiner l'état réel du dépôt Git ;
4. consulter les derniers commits pertinents ;
5. vérifier que `PROJECT_STATE.md` est cohérent avec l'état réel du dépôt.

En cas de divergence entre `PROJECT_STATE.md` et le dépôt Git, l'état réel du dépôt Git et du code source prévaut.

Ne jamais inventer l'état d'une fonctionnalité, d'un test ou d'une modification.

---

## 2. Contexte du projet

TranscriptStudio est une application de bureau Python destinée notamment :

- au prétraitement d'enregistrements audio ;
- à la transcription audio ;
- à la relecture et correction des transcriptions ;
- à la gestion de projets contenant les données nécessaires à ces traitements.

Le projet est en cours d'évolution vers une architecture portable entre :

- Windows ;
- macOS ;
- Linux.

Toute nouvelle modification doit éviter d'introduire une dépendance inutile à un système d'exploitation particulier.

---

## 3. Sources de vérité

Utiliser cet ordre de priorité pour déterminer l'état réel du projet :

1. code source actuel ;
2. dépôt Git et historique des commits ;
3. tests automatisés et résultats d'exécution ;
4. documentation technique ;
5. `PROJECT_STATE.md`.

`PROJECT_STATE.md` est une mémoire de travail destinée à faciliter les reprises de session. Ce fichier ne remplace ni Git, ni les tests, ni l'inspection du code.

---

## 4. Règles avant modification

Avant de modifier le code :

1. examiner `git status` ;
2. identifier les modifications locales éventuellement présentes ;
3. ne jamais écraser des modifications utilisateur non comprises ;
4. examiner les fichiers concernés ;
5. identifier les dépendances de la modification ;
6. déterminer les tests à effectuer ;
7. vérifier si une décision d'architecture existante s'applique.

Si l'état du dépôt est ambigu ou incohérent, interrompre la modification et expliquer la situation avant de poursuivre.

---

## 5. Règles de développement

### 5.1 Modifications minimales

Privilégier les changements :

- ciblés ;
- compréhensibles ;
- testables ;
- réversibles.

Éviter les refactorisations non nécessaires à la tâche demandée.

### 5.2 roadmap et commits

Mettre à jour la raodmap à chaque fois qu'une tache a été réalisée.lancer le commit uniquement à la fin. ne pas relancer de commit quand seule la raodmap a été mise à jour. les commit doivent toujours correspondre à une étape de développpement.

### 5.3 Multiplateforme

Ne pas coder directement des chemins dépendants de Windows tels que :



```text
C:\Users\...
AppData\...
Documents\...
```

## 6. Synchro avec l'atelier de spécification (Vibe Work)

L'atelier maintient un skill partagé dans le workspace Mistral « transcriptstudio » :
  transcriptstudio-spec  (consignes + documents spec/ en assets)

### Déclencheurs du rituel de synchro
1. Au DÉBUT de chaque session de travail ;
2. à chaque commande utilisateur du type « synchronise avec agent de spec ».

### Rituel de synchro
1. Lire le skill transcriptstudio-spec (dernière version) : corps + assets spec/
   nécessaires à la tâche du jour.
2. Recopier tout asset spec/ nouveau ou plus récent que sa copie locale dans
   architecture/spec_v2/ (remplacement ou création, jamais de fusion ni
   d'édition — les fichiers de l'atelier sont complets, les compléments
   arrivent en fichiers séparés).
3. Copier architecture/PROJECT_STATE.md courant vers le dossier Drive local
   G:\Mon Drive\TranscriptStudio\Synchro (montée vers l'atelier).

### Règles de fond
- Ne jamais modifier le skill ni ses assets : écrits par l'atelier seul.
- Écrire librement dans PROJECT_STATE.md (décisions techniques, contraintes,
  écarts) ; en cas de conflit avec la spec, le signaler dedans et poursuivre.
- La v2 (P14+) démarre après la livraison de P11.