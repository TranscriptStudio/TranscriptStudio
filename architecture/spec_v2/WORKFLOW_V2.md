
# TranscriptStudio v2 — Workflow

Deux vues du même workflow : une vue d'ensemble (le pipeline de bout en bout) et une vue détaillée (mécanismes internes du moteur de traitement, de la validation et de la construction de l'ouvrage). Chaque couleur identifie une zone du système.

**Code couleur** : 🟦 préparation des données · 🟪 moteur de traitement (IA) · 🟩 boucle humaine · 🟧 bloc Résumé · 🟫 niveau étude · 🟥 ouvrage de référence · ⬜ entrées/sorties.

## Vue d'ensemble — du fichier audio à l'ouvrage

```mermaid
flowchart TD
  AUDIO["🎤 Audio de la réunion"] --> PRE["🟦 Prétraitement\nDécoupe · suppression des silences · accélération\n(journal des opérations persisté)"]
  PRE --> ASR["⬜ Transcription ElevenLabs"]
  ASR --> EDIT["🟩 Correction et diarisation\n(éditeur v1 existant)"]
  EDIT --> ETUDE["🟫 Étude\nRegroupement ordonné des réunions"]
  ETUDE --> DECOUP["🟦 Découpage en blocs de parole\nSéparation des blocs multi-points · fusions"]
  DECOUP --> BLOCS["🟪 Blocs de traitement\nReformulation (par bloc) · Résumé (par réunion)"]
  SYNT["🟫 Synthèse d'étude"] -->|"contexte niveau 2"| BLOCS
  BLOCS --> VAL["🟩 Relecture et validation\nbloc par bloc"]
  VAL -->|"résumés validés"| SYNT
  VAL --> OUV["🟥 Ouvrage de référence\nOrdre éditable · Titre 1 paramétrable"]
  OUV --> AIDE["🟩 Aides à la relecture\nRécurrences · emphase · sous-titres IA · cohérence"]
  AIDE --> OUV
  OUV --> EXPORT["📄 Export DOCX"]

  style AUDIO fill:#e8eaf6,stroke:#5c6bc0,color:#1a237e
  style PRE fill:#bbdefb,stroke:#1976d2,color:#0d47a1
  style ASR fill:#f5f5f5,stroke:#9e9e9e,color:#212121
  style EDIT fill:#c8e6c9,stroke:#388e3c,color:#1b5e20
  style ETUDE fill:#ffe0b2,stroke:#f57c00,color:#e65100
  style DECOUP fill:#bbdefb,stroke:#1976d2,color:#0d47a1
  style BLOCS fill:#e1bee7,stroke:#8e24aa,color:#4a148c
  style SYNT fill:#ffe0b2,stroke:#f57c00,color:#e65100
  style VAL fill:#c8e6c9,stroke:#388e3c,color:#1b5e20
  style OUV fill:#ffcdd2,stroke:#d32f2f,color:#b71c1c
  style AIDE fill:#c8e6c9,stroke:#388e3c,color:#1b5e20
  style EXPORT fill:#e8eaf6,stroke:#5c6bc0,color:#1a237e
```

Le pipeline en une phrase : l'audio devient transcription corrigée, la réunion rejoint une étude, les blocs de parole sont reformulés ou résumés avec un contexte hiérarchique (fenêtre glissante + synthèse d'étude), l'utilisateur valide, les textes validés alimentent la synthèse d'étude et l'ouvrage de référence, qui s'exporte en DOCX.

## Vue détaillée — mécanismes internes

```mermaid
flowchart TD
  subgraph P14["🟦 Préparation des blocs — P14"]
    JOURNAL["Journal des opérations\nDécoupe · silences (positions, durées) · accélération"] --> CONV["Conversions\nposition traité ↔ original"]
    CONV --> AUTO["Sous-découpage automatique des monologues\nCoupes aux pauses longues · jamais dans une citation"]
    AUTO --> MANU["Ajustements manuels\nSéparation (split v1) · fusion multi-locuteurs"]
    MANU --> FID["Blocs identifiés par FID stable\nTexte source + locuteur(s) + positions"]
  end

  subgraph MOTEUR["🟪 Moteur de traitement — P15–P16"]
    CTX["Assemblage du contexte\nPrompt du bloc + fenêtre glissante (~2000 tokens)\n+ synthèse d'étude (~1500 tokens) + bloc courant\n+ versions antérieures si relance ciblée"] --> LLM["Appel LLM\nStreaming · usage et coûts estimés"]
    LLM --> NORM["Normalisation\nDoubles retours à la ligne → un seul"]
    NORM --> QC["Contrôles qualité locaux\nRapport de longueur · références ajoutées/perdues\nInterdits stylistiques · emphase · citations vs JND"]
    QC --> STOCK["Stockage versionné par bloc\nNouvelle version à chaque exécution ou relance"]
  end

  subgraph BOUCLE["🟩 Boucle humaine de validation"]
    STOCK --> RELIRE["Relecture\nRésultat face au bloc source"]
    RELIRE --> EDITER["Édition au paragraphe\nRelance avec consigne libre\nRelance ciblée sur sélection"]
    EDITER -->|"nouvelle version"| STOCK
    RELIRE --> VALIDER["✅ Validation du bloc"]
    VALIDER -->|"bloc antérieur modifié :\nrelance laissée à l'utilisateur\n(aucune cascade)"| MOTEUR
  end

  subgraph RESUME["🟧 Bloc Résumé — P17"]
    SRC["Source au choix au lancement\nBrute corrigée ou reformulations validées"] --> SEG["Traitement en 3–5 segments\nAvec léger chevauchement"]
    SEG --> ASS["Assemblage"]
    ASS -->|"même outillage d'édition"| RELIRE
  end

  subgraph ETUDE2["🟫 Niveau étude — P17"]
    VALIDER --> SYN["Synthèse d'étude mise à jour\nPensées déjà développées · versets déjà cités"]
    SYN -->|"contexte niveau 2"| CTX
  end

  subgraph OUVRAGE["🟥 Ouvrage de référence — P19–P20"]
    VALIDER --> GEN["Génération de l'ouvrage\nParagraphes avec provenance (FID, réunion, date)"]
    GEN --> STRUCT["Structure éditable\nTitre 1 paramétrable · sous-titres IA\nMétadonnées de réunion non structurelles"]
    STRUCT --> MOUV["Paragraphes mobiles inter-blocs\nDétection des renvois orphelins"]
    MOUV --> OUTILS["Aide à l'écriture globale\nN-grammes récurrents (local) · emphase (lexique)\nIncohérences/redondances (LLM à la demande)"]
    OUTILS --> DOCX["Export DOCX de l'ouvrage structuré"]
  end

  style P14 fill:#e3f2fd,stroke:#1976d2,color:#0d47a1
  style MOTEUR fill:#f3e5f5,stroke:#8e24aa,color:#4a148c
  style BOUCLE fill:#e8f5e9,stroke:#388e3c,color:#1b5e20
  style RESUME fill:#fff3e0,stroke:#ef6c00,color:#e65100
  style ETUDE2 fill:#fff8e1,stroke:#f57c00,color:#e65100
  style OUVRAGE fill:#ffebee,stroke:#d32f2f,color:#b71c1c

  style JOURNAL fill:#bbdefb,stroke:#1976d2
  style CONV fill:#bbdefb,stroke:#1976d2
  style AUTO fill:#bbdefb,stroke:#1976d2
  style MANU fill:#bbdefb,stroke:#1976d2
  style FID fill:#bbdefb,stroke:#1976d2

  style CTX fill:#e1bee7,stroke:#8e24aa
  style LLM fill:#ce93d8,stroke:#8e24aa,color:#4a148c
  style NORM fill:#e1bee7,stroke:#8e24aa
  style QC fill:#e1bee7,stroke:#8e24aa
  style STOCK fill:#e1bee7,stroke:#8e24aa

  style RELIRE fill:#c8e6c9,stroke:#388e3c
  style EDITER fill:#c8e6c9,stroke:#388e3c
  style VALIDER fill:#a5d6a7,stroke:#2e7d32,color:#1b5e20
  style REPRISE fill:#c8e6c9,stroke:#388e3c
  style PROP fill:#c8e6c9,stroke:#388e3c

  style SRC fill:#ffe0b2,stroke:#ef6c00
  style SEG fill:#ffe0b2,stroke:#ef6c00
  style ASS fill:#ffe0b2,stroke:#ef6c00

  style SYN fill:#ffe0b2,stroke:#f57c00,color:#e65100

  style GEN fill:#ffcdd2,stroke:#d32f2f
  style STRUCT fill:#ffcdd2,stroke:#d32f2f
  style MOUV fill:#ffcdd2,stroke:#d32f2f
  style OUTILS fill:#ffcdd2,stroke:#d32f2f
  style DOCX fill:#ef9a9a,stroke:#b71c1c,color:#b71c1c
```

Points de lecture :

- **La fenêtre glissante n'utilise que ce qui est validé ou produit en amont** : en passe complète, chaque bloc est traité avec les résultats frais des précédents ; en reprise (bloc antérieur modifié), avec les textes validés seulement.
- **La boucle humaine est le cœur du système** : stockage versionné → relecture → édition ou relance (globale, ciblée sur sélection) → validation → reprise éventuelle des blocs suivants. Aucun texte non validé ne sort vers l'ouvrage.
- **Deux contextes, deux niveaux** : la fenêtre glissante assure la continuité au sein d'une réunion (violet) ; la synthèse d'étude assure la continuité entre réunions (orange — elle sait ce qui a déjà été développé).
- **L'ouvrage est un document dérivé autonome** : généré depuis les blocs validés, chaque paragraphe garde sa provenance, puis il vit sa propre vie (structure, déplacements, aides à la relecture) indépendamment des régénérations de réunion.