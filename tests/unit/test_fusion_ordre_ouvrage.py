"""
Tests unitaires de la fusion de segmentation et de
l'ordre d'ouvrage par réunion (P14.5).

Contrats couverts :
- fusion de deux blocs adjacents : NOUVEAU FID,
  locuteurs union (multi-locuteurs si besoin),
  positions = bornes extrêmes, source =
  concaténation chronologique, fusion_de = FID
  sources ;
- FID sources passent actif: false avec
  horodatage de fin, jamais réutilisés ;
- résultats conservés (sources et fusionné) ;
- réversibilité : dé-fusion réactive les FID
  sources (mêmes discours, mêmes FID) et rend le
  FID fusionné inactif ;
- ordre d'ouvrage : défaut chronologique, liste
  réordonnable stockée en parallèle de l'ordre
  chronologique, mise à jour par fusion/dé-fusion.
"""

import json
from pathlib import Path

import pytest

from models.block import Block
from models.project import Project
from models.speaker import Speaker
from models.word import Word
from services.decoupage import (
    DecoupageError,
    blocs_actifs,
    defusionner_bloc,
    definir_ordre_ouvrage,
    fusionner_blocs,
    generer_decoupage,
    ordre_ouvrage_effectif,
    reinitialiser_ordre_ouvrage,
)
from services.etude_io import (
    ajouter_reunion,
    ajouter_version_reformulation,
    creer_etude,
    enregistrer_decoupage,
    ouvrir_etude,
    sauvegarder_etude,
)
from services.etude_schema import (
    EtudeFormatError,
    valider_decoupage,
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


def projet_trois_blocs():
    """
    Projet v1 fictif à trois blocs de diarisation :

    - bloc 1 (fid 1) : Philippe, 0.0 -> 1.0 ;
    - bloc 2 (fid 2) : Philippe, 1.0 -> 2.0 ;
    - bloc 3 (fid 3) : Daniel,   2.0 -> 3.0.
    """

    projet = Project(name="Reunion", audio_file="")

    projet.add_speaker(
        Speaker(id="speaker_0", name="Philippe")
    )

    projet.add_speaker(
        Speaker(id="speaker_1", name="Daniel")
    )

    mots = []
    blocs = []

    for index_bloc in range(3):

        speaker_id = (
            "speaker_0" if index_bloc < 2 else "speaker_1"
        )

        debut_bloc = len(mots)

        for index_mot in range(2):

            mots.append(
                Word(
                    text=(
                        f"b{index_bloc}m{index_mot}"
                        "."
                        if index_mot == 1
                        else f"b{index_bloc}m{index_mot}"
                    ),
                    start=(
                        index_bloc * 1.0
                        + index_mot * 0.5
                    ),
                    end=(
                        index_bloc * 1.0
                        + index_mot * 0.5
                        + 0.5
                    ),
                    speaker_id=speaker_id,
                    item_type="word",
                )
            )

            mots.append(
                Word(
                    text=" ",
                    start=None,
                    end=None,
                    speaker_id=speaker_id,
                    item_type="spacing",
                )
            )

        blocs.append(
            Block(
                id=index_bloc,
                speaker_id=speaker_id,
                start_word=debut_bloc,
                end_word=len(mots) - 1,
                created_by_user=False,
            )
        )

    projet.words = mots
    projet.blocks = blocs

    return projet


@pytest.fixture
def etude_avec_decoupage(tmp_path):
    """
    Étude d'une réunion, découpage généré depuis la
    diarisation (FID 1, 2, 3 dans l'ordre
    chronologique).
    """

    projet_v1 = creer_projet_v1(
        tmp_path,
        "2026-10-13_Luc1b"
    )

    etude = creer_etude(
        tmp_path / "Etude",
        "Évangile de Luc"
    )

    nom = ajouter_reunion(etude, projet_v1)

    decoupage = generer_decoupage(
        etude,
        nom,
        projet_trois_blocs()
    )

    enregistrer_decoupage(etude, decoupage)

    return etude, nom


class TestFusion:

    def test_fusion_deux_blocs(self, etude_avec_decoupage):
        etude, nom = etude_avec_decoupage

        fid_fusionne = fusionner_blocs(
            etude,
            nom,
            [1, 2]
        )

        #
        # NOUVEAU FID, jamais réutilisé.
        #
        assert fid_fusionne == 4
        assert etude.registre.prochain_fid == 5

        blocs = etude.decoupages[nom].blocs

        fusion = next(
            bloc
            for bloc in blocs
            if bloc.fid == fid_fusionne
        )

        #
        # fusion_de = FID sources, dans l'ordre
        # chronologique.
        #
        assert fusion.origine.fusion_de == [1, 2]
        assert fusion.origine.sous_decoupage is False

        #
        # Positions = bornes extrêmes des sources.
        #
        assert lire_timecode(
            fusion.positions.debut
        ) == pytest.approx(0.0)

        assert lire_timecode(
            fusion.positions.fin
        ) == pytest.approx(2.0)

        #
        # Source = concaténation chronologique.
        #
        assert fusion.source == (
            "b0m0 b0m1. b1m0 b1m1."
        )

        #
        # Locuteurs : union (ici un seul locuteur).
        #
        assert fusion.locuteurs == ["Philippe"]

        #
        # FID sources : inactifs avec horodatage de
        # fin ; bloc fusionné actif.
        #
        assert etude.registre.entrees[1].actif is False
        assert etude.registre.entrees[2].actif is False
        assert etude.registre.entrees[1].fin is not None
        assert etude.registre.entrees[2].fin is not None
        assert etude.registre.entrees[4].actif is True

        #
        # Segmentation active : le bloc fusionné
        # remplace les sources ; le bloc 3 reste.
        #
        assert [
            bloc.fid for bloc in blocs_actifs(etude, nom)
        ] == [4, 3]

        #
        # Les blocs sources restent dans le découpage
        # (mêmes discours conservés pour la
        # réversibilité).
        #
        fids_presents = {
            bloc.fid for bloc in blocs
        }

        assert fids_presents == {1, 2, 3, 4}

    def test_fusion_multi_locuteurs(self, etude_avec_decoupage):
        etude, nom = etude_avec_decoupage

        fid_fusionne = fusionner_blocs(
            etude,
            nom,
            [2, 3]
        )

        fusion = next(
            bloc
            for bloc in etude.decoupages[nom].blocs
            if bloc.fid == fid_fusionne
        )

        assert fusion.locuteurs == [
            "Philippe",
            "Daniel"
        ]

    def test_fusion_non_adjacente_refusee(self, etude_avec_decoupage):
        etude, nom = etude_avec_decoupage

        with pytest.raises(DecoupageError):
            fusionner_blocs(etude, nom, [1, 3])

    def test_fusion_fid_inconnu_refusee(self, etude_avec_decoupage):
        etude, nom = etude_avec_decoupage

        with pytest.raises(DecoupageError):
            fusionner_blocs(etude, nom, [1, 99])

    def test_fusion_fid_inactif_refusee(self, etude_avec_decoupage):
        etude, nom = etude_avec_decoupage

        fusionner_blocs(etude, nom, [1, 2])

        # Les sources (1, 2) sont inactives.
        with pytest.raises(DecoupageError):
            fusionner_blocs(etude, nom, [1, 2])

    def test_fusion_unique_refusee(self, etude_avec_decoupage):
        etude, nom = etude_avec_decoupage

        with pytest.raises(DecoupageError):
            fusionner_blocs(etude, nom, [1])

    def test_resultats_conserves(self, etude_avec_decoupage, tmp_path):
        """
        Les résultats des FID sources restent attachés
        après la fusion (règle d'invariance 2), et le
        disque reflète la fusion.
        """

        etude, nom = etude_avec_decoupage

        ajouter_version_reformulation(
            etude,
            1,
            "Reformulation du bloc 1."
        )

        ajouter_version_reformulation(
            etude,
            2,
            "Reformulation du bloc 2."
        )

        sauvegarder_etude(etude)

        reouverte = ouvrir_etude(tmp_path / "Etude")

        fid_fusionne = fusionner_blocs(
            reouverte,
            nom,
            [1, 2]
        )

        ajouter_version_reformulation(
            reouverte,
            fid_fusionne,
            "Reformulation du bloc fusionné."
        )

        sauvegarder_etude(reouverte)

        encore = ouvrir_etude(tmp_path / "Etude")

        #
        # Résultats des FID sources conservés.
        #
        assert encore.reformulations[1].versions[
            0
        ].texte == "Reformulation du bloc 1."

        assert encore.reformulations[2].versions[
            0
        ].texte == "Reformulation du bloc 2."

        #
        # Résultat du bloc fusionné présent.
        #
        assert encore.reformulations[
            fid_fusionne
        ].versions[0].texte == (
            "Reformulation du bloc fusionné."
        )

        #
        # Registre : sources inactives, fusion actif.
        #
        assert encore.registre.entrees[1].actif is False
        assert encore.registre.entrees[2].actif is False
        assert encore.registre.entrees[
            fid_fusionne
        ].actif is True


class TestDefusion:

    def test_defusion_reversible(self, etude_avec_decoupage):
        etude, nom = etude_avec_decoupage

        textes_avant = {
            bloc.fid: bloc.source
            for bloc in etude.decoupages[nom].blocs
        }

        fid_fusionne = fusionner_blocs(
            etude,
            nom,
            [1, 2]
        )

        fids_sources = defusionner_bloc(
            etude,
            nom,
            fid_fusionne
        )

        assert fids_sources == [1, 2]

        #
        # FID sources réactivés : mêmes discours,
        # mêmes FID (textes inchangés).
        #
        for fid in (1, 2):

            entree = etude.registre.entrees[fid]

            assert entree.actif is True
            assert entree.fin is None

            bloc = next(
                bloc
                for bloc in etude.decoupages[nom].blocs
                if bloc.fid == fid
            )

            assert bloc.source == textes_avant[fid]

        #
        # Le bloc fusionné est inactif, jamais
        # réutilisé.
        #
        entree = etude.registre.entrees[fid_fusionne]

        assert entree.actif is False
        assert entree.fin is not None

        #
        # Segmentation active : retour aux blocs
        # d'origine.
        #
        assert [
            bloc.fid for bloc in blocs_actifs(etude, nom)
        ] == [1, 2, 3]

    def test_defusion_resultats_conserves(
        self,
        etude_avec_decoupage,
        tmp_path
    ):
        etude, nom = etude_avec_decoupage

        fid_fusionne = fusionner_blocs(
            etude,
            nom,
            [1, 2]
        )

        ajouter_version_reformulation(
            etude,
            fid_fusionne,
            "Reformulation du bloc fusionné."
        )

        sauvegarder_etude(etude)

        reouverte = ouvrir_etude(tmp_path / "Etude")

        defusionner_bloc(
            reouverte,
            nom,
            fid_fusionne
        )

        sauvegarder_etude(reouverte)

        encore = ouvrir_etude(tmp_path / "Etude")

        #
        # Le résultat du FID fusionné reste attaché
        # au registre.
        #
        assert encore.reformulations[
            fid_fusionne
        ].versions[0].texte == (
            "Reformulation du bloc fusionné."
        )

        assert encore.registre.entrees[
            fid_fusionne
        ].actif is False

    def test_refusion_attribue_nouveau_fid(self, etude_avec_decoupage):
        """
        Le FID fusionné d'une première fusion n'est
        jamais réutilisé par une seconde.
        """

        etude, nom = etude_avec_decoupage

        premier = fusionner_blocs(etude, nom, [1, 2])

        defusionner_bloc(etude, nom, premier)

        second = fusionner_blocs(etude, nom, [1, 2])

        assert second != premier
        assert second == 5

    def test_defusion_bloc_non_fusionne_refusee(self, etude_avec_decoupage):
        etude, nom = etude_avec_decoupage

        with pytest.raises(DecoupageError):
            defusionner_bloc(etude, nom, 1)


class TestOrdreOuvrage:

    def test_defaut_chronologique(self, etude_avec_decoupage):
        etude, nom = etude_avec_decoupage

        assert ordre_ouvrage_effectif(etude, nom) == [
            1, 2, 3
        ]

        assert etude.decoupages[nom].ordre_ouvrage is None

    def test_ordre_stocke_et_persiste(self, etude_avec_decoupage, tmp_path):
        etude, nom = etude_avec_decoupage

        definir_ordre_ouvrage(etude, nom, [2, 1, 3])

        assert ordre_ouvrage_effectif(etude, nom) == [
            2, 1, 3
        ]

        sauvegarder_etude(etude)

        reouverte = ouvrir_etude(tmp_path / "Etude")

        assert ordre_ouvrage_effectif(reouverte, nom) == [
            2, 1, 3
        ]

        #
        # L'ordre chronologique (blocs) reste
        # immuable, en parallèle.
        #
        assert [
            bloc.fid
            for bloc in reouverte.decoupages[nom].blocs
        ] == [1, 2, 3]

    def test_ordre_invalide_refusee(self, etude_avec_decoupage):
        etude, nom = etude_avec_decoupage

        with pytest.raises(DecoupageError):
            definir_ordre_ouvrage(etude, nom, [1, 1, 2])

        with pytest.raises(DecoupageError):
            definir_ordre_ouvrage(etude, nom, [1, 2])

        with pytest.raises(DecoupageError):
            definir_ordre_ouvrage(etude, nom, [1, 2, 99])

    def test_ordre_fid_inactif_refusee(self, etude_avec_decoupage):
        etude, nom = etude_avec_decoupage

        fusionner_blocs(etude, nom, [1, 2])

        # Les FID 1 et 2 sont inactifs : l'ordre ne
        # peut plus les contenir.
        with pytest.raises(DecoupageError):
            definir_ordre_ouvrage(etude, nom, [1, 2, 4])

    def test_reinitialisation(self, etude_avec_decoupage, tmp_path):
        etude, nom = etude_avec_decoupage

        definir_ordre_ouvrage(etude, nom, [3, 2, 1])
        reinitialiser_ordre_ouvrage(etude, nom)

        assert ordre_ouvrage_effectif(etude, nom) == [
            1, 2, 3
        ]

        sauvegarder_etude(etude)

        reouverte = ouvrir_etude(tmp_path / "Etude")

        assert (
            reouverte.decoupages[nom].ordre_ouvrage
            is None
        )

    def test_fusion_met_a_jour_ordre_stocke(self, etude_avec_decoupage):
        etude, nom = etude_avec_decoupage

        definir_ordre_ouvrage(etude, nom, [2, 1, 3])

        fid_fusionne = fusionner_blocs(etude, nom, [1, 2])

        #
        # Le FID fusionné prend la place du premier
        # FID source de l'ordre stocké.
        #
        assert ordre_ouvrage_effectif(etude, nom) == [
            fid_fusionne,
            3
        ]

    def test_defusion_restaure_ordre_stocke(self, etude_avec_decoupage):
        etude, nom = etude_avec_decoupage

        definir_ordre_ouvrage(etude, nom, [2, 1, 3])

        fid_fusionne = fusionner_blocs(etude, nom, [1, 2])

        defusionner_bloc(etude, nom, fid_fusionne)

        assert ordre_ouvrage_effectif(etude, nom) == [
            1, 2, 3
        ]

        # L'ordre reste stocké (non remis au défaut).
        assert etude.decoupages[nom].ordre_ouvrage == [
            1, 2, 3
        ]


class TestSchemaOrdreOuvrage:

    def test_ordre_avec_fid_inconnu_refuse(self):
        with pytest.raises(EtudeFormatError):
            valider_decoupage({
                "reunion": "r",
                "blocs": [],
                "ordre_ouvrage": [7],
            })

    def test_ordre_avec_doublon_refuse(self):
        with pytest.raises(EtudeFormatError):
            valider_decoupage({
                "reunion": "r",
                "blocs": [],
                "ordre_ouvrage": [1, 1],
            })

    def test_ordre_absent_valide(self):
        valider_decoupage({
            "reunion": "r",
            "blocs": [],
        })
