
# Contrat du format étude (v2 — P14.1)

Ce document définit le contrat exact du format étude. Il fait autorité pour l'implémentation de P14 ; toute divergence constatée en développant se signale dans PROJECT_STATE.md et s'arbitre à l'atelier.

> Révision 2026-10-29 : invariant 13.5 réécrit (exclusivité réunion ↔ étude, cf. ARBITRAGE_EXCLUSIVITE_REUNIONS_2026-10-29.md). Le reste est inchangé par rapport à CONTRAT_FORMAT_ETUDE_V2_2026-10-27.md.

## 1. Principes de fond

1. **L'étude référence les projets v1, elle ne les copie pas** : un projet v1 reste inchangé et réutilisable tel quel ; l'étude ne détient que des références (chemins relatifs + métadonnées).
2. **Non-destructif** : aucun traitement ne modifie le texte source d'un bloc ; les résultats vivent à part, versionnés.
3. **FID stable** : chaque bloc de parole reçoit un identifiant (FID) attribué une seule fois, jamais réutilisé, même après suppression ou fusion — la traçabilité résultat ↔ audio est garantie.
4. **Portabilité** : chemins relatifs partout, résolution à l'ouverture avec fallback et relocalisation guidée (même mécanique que P1.2 v1).
5. **Une étude = un livre biblique par défaut** (ex. « Évangile de Luc »), **thème libre possible** — le titre et le gabarit de Titre 1 sont paramétrables.

## 2. Structure du dossier étude

```text
Etude_Luc\                                    ← dossier étude (nom libre)
├── etude.json                                ← contrat de l'étude (§3)
├── reunions\
│   ├── 2026-10-13_Luc1b.json                 ← référence à un projet v1 (§4)
│   └── 2026-10-20_Luc1c.json
├── blocs\
│   ├── journal-fid.json                      ← registre FID de l'étude (§5)
│   └── decoupage\
│       └── 2026-10-13_Luc1b.json             ← segmentation en blocs d'une réunion (§6)
├── traitements\
│   ├── reformulation\
│   │   └── <FID>.json                        ← résultat versionné par bloc (§7)
│   ├── resume\
│   │   └── 2026-10-13_Luc1b.json             ← résumé versionné par réunion (§8)
│   └── journal_operations.json                ← log des opérations de l'étude, append-only (§11)
├── synthese\
│   └── synthese.json                         ← synthèse d'étude versionnée (§9)
└── parametres\
    └── parametres.json                       ← réglages de l'étude (§10)
```

Conventions : encodage UTF-8 partout ; un seul retour à la ligne par saut de paragraphe dans les textes stockés ; noms de fichiers sans accents ni espaces ; dates au format `AAAA-MM-JJ`.

## 3. `etude.json`

```json
{
  "etude_format_version": 1,
  "titre": "Évangile de Luc",
  "theme": "livre",                          // "livre" | "libre"
  "gabarit_titre_1": "Chapitre {chapitre} — {section}",
  "ordre_reunions": ["2026-10-13_Luc1b", "2026-10-20_Luc1c"],
  "creation": "2026-10-27T14:30:00",
  "modification": "2026-10-27T14:30:00"
}
```

- `ordre_reunions` fait autorité pour l'ordre de lecture ; il correspond aux noms de fichiers de `reunions\` sans extension.
- `gabarit_titre_1` définit le Titre 1 de l'ouvrage (P19) ; les métadonnées de réunion (numéro, date) ne sont jamais structurelles.

## 4. `reunions\<nom>.json`

```json
{
  "reference": "2026-10-13_Luc1b.json",
  "chemin_projet": "../../Projets/2026-10-13_Luc1b",   // chemin relatif vers le projet v1
  "chemin_absolu": "C:\\Users\\David\\Projets\\2026-10-13_Luc1b",  // secours historique : null à la création, rempli à la première résolution réussie, persisté (validé atelier 2026-10-27)
  "date": "2026-10-13",
  "numero": 1,
  "titre_1": "Chapitre 1 — Naissance de Jean-Baptiste", // instance du gabarit, éditable
  "resume_valide": true                                  // dernier résumé validé ?
}
```

Règles de résolution : à l'ouverture, résoudre `chemin_projet` relatif au dossier étude ; en cas d'échec, tenter le chemin absolu historique (stocké en secours à la première résolution réussie), puis proposer la relocalisation guidée ; en cas de projet introuvable, ouvrir l'étude en mode dégradé (réunions joignables uniquement) sans bloquer les autres réunions.

## 5. `blocs\journal-fid.json` (registre par étude)

```json
{
  "prochain_fid": 57,
  "fid_attribues": {
    "42": { "reunion": "2026-10-13_Luc1b", "cree": "2026-10-27T14:35:00", "actif": true, "fin": null }
  }
}
```

- FID = entier séquentiel, attribué à la première segmentation d'un bloc, **jamais réutilisé** ;
- `actif: false` = bloc supprimé ou fusionné (le FID reste au registre, les résultats associés aussi) ;
- le registre est **unique pour toute l'étude** (décision d'atelier du 2026-10-27) — il garantit qu'un FID désigne toujours le même discours dans toute l'étude, y compris entre réunions.

## 6. `blocs\decoupage\<réunion>.json`

```json
{
  "reunion": "2026-10-13_Luc1b",
  "blocs": [
    {
      "fid": 42,
      "locuteurs": ["Philippe"],
      "positions": { "debut": "00:02:31.400", "fin": "00:04:12.100" },   // positions dans l'audio TRAITÉ
      "source": "…texte du bloc (transcription corrigée), immuable…",
      "origine": { "fusion_de": null, "sous_decoupage": false }
    }
  ]
}
```

- `source` est le texte de la transcription corrigée, **immuable après enregistrement du bloc** ;
- `positions` réfèrent à l'audio traité ; la conversion vers l'audio original se fait via le journal des opérations de prétraitement (§12) ;
- pour un bloc fusionné : `locuteurs` porte plusieurs noms, `fusion_de` liste les FID d'origine ;
- ré-attribution des FID : toute re-segmentation attribue de nouveaux FID aux nouveaux blocs ; les blocs inchangés (mêmes bornes) conservent leur FID.

## 7. `traitements\reformulation\<FID>.json`

```json
{
  "fid": 42,
  "versions": [
    {
      "numero": 3,
      "texte": "…reformulation…",
      "horodatage": "2026-10-28T09:12:00",
      "type": "relance",          // "passe" | "relance" | "relance_ciblee" | "edition_manuelle"
      "consigne": null,          // consigne libre éventuelle de la relance
      "selection": null,         // { "debut": 120, "fin": 260 } si relance ciblée (offsets caractères)
      "stats": { "duree_ms": 8400, "tokens_in": 3120, "tokens_out": 1180, "cout_estime": 0.012 },  // LLM uniquement ; null pour édition_manuelle
      "validation": { "statut": "valide", "horodatage": "2026-10-28T09:20:00", "validateur": "David" }
    }
  ]
}
```

- une **version par exécution ou édition** ; l'historique complet est conservé, jamais écrasé ;
- **la version porte la validation** : `validation.statut` ∈ `valide` uniquement (la validation se porte sur une version précise, qui devient la version figée du bloc) ; pas de statut « refusé » — un bloc non validé est simplement modifiable ;
- seules les versions **validées** alimentent contexte, synthèse et ouvrage ;
- **reformulation partielle** : le passage reformé est intégré dans le texte complet du bloc — c'est toujours **l'ensemble du bloc qui est versionné** (une version `relance_ciblee` contient le bloc entier, reformulé partiellement) ;
- `stats` (durée, tokens, coût) alimente l'indicateur de version de l'UI ; les coûts proviennent du **catalogue de coûts par modèle des réglages de l'app** (éditable, mise à jour régulière) ;
- contexte utilisé (fichiers sources des fenêtres) consigné dans un champ `contexte` de la version (liste de FID/références) pour la reproductibilité.

## 8. `traitements\resume\<réunion>.json`

```json
{
  "reunion": "2026-10-13_Luc1b",
  "versions": [
    {
      "numero": 2,
      "texte": "…résumé final…",
      "source": "reformulations_valides",     // "brute_corrigee" | "reformulations_valides"
      "horodatage": "2026-10-28T10:05:00",
      "validation": { "statut": "valide", "horodatage": "…", "validateur": "David" }
    }
  ]
}
```

La source utilisée est **stockée avec le résultat** (décision : source au choix à chaque lancement) ; un avertissement s'affiche si la source a évolué depuis la génération.

## 9. `synthese\synthese.json`

```json
{
  "versions": [
    {
      "numero": 5,
      "texte": "…synthèse d'étude…",
      "horodatage": "…",
      "declencheur": "validation_bloc"       // "validation_bloc" | "manuel" | "creation_etude"
    }
  ]
}
```

Mise à jour à chaque validation de bloc (niveau 2 du contexte) ; versionnée ; plafonnée en tokens selon les réglages.

## 10. `parametres\parametres.json`

```json
{
  "reformulation": {
    "prompt": "…prompt v2 complet, éditable…",
    "modele": "mistral-large-latest",
    "temperature": 0.3,                        // défaut venant des réglages de l'app, surchargeable par étude (décision 2026-10-27)
    "fenetre_glissante_tokens": 2000
  },
  "resume": {
    "prompt": "…prompt résumé v2 complet, éditable…",
    "modele": "mistral-large-latest",
    "temperature": 0.2,
    "longueur_cible_mots": [650, 700],
    "source_defaut": "reformulations_valides"
  },
  "synthese": { "tokens_max": 1500, "modele": "mistral-small-latest" },
  "controle_qualite": { "lexique_emphase": ["puissamment", "profondément", "véritablement"] },
  "llm": { "fournisseurs": [ { "nom": "mistral", "url": "…", "cle_ref": "credential_store" } ] }
}
```

Les prompts stockés sont **les valeurs actives** de l'étude (initialisés depuis les v2 de référence) ; aucune clé API en clair — référence au CredentialStore v1.

## 11. `traitements\journal_operations.json` — log des opérations de l'étude

Décision David du 2026-10-27 : fichier dédié associé à l'étude, journalisant **toutes les opérations du process** (passes complètes, reformulations par bloc, éditions manuelles, validations/dévalidations, fusions, erreurs API, annulations). Le comportement du moteur (P15.3/P15.4) est spécifié dans « Spécification du moteur de traitement » (asset `spec/SPEC_MOTEUR_P15_V2.md`) ; le contrat ci-dessous fixe le stockage.

```json
{
  "journal_version": 1,
  "entrees": [
    {
      "horodatage": "2026-10-28T09:12:00",
      "type": "reformulation_bloc",       // passe_complete | reformulation_bloc | edition_manuelle | validation | devalidation | fusion_blocs | erreur_api | annulation_passe | resume | synthese
      "fid": 42,                          // null si périmètre réunion/passe
      "reunion": "2026-10-13_Luc1b",
      "modele": "mistral-large-latest",
      "version": 3,                       // version produite le cas échéant
      "resultat": "succes",               // "succes" | "erreur" (+ "message")
      "stats": { "duree_ms": 8400, "tokens_in": 3120, "tokens_out": 1180, "cout_estime": 0.012 }   // null hors appel LLM
    }
  ]
}
```

- **append-only** : aucune entrée n'est jamais effacée ni réécrite ; fichier unique pour toute l'étude ;
- écrit à chaque opération (pas seulement en fin de passe) — survit à un crash ;
- document d'audit et d'affichage uniquement : jamais consommé par le moteur ni par les traitements ; l'affichage in-app (icône 📋 Log, spec UI §8) le lit en lecture seule.

## 12. Journal des opérations de prétraitement (fichier additionnel du projet v1)

Décision d'atelier du 2026-10-27 : stocké **dans le dossier projet v1** sous le nom `journal_operations.json` (additif, non destructif — le format v1 n'est pas modifié).

```json
{
  "journal_version": 1,
  "horodatage": "2026-10-13T20:00:00",
  "operations": [
    { "type": "decoupe", "positions": ["00:00:00", "00:45:12"] },
    { "type": "silence_supprime", "position": "00:03:12.400", "duree_originale": "00:00:04.200", "buffer": 0.25 },  // buffer conservé en secondes (validé atelier 2026-10-27)
    { "type": "acceleration", "facteur": 1.15 }
  ]
}
```

- **un nouveau journal remplace l'ancien à chaque re-prétraitement** (pas de composition) ;
- sert aux conversions position traité ↔ original (P14.4, tests unitaires obligatoires) et au sous-découpage aux pauses réelles ;
- jamais supprimé par l'étude ; sa présence est optionnelle (projets v1 antérieurs).

## 13. Règles d'invariance (à tester unitairement)

1. Ouvrir une étude ne modifie jamais aucun projet v1 référencé (hors journal des opérations créé par un prétraitement).
2. Un FID, une fois attribué, désigne pour toujours le même discours ; les versions ne s'écrasent pas.
3. La suppression d'une réunion de l'étude retire sa référence et ses résultats d'étude, mais ne touche ni le projet v1 ni le registre FID.
4. Déplacer le dossier étude reste sûr : les chemins se résolvent par ordre relatif → absolu → relocalisation.
5. Une réunion (projet v1) est référencée par **au plus une étude** à la fois (exclusivité — ARBITRAGE_EXCLUSIVITE_REUNIONS, 2026-10-29). Le rattachement reste possible à tout moment dès le prétraitement ; le changement d'étude demande une confirmation et laisse les traitements déjà réalisés à l'ancienne étude (la réunion change seulement de rattachement).
6. Le log des opérations ne perd jamais une entrée : toute opération aboutie ou échouée y laisse exactement une trace horodatée, même en cas de crash ultérieur.