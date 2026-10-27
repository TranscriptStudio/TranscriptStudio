
# TranscriptStudio v2 — Workflow

Deux vues du même workflow : une vue d'ensemble (le pipeline de bout en bout) et une vue détaillée (mécanismes internes du moteur de traitement, de la validation et de la construction de l'ouvrage).

## Vue d'ensemble — du fichier audio à l'ouvrage

```mermaid
flowchart TD
  AUDIO["Audio de la réunion"] --> PRE["Prétraitement
  découpe · suppression des silences · accélération
  (journal des opérations persisté)"]
  PRE --> ASR["Transcription ElevenLabs"]
  ASR --> EDIT["Correction et diarisation
  (éditeur v1 existant)"]
  EDIT --> ETUDE["Étude
  regroupement ordonné des réunions"]
  ETUDE --> DECOUP["Découpage en blocs de parole
  séparation des blocs multi-points · fusions éventuelles"]
  DECOUP --> BLOCS["Blocs de traitement
  Reformulation (par bloc) · Résumé (par réunion)"]
  SYNT["Synthèse d'étude"] -->|"contexte niveau 2"| BLOCS
  BLOCS --> VAL["Relecture et validation
  bloc par bloc"]
  VAL -->|"résumés validés"| SYNT
  VAL --> OUV["Ouvrage de référence
  ordre éditable · Titre 1 paramétrable"]
  OUV --> AIDE["Aides à la relecture
  récurrences · emphase · sous-titres IA · cohérence"]
  AIDE --> OUV
  OUV --> EXPORT["Export DOCX"]
```

Le pipeline en une phrase : l'audio devient transcription corrigée, la réunion rejoint une étude, les blocs de parole sont reformulés ou résumés avec un contexte hiérarchique (fenêtre glissante + synthèse d'étude), l'utilisateur valide, les textes validés alimentent la synthèse d'étude et l'ouvrage de référence, qui s'exporte en DOCX.

## Vue détaillée — mécanismes internes

```mermaid
flowchart TD
  subgraph P14["Préparation des blocs (P14)"]
    JOURNAL["Journal des opérations de prétraitement
    découpe · silences (positions, durées) · accélération"] --> CONV["Conversions
    position audio traité ↔ original"]
    CONV --> AUTO["Sous-découpage automatique des monologues
    coupes aux pauses longues · jamais dans une citation"]
    AUTO --> MANU["Ajustements manuels
    séparation (fonction split v1) · fusion multi-locuteurs"]
    MANU --> FID["Blocs identifiés par FID stable
    texte source + locuteur(s) + positions"]
  end

  subgraph MOTEUR["Moteur de traitement (P15-P16)"]
    CTX["Assemblage du contexte
    prompt du bloc + fenêtre glissante (≤ ~2000 tokens)
    + synthèse d'étude (≤ ~1500 tokens) + bloc courant
    (+ versions antérieures si relance ciblée)"] --> LLM["Appel LLM
    streaming · usage et coût estimés"]
    LLM --> NORM["Normalisation
    doubles retours à la ligne → un seul"]
    NORM --> QC["Contrôles qualité locaux
    rapport de longueur · références ajoutées/perdues
    interdits stylistiques · citations vs JND"]
    QC --> STOCK["Stockage versionné par bloc
    nouvelle version à chaque exécution ou relance"]
  end

  subgraph BOUCLE["Boucle humaine de validation"]
    STOCK --> RELIRE["Relecture du résultat face au bloc source"]
    RELIRE --> EDITER["Édition au paragraphe
    ou relance avec consigne libre
    ou relance ciblée sur sélection"]
    EDITER -->|"nouvelle version"| STOCK
    RELIRE --> VALIDER["Validation du bloc"]
    VALIDER --> REPRISE{"Un bloc antérieur
    a-t-il changé ?"}
    REPRISE -->|"oui"| PROP["Reprise proposée des blocs suivants
    (contexte = textes validés)"]
    PROP --> MOTEUR
  end

  subgraph RESUME["Bloc Résumé (P17)"]
    SRC["Source au choix au lancement
    transcription brute corrigée
    ou reformulations validées"] --> SEG["Traitement en 3-5 segments
    avec léger chevauchement"]
    SEG --> ASS["Assemblage"]
    ASS -->|"même outillage d'édition"| RELIRE
  end

  subgraph ETUDE2["Niveau étude (P17)"]
    VALIDER --> SYN["Synthèse d'étude mise à jour
    pensées déjà développées · versets déjà cités"]
    SYN -->|"contexte niveau 2"| CTX
  end

  subgraph OUVRAGE["Ouvrage de référence (P19-P20)"]
    VALIDER --> GEN["Génération de l'ouvrage
    paragraphes avec provenance (FID, réunion, date)"]
    GEN --> STRUCT["Structure éditable
    Titre 1 paramétrable · sous-titres proposés par IA
    métadonnées de réunion non structurelles"]
    STRUCT --> MOUV["Paragraphes mobiles inter-blocs
    détection des renvois orphelins"]
    MOUV --> OUTILS["Aide à l'écriture globale
    n-grammes récurrents (local) · emphase (lexique)
    incohérences et redondances (passe LLM à la demande)"]
    OUTILS --> DOCX["Export DOCX de l'ouvrage structuré"]
  end
```

Points de lecture :

- **La fenêtre glissante n'utilise que ce qui est validé ou produit en amont** : en passe complète, chaque bloc est traité avec les résultats frais des précédents ; en reprise (bloc antérieur modifié), avec les textes validés seulement.
- **La boucle humaine est le cœur du système** : stockage versionné → relecture → édition ou relance (globale, ciblée sur sélection) → validation → reprise éventuelle des blocs suivants. Aucun texte non validé ne sort vers l'ouvrage.
- **Deux contextes, deux niveaux** : la fenêtre glissante assure la continuité au sein d'une réunion ; la synthèse d'étude assure la continuité entre réunions (elle sait ce qui a déjà été développé).
- **L'ouvrage est un document dérivé autonome** : généré depuis les blocs validés, chaque paragraphe garde sa provenance, puis il vit sa propre vie (structure, déplacements, aides à la relecture) indépendamment des régénérations de réunion.