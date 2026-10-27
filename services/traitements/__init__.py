# services/traitements/__init__.py
"""
Moteur de traitement et log des opérations (P15).

- ``journal`` : log des opérations de l'étude
  (append-only, écrit à chaque opération) — importé
  en eager (utilisé par etude_io, sans cycle) ;
- ``moteur`` : assemblage de contexte, exécution
  séquentielle, annulation, reprise, coûts — importé
  en lazy (il importe etude_io) : accessible via
  ``from services.traitements.moteur import ...``
  ou par les réexportations différées ci-dessous.
"""

from services.traitements.journal import (
    FICHIER_JOURNAL,
    JournalError,
    JournalEtude,
    RESULTAT_ERREUR,
    RESULTAT_SUCCES,
    TYPES_ENTRUES,
    TYPE_ANNULATION_PASSE,
    TYPE_DEVALIDATION,
    TYPE_EDITION_MANUELLE,
    TYPE_ERREUR_API,
    TYPE_FUSION_BLOCS,
    TYPE_PASSE_COMPLETE,
    TYPE_REFORMULATION_BLOC,
    TYPE_RESUME,
    TYPE_SYNTHESE,
    TYPE_VALIDATION,
)

_EXPORTS_MOTEUR = {
    "CIBLE_NON_VALIDES",
    "CIBLE_SANS_RESULTAT",
    "ContexteAssemble",
    "ErreurContexte",
    "MoteurTraitements",
    "ResultatPasse",
    "TEMPERATURE_REFORMULATION_DEFAUT",
    "TEMPERATURE_RESUME_DEFAUT",
}


def __getattr__(nom):

    if nom in _EXPORTS_MOTEUR:

        from services.traitements import moteur

        return getattr(moteur, nom)

    raise AttributeError(
        f"module {__name__!r} n'a pas d'attribut "
        f"{nom!r}"
    )
