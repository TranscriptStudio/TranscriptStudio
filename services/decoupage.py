# services/decoupage.py
"""
Découpage d'une réunion en blocs de parole (P14.4).

- segmentation depuis la diarisation validée du
  projet v1 (blocs = interventions) ;
- sous-découpage automatique des monologues longs
  (méditations, prédications) en blocs traitables,
  le signal principal étant la pause longue du
  discours originel, reconstituée via le journal
  des opérations de prétraitement ;
- jamais de coupe à l'intérieur d'une citation
  biblique entre guillemets ;
- ré-attribution des FID : toute re-segmentation
  attribue de nouveaux FID aux nouveaux blocs ;
  les blocs inchangés (mêmes bornes) conservent
  leur FID (contrat §6).

Le découpage est déterministe et local : aucun appel
LLM (FEUILLE_DE_ROUTE_V2.md §3.1).
"""

from models.etude import (
    BlocParole,
    DecoupageReunion,
    OrigineBloc,
    PositionsBloc,
)
from services.etude_io import (
    EtudeOuverte,
    attribuer_fid,
    marquer_fid_inactif,
    reactiver_fid,
)
from services.traitements.journal import (
    RESULTAT_SUCCES,
    TYPE_FUSION_BLOCS,
)
from services.timecodes import (
    formater_timecode,
    lire_timecode,
)
from services.preprocessing_journal import (
    JournalOperations,
    duree_originale_pause,
)

#
# Marqueurs de transition du discours : le début
# de la phrase suivante annonce un changement de
# point (liste extensible).
#

MARQUEURS_TRANSITION = (
    "ensuite",
    "enfin",
    "puis",
    "deuxième",
    "troisième",
    "quatrième",
    "en second lieu",
    "en troisième lieu",
    "autre chose",
    "pour terminer",
    "en guise de conclusion",
)

FIN_DE_PHRASE = (".", "!", "?", "…")

GUILLEMET_OUVRANT = "«"
GUILLEMET_FERMANT = "»"

#
# Bornes par défaut du sous-découpage (mots).
#

MOTS_MIN_DEFAUT = 600
MOTS_MAX_DEFAUT = 900

#
# Seuil de pause longue dans le discours originel
# (secondes) pour un point de coupe.
#

SEUIL_PAUSE_DEFAUT = 2.0


class DecoupageError(Exception):
    """
    Erreur de découpage d'une réunion.
    """

    pass


def _est_mot(item) -> bool:
    """
    Un « mot » comptable : pas un espacement,
    pas supprimé.
    """

    return (
        not item.is_deleted
        and item.item_type != "spacing"
        and item.text.strip() != ""
    )


def _compter_mots(mots) -> int:
    """
    Nombre de mots comptables d'une plage.
    """

    return sum(
        1
        for item in mots
        if _est_mot(item)
    )


def _texte_plage(projet, debut: int, fin: int) -> str:
    """
    Texte d'une plage de mots (indices inclus),
    espacements compris, mots supprimés exclus.
    """

    return "".join(
        item.text
        for item in projet.words[debut:fin + 1]
        if not item.is_deleted
    )


def _position_fin(mot):
    """
    Position de fin d'un mot (secondes, audio
    traité) ; 0 si le mot n'est pas horodaté
    (inséré).
    """

    if mot.end is None:
        return 0.0

    return float(mot.end)


def _position_debut(mot):
    """
    Position de début d'un mot (secondes, audio
    traité) ; 0 si le mot n'est pas horodaté
    (inséré).
    """

    if mot.start is None:
        return 0.0

    return float(mot.start)


def _est_dans_citation(texte_avant: str) -> bool:
    """
    Le point de coupe est-il à l'intérieur d'une
    citation biblique entre guillemets ?

    Un nombre impair de guillemets ouvrants non
    refermés signifie que la citation est ouverte.
    """

    ouverts = texte_avant.count(GUILLEMET_OUVRANT)
    fermes = texte_avant.count(GUILLEMET_FERMANT)

    return ouverts > fermes


def _phrase_suivante_commence_par_marqueur(
    mots,
    index_coupe: int
) -> bool:
    """
    Les premiers mots après le point de coupe
    annoncent-ils une transition ?
    """

    premiers_mots = []

    for item in mots[
        index_coupe:index_coupe + 6
    ]:

        if not _est_mot(item):
            continue

        premiers_mots.append(
            item.text.strip().lower()
        )

        if len(premiers_mots) >= 4:
            break

    debut_phrase = " ".join(premiers_mots)

    return any(
        debut_phrase.startswith(marqueur)
        or f" {marqueur}" in debut_phrase
        for marqueur in MARQUEURS_TRANSITION
    )


def _points_de_coupe_candidats(
    projet,
    mots,
    debut_plage: int,
    fin_plage: int,
    journal=None,
    seuil_pause: float = SEUIL_PAUSE_DEFAUT
) -> list:
    """
    Génère les points de coupe candidats d'un
    monologue, scorés.

    Un candidat est une fin de phrase (index du
    dernier mot de la phrase, la coupe se faisant
    après ce mot) :
    - jamais à l'intérieur d'une citation
      biblique (pénalité absolue) ;
    - score principal : pause longue du discours
      originel, reconstituée depuis le journal
      (le buffer conservé dans l'audio traité est
      déduit par la fonction de conversion) ;
    - complément : marqueur de transition en
      début de phrase suivante.

    Sans journal (transcription importée, projet
      antérieur), le scoring est textuel seul.

    Retourne une liste triée de tuples
    (index_coupe, score).
    """

    candidats = []

    texte_cumule = ""

    for index in range(debut_plage, fin_plage + 1):

        item = mots[index]

        texte_cumule += item.text

        if not _est_mot(item):
            continue

        texte = item.text.strip()

        if not texte.endswith(FIN_DE_PHRASE):
            continue

        #
        # Jamais dans une citation biblique.
        #
        if _est_dans_citation(texte_cumule):
            continue

        #
        # Ni la toute fin du monologue (ce n'est
        # pas un point de coupe interne).
        #
        if index >= fin_plage:
            continue

        score = 1.0

        #
        # Pause longue du discours originel.
        #
        if journal is not None:

            position_traitee = _position_fin(item)

            pause = duree_originale_pause(
                journal,
                position_traitee,
                seuil=seuil_pause
            )

            if pause is not None:
                score += 10.0 * min(pause, 10.0)

        #
        # Marqueur de transition.
        #
        if _phrase_suivante_commence_par_marqueur(
            mots,
            index + 1
        ):
            score += 5.0

        candidats.append((index, score))

    return candidats


def _selectionner_coupes(
    candidats: list,
    total_mots: int,
    mots_min: int,
    mots_max: int
) -> list:
    """
    Sélectionne les coupes par programmation
    dynamique sous contrainte de taille :
    chaque sous-bloc compte entre mots_min et
    mots_max mots (bornes configurables), en
    maximisant le score des jonctions naturelles.

    ``candidats`` : liste triée de
    (index_coute_apres_ce_mot... en mots comptés).

    Les index de coupe sont exprimés en nombre de
    mots depuis le début du monologue.

    Retourne la liste triée des index de coupe
    (nombre de mots du début du monologue), vide
    si aucune coupe n'est possible (monologue
    court ou contraintes irréalisables).
    """

    if total_mots <= mots_max:
        return []

    positions = [0] + [
        position
        for position, _score in candidats
    ] + [total_mots]

    scores = {
        position: score
        for position, score in candidats
    }

    #
    # dp[i] : meilleur score pour couvrir les
    # i premiers mots ; parent[i] : index du
    # point de coupe précédent.
    #

    dp = {0: 0.0}
    parent = {}

    for position in positions:

        for precedent, score_precedent in list(
            dp.items()
        ):

            longueur = position - precedent

            if longueur < mots_min or longueur > mots_max:
                continue

            score_total = (
                score_precedent
                + scores.get(position, 0.0)
            )

            if (
                position not in dp
                or score_total > dp[position]
            ):
                dp[position] = score_total
                parent[position] = precedent

    #
    # Chercher la meilleure fin.
    #

    fins_possibles = [
        position
        for position in dp
        if total_mots - position <= mots_max
        and total_mots - position >= mots_min
    ]

    if not fins_possibles:

        #
        # Contraintes irréalisables : repli
        # glouton (le dernier sous-bloc peut
        # dépasser la borne ; jamais de coupe
        # dans une citation).
        #

        fins_possibles = [
            position
            for position in dp
            if total_mots - position <= total_mots
        ]

    if not fins_possibles:
        return []

    meilleure_fin = max(
        fins_possibles,
        key=lambda position: dp[position]
    )

    coupes = []

    position = meilleure_fin

    while position in parent:
        coupes.append(position)
        position = parent[position]

    coupes.reverse()

    return coupes


def sous_decouper_monologue(
    projet,
    block,
    journal=None,
    mots_min: int = MOTS_MIN_DEFAUT,
    mots_max: int = MOTS_MAX_DEFAUT,
    seuil_pause: float = SEUIL_PAUSE_DEFAUT
) -> list:
    """
    Sous-découpe un monologue long en plages de
    mots (indices de début, fin inclus).

    Retourne une liste de (debut, fin) ; une
    seule plage si le monologue est court ou
    qu'aucune coupe valable n'existe.
    """

    debut_plage = block.start_word
    fin_plage = block.end_word

    mots = projet.words[debut_plage:fin_plage + 1]

    total_mots = _compter_mots(mots)

    if total_mots <= mots_max:
        return [(debut_plage, fin_plage)]

    candidats = _points_de_coupe_candidats(
        projet,
        projet.words,
        debut_plage,
        fin_plage,
        journal=journal,
        seuil_pause=seuil_pause
    )

    #
    # Les coupes sont exprimées en nombre de mots
    # depuis le début du monologue : recompter les
    # mots réels (hors espacements) avant chaque
    # candidat.
    #

    compteur = 0

    candidats_comptes = []

    for index, score in candidats:

        plage = projet.words[debut_plage:index + 1]

        nb_mots = _compter_mots(plage)

        if nb_mots < mots_min:
            continue

        if total_mots - nb_mots < mots_min:
            continue

        candidats_comptes.append(
            (nb_mots, score)
        )

    coupes = _selectionner_coupes(
        candidats_comptes,
        total_mots,
        mots_min,
        mots_max
    )

    #
    # Traduire les coupes (nombre de mots) en
    # indices de mots du projet.
    #

    if not coupes:
        return [(debut_plage, fin_plage)]

    plages = []

    index_courant = debut_plage
    mots_vus = 0

    index = debut_plage

    coupes_restantes = list(coupes)

    while index <= fin_plage:

        if _est_mot(projet.words[index]):
            mots_vus += 1

        if (
            coupes_restantes
            and mots_vus >= coupes_restantes[0]
        ):

            plages.append(
                (index_courant, index)
            )

            index_courant = index + 1
            coupes_restantes.pop(0)

        index += 1

    if index_courant <= fin_plage:
        plages.append(
            (index_courant, fin_plage)
        )

    return plages


def generer_decoupage(
    etude_ouverte: EtudeOuverte,
    nom_reunion: str,
    projet,
    journal: JournalOperations = None,
    mots_min: int = MOTS_MIN_DEFAUT,
    mots_max: int = MOTS_MAX_DEFAUT,
    seuil_pause: float = SEUIL_PAUSE_DEFAUT
) -> DecoupageReunion:
    """
    Génère (ou régénère) le découpage d'une réunion
    depuis la diarisation validée de son projet v1,
    avec sous-découpage automatique des monologues
    longs.

    Ré-attribution des FID (contrat §6) :
    - un nouveau bloc dont les bornes (positions)
      correspondent à un bloc existant de la
      réunion conserve son FID ;
    - tout autre bloc reçoit un nouveau FID (jamais
      réutilisé) ;
    - les FID des blocs disparus passent inactifs
      (ils restent au registre avec leurs
      résultats).

    Ne modifie jamais le projet v1 (règle
    d'invariance 1).
    """

    if nom_reunion not in etude_ouverte.reunions:
        raise DecoupageError(
            f"Réunion inconnue : {nom_reunion}"
        )

    ancien_decoupage = (
        etude_ouverte.decoupages.get(nom_reunion)
    )

    bornes_connues = {}

    if ancien_decoupage is not None:

        for bloc in ancien_decoupage.blocs:
            bornes_connues[
                (bloc.positions.debut, bloc.positions.fin)
            ] = bloc.fid

    blocs = []

    for block in projet.blocks:

        locuteur = (
            projet.get_speaker_by_id(block.speaker_id)
        )

        nom_locuteur = (
            locuteur.name if locuteur else "Inconnu"
        )

        plages = sous_decouper_monologue(
            projet,
            block,
            journal=journal,
            mots_min=mots_min,
            mots_max=mots_max,
            seuil_pause=seuil_pause
        )

        for debut_plage, fin_plage in plages:

            if fin_plage < debut_plage:
                continue

            mots_plage = (
                projet.words[debut_plage:fin_plage + 1]
            )

            if not mots_plage:
                continue

            #
            # Positions : premier et dernier mot
            # réellement horodaté de la plage (les
            # espacements et mots insérés ne portent
            # pas d'horodatage).
            #
            mots_horodates = [
                mot
                for mot in mots_plage
                if mot.start is not None
            ]

            if not mots_horodates:
                continue

            premiere_position = _position_debut(
                mots_horodates[0]
            )

            derniere_position = _position_fin(
                mots_horodates[-1]
            )

            positions = PositionsBloc(
                debut=formater_timecode(
                    premiere_position
                ),
                fin=formater_timecode(
                    derniere_position
                ),
            )

            sous_decoupage = (
                len(plages) > 1
            )

            bloc = BlocParole(
                fid=0,
                locuteurs=[nom_locuteur],
                positions=positions,
                source=_texte_plage(
                    projet,
                    debut_plage,
                    fin_plage
                ),
                origine=OrigineBloc(
                    fusion_de=None,
                    sous_decoupage=sous_decoupage,
                ),
            )

            fid_conserve = bornes_connues.get(
                (positions.debut, positions.fin)
            )

            if fid_conserve is not None:
                bloc.fid = fid_conserve
            else:
                bloc.fid = attribuer_fid(
                    etude_ouverte,
                    nom_reunion
                )

            blocs.append(bloc)

    #
    # FID des blocs disparus : inactifs (le FID
    # reste au registre, les résultats associés
    # aussi — règle d'invariance 2).
    #
    if ancien_decoupage is not None:

        fids_nouveaux = {
            bloc.fid for bloc in blocs
        }

        for ancien_bloc in ancien_decoupage.blocs:

            if ancien_bloc.fid not in fids_nouveaux:
                marquer_fid_inactif(
                    etude_ouverte,
                    ancien_bloc.fid
                )

    decoupage = DecoupageReunion(
        reunion=nom_reunion,
        blocs=blocs
    )

    return decoupage


#
# P14.5 — Fusion de segmentation, dé-fusion et
# ordre d'ouvrage par réunion.
#

def blocs_actifs(
    etude_ouverte: EtudeOuverte,
    nom_reunion: str
) -> list:
    """
    Blocs de la segmentation active d'une réunion :
    ceux dont le FID est actif au registre.

    Les blocs fusionnés ou disparus restent dans le
    découpage (avec leur FID inactif) pour que la
    dé-fusion restaure les mêmes discours.
    """

    decoupage = etude_ouverte.decoupages.get(
        nom_reunion
    )

    if decoupage is None:
        raise DecoupageError(
            f"Aucun découpage pour la réunion {nom_reunion}"
        )

    return [
        bloc
        for bloc in decoupage.blocs
        if etude_ouverte.registre.entrees[
            bloc.fid
        ].actif
    ]


def fusionner_blocs(
    etude_ouverte: EtudeOuverte,
    nom_reunion: str,
    fids_sources: list
) -> int:
    """
    Fusionne des blocs adjacents de la segmentation
    d'une réunion en un seul bloc de traitement
    (P14.5, feuille de route §3.1) :

    - NOUVEAU FID (jamais réutilisé) ;
    - locuteurs = union des locuteurs sources
      (multi-locuteurs si besoin) ;
    - positions = bornes extrêmes des sources ;
    - source = concaténation des textes sources
      dans l'ordre chronologique ;
    - ``origine.fusion_de`` = FID sources.

    Les FID sources passent ``actif: false`` avec
    horodatage de fin ; ils ne sont jamais
    réutilisés et leurs résultats restent attachés
    (règle d'invariance 2). Les blocs sources
    restent dans le découpage (inactifs) pour que
    la dé-fusion restaure les mêmes discours.

    L'ordre d'ouvrage stocké, s'il existe, remplace
    les FID sources par le FID fusionné.

    Retourne le FID du bloc fusionné.
    """

    decoupage = etude_ouverte.decoupages.get(
        nom_reunion
    )

    if decoupage is None:
        raise DecoupageError(
            f"Aucun découpage pour la réunion {nom_reunion}"
        )

    if not isinstance(fids_sources, list):
        raise DecoupageError(
            "Liste de FID sources attendue"
        )

    if len(fids_sources) < 2:
        raise DecoupageError(
            "La fusion porte sur deux blocs ou plus"
        )

    if len(set(fids_sources)) != len(fids_sources):
        raise DecoupageError(
            "FID sources en doublon"
        )

    par_fid = {
        bloc.fid: (index, bloc)
        for index, bloc in enumerate(decoupage.blocs)
    }

    sources = []

    for fid in fids_sources:

        if fid not in par_fid:
            raise DecoupageError(
                f"FID {fid} absent du découpage de "
                f"{nom_reunion}"
            )

        entree = etude_ouverte.registre.entrees.get(fid)

        if entree is None or not entree.actif:
            raise DecoupageError(
                f"FID {fid} inactif : seuls des blocs "
                "actifs se fusionnent"
            )

        sources.append(par_fid[fid])

    #
    # Adjacence dans l'ordre chronologique du
    # découpage : la fusion conserve un bloc de
    # traitement continu (bornes extrêmes,
    # concaténation chronologique).
    #
    indices_tries = sorted(
        index for index, _bloc in sources
    )

    if indices_tries != list(
        range(
            indices_tries[0],
            indices_tries[0] + len(indices_tries)
        )
    ):
        raise DecoupageError(
            "Les blocs à fusionner doivent être "
            "adjacents dans l'ordre chronologique"
        )

    sources_chronologiques = [
        bloc for _index, bloc in sorted(
            sources,
            key=lambda paire: paire[0]
        )
    ]

    fids_chronologiques = [
        bloc.fid for bloc in sources_chronologiques
    ]

    #
    # Positions : bornes extrêmes dans l'audio
    # traité.
    #
    debuts = [
        lire_timecode(bloc.positions.debut)
        for bloc in sources_chronologiques
    ]

    fins = [
        lire_timecode(bloc.positions.fin)
        for bloc in sources_chronologiques
    ]

    positions = PositionsBloc(
        debut=formater_timecode(min(debuts)),
        fin=formater_timecode(max(fins)),
    )

    #
    # Locuteurs : union, dans l'ordre de première
    # apparition.
    #
    locuteurs = []

    for bloc in sources_chronologiques:

        for locuteur in bloc.locuteurs:

            if locuteur not in locuteurs:
                locuteurs.append(locuteur)

    #
    # Source : concaténation dans l'ordre
    # chronologique.
    #
    texte_fusionne = " ".join(
        bloc.source
        for bloc in sources_chronologiques
    )

    nouveau_fid = attribuer_fid(
        etude_ouverte,
        nom_reunion
    )

    bloc_fusionne = BlocParole(
        fid=nouveau_fid,
        locuteurs=locuteurs,
        positions=positions,
        source=texte_fusionne,
        origine=OrigineBloc(
            fusion_de=fids_chronologiques,
            sous_decoupage=False,
        ),
    )

    #
    # Le bloc fusionné prend la place des sources
    # dans la segmentation active : il s'insère
    # après la dernière source, qui restent
    # présentes mais inactives.
    #
    index_insertion = indices_tries[-1] + 1

    decoupage.blocs.insert(
        index_insertion,
        bloc_fusionne
    )

    for fid in fids_chronologiques:
        marquer_fid_inactif(etude_ouverte, fid)

    #
    # Ordre d'ouvrage stocké : les FID sources
    # cèdent leur place au FID fusionné.
    #
    if decoupage.ordre_ouvrage is not None:

        ordre = decoupage.ordre_ouvrage

        position = next(
            (
                index
                for index, fid
                in enumerate(ordre)
                if fid in fids_chronologiques
            ),
            None
        )

        if position is None:
            position = len(ordre)

        nouvel_ordre = [
            fid
            for fid in ordre
            if fid not in fids_chronologiques
        ]

        nouvel_ordre.insert(position, nouveau_fid)

        decoupage.ordre_ouvrage = nouvel_ordre

    etude_ouverte.journal.ajouter(
        TYPE_FUSION_BLOCS,
        fid=nouveau_fid,
        reunion=nom_reunion,
        resultat=RESULTAT_SUCCES,
        message=(
            "Fusion des FID "
            + ", ".join(str(fid) for fid in fids_chronologiques)
            + f" en un bloc de traitement (FID {nouveau_fid})."
        ),
        extras={
            "fids_sources": fids_chronologiques,
        }
    )

    return nouveau_fid


def defusionner_bloc(
    etude_ouverte: EtudeOuverte,
    nom_reunion: str,
    fid_fusionne: int
) -> list:
    """
    Dé-fusionne un bloc fusionné : la fusion est
    réversible.

    - les FID sources sont réactivés (mêmes
      discours, mêmes FID : leurs blocs n'ont pas
      bougé du découpage) ;
    - le bloc fusionné quitte la segmentation
      active et son FID passe ``actif: false``
      (jamais réutilisé, résultats conservés) ;
    - l'ordre d'ouvrage stocké, s'il existe,
      remplace le FID fusionné par les FID sources
      dans l'ordre chronologique.

    Retourne les FID sources réactivés.
    """

    decoupage = etude_ouverte.decoupages.get(
        nom_reunion
    )

    if decoupage is None:
        raise DecoupageError(
            f"Aucun découpage pour la réunion {nom_reunion}"
        )

    bloc = next(
        (
            bloc
            for bloc in decoupage.blocs
            if bloc.fid == fid_fusionne
        ),
        None
    )

    if bloc is None:
        raise DecoupageError(
            f"FID {fid_fusionne} absent du découpage "
            f"de {nom_reunion}"
        )

    if not bloc.origine.fusion_de:
        raise DecoupageError(
            f"Le FID {fid_fusionne} n'est pas un "
            "bloc fusionné"
        )

    entree = etude_ouverte.registre.entrees.get(
        fid_fusionne
    )

    if entree is None or not entree.actif:
        raise DecoupageError(
            f"Le FID {fid_fusionne} est inactif : "
            "rien à dé-fusionner"
        )

    fids_sources = list(bloc.origine.fusion_de)

    par_fid = {
        bloc.fid: bloc
        for bloc in decoupage.blocs
    }

    for fid in fids_sources:

        if fid not in par_fid:
            raise DecoupageError(
                f"FID source {fid} absent du découpage : "
                "dé-fusion impossible"
            )

        entree_source = (
            etude_ouverte.registre.entrees.get(fid)
        )

        if entree_source is None:
            raise DecoupageError(
                f"FID source {fid} absent du registre"
            )

    #
    # Le bloc fusionné quitte la segmentation ; son
    # FID devient inactif (jamais réutilisé), ses
    # résultats restent attachés.
    #
    decoupage.blocs.remove(bloc)

    marquer_fid_inactif(
        etude_ouverte,
        fid_fusionne
    )

    #
    # Réactivation des sources : mêmes discours,
    # mêmes FID.
    #
    for fid in fids_sources:
        reactiver_fid(etude_ouverte, fid)

    #
    # Ordre d'ouvrage stocké : le FID fusionné
    # cède sa place aux FID sources, dans l'ordre
    # chronologique de la fusion.
    #
    if decoupage.ordre_ouvrage is not None:

        ordre = decoupage.ordre_ouvrage

        position = next(
            (
                index
                for index, fid
                in enumerate(ordre)
                if fid == fid_fusionne
            ),
            None
        )

        if position is None:
            position = len(ordre)

        nouvel_ordre = [
            fid
            for fid in ordre
            if fid != fid_fusionne
        ]

        nouvel_ordre[
            position:position
        ] = fids_sources

        decoupage.ordre_ouvrage = nouvel_ordre

    etude_ouverte.journal.ajouter(
        TYPE_FUSION_BLOCS,
        fid=fid_fusionne,
        reunion=nom_reunion,
        resultat=RESULTAT_SUCCES,
        message=(
            "Dé-fusion du bloc "
            f"{fid_fusionne} : réactivation des FID "
            + ", ".join(str(fid) for fid in fids_sources)
            + "."
        ),
        extras={
            "fids_sources": fids_sources,
            "defusion": True,
        }
    )

    return fids_sources


def ordre_ouvrage_effectif(
    etude_ouverte: EtudeOuverte,
    nom_reunion: str
) -> list:
    """
    Ordre d'ouvrage d'une réunion : ordre stocké
    s'il existe, sinon ordre chronologique des
    blocs actifs (défaut).
    """

    decoupage = etude_ouverte.decoupages.get(
        nom_reunion
    )

    if decoupage is None:
        raise DecoupageError(
            f"Aucun découpage pour la réunion {nom_reunion}"
        )

    if decoupage.ordre_ouvrage is not None:
        return list(decoupage.ordre_ouvrage)

    return [
        bloc.fid
        for bloc in blocs_actifs(
            etude_ouverte,
            nom_reunion
        )
    ]


def definir_ordre_ouvrage(
    etude_ouverte: EtudeOuverte,
    nom_reunion: str,
    fids: list
) -> None:
    """
    Définit l'ordre d'ouvrage d'une réunion :
    liste réordonnable des FID actifs, stockée en
    parallèle de l'ordre chronologique (utilisé par
    la génération d'ouvrage, P19).

    La liste doit contenir chaque bloc actif de la
    réunion exactement une fois (une permutation de
    la segmentation active).
    """

    decoupage = etude_ouverte.decoupages.get(
        nom_reunion
    )

    if decoupage is None:
        raise DecoupageError(
            f"Aucun découpage pour la réunion {nom_reunion}"
        )

    if not isinstance(fids, list):
        raise DecoupageError(
            "Liste de FID attendue"
        )

    fids_actifs = {
        bloc.fid
        for bloc in blocs_actifs(
            etude_ouverte,
            nom_reunion
        )
    }

    if len(set(fids)) != len(fids):
        raise DecoupageError(
            "Ordre d'ouvrage : doublons interdits"
        )

    if set(fids) != fids_actifs:
        raise DecoupageError(
            "Ordre d'ouvrage : la liste doit être une "
            "permutation des blocs actifs de la réunion "
            f"({sorted(fids_actifs)})"
        )

    decoupage.ordre_ouvrage = list(fids)


def reinitialiser_ordre_ouvrage(
    etude_ouverte: EtudeOuverte,
    nom_reunion: str
) -> None:
    """
    Retire l'ordre d'ouvrage stocké : la réunion
    revient à l'ordre chronologique par défaut.
    """

    decoupage = etude_ouverte.decoupages.get(
        nom_reunion
    )

    if decoupage is None:
        raise DecoupageError(
            f"Aucun découpage pour la réunion {nom_reunion}"
        )

    decoupage.ordre_ouvrage = None
