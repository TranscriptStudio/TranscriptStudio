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

            from services.timecodes import (
                formater_timecode
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
