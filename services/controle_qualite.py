# services/controle_qualite.py
"""
Contrôle qualité local (P16.4).

Feuille de route §5 — sans LLM, affiché comme
indicateurs/suggestions, **jamais de modification
automatique du texte** :

- §5.1 **rapport de longueur** : mots résultat vs
  mots source ; avertissement si le résultat dépasse
  ~120 % de la source ;
- §5.3 **interdits stylistiques** : recherche locale
  de motifs dans une liste éditable (« l'orateur »,
  « le frère », « nous avons vu que », « il convient
  de »...), stockée dans les paramètres de l'étude
  (contrat §10, controle_qualite) ;
- §5.2 **références bibliques** (P18.2) :
  références ajoutées par le résultat (suggestion
  de validation avec extrait JND — PAS une alerte :
  la complétion est voulue) et références de la
  source absentes du résultat (alerte discrète) ;
- §5.4 **citations** (P18.2) : correspondance
  citation ↔ référence avec le texte JND local ;
  écart signalé (paraphrase vs citation exacte),
  alignement sur le texte JND À LA DEMANDE
  (``aligner_citations``), jamais automatique.

La récurrence d'emphase (P20) portera sur
l'ouvrage, pas sur le bloc.
"""

import re

#
# Seuil du rapport de longueur (feuille de route
# §5.1 : avertissement si > ~120 %).
#

SEUIL_LONGUEUR_POURCENT = 120

#
# Interdits stylistiques par défaut (§5.3, liste
# éditable dans les paramètres de l'étude).
#

INTERDITS_STYLISTIQUES_DEFAUT = [
    "l'orateur",
    "le frère",
    "la sœur",
    "nous avons vu que",
    "il convient de",
    "il faut remarquer que",
]


def compter_mots(texte: str) -> int:
    """
    Nombre de mots d'un texte (séquences de
    caractères non-espaces).
    """

    if not texte:
        return 0

    return len(
        re.findall(r"\S+", texte)
    )


def rapport_longueur(
    source: str,
    resultat: str,
    seuil_pourcent: int = SEUIL_LONGUEUR_POURCENT
) -> dict:
    """
    §5.1 : rapport de longueur entre le texte source
    et le résultat ; avertissement si le résultat
    dépasse le seuil (en pourcentage de la source).

    Retourne :
    - ``mots_source``, ``mots_resultat`` ;
    - ``ratio_pourcent`` (None si source vide) ;
    - ``avertissement`` (bool) ;
    - ``message`` (libellé court pour l'UI).
    """

    mots_source = compter_mots(source)
    mots_resultat = compter_mots(resultat)

    ratio = None
    avertissement = False
    message = "Longueur : —"

    if mots_source > 0:

        ratio = round(
            100.0 * mots_resultat / mots_source
        )

        avertissement = (
            ratio > seuil_pourcent
        )

        if avertissement:
            message = (
                f"Longueur : {mots_resultat} mots "
                f"pour {mots_source} "
                f"(+{ratio - 100} %) — la reformulation "
                "est nettement plus longue que la source."
            )
        else:
            message = (
                f"Longueur : {mots_resultat} mots "
                f"pour {mots_source} ({ratio} %)."
            )

    return {
        "mots_source": mots_source,
        "mots_resultat": mots_resultat,
        "ratio_pourcent": ratio,
        "avertissement": avertissement,
        "message": message,
    }


def interdits_stylistiques(
    texte: str,
    motifs: list
) -> list:
    """
    §5.3 : recherche locale (insensible à la casse)
    des motifs interdits dans le texte.

    Retourne une liste triée par nombre
    d'occurrences décroissant :
    ``{"motif", "occurrences", "positions"}``
    (positions = index de début des occurrences).
    """

    trouves = []

    if not texte or not motifs:
        return trouves

    for motif in motifs:

        if not motif or not motif.strip():
            continue

        positions = [
            occurrence.start()
            for occurrence in re.finditer(
                re.escape(motif),
                texte,
                flags=re.IGNORECASE
            )
        ]

        if positions:
            trouves.append({
                "motif": motif,
                "occurrences": len(positions),
                "positions": positions,
            })

    trouves.sort(
        key=lambda item: item["occurrences"],
        reverse=True
    )

    return trouves


def controles_bloc(
    source: str,
    resultat: str,
    controle_qualite: dict = None,
    bible=None,
    autres_versions=None
) -> dict:
    """
    Contrôles qualité locaux d'un bloc (indicateurs
    discrets de la page Reformulation, spec UI §4) :
    longueur + interdits stylistiques + références
    bibliques et citations (P18.2).

    ``controle_qualite`` : la section
    ``controle_qualite`` des paramètres de l'étude
    (contrat §10) — liste éditable
    ``interdits_stylistiques``.

    ``bible`` : la BibleJND chargée (facultative —
    sans elle, les références sont extraites mais
    sans extrait JND ; le parsing reste local et
    gratuit).

    ``autres_versions`` : {identifiant, BibleJND}
    des AUTRES versions installées (P18.5, spec
    §4) — quand une référence est introuvable dans
    la version retenue, un éventuel texte trouvé
    dans une autre versification est proposé à la
    CONSULTATION, jamais comme décision.
    """

    controle_qualite = controle_qualite or {}

    motifs = controle_qualite.get(
        "interdits_stylistiques",
        INTERDITS_STYLISTIQUES_DEFAUT
    )

    longueur = rapport_longueur(source, resultat)

    interdits = interdits_stylistiques(
        resultat,
        motifs
    )

    if interdits:

        resume = ", ".join(
            f"« {trouve['motif']} » "
            f"(×{trouve['occurrences']})"
            for trouve in interdits
        )

        message_interdits = (
            "Interdits stylistiques : " + resume
        )

    else:

        message_interdits = (
            "Interdits stylistiques : aucun."
        )

    references = controle_references(
        source,
        resultat,
        bible=bible,
        autres_versions=autres_versions
    )

    return {
        "longueur": longueur,
        "interdits": interdits,
        "message_interdits": message_interdits,
        "references": references,
        "message_references": references["message"],
        "nb_alertes": (
            (1 if longueur["avertissement"] else 0)
            + len(interdits)
            + len(references["perdues"])
        ),
    }


#
# P18.2 — références bibliques et citations (§5.2
# et §5.4 de la feuille de route) : vérifications
# locales et gratuites, signalées seulement — jamais
# de modification automatique du texte.
#

_EXTRAIT_JND_MAX = 220

_MOTIF_CITATION = re.compile(
    r"[«“]([^»”]{10,600})[»”]"
)


def _normaliser_pour_comparaison(texte: str) -> str:
    """
    Normalisation pour la comparaison citation ↔
    texte JND : minuscules sans accents, sans
    ponctuation, espaces resserrées.
    """

    from services.jnd import _sans_accents

    if not texte:
        return ""

    nettoye = re.sub(
        r"[^\w\sÀ-ÿ]",
        " ",
        _sans_accents(texte).lower()
    )

    return re.sub(r"\s+", " ", nettoye).strip()


def controle_references(
    source: str,
    resultat: str,
    bible=None,
    autres_versions=None
) -> dict:
    """
    §5.2 : références du résultat absentes de la
    source (complétions — SUGGESTION de validation
    avec extrait JND quand la Bible est installée)
    et références de la source absentes du résultat
    (alerte discrète). §5.4 : citations entre
    guillemets associées à une référence — citation
    exacte ou écart (paraphrase) signalé.

    La comparaison des références se fait au niveau
    livre + chapitre : « Luc 15 » dans la source et
    « Luc 15.11-32 » dans le résultat n'est ni un
    ajout ni une perte — MAIS une complétion de
    numéros de versets (« Luc 15 » -> « Luc 15.11 »)
    est signalée comme référence complétée : les
    numéros ont été ajoutés, la vérification JND se
    justifie.
    """

    from services.jnd import extraire_references

    references_source = extraire_references(source)
    references_resultat = extraire_references(
        resultat
    )

    cles_source = {
        reference.cle
        for reference in references_source
    }

    cles_resultat = {
        reference.cle
        for reference in references_resultat
    }

    ajoutees = []

    for reference in references_resultat:

        if reference.cle not in cles_source:

            entree = {"reference": str(reference)}

            if bible is not None:

                texte_jnd = bible.texte_reference(
                    reference
                )

                if texte_jnd:
                    entree["extrait_jnd"] = texte_jnd[
                        :_EXTRAIT_JND_MAX
                    ]

                else:
                    entree.update(
                        _versification_autres(
                            reference,
                            autres_versions
                        )
                    )

            ajoutees.append(entree)

            continue

        #
        # Complétion de numéros de versets : la
        # source cite le chapitre sans verset, le
        # résultat précise des versets — les numéros
        # ont été ajoutés, la vérification se
        # justifie (§5.2 : suggestion, pas alerte).
        #
        if reference.verset_debut is not None:

            chapitre_sans_versets = any(
                source_ref.cle == reference.cle
                and source_ref.verset_debut is None
                for source_ref in references_source
            )

            if chapitre_sans_versets:

                entree = {
                    "reference": str(reference)
                }

                if bible is not None:

                    texte_jnd = bible.texte_reference(
                        reference
                    )

                    if texte_jnd:
                        entree["extrait_jnd"] = (
                            texte_jnd[:_EXTRAIT_JND_MAX]
                        )

                    else:
                        entree.update(
                            _versification_autres(
                                reference,
                                autres_versions
                            )
                        )

                ajoutees.append(entree)

    perdues = [
        {"reference": str(reference)}
        for reference in references_source
        if reference.cle not in cles_resultat
    ]

    citations = controle_citations(
        resultat,
        references=references_resultat,
        bible=bible,
        autres_versions=autres_versions
    )

    #
    # Message court pour l'indicateur discret de la
    # page Reformulation.
    #
    morceaux = []

    if ajoutees:

        detail = ", ".join(
            ajoutee["reference"]
            for ajoutee in ajoutees
        )

        if any(
            "extrait_jnd" in ajoutee
            for ajoutee in ajoutees
        ):
            morceaux.append(
                "Références complétées (à vérifier "
                f"face à la JND) : {detail}."
            )
        else:
            morceaux.append(
                "Références complétées : "
                f"{detail}."
            )

    if perdues:
        morceaux.append(
            "Références de la source absentes du "
            "résultat : "
            + ", ".join(
                perdue["reference"]
                for perdue in perdues
            )
            + "."
        )

    ecarts = [
        citation
        for citation in citations
        if citation["statut"] == "ecart"
    ]

    if ecarts:
        morceaux.append(
            "Citations s'écartant du texte JND : "
            + ", ".join(
                citation["reference"]
                for citation in ecarts
            )
            + "."
        )

    citations_sans_jnd = [
        citation
        for citation in citations
        if citation["statut"] == "jnd_absente"
    ]

    if citations_sans_jnd:
        morceaux.append(
            "Citations à références introuvables "
            "dans la JND : "
            + ", ".join(
                citation["reference"]
                for citation in citations_sans_jnd
            )
            + "."
        )

    #
    # Versifications différentes (P18.5, spec
    # §4) : une référence introuvable dans la
    # version retenue est une INFORMATION —
    # existerait-elle dans une autre version
    # installée ? Consultation seulement, jamais
    # de décision automatique.
    #
    versification = [
        ajoutee
        for ajoutee in ajoutees
        if ajoutee.get("autres_versifications")
    ]

    versification += [
        citation
        for citation in citations_sans_jnd
        if citation.get("autres_versifications")
    ]

    if versification:

        detail = ", ".join(
            entree["reference"]
            for entree in versification
        )

        trouvees = sorted({
            autre["version"]
            for entree in versification
            for autre in entree["autres_versifications"]
        })

        morceaux.append(
            "Référence(s) introuvable(s) dans la "
            "version retenue — autre versification ? "
            f"À consulter dans {', '.join(trouvees)} "
            f": {detail}."
        )

    message = (
        "Références : "
        + (" ; ".join(morceaux) if morceaux
           else "rien à signaler.")
    )

    if (
        ajoutees
        and bible is None
    ):
        message += (
            "  (Bible JND non installée : sans extrait "
            "de vérification — voir README.)"
        )

    return {
        "source": references_source,
        "resultat": references_resultat,
        "ajoutees": ajoutees,
        "perdues": perdues,
        "citations": citations,
        "message": message,
    }


def _versification_autres(
    reference,
    autres_versions
) -> dict:
    """
    Consultation d'une référence dans les autres
    versions installées (P18.5, spec §4) : les
    versifications différent d'une traduction à
    l'autre — un texte trouvé ailleurs est une
    information à consulter, jamais une décision
    automatique.
    """

    consultations = []

    if autres_versions:

        for identifiant, bible in (
            autres_versions.items()
        ):

            texte = bible.texte_reference(reference)

            if texte:
                consultations.append({
                    "version": identifiant,
                    "extrait": texte[:_EXTRAIT_JND_MAX],
                })

    if not consultations:
        return {}

    return {
        "autres_versifications": consultations
    }


def controle_citations(
    texte: str,
    references=None,
    bible=None,
    autres_versions=None
) -> list:
    """
    §5.4 : citations entre guillemets associées à
    une référence proche (avant ou après, dans les
    ~120 caractères). Statut :

    - ``exacte`` : citation = texte JND (au signes
      près) ;
    - ``ecart`` : paraphrase — écart signalé,
      alignement possible à la demande ;
    - ``jnd_absente`` : référence introuvable dans
      la JND (ou Bible non installée) ;
    - ``sans_reference`` : citation sans référence
      proche (non vérifiable localement).

    Retour : liste ``{"citation", "reference",
    "statut", "texte_jnd"}`` (texte_jnd seulement
    quand disponible).
    """

    from services.jnd import extraire_references

    if not texte:
        return []

    if references is None:
        references = extraire_references(texte)

    citations = []

    for occurrence in _MOTIF_CITATION.finditer(
        texte
    ):

        citation = occurrence.group(1).strip()

        #
        # Référence la plus proche (avant ou après),
        # dans une fenêtre de ~160 caractères.
        #
        reference_proche = None
        distance_min = None

        for position, reference in _positions_references(
            texte,
            references
        ):

            distance = min(
                abs(position - occurrence.start()),
                abs(position - occurrence.end()),
            )

            if distance > 160:
                continue

            if (
                distance_min is None
                or distance < distance_min
            ):
                distance_min = distance
                reference_proche = reference

        if reference_proche is None:
            citations.append({
                "citation": citation,
                "reference": None,
                "statut": "sans_reference",
            })
            continue

        entree = {
            "citation": citation,
            "reference": str(reference_proche),
            "statut": "jnd_absente",
        }

        if bible is None:
            entree["statut"] = "jnd_absente"
            citations.append(entree)
            continue

        texte_jnd = bible.texte_reference(
            reference_proche
        )

        if not texte_jnd:
            entree["statut"] = "jnd_absente"
            entree.update(
                _versification_autres(
                    reference_proche,
                    autres_versions
                )
            )
            citations.append(entree)
            continue

        entree["texte_jnd"] = texte_jnd

        if _normaliser_pour_comparaison(
            citation
        ) in _normaliser_pour_comparaison(texte_jnd):
            entree["statut"] = "exacte"
        else:
            entree["statut"] = "ecart"

        citations.append(entree)

    return citations


def _positions_references(texte: str, references):
    """
    Position approximative de chaque référence dans
    le texte (recherche du libellé canonique).
    """

    for reference in references:

        libelle = str(reference)

        position = texte.find(libelle)

        if position < 0:
            continue

        yield position, reference


def aligner_citations(
    texte: str,
    bible,
    references=None
) -> str:
    """
    §5.4 — option « aligner sur le texte JND »,
    À LA DEMANDE (jamais automatique) : chaque
    citation entre guillemets associée à une
    référence dont le texte JND est disponible et
    diffère (paraphrase) est remplacée par le texte
    JND. Les citations exactes et sans référence
    sont laissées telles quelles.
    """

    if not texte:
        return texte

    citations = controle_citations(
        texte,
        references=references,
        bible=bible
    )

    resultat = texte

    for entree in citations:

        if entree["statut"] != "ecart":
            continue

        if not entree.get("texte_jnd"):
            continue

        citation = entree["citation"]

        texte_jnd = entree["texte_jnd"].strip()

        #
        # Substitution prudente : exactement la
        # citation détectée, guillemets français.
        #
        resultat = resultat.replace(
            f"« {citation} »",
            f"« {texte_jnd} »",
            1
        )

        resultat = resultat.replace(
            f"«{citation}»",
            f"« {texte_jnd} »",
            1
        )

    return resultat


#
# P17.3 — expressions récurrentes entre réunions
# (contrôle qualité étendu : comparaison des
# formules les plus fréquentes de l'étude, à titre
# indicatif — signalement seulement, jamais de
# suggestion de remplacement, jamais de réécriture).
#

RECURRENTES_TAILLE_MIN = 3
RECURRENTES_TAILLE_MAX = 6
RECURRENTES_OCCURRENCES_MIN = 3
RECURRENTES_REUNIONS_MIN = 2
RECURRENTES_LIMITE = 30


def _normaliser_expression(texte: str) -> str:
    """
    Normalisation pour la comparaison : minuscules,
    ponctuation retirée, espaces resserrées.
    """

    if not texte:
        return ""

    nettoye = re.sub(
        r"[^\w\sÀ-ÿ']",
        " ",
        texte.lower()
    )

    return re.sub(r"\s+", " ", nettoye).strip()


def _n_grammes(texte: str, taille_min: int, taille_max: int):
    """
    Itère les n-grammes de ``taille_min`` à
    ``taille_max`` mots du texte normalisé.
    """

    mots = _normaliser_expression(texte).split(" ")

    for taille in range(taille_min, taille_max + 1):

        if len(mots) < taille:
            continue

        for debut in range(0, len(mots) - taille + 1):
            yield " ".join(mots[debut:debut + taille])


def _textes_valides_etude(etude_ouverte):
    """
    Textes validés par réunion (reformulations
    validées + résumé validé), dans l'ordre des
    réunions de l'étude.

    Retour : liste (réunion, liste de textes).
    """

    from services.decoupage import blocs_actifs

    par_reunion = []

    for reunion in etude_ouverte.etude.ordre_reunions:

        textes = []

        for bloc in blocs_actifs(etude_ouverte, reunion):

            resultat = etude_ouverte.reformulations.get(
                bloc.fid
            )

            if not resultat or not resultat.versions:
                continue

            for version in reversed(resultat.versions):

                if (
                    version.validation
                    and version.validation.statut
                    == "valide"
                ):
                    textes.append(version.texte)
                    break

        resume = etude_ouverte.resumes.get(reunion)

        if resume:

            for version in reversed(resume.versions):

                if (
                    version.validation
                    and version.validation.statut
                    == "valide"
                ):
                    textes.append(version.texte)
                    break

        if textes:
            par_reunion.append((reunion, textes))

    return par_reunion


def expressions_recurrentes(
    etude_ouverte,
    taille_min: int = RECURRENTES_TAILLE_MIN,
    taille_max: int = RECURRENTES_TAILLE_MAX,
    occurrences_min: int = RECURRENTES_OCCURRENCES_MIN,
    reunions_min: int = RECURRENTES_REUNIONS_MIN,
    limite: int = RECURRENTES_LIMITE
) -> list:
    """
    P17.3 : formules les plus fréquentes de l'étude,
    comparées entre réunions — gratuit, sans LLM,
    signalement indicatif seulement.

    Une expression est signalée quand elle apparaît
    au moins ``occurrences_min`` fois dans au moins
    ``reunions_min`` réunions (le vocabulaire du
    thème de l'étude ressort inévitablement : le
    filtre sur les réunions concentre le rapport sur
    les tics de reformulation).

    Retour : liste triée
    ``{"expression", "occurrences", "reunions"}``,
    limitée à ``limite`` entrées.
    """

    occurrences = {}
    reunions_par_expression = {}

    for reunion, textes in _textes_valides_etude(
        etude_ouverte
    ):

        compte_reunion = {}

        for texte in textes:

            for gram in _n_grammes(
                texte,
                taille_min,
                taille_max
            ):

                compte_reunion[gram] = (
                    compte_reunion.get(gram, 0) + 1
                )

        for gram, total in compte_reunion.items():

            occurrences[gram] = (
                occurrences.get(gram, 0) + total
            )

            reunions_par_expression.setdefault(
                gram,
                set()
            ).add(reunion)

    candidates = []

    for expression, total in occurrences.items():

        reunions = reunions_par_expression[expression]

        if (
            total >= occurrences_min
            and len(reunions) >= reunions_min
        ):
            candidates.append({
                "expression": expression,
                "occurrences": total,
                "reunions": sorted(reunions),
            })

    candidates.sort(
        key=lambda item: (
            -item["occurrences"],
            item["expression"]
        )
    )

    return candidates[:limite]
