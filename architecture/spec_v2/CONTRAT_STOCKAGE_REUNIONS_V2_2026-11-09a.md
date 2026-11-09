# Amendement : stockage des traitements au niveau réunion (P18.7)

> Statut : **fait autorité** — amende CONTRAT_FORMAT_ETUDE_V2.md pour les points traités (prime sur ce contrat).
> Décision David du 2026-11-08 (3 arbitrages : tier dans le projet v1 ; héritage total silencieux à l'attachement ; migration one-shot à l'ouverture).
> Motivation : une reformulation ou un résumé sont des propriétés de la **réunion**, réalisables sur une réunion autonome sans étude (P18.6 : réunion objet de premier rang). L'étude ne fait plus que référencer les traitements, comme elle référence déjà les projets v1.

## 1. Principe

**Inversion du rang de stockage** : tout ce qui dépend de la parole d'une réunion vit dans un tier « réunion TranscriptStudio » stocké **dans le dossier projet v1** (sous-dossier additif `transcriptstudio\`). L'étude ne détient plus que ce qui est propre à l'agrégat : ordre, thème, gabarit, synthèse, surcharges de paramètres.

- Le sous-dossier `transcriptstudio\` est **additif et namespacé** : le projet v1 reste ouvrable et utilisable tel quel par la v1, conformément au précédent du journal de prétraitement (§12 du contrat).
- Copier le dossier projet emporte la réunion **et tout son travail** (autonomie totale).
- L'exclusivité réunion ↔ étude (invariant 13.5, ARBITRAGE_EXCLUSIVITE_REUNIONS) est inchangée.

## 2. Structure du projet v1 augmenté

```text
Projets\<reunion>\                       ← projet v1, fichiers inchangés par ailleurs
├── (audio, transcription, … v1)
├── journal_operations.json              ← prétraitement (§12 du contrat, inchangé)
└── transcriptstudio\                   ← tier réunion (P18.7)
    ├── reunion.json                    ← métadonnées du tier (§3)
    ├── blocs\
    │   ├── journal-fid.json            ← registre FID de la RÉUNION (§4)
    │   └── decoupage.json              ← segmentation en blocs (§5)
    ├── traitements\
    │   ├── reformulation\<FID>.json    ← versionné par bloc (identique au §7 du contrat)
    │   ├── resume.json                 ← versionné (ex-<réunion>.json du §8)
    │   └── journal_operations.json     ← log réunion (§7 ci-dessous)
    └── parametres\parametres.json      ← paramètres actifs de la réunion (§8)
```

## 3. `reunion.json` (tier)

```json
{
  "reunion_format_version": 1,
  "creation": "2026-11-08T10:00:00",
  "modification": "2026-11-08T10:00:00",
  "resume_valide": true,
  "etudes": [ ]                          // liste vide (autonome) ou 1 élément max { "chemin": "../../Etude_Luc", "rattachement": "2026-11-08T10:00:00" }
}
```

- `resume_valide` migre depuis `reunions\<nom>.json` de l'étude.
- `etudes` matérialise l'exclusivité côté réunion (0 ou 1 élément) ; l'étude garde `ordre_reunions` côté sien. Une divergence (réunion qui se dit rattachée, étude qui ne la liste pas, ou l'inverse) est détectée à l'ouverture et signalée : l'utilisateur choisit la correction, aucune écriture automatique.

## 4. Registre FID : portée réunion

- Le registre **n'est plus global à l'étude** ; il vit dans le tier, un par réunion.
- L'identité d'un bloc dans une étude devient le couple **(réunion, FID)** — les FID restent séquentiels et jamais réutilisés au sein de leur réunion.
- Le contexte (fenêtre glissante, niveau 2), la synthèse et l'ouvrage référencent désormais des paires (réunion, fid), jamais un FID seul.
- La décision d'atelier du 2026-10-27 (registre unique pour toute l'étude) est **abrogée** pour les nouvelles données ; la migration la préserve historiquement via l'éclatement du registre (§9).

## 5. Découpage

- `blocs\decoupage.json` du tier reprend tel quel le schéma §6 du contrat (le champ `reunion` devient redondant mais est conservé pour compatibilité).
- Le découpage est réalisable sur une réunion autonome, sans étude.

## 6. Reformulation et résumé

- Schémas **inchangés** (§7 et §8 du contrat) : versions, validation portée par la version, `stats`, `source` du résumé stockée avec le résultat.
- Réalisables sur une réunion autonome. L'étude consomme les versions validées du tier.

## 7. Journaux des opérations

- **Journal réunion** (`transcriptstudio\traitements\journal_operations.json`) : append-only, un par réunion ; journalise réformulations de blocs, éditions manuelles, validations/dévalidations, fusions, résumés, erreurs API, annulations — avec le couple (réunion, fid). Mêmes règles que le §11 du contrat (append-only, écrit à chaque opération, document d'audit et d'affichage uniquement).
- **Journal étude** : conservé, mais réduit au périmètre étude — synthèses, rattachements/détachements de réunions, migrations de format.

## 8. Paramètres actifs

- Le tier porte ses propres `parametres\parametres.json`, initialisés depuis les réglages de l'app (mêmes champs que le §10 du contrat, volets `reformulation`, `resume`).
- **Toute opération sur les traitements d'une réunion — où qu'elle soit lancée — utilise les paramètres du tier** (précision David du 2026-11-08) : l'étude ne modifie jamais les conditions de travail de la réunion. Les surcharges d'étude s'appliquent **à la synthèse uniquement**.
- La version produite mémorise ce qui a été utilisé (stats + hash du prompt, cf. UI_GESTION_PROMPTS).

### 8bis. Aucune écriture en retour (précision David du 2026-11-08)

- **Ni l'étude, ni l'ouvrage n'écrivent jamais dans le tier** : les traitements d'une réunion (découpage, reformulations, résumés) ne sont modifiés que depuis les pages de la réunion elle-même.
- Les modifications réalisées dans le volet Ouvrage (fusions de pensées — même entre blocs de réunions différentes —, titres, sous-titres, éditions de texte) **restent dans la couche ouvrage** (P19) : jamais répercutées vers les réunions. Raison d'être : une fusion de pensées inter-réunions répercutée serait d'une complexité disproportionnée et sans intérêt ; l'ouvrage est une composition, pas une réécriture des sources.
- Renforce la décision P19.4 (fusion = opération de composition de l'ouvrage, jamais de la page Reformulation) et l'étend à toutes les écritures de l'ouvrage.

## 9. Ce qui reste à l'étude (contrat v2, `etude_format_version: 2`)

```text
Etude_Luc\
├── etude.json                 ← + "etude_format_version": 2
├── reunions\<nom>.json        ← garde reference, chemins, date, numero, titre_1 ; PERD resume_valide (→ tier)
├── synthese\synthese.json     ← inchangé (§9 du contrat)
├── parametres\parametres.json ← surcharges d'étude (synthèse + volets de relance)
├── journal_etude.json         ← ex-journal_operations de l'étude, périmètre étude seul
└── sauvegardes\               ← copies de sécurité créées par la migration
```

- `blocs\` et `traitements\` **disparaissent** du dossier étude.

## 10. Rattachement / détachement

- **Attachement** (à tout moment dès le prétraitement) : l'étude référence le tier ; **héritage total silencieux** (arbitrage David 2026-11-08) — découpage, FID, reformulations et résumés validés deviennent la base de travail de l'étude ; la synthèse d'étude s'incruste à la prochaine validation de bloc. Si le tier n'existe pas encore, il est créé à la première opération sur la réunion.
- **Détachement / changement d'étude** : la réunion garde son tier et tout son travail ; l'ancien comportement (invariant 13.3 : les résultats d'étude restent à l'ancienne étude) est **remplacé** — les traitements suivent la réunion, l'étude perd seulement la référence.
- P18.6d (confirmation au changement d'étude) est inchangé.

## 11. Migration one-shot (arbitrage David 2026-11-08)

À l'ouverture d'une étude `etude_format_version: 1` :

1. **Sauvegarde complète** du dossier étude vers `sauvegardes\<nom>_<AAAAMMJJ-HHMM>\` avant toute écriture.
2. Pour chaque réunion référencée, création/valorisation du tier `transcriptstudio\` dans le projet v1 :
   - `blocs\decoupage\<réunion>.json` → `transcriptstudio\blocs\decoupage.json` ;
   - éclatement du registre FID global en registres par réunion (chaque entrée porte déjà `reunion`) ;
   - `traitements\reformulation\<FID>.json` → tier, aiguillé par le registre (fid → réunion) ;
   - `traitements\resume\<réunion>.json` → `transcriptstudio\traitements\resume.json` ;
   - `resume_valide` → `reunion.json` ; paramètres actifs initialisés depuis `parametres\parametres.json` de l'étude (volets reformulation/resume), puis ces volets deviennent surcharges d'étude ;
   - entrées du journal d'étude de périmètre réunion → journal réunion du tier ; le reste → `journal_etude.json`.
3. **Références croisées** (P19 livré le 07/11 — l'ouvrage existe déjà) : requalifier en couples (réunion, FID) toute référence de bloc qui désignerait un FID seul — provenances des paragraphes d'`ouvrage.json` (y compris instantanés de fusion et historique de dé-fusion), contexte de la synthèse, fenêtre glissante — et vérifier que chaque référence résout vers le tier de sa réunion après éclatement du registre. L'`ouvrage.json` reste au niveau étude (couche ouvrage, P19.1 inchangé).
4. `etude.json` passe à `etude_format_version: 2` ; `blocs\` et `traitements\` supprimés **après** copie vérifiée (contrôle d'intégrité : nombre de fichiers, FID, versions).
5. La migration est **idempotente et reprenable** : tout fichier déjà migré n'est pas retraité ; un crash reprend au point d'arrêt.

## 12. Invariants mis à jour (testés unitairement)

1. Ouvrir une étude ou une réunion ne modifie jamais le projet v1, **hors du sous-dossier additif `transcriptstudio\`** et du journal de prétraitement (§12 du contrat).
2. Un FID, une fois attribué dans sa réunion, désigne pour toujours le même discours ; les versions ne s'écrasent pas.
3. **Retirer une réunion d'une étude ne touche ni le projet v1 ni son tier** : la réunion reste ouvrable autonome avec tout son travail.
4. Déplacer un dossier étude ou un dossier projet reste sûr : résolution relative → absolue → relocalisation guidée, pour chaque référence (études ↔ réunions, réunions ↔ projets v1).
5. Exclusivité réunion ↔ étude (au plus une étude) ; toute divergence constatée est signalée, jamais corrigée silencieusement.
6. Les journaux ne perdent jamais une entrée ; chaque journal ne couvre que son périmètre (réunion ou étude).
7. La migration ne détruit rien : la sauvegarde précède toute écriture, la source n'est supprimée qu'après contrôle d'intégrité, l'opération est idempotente et reprenable.
8. **Aucune écriture en retour** : ni l'étude, ni l'ouvrage n'écrivent jamais dans le tier d'une réunion (§8bis) ; les paramètres de toute opération de la réunion viennent toujours du tier.
