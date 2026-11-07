# models/ouvrage.py
"""
Modèle du document ouvrage (P19.1, feuille de
route v2.1 §P19).

Le document ouvrage est un **document dérivé
autonome** : initialisé à partir des
reformulations validées de l'étude selon l'ordre
d'ouvrage, chaque paragraphe conserve une
**provenance** (FID du bloc source, réunion,
date) ; ensuite l'ouvrage vit sa propre vie et
peut diverger des textes validés par réunion.

Il est stocké dans le dossier de l'étude sous le
nom ``ouvrage.json`` (format additionnel au
contrat format étude — le dossier reste
autonome et portable).

Structure du document : liste PLATTE ordonnée
d'éléments (style corps de document Word) :

- ``titre_1`` : titre de chapitre — ajouté
  MANUELLEMENT (l'enchaînement des réunions ne
  suit pas les chapitres, maquette validée
  2026-10-29) ;
- ``sous_titre`` : sous-titre thématique
  (granularité plus fine que le chapitre) —
  manuel, ou suggéré par IA à valider (P20.2) ;
- ``separateur`` : séparateur de section ;
- ``paragraphe`` : texte avec **provenances**
  (une à la génération, PLUSIEURS après une
  fusion de pensées — P19.4).

Les éléments placés AVANT le premier ``titre_1``
ne relèvent d'aucun chapitre : ils constituent
les **Réserves** (réunions non placées, visibles
dans l'arborescence de la page Ouvrage).

Les métadonnées de réunion (numéro, date) sont
NON STRUCTURELLES : elles voyagent dans la
provenance des paragraphes, jamais dans la
structure du document.
"""

from dataclasses import (
    dataclass,
    field,
)
from typing import Optional

from services.etude_schema import (
    EtudeFormatError,
)


class OuvrageFormatError(EtudeFormatError):
    """
    Le fichier ``ouvrage.json`` n'est pas lisible
    comme un document ouvrage (clé manquante,
    type inattendu, version de format non gérée).

    Hérite d'EtudeFormatError : même famille
    « ce dossier d'étude n'est pas lisible » — un
    appelant qui attrape l'une voit l'autre.
    """

    def __init__(self, message: str):

        super().__init__(
            "ouvrage.json",
            message
        )


FORMAT_OUVRAGE = 1

# Types d'éléments du document.
TYPE_TITRE_1 = "titre_1"
TYPE_SOUS_TITRE = "sous_titre"
TYPE_SEPARATEUR = "separateur"
TYPE_PARAGRAPHE = "paragraphe"

TYPES_TITRES = (
    TYPE_TITRE_1,
    TYPE_SOUS_TITRE,
)

# Origine d'un paragraphe.
SOURCE_GENERATION = "generation"
SOURCE_SAISIE = "saisie"
SOURCE_FUSION = "fusion"


def _exiger(data: dict, cle: str):
    """
    Exige une clé d'un dictionnaire JSON, avec un
    message d'erreur au canon du format étude.
    """

    if cle not in data:
        raise OuvrageFormatError(
            f"ouvrage.json : clé manquante « {cle} »"
        )

    return data[cle]


def _texte(data: dict, cle: str) -> str:
    """
    Exige une chaîne (None accepté et normalisé
    en chaîne vide pour les clés optionnelles).
    """

    valeur = _exiger(data, cle)

    if valeur is None:
        return ""

    if not isinstance(valeur, str):
        raise OuvrageFormatError(
            f"ouvrage.json : clé « {cle} » : "
            f"texte attendu"
        )

    return valeur


@dataclass
class ProvenanceParagraphe:
    """
    Provenance d'un paragraphe : le bloc source
    (FID), sa réunion, et la version validée
    utilisée à la génération.

    Un paragraphe FUSIONNÉ (P19.4) porte
    PLUSIEURS provenances (FIDs, locuteurs,
    réunions) — la liste existe dès P19.1.
    """

    reunion: str = ""
    fid: int = 0
    numero_reunion: int = 0
    date_reunion: str = ""
    locuteurs: str = ""
    numero_version: int = 0
    horodatage_version: str = ""

    def to_dict(self) -> dict:

        return {
            "reunion": self.reunion,
            "fid": self.fid,
            "numero_reunion": self.numero_reunion,
            "date_reunion": self.date_reunion,
            "locuteurs": self.locuteurs,
            "numero_version": self.numero_version,
            "horodatage_version": (
                self.horodatage_version
            ),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict
    ) -> "ProvenanceParagraphe":

        fid = _exiger(data, "fid")

        if not isinstance(fid, int):
            raise OuvrageFormatError(
                "ouvrage.json : provenance : "
                "fid entier attendu"
            )

        return cls(
            reunion=_texte(data, "reunion"),
            fid=fid,
            numero_reunion=(
                _exiger(data, "numero_reunion")
            ),
            date_reunion=_texte(
                data,
                "date_reunion"
            ),
            locuteurs=(
                data.get("locuteurs")
                if isinstance(
                    data.get("locuteurs"),
                    str
                )
                else ""
            ),
            numero_version=(
                _exiger(data, "numero_version")
            ),
            horodatage_version=_texte(
                data,
                "horodatage_version"
            ),
        )


@dataclass
class ElementOuvrage:
    """
    Un élément du corps du document ouvrage :

    - ``titre_1`` / ``sous_titre`` : ``texte``
      (le titre), pas de provenance ;
    - ``separateur`` : rien ;
    - ``paragraphe`` : ``texte`` +
      ``provenances`` (au moins une), ``source``
      (``generation``, ``saisie``, ``fusion``) et
      ``fusion`` — historique de fusion pour la
      dé-fusion (P19.4, None hors fusion).

    ``id`` : identifiant stable, unique dans le
    document (les références croisées —
    signalements d'analyse, fusion — s'y
    raccrochent).
    """

    id: str
    type: str
    texte: str = ""
    provenances: list = field(
        default_factory=list
    )
    source: str = SOURCE_GENERATION
    fusion: Optional[dict] = None

    def to_dict(self) -> dict:

        data = {
            "id": self.id,
            "type": self.type,
        }

        if self.type == TYPE_SEPARATEUR:
            return data

        data["texte"] = self.texte

        if self.type == TYPE_PARAGRAPHE:

            data["source"] = self.source
            data["provenances"] = [
                p.to_dict()
                for p in self.provenances
            ]

            if self.fusion is not None:
                data["fusion"] = self.fusion

        return data

    @classmethod
    def from_dict(
        cls,
        data: dict
    ) -> "ElementOuvrage":

        type_element = _texte(data, "type")

        if type_element not in (
            TYPE_TITRE_1,
            TYPE_SOUS_TITRE,
            TYPE_SEPARATEUR,
            TYPE_PARAGRAPHE,
        ):
            raise OuvrageFormatError(
                "ouvrage.json : type d'élément "
                f"inconnu « {type_element} »"
            )

        element = cls(
            id=_texte(data, "id"),
            type=type_element,
        )

        if type_element == TYPE_SEPARATEUR:
            return element

        element.texte = _texte(data, "texte")

        if type_element == TYPE_PARAGRAPHE:

            element.source = _texte(
                data,
                "source"
            )

            provenances = _exiger(
                data,
                "provenances"
            )

            if not isinstance(provenances, list):
                raise OuvrageFormatError(
                    "ouvrage.json : provenances : "
                    "liste attendue"
                )

            element.provenances = [
                ProvenanceParagraphe
                .from_dict(p)
                for p in provenances
            ]

            if not element.provenances:
                raise OuvrageFormatError(
                    "ouvrage.json : paragraphe "
                    "sans provenance"
                )

            fusion = data.get("fusion")

            if fusion is not None and (
                not isinstance(fusion, dict)
            ):
                raise OuvrageFormatError(
                    "ouvrage.json : fusion : "
                    "objet attendu"
                )

            element.fusion = fusion

        return element


@dataclass
class DocumentOuvrage:
    """
    Le document ouvrage complet d'une étude :

    - ``titre`` : titre de l'ouvrage (défaut à la
      génération : titre de l'étude) ;
    - ``elements`` : corps du document, liste
      PLATTE ordonnée ;
    - ``generation`` : instantané de la dernière
      génération — horodatage et, par réunion,
      numéro/date et les versions validées
      utilisées ; sert au signalement « réunion
      re-reformulée depuis la génération » (le
      document dérivé n'est JAMAIS mis à jour
      automatiquement).
    - ``historique`` : paragraphes fusionnés
      conservés quand une fusion de pensées est
      DÉFAITE (P19.4) — chaque paragraphe reprend
      son texte, le texte fusionné n'est pas perdu.
    """

    titre: str = ""
    elements: list = field(default_factory=list)
    generation: Optional[dict] = None
    historique: list = field(default_factory=list)
    format_version: int = FORMAT_OUVRAGE

    def to_dict(self) -> dict:

        return {
            "format_version": self.format_version,
            "titre": self.titre,
            "generation": self.generation,
            "historique": self.historique,
            "elements": [
                e.to_dict()
                for e in self.elements
            ],
        }

    @classmethod
    def from_dict(
        cls,
        data: dict
    ) -> "DocumentOuvrage":

        version = _exiger(
            data,
            "format_version"
        )

        if version != FORMAT_OUVRAGE:
            raise OuvrageFormatError(
                "ouvrage.json : format_version "
                f"{version} non géré "
                f"(attendu : {FORMAT_OUVRAGE})"
            )

        elements = _exiger(data, "elements")

        if not isinstance(elements, list):
            raise OuvrageFormatError(
                "ouvrage.json : elements : "
                "liste attendue"
            )

        historique = (
            data.get("historique") or []
        )

        if not isinstance(historique, list):
            raise OuvrageFormatError(
                "ouvrage.json : historique : "
                "liste attendue"
            )

        for entree in historique:

            if not isinstance(entree, dict):
                raise OuvrageFormatError(
                    "ouvrage.json : historique : "
                    "objet attendu"
                )

        document = cls(
            titre=_texte(data, "titre"),
            generation=data.get("generation"),
            historique=historique,
        )

        document.elements = [
            ElementOuvrage.from_dict(e)
            for e in elements
        ]

        ids = [
            e.id for e in document.elements
        ]

        if len(ids) != len(set(ids)):
            raise OuvrageFormatError(
                "ouvrage.json : identifiants "
                "d'éléments en double"
            )

        return document

    # ==================================================
    # Consultation.
    # ==================================================

    def paragraphes(self) -> list:
        """
        Les paragraphes du document, dans l'ordre.
        """

        return [
            e for e in self.elements
            if e.type == TYPE_PARAGRAPHE
        ]

    def paragraphes_reserves(self) -> list:
        """
        Les paragraphes NON PLACÉS : ceux qui
        précèdent le premier titre de chapitre
        (aucun chapitre = tout est en réserve,
        c'est le cas d'un document fraîchement
        généré).
        """

        reserves = []
        place = False

        for element in self.elements:

            if element.type == TYPE_TITRE_1:
                place = True
                continue

            if (
                element.type == TYPE_PARAGRAPHE
                and not place
            ):
                reserves.append(element)

        return reserves

    def element(self, identifiant: str):
        """
        Élément par identifiant (None si absent).
        """

        for element in self.elements:
            if element.id == identifiant:
                return element

        return None

    def nouvel_id(self, prefixe: str) -> str:
        """
        Identifiant stable unique, préfixé
        (``p3``, ``t1_2``, …).
        """

        existants = {
            e.id for e in self.elements
        }

        numero = 1

        while (
            f"{prefixe}{numero}" in existants
        ):
            numero += 1

        return f"{prefixe}{numero}"
