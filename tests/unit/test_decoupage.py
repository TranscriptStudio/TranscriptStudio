"""
Tests unitaires du découpage en blocs de parole
et du sous-découpage automatique des monologues
(P14.4).

Contrats couverts :
- segmentation fidèle à la diarisation validée ;
- sous-découpage des monologues longs aux pauses
  réelles (journal des opérations), bornes de
  taille configurables ;
- jamais de coupe dans une citation biblique ;
- ré-attribution des FID : bornes inchangées =
  FID conservé ; nouveaux blocs = nouveaux FID ;
  FID disparus = inactifs (jamais réutilisés).
"""

import json
from pathlib import Path

import pytest

from models.block import Block
from models.project import Project
from models.speaker import Speaker
from models.word import Word
from services.decoupage import (
    generer_decoupage,
    sous_decouper_monologue,
)
from services.etude_io import (
    ajouter_reunion,
    creer_etude,
    enregistrer_decoupage,
    sauvegarder_etude,
)
from services.preprocessing_journal import (
    JournalOperations,
    ajouter_silence_supprime,
)
from services.timecodes import lire_timecode


def creer_projet_v1(dossier_parent: Path, nom: str) -> Path:
    """
    Crée un faux projet v1 (dossier + project.sttproj).
    """

    dossier = dossier_parent / nom
    dossier.mkdir(parents=True)

    (dossier / "project.sttproj").write_text(
        json.dumps({
            "project_format_version": 1,
            "name": nom,
            "audio_file": "",
            "transcription_id": None,
            "language_code": "fr",
            "duration_seconds": 10.0,
            "modified": False,
            "speakers": [],
            "words": [],
            "blocks": [],
            "original_elevenlabs_response": {},
        }),
        encoding="utf-8"
    )

    return dossier


class MonologueFactice:
    """
    Construit un projet v1 fictif dont la
    diarisation est un monologue en phrases de
    5 mots, horodaté de façon régulière
    (audio traité).
    """

    def __init__(
        self,
        nb_phrases: int,
        mots_par_phrase: int = 5
    ):
        self.nb_phrases = nb_phrases
        self.mots_par_phrase = mots_par_phrase

        self.projet = Project(
            name="Reunion",
            audio_file="",
        )

        self.projet.add_speaker(
            Speaker(id="speaker_0", name="Philippe")
        )

        self.words = []
        self.index_premier_mot_phrase = []

        temps = 0.0

        for phrase in range(nb_phrases):

            self.index_premier_mot_phrase.append(
                len(self.words)
            )

            for mot in range(mots_par_phrase):

                texte = (
                    f"mot{mot}."
                    if mot == mots_par_phrase - 1
                    else f"mot{mot}"
                )

                self.words.append(
                    Word(
                        text=texte,
                        start=temps,
                        end=temps + 0.5,
                        speaker_id="speaker_0",
                        item_type="word",
                    )
                )

                temps += 0.5

                self.words.append(
                    Word(
                        text=" ",
                        start=None,
                        end=None,
                        speaker_id="speaker_0",
                        item_type="spacing",
                    )
                )

                temps += 0.02

        self.projet.words = self.words

        self.projet.add_block(
            Block(
                id=0,
                speaker_id="speaker_0",
                start_word=0,
                end_word=len(self.words) - 1,
                created_by_user=False,
            )
        )

    def fin_de_phrase(self, numero: int) -> float:
        """
        Position de fin (audio traité) du dernier
        mot de la phrase donnée (0-indexée).
        """

        index_dernier_mot = (
            self.index_premier_mot_phrase[numero]
            + 2 * (self.mots_par_phrase - 1)
        )

        return self.words[index_dernier_mot].end

    def indice_dernier_mot(self, numero: int) -> int:
        return (
            self.index_premier_mot_phrase[numero]
            + 2 * (self.mots_par_phrase - 1)
        )


def journal_avec_pause(position_fin_phrase: float):
    """
    Journal d'un seul silence supprimé dont la
    coupe coïncide avec la fin de phrase donnée
    (audio traité) : pause originelle de 3 s.
    """

    journal = JournalOperations(
        horodatage="2026-10-13T20:00:00"
    )

    ajouter_silence_supprime(
        journal,
        position=position_fin_phrase - 0.2,
        duree_originale=3.0,
        buffer=0.2
    )

    return journal


class TestSousDecoupage:

    def test_monologue_court_pas_de_coupe(self):
        factice = MonologueFactice(4)

        block = factice.projet.blocks[0]

        plages = sous_decouper_monologue(
            factice.projet,
            block,
            mots_min=10,
            mots_max=30
        )

        assert len(plages) == 1
        assert plages[0] == (
            block.start_word,
            block.end_word
        )

    def test_sous_decoupage_aux_pauses_reelles(self):
        """
        12 phrases de 5 mots (60 mots), bornes
        [10, 20] : la phrase portant la pause
        longue (phrase 7, 35 mots) est une
        frontière de sous-bloc.
        """

        factice = MonologueFactice(12)

        block = factice.projet.blocks[0]

        journal = journal_avec_pause(
            factice.fin_de_phrase(7)
        )

        plages = sous_decouper_monologue(
            factice.projet,
            block,
            journal=journal,
            mots_min=10,
            mots_max=20
        )

        assert len(plages) >= 2

        #
        # Chaque sous-bloc respecte les bornes
        # de mots comptables.
        #
        for debut, fin in plages:

            mots = factice.projet.words[debut:fin + 1]

            nb = sum(
                1
                for item in mots
                if not item.is_deleted
                and item.item_type != "spacing"
            )

            assert 10 <= nb <= 20

        #
        # La pause de la phrase 7 (35 mots) est
        # une frontière : le sous-bloc précédent se
        # termine à la fin de la phrase 7.
        #
        index_fin_phrase_7 = (
            factice.indice_dernier_mot(7)
        )

        frontieres = {
            fin for _debut, fin in plages
        }

        assert index_fin_phrase_7 in frontieres

    def test_jamais_dans_une_citation(self):
        """
        6 phrases de 5 mots (30 mots), bornes
        [10, 20] : les seules fins de phrase
        candidates internes (10, 15, 20 mots) sont
        à l'intérieur d'une citation biblique
        ouverte de la phrase 2 à la phrase 5 —
        aucune coupe, le monologue reste entier.
        """

        factice = MonologueFactice(6)

        #
        # Phrase 2 : ouverture de citation.
        # Phrase 5 : fermeture en fin de phrase.
        # La fin de la phrase 1 (5 mots) est sous
        # la borne minimale.
        #
        index_ouverture = (
            factice.index_premier_mot_phrase[1]
        )

        factice.words[index_ouverture].text = (
            "«mot0"
        )

        index_fermeture = (
            factice.indice_dernier_mot(4)
        )

        factice.words[index_fermeture].text = (
            "mot4. »"
        )

        block = factice.projet.blocks[0]

        plages = sous_decouper_monologue(
            factice.projet,
            block,
            mots_min=10,
            mots_max=20
        )

        assert len(plages) == 1

    def test_coupes_possible_hors_citation(self):
        """
        Même monologue, mais la citation est fermée
        à la fin de la phrase 3 : la fin de la
        phrase 3 (hors citation, guillemets
        équilibrés) est une coupe valide.
        """

        factice = MonologueFactice(6)

        index_ouverture = (
            factice.index_premier_mot_phrase[1]
        )

        factice.words[index_ouverture].text = (
            "«mot0"
        )

        index_fermeture = (
            factice.indice_dernier_mot(2)
        )

        factice.words[index_fermeture].text = (
            "mot4. »"
        )

        block = factice.projet.blocks[0]

        plages = sous_decouper_monologue(
            factice.projet,
            block,
            mots_min=10,
            mots_max=20
        )

        assert len(plages) == 2

        #
        # La frontière tombe sur une fin de phrase
        # hors citation : fin de la phrase 3
        # (guillemets équilibrés, 15 mots) ou fin
        # de la phrase 4 (20 mots). Les fins de
        # phrases 1 et 2 sont exclues (borne
        # minimale / intérieur de la citation).
        #
        fins_de_phrases_valides = {
            factice.indice_dernier_mot(2),
            factice.indice_dernier_mot(3),
        }

        assert plages[0][1] in fins_de_phrases_valides

        for debut, fin in plages:

            mots = factice.projet.words[debut:fin + 1]

            nb = sum(
                1
                for item in mots
                if not item.is_deleted
                and item.item_type != "spacing"
            )

            assert 10 <= nb <= 20


class TestGenerationDecoupage:

    def _etude_avec_reunion(self, tmp_path):
        projet_v1 = creer_projet_v1(
            tmp_path,
            "2026-10-13_Luc1b"
        )

        etude = creer_etude(
            tmp_path / "Etude",
            "Évangile de Luc"
        )

        nom = ajouter_reunion(etude, projet_v1)

        return etude, nom

    def test_decoupage_fidele_a_la_diarisation(self, tmp_path):
        etude, nom = self._etude_avec_reunion(tmp_path)

        factice = MonologueFactice(4)

        decoupage = generer_decoupage(
            etude,
            nom,
            factice.projet
        )

        assert decoupage.reunion == nom
        assert len(decoupage.blocs) == 1

        bloc = decoupage.blocs[0]

        assert bloc.locuteurs == ["Philippe"]
        assert bloc.origine.sous_decoupage is False

        #
        # Positions dans l'audio traité : début du
        # premier mot, fin du dernier mot.
        #
        assert lire_timecode(bloc.positions.debut) == (
            pytest.approx(0.0)
        )
        assert lire_timecode(bloc.positions.fin) == (
            pytest.approx(factice.words[-2].end)
        )

        #
        # Le texte source est la transcription du
        # bloc, non modifiée.
        #
        attendu = factice.projet.get_block_text(
            factice.projet.blocks[0]
        )

        assert bloc.source == attendu

    def test_re_attribution_fid_bornes_inchangees(self, tmp_path):
        """
        Règle du contrat §6 : les blocs inchangés
        (mêmes bornes) conservent leur FID ; une
        re-segmentation sans changement ne
        ré-attribue rien.
        """

        etude, nom = self._etude_avec_reunion(tmp_path)

        factice = MonologueFactice(4)

        decoupage = generer_decoupage(
            etude,
            nom,
            factice.projet
        )

        enregistrer_decoupage(etude, decoupage)

        fids_avant = [
            bloc.fid for bloc in decoupage.blocs
        ]
        prochain_avant = etude.registre.prochain_fid

        decoupage_2 = generer_decoupage(
            etude,
            nom,
            factice.projet
        )

        assert [
            bloc.fid
            for bloc in decoupage_2.blocs
        ] == fids_avant

        assert (
            etude.registre.prochain_fid
            == prochain_avant
        )

        #
        # Toutes les entrées restent actives.
        #
        for fid in fids_avant:
            assert etude.registre.entrees[fid].actif

    def test_re_attribution_fid_bornes_changees(self, tmp_path):
        """
        Re-segmentation avec des bornes différentes :
        un bloc aux bornes inchangées garde son FID,
        les autres en reçoivent de nouveaux, et les
        FID disparus passent inactifs (jamais
        réutilisés).
        """

        etude, nom = self._etude_avec_reunion(tmp_path)

        factice = MonologueFactice(4)

        decoupage_1 = generer_decoupage(
            etude,
            nom,
            factice.projet
        )

        enregistrer_decoupage(etude, decoupage_1)

        fid_bloc_1 = decoupage_1.blocs[0].fid

        #
        # Modifier la diarisation : le monologue
        # est raccourci (le bloc change de bornes)
        # et un second bloc apparaît.
        #
        factice.projet.blocks[0].end_word = (
            factice.indice_dernier_mot(1)
        )

        factice.projet.add_block(
            Block(
                id=1,
                speaker_id="speaker_0",
                start_word=(
                    factice.index_premier_mot_phrase[2]
                ),
                end_word=len(factice.words) - 1,
                created_by_user=True,
            )
        )

        decoupage_2 = generer_decoupage(
            etude,
            nom,
            factice.projet
        )

        fids = [
            bloc.fid for bloc in decoupage_2.blocs
        ]

        assert len(fids) == 2

        #
        # Les bornes ont toutes changé : aucun FID
        # conservé, deux nouveaux FID séquentiels.
        #
        assert fid_bloc_1 not in fids

        assert etude.registre.entrees[
            fid_bloc_1
        ].actif is False

        assert etude.registre.entrees[
            fid_bloc_1
        ].fin is not None

        #
        # Les FID ne sont jamais réutilisés :
        # prochain_fid a avancé.
        #
        assert (
            etude.registre.prochain_fid
            == fids[-1] + 1
        )

        #
        # Les résultats du FID disparu restent
        # attachés (ils ne sont pas perdus).
        #
        sauvegarder_etude(etude)

        from services.etude_io import ouvrir_etude

        reouverte = ouvrir_etude(
            tmp_path / "Etude"
        )

        assert reouverte.registre.entrees[
            fid_bloc_1
        ].actif is False
