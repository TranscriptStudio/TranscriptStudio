# services/jnd.py
"""
Ressource JND locale (P18.1 — feuille de route §6).

Bible JND (et JND révisée) au format OSIS XML,
chargée depuis ``resources/bible/JND.osis.xml``
(fichier volumineux NON suivi dans le dépôt —
instructions de téléchargement dans le README,
comme FFmpeg ; la BibleAbsente est une erreur claire
tant qu'il n'est pas installé).

API locale :
- ``charger_bible(chemin)`` : parse le OSIS XML en
  mémoire (une entrée par verset) ;
- ``ReferenceBiblique`` : livre / chapitre / versets,
  affichage normalisé « Livre C.v » / « Livre C.v-v » ;
- ``extraire_references(texte)`` : parsing du format
  français et de ses variantes (« Luc 15.11-32 »,
  « Jn 3:16 », « genèse 2 verset 4 à 6 », « Ps 23 »,
  « 1 Samuel 3 »...) — insensible à la casse et aux
  accents ;
- ``texte_versets(reference)`` : texte JND d'une
  référence ;
- ``rechercher(expression)`` : occurrences d'une
  expression dans la Bible chargée.

Utilisée par le contrôle qualité (P18.2) et
l'éventuelle pré-correction.
"""

import re
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from services.resources import resource_path


#
# Emplacement de la ressource (voir README pour le
# téléchargement — le fichier n'est pas dans le
# dépôt).
#

NOM_FICHIER_BIBLE = "JND.osis.xml"

#
# Noms de fichiers acceptés, par ordre de priorité
# pour un chargement IMPLICITE (sans version
# d'étude) : un JND.osis.xml explicite prime
# toujours, sinon la version par défaut de P18.5
# (darbyR — décision David 2026-10-28) avant la
# Darby classique. Le contrôle qualité passe
# désormais par services/bibles.py, qui travaille
# contre la version retenue par l'étude (spec
# BIBLE_JND §3.3) — ce repli ne sert qu'aux
# usages hors étude.
#

NOMS_FICHIERS_BIBLE = [
    "JND.osis.xml",
    "DarbyR.osis.xml",
    "Darby.osis.xml",
]

MESSAGE_BIBLE_ABSENTE = (
    "La Bible (OSIS XML) n'est pas installée.\n\n"
    "Installez une version depuis les réglages de "
    "l'application, onglet « Bibles » (téléchargeur "
    "intégré ou « Charger depuis un fichier… »)."
)


class BibleAbsente(Exception):
    """
    La ressource JND n'est pas installée.
    """


def chemin_bible() -> Path:
    """
    Chemin de la ressource JND installée : le
    premier fichier attendu qui existe (JND.osis.xml
    explicite, puis Darby.osis.xml, puis DarbyR).
    Aucun n'est installé → chemin par défaut
    (JND.osis.xml, utilisé dans le message d'erreur).
    """

    for nom in NOMS_FICHIERS_BIBLE:

        chemin = resource_path(
            f"resources/bible/{nom}"
        )

        if chemin.is_file():
            return chemin

    return resource_path(
        f"resources/bible/{NOM_FICHIER_BIBLE}"
    )


#
# Table des livres : identifiant OSIS, nom français
# canonique, variantes courantes (abréviations).
#

_TABLE_LIVRES = [
    ("Gen", "Genèse", ["Gen", "Gn", "Ge"]),
    ("Exod", "Exode", ["Ex", "Exo"]),
    ("Lev", "Lévitique", ["Lv", "Le"]),
    ("Num", "Nombres", ["Nb", "Nu"]),
    ("Deut", "Deutéronome", ["Dt", "Deut"]),
    ("Josh", "Josué", ["Jos", "Js"]),
    ("Judg", "Juges", ["Jg", "Jug"]),
    ("Ruth", "Ruth", ["Rt", "Rut"]),
    ("1Sam", "1 Samuel", ["1 Sam", "1S", "1 Sa"]),
    ("2Sam", "2 Samuel", ["2 Sam", "2S", "2 Sa"]),
    ("1Kgs", "1 Rois", ["1 R", "1R", "1 Rois"]),
    ("2Kgs", "2 Rois", ["2 R", "2R", "2 Rois"]),
    ("Ezra", "Esdras", ["Esd", "Ezr"]),
    ("Neh", "Néhémie", ["Néh", "Ne", "Neh"]),
    ("Esth", "Esther", ["Est", "Esth"]),
    ("Job", "Job", []),
    ("Ps", "Psaumes", ["Ps", "Psaume", "Psa"]),
    ("Prov", "Proverbes", ["Pr", "Prov"]),
    ("Eccl", "Ecclésiaste", ["Ec", "Ecc", "Eccl"]),
    ("Song", "Cantique des cantiques", ["Cantique", "Cant", "Ct"]),
    ("Isa", "Ésaïe", ["Es", "És", "Esa", "Esaïe", "Is", "Isaïe"]),
    ("Jer", "Jérémie", ["Jr", "Jer", "Jeremie"]),
    ("Lam", "Lamentations", ["Lm", "Lam"]),
    ("Ezek", "Ézéchiel", ["Éz", "Ez", "Ezechiel"]),
    ("Dan", "Daniel", ["Dn", "Dan"]),
    ("Hos", "Osée", ["Os", "Osee"]),
    ("Joel", "Joël", ["Joe", "Joel"]),
    ("Amos", "Amos", ["Am"]),
    ("Obad", "Abdias", ["Ab", "Ob"]),
    ("Jonah", "Jonas", ["Jon", "Jonas"]),
    ("Mic", "Michée", ["Mi", "Michee"]),
    ("Nah", "Nahum", ["Na", "Nah"]),
    ("Hab", "Habakuk", ["Hab", "Hb"]),
    ("Zeph", "Sophonie", ["So", "Soph", "Sop"]),
    ("Hag", "Aggée", ["Ag", "Hag", "Aggee"]),
    ("Zech", "Zacharie", ["Za", "Zech", "Zac"]),
    ("Mal", "Malachie", ["Mal", "Ml"]),
    ("Matt", "Matthieu", ["Mt", "Mat"]),
    ("Mark", "Marc", ["Mc", "Mar", "Mrc"]),
    ("Luke", "Luc", ["Lu", "Lc"]),
    ("John", "Jean", ["Jn", "Jea"]),
    ("Acts", "Actes", ["Ac", "Act"]),
    ("Rom", "Romains", ["Rm", "Ro", "Rom"]),
    ("1Cor", "1 Corinthiens", ["1 Cor", "1Co", "1 Co"]),
    ("2Cor", "2 Corinthiens", ["2 Cor", "2Co", "2 Co"]),
    ("Gal", "Galates", ["Ga", "Gal"]),
    ("Eph", "Éphésiens", ["Ép", "Ep", "Eph"]),
    ("Phil", "Philippiens", ["Ph", "Phil", "Php"]),
    ("Col", "Colossiens", ["Col", "Co"]),
    ("1Thess", "1 Thessaloniciens", ["1 Thess", "1Th", "1 Th"]),
    ("2Thess", "2 Thessaloniciens", ["2 Thess", "2Th", "2 Th"]),
    ("1Tim", "1 Timothée", ["1 Tim", "1Ti", "1 Ti"]),
    ("2Tim", "2 Timothée", ["2 Tim", "2Ti", "2 Ti"]),
    ("Titus", "Tite", ["Tt", "Tit", "Tite"]),
    ("Phlm", "Philémon", ["Phm", "Phlm", "Philemon"]),
    ("Heb", "Hébreux", ["Hé", "He", "Heb"]),
    ("Jas", "Jacques", ["Jc", "Ja", "Jac", "Jas"]),
    ("1Pet", "1 Pierre", ["1 Pi", "1Pi", "1 P"]),
    ("2Pet", "2 Pierre", ["2 Pi", "2Pi", "2 P"]),
    ("1John", "1 Jean", ["1 Jn", "1Jn", "1 Jean"]),
    ("2John", "2 Jean", ["2 Jn", "2Jn", "2 Jean"]),
    ("3John", "3 Jean", ["3 Jn", "3Jn", "3 Jean"]),
    ("Jude", "Jude", ["Jude", "Jud"]),
    ("Rev", "Apocalypse", ["Ap", "Apo", "Apoc"]),
]


def _sans_accents(texte: str) -> str:
    """
    Forme décomposée sans diacritiques (comparaison
    insensible aux accents : « Ésaïe » = « Esaie »).
    """

    decompose = unicodedata.normalize(
        "NFD",
        texte
    )

    return "".join(
        caractere
        for caractere in decompose
        if not unicodedata.combining(caractere)
    )


#
# Index des livres : clef de correspondance (minuscule,
# sans accents) -> (osis_id, nom canonique).
#

_INDEX_LIVRES = {}

for _osis, _nom, _variantes in _TABLE_LIVRES:

    _INDEX_LIVRES[
        _sans_accents(_nom).lower()
    ] = (_osis, _nom)

    for _variante in _variantes:

        _cle = _sans_accents(_variante).lower()

        # Le nom canonique prime sur les variantes.
        if _cle not in _INDEX_LIVRES:
            _INDEX_LIVRES[_cle] = (_osis, _nom)


@dataclass
class ReferenceBiblique:
    """
    Une référence biblique : livre, chapitre, verset
    de début et de fin (égaux pour une référence
    ponctuelle ; ``verset_fin`` = None pour une
    référence de chapitre entier).
    """

    livre: str
    osis_id: str
    chapitre: int
    verset_debut: int = None
    verset_fin: int = None

    def __str__(self):

        if self.verset_debut is None:
            return f"{self.livre} {self.chapitre}"

        if self.verset_fin == self.verset_debut:
            return (
                f"{self.livre} {self.chapitre}."
                f"{self.verset_debut}"
            )

        return (
            f"{self.livre} {self.chapitre}."
            f"{self.verset_debut}-{self.verset_fin}"
        )

    @property
    def cle(self) -> tuple:
        """
        Clé de comparaison livre + chapitre (une
        complétion « Luc 15 » -> « Luc 15.11-32 »
        n'est ni un ajout ni une perte).
        """

        return (self.osis_id, self.chapitre)


#
# Parsing des références : alternance livre +
# chapitre [. versets] dans le format français.
#

_MOTIF_LIVRES = "|".join(
    sorted(
        (
            re.escape(_sans_accents(nom).lower())
            for nom in _INDEX_LIVRES
        ),
        key=len,
        reverse=True,
    )
)

_MOTIF_REFERENCE = re.compile(
    r"(?<![\wÀ-ÿ])"
    rf"(?P<livre>(?:{_MOTIF_LIVRES}))"
    r"(?:[.\s]+(?P<chapitre>\d{1,3}))?"
    r"(?:\s*(?:[.:;,]|\bversets?\b|\bv[.\s]|\bvs[.\s])\s*"
    r"(?P<verset>\d{1,3}))?"
    r"(?:\s*(?:[-–—]|\ba\b|\bet\b)\s*"
    r"(?P<fin>\d{1,3}))?",
    flags=re.IGNORECASE,
)


def extraire_references(texte: str) -> list:
    """
    Références bibliques d'un texte libre (insensible
    à la casse et aux accents), dans l'ordre
    d'apparition. Une occurrence de nom de livre sans
    numéro n'est PAS une référence (le mot « job »
    ou « actes » du langage courant ne doit pas
    déclencher) : le chapitre est requis.
    """

    if not texte:
        return []

    references = []

    normalise = _sans_accents(texte)

    for occurrence in _MOTIF_REFERENCE.finditer(
        normalise
    ):

        groupes = occurrence.groupdict()

        chapitre = groupes.get("chapitre")

        if not chapitre:
            continue

        cle = occurrence.group("livre").lower()

        osis_id, nom = _INDEX_LIVRES.get(
            cle,
            (None, None)
        )

        if osis_id is None:
            continue

        verset_debut = groupes.get("verset")
        verset_fin = groupes.get("fin")

        if verset_debut:

            debut = int(verset_debut)

            fin = (
                int(verset_fin)
                if verset_fin
                else debut
            )

            references.append(
                ReferenceBiblique(
                    livre=nom,
                    osis_id=osis_id,
                    chapitre=int(chapitre),
                    verset_debut=debut,
                    verset_fin=fin,
                )
            )

        else:

            references.append(
                ReferenceBiblique(
                    livre=nom,
                    osis_id=osis_id,
                    chapitre=int(chapitre),
                )
            )

    return references


def normaliser_reference(texte: str):
    """
    Normalise une référence en texte canonique
    (« genèse 2 verset 4 à 6 » -> « Genèse 2.4-6 ») ;
    None si aucune référence n'est trouvée.
    """

    references = extraire_references(texte)

    if not references:
        return None

    return str(references[0])


#
# Chargement OSIS XML.
#
# Deux styles de versets coexistent dans les
# modules réels (CrossWire) :
# - conteneurs : <verse osisID="Gen 1.1">texte…</verse> ;
# - milestones : <verse sID="Gen.1.1"/>texte…<verse eID="Gen.1.1"/>
#   (le texte VIT ENTRE les deux marqueurs ; les modules
#   FreJND/FreBPC de la Darby utilisent ce style — un
#   lecteur naïf n'y verrait que des éléments vides).
#

_EXCLUS_TEXTE = ("note", "title")


def _nom_local(tag: str) -> str:
    """
    Nom local d'un tag XML (sans l'éventuel espace
    de noms OSIS — les modules réels utilisent
    bibletechnologies.net/2003, le synthétique
    crosswire.org, les deux sont acceptés).
    """

    return tag.rsplit("}", 1)[-1]


def _texte_verse(element) -> str:
    """
    Texte d'un élément <verse> CONTENEUR : le texte
    de l'élément et de ses enfants, en excluant les
    <note> et <title> (apparats et renvois).
    """

    morceaux = []

    if element.text:
        morceaux.append(element.text)

    for enfant in element:

        if _nom_local(enfant.tag) not in _EXCLUS_TEXTE:
            morceaux.append(
                "".join(enfant.itertext())
            )

        if enfant.tail:
            morceaux.append(enfant.tail)

    return "".join(morceaux).strip()


def _nettoyer_texte(morceaux: list) -> str:
    """
    Assemble et nettoie le texte d'un verset :
    espaces insécables (y compris fine) ramenées à
    l'espace, espaces multiples resserrées.
    """

    texte = "".join(morceaux)

    texte = texte.replace("\xa0", " ")
    texte = texte.replace("\u202f", " ")

    return " ".join(texte.split()).strip()


def _identifiants_verset(identifiant: str):
    """
    Décompose un osisID (« Gen 1.1 » ou « Gen.1.1 »)
    en (osis_id, chapitre, verset) ; None si
    illisible.
    """

    parties = re.split(
        r"[ .]",
        (identifiant or "").strip()
    )

    if len(parties) < 3:
        return None

    try:
        return (
            parties[0],
            int(parties[1]),
            int(parties[2]),
        )
    except ValueError:
        return None


def _stocker_verset(
    versets: dict,
    identifiant: str,
    morceaux: list
) -> None:
    """
    Range le texte d'un verset dans l'index
    (ignore silencieusement les identifiants
    illisibles et les textes vides).
    """

    identifiants = _identifiants_verset(identifiant)

    if identifiants is None:
        return

    osis_id, chapitre, numero = identifiants

    texte = _nettoyer_texte(morceaux)

    if not texte:
        return

    versets.setdefault(
        osis_id,
        {}
    ).setdefault(
        chapitre,
        {}
    )[numero] = texte


def _parcourir_osis(
    element,
    etat: dict,
    versets: dict
) -> None:
    """
    Parcours récursif du document dans l'ordre :
    détecte les ouvertures/fermetures de versets
    milestone, collecte le texte entre elles (hors
    notes et titres), et traite aussi les versets
    conteneurs.
    """

    for enfant in element:

        local = _nom_local(enfant.tag)

        if local == "verse":

            sid = enfant.get("sID")
            eid = enfant.get("eID")

            if sid:

                #
                # Ouverture milestone : le texte du
                # verset commence par le tail du
                # marqueur d'ouverture.
                #
                if etat["id"] is not None:
                    _stocker_verset(
                        versets,
                        etat["id"],
                        etat["morceaux"]
                    )

                etat["id"] = (
                    enfant.get("osisID") or sid
                )
                etat["morceaux"] = []

                if enfant.tail:
                    etat["morceaux"].append(
                        enfant.tail
                    )

            elif eid:

                #
                # Fermeture milestone.
                #
                if etat["id"] is not None:
                    _stocker_verset(
                        versets,
                        etat["id"],
                        etat["morceaux"]
                    )

                etat["id"] = None
                etat["morceaux"] = []

            else:

                #
                # Verset conteneur : texte complet de
                # l'élément (hors notes/titres).
                #
                identifiant = enfant.get("osisID")

                if identifiant:
                    _stocker_verset(
                        versets,
                        identifiant,
                        [_texte_verse(enfant)]
                    )

            continue

        if local in _EXCLUS_TEXTE:

            #
            # Note ou titre : sous-arbre ignoré, mais
            # le texte qui suit (tail) appartient au
            # verset en cours.
            #
            if (
                etat["id"] is not None
                and enfant.tail
            ):
                etat["morceaux"].append(enfant.tail)

            continue

        #
        # Élément de contenu (w, q, divineName...) :
        # son texte puis sa descendance, puis le
        # texte qui le suit.
        #
        if etat["id"] is not None:

            if enfant.text:
                etat["morceaux"].append(enfant.text)

        _parcourir_osis(enfant, etat, versets)

        if (
            etat["id"] is not None
            and enfant.tail
        ):
            etat["morceaux"].append(enfant.tail)


class BibleJND:
    """
    Bible JND en mémoire : une entrée par verset,
    indexée livre / chapitre / verset.
    """

    def __init__(self, versets: dict):

        # osis_id -> chapitre -> verset -> texte
        self.versets = versets

    def texte_verset(
        self,
        osis_id: str,
        chapitre: int,
        verset: int
    ) -> str:

        return (
            self.versets
            .get(osis_id, {})
            .get(int(chapitre), {})
            .get(int(verset), "")
        )

    def texte_reference(
        self,
        reference: ReferenceBiblique
    ) -> str:
        """
        Texte JND d'une référence : les versets de la
        plage, joints par un espace (chapitre entier
        si la référence ne précise pas de verset).
        """

        chapitre = (
            self.versets
            .get(reference.osis_id, {})
            .get(reference.chapitre, {})
        )

        if not chapitre:
            return ""

        if reference.verset_debut is None:
            numeros = sorted(chapitre)
        else:
            numeros = [
                numero
                for numero in sorted(chapitre)
                if (
                    reference.verset_debut
                    <= numero
                    <= reference.verset_fin
                )
            ]

        return " ".join(
            chapitre[numero]
            for numero in numeros
        ).strip()

    def rechercher(
        self,
        expression: str,
        limite: int = 50
    ) -> list:
        """
        Recherche d'une expression dans la Bible
        chargée (insensible à la casse et aux
        accents). Retour : liste
        ``{"reference", "texte"}``.
        """

        resultats = []

        cible = _sans_accents(expression).lower()

        if not cible:
            return resultats

        for osis_id, chapitres in self.versets.items():

            for numero_chapitre, chapitre in (
                chapitres.items()
            ):

                for numero, texte in chapitre.items():

                    if cible in _sans_accents(
                        texte
                    ).lower():

                        nom = next(
                            (
                                _nom
                                for _osis, _nom, _v
                                in _TABLE_LIVRES
                                if _osis == osis_id
                            ),
                            osis_id,
                        )

                        resultats.append({
                            "reference": (
                                f"{nom} "
                                f"{numero_chapitre}.{numero}"
                            ),
                            "texte": texte,
                        })

                        if len(resultats) >= limite:
                            return resultats

        return resultats


_BIBLE_CHARGEE = {}

_BIBLE_CHEMIN = None


def charger_bible(chemin=None) -> BibleJND:
    """
    Charge (et met en cache) la Bible JND OSIS XML.
    BibleAbsente si le fichier n'est pas installé —
    voir le README pour le téléchargement.
    """

    global _BIBLE_CHEMIN

    if chemin is None:

        if _BIBLE_CHEMIN is None:
            _BIBLE_CHEMIN = chemin_bible()

        chemin = _BIBLE_CHEMIN

    chemin = Path(chemin)

    if chemin in _BIBLE_CHARGEE:
        return _BIBLE_CHARGEE[chemin]

    if not chemin.is_file():
        raise BibleAbsente(MESSAGE_BIBLE_ABSENTE)

    racine = ET.parse(chemin).getroot()

    versets = {}

    etat = {"id": None, "morceaux": []}

    _parcourir_osis(racine, etat, versets)

    #
    # Dernier verset non refermé (fichier tronqué).
    #
    if etat["id"] is not None:
        _stocker_verset(
            versets,
            etat["id"],
            etat["morceaux"]
        )

    bible = BibleJND(versets)

    _BIBLE_CHARGEE[chemin] = bible

    return bible


def bible_disponible(chemin=None) -> bool:
    """
    La ressource JND est-elle installée ?
    """

    try:
        charger_bible(chemin)
        return True
    except BibleAbsente:
        return False
