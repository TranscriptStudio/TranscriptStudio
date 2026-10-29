# Arbitrage — Exclusivité du rattachement des réunions aux études (P18.6)

Date : 2026-10-29 (atelier de conception, validé par David).

## Contexte

Le contrat du format étude (v2 — P14.1) énonce en invariant 13.5 : « Un projet v1 peut être référencé par plusieurs études simultanément. » La refonte de la navigation (P18.6) fait de la réunion un objet de premier rang (autonome ou appartenant à une étude) ; aucun cas d'usage réel ne justifie de retrouver une même réunion dans plusieurs études — l'ouvrage final correspond à une étude, et la duplication du travail d'édition/reformulation entre études serait source de divergence.

## Décision

1. **Inversion de l'invariant 13.5 du contrat** : une réunion (projet v1) est référencée par **au plus une étude** à la fois (exclusivité).
2. Le contrat est republié (CONTRAT_FORMAT_ETUDE_V2_2026-10-29.md) avec l'invariant 13.5 réécrit ; les autres sections sont inchangées.
3. Le rattachement à une étude reste possible **à tout moment, dès le prétraitement**. Si la réunion est déjà rattachée, un nouveau rattachement devient un **changement d'étude** avec confirmation, **option A** : les traitements déjà réalisés (reformulations, résumés, validations) **restent à l'ancienne étude** — aucun déplacement, aucune copie ; la réunion change seulement de rattachement.

## Conséquences

- **UI** : « Rattacher à une étude… » sur les réunions autonomes (hub, ruban Réunion) ; « Gestion de l'étude » (page Réunion) ; badge d'étude (titre + version de Bible). Sur la page Étude, « Ajouter une réunion » liste les nouveaux audios et les réunions autonomes.
- **Données** : l'unicité est vérifiée à l'attachement ; aucun changement de format de fichier (l'étude référence toujours la réunion, l'unicité est contrôlée à l'écriture). Les études existantes non conformes, s'il y en a, ne sont pas migrées : la contrainte s'applique aux nouveaux rattachements.
- **Invariants de test** : SPEC_NAVIGATION_V2_2026-10-29.md §9.1 (0 ou 1 étude) et §9.5 (aucun traitement déplacé lors d'un changement d'étude).