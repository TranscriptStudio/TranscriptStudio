"""
Tests P16-bis, 4ᵉ SÉRIE — progression de la
reformulation (UI_REFORMULATION_MODIFS_V2_
2026-10-30f.md §19-§23, arbitrage du 2026-10-30
au soir) :

- §19 : N ≥ 2 blocs — barre DÉTERMINÉE par
  blocs entiers, libellé « Bloc k/N —
  Reformulation en cours… », k = blocs validés ;
- §20 : temps écoulé en TOUTE circonstance
  (m:ss, h:mm:ss au-delà d'une heure),
  estimation du temps restant dès le premier
  bloc terminé, « Reformulation terminée en
  mm:ss » à la fin ;
- §21 : N = 1 — pas de barre déterminée,
  temps écoulé seul, animation indéterminée
  discrète ;
- §22 : annulation — arrêt après le bloc en
  cours, blocs déjà validés conservés, relance
  dont le décompte REPART des blocs déjà faits ;
- §23 : couleurs de la série 5 (#3b9eff /
  #2563eb), aucune teinte ardoise.

Les 5 invariants de la série sont testés
unitairement (zone de progression pilotée
directement — aucune passe LLM réelle).
"""

import os
import time
from unittest.mock import patch

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

import pytest

from PySide6.QtWidgets import (
    QApplication,
    QProgressBar,
)

from services.etude_io import ouvrir_etude
from services.settings import SettingsManager
from tests.unit.test_reformulation_ui import (
    construire_etude_test,
)


@pytest.fixture(scope="module")
def qapp():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    yield application


@pytest.fixture
def fenetre(qapp, tmp_path):
    """
    Page Reformulation d'une étude de test
    (réglages isolés, jamais la configuration
    réelle de l'utilisateur).
    """

    _p, _pv, _e, nom = (
        construire_etude_test(tmp_path)
    )

    etude = ouvrir_etude(
        tmp_path / "Etude"
    )

    from ui.reformulation_window import (
        ReformulationWindow
    )

    fen = ReformulationWindow(
        etude,
        nom,
        settings=SettingsManager(
            str(tmp_path / "reglages")
        )
    )

    yield fen

    fen.close()


#
# ==================================================
# Invariant 1 : N ≥ 2 — barre déterminée
# « Bloc k/N », k = blocs validés.
# ==================================================
#

class TestInvariant1BarreDeterminnee:

    def test_barre_par_blocs_entiers(
        self,
        fenetre
    ):
        """
        N ≥ 2 : la barre est DÉTERMINÉE (0..N),
        un PAS ENTIER par bloc terminé, libellé
        « Bloc k/N — Reformulation en cours… ».
        """

        fenetre._demarrer_zone_progression(4)

        try:

            assert isinstance(
                fenetre.progression_barre,
                QProgressBar
            )

            assert (
                fenetre.progression_barre.maximum()
                == 4
            )

            assert (
                fenetre.progression_barre.value()
                == 0
            )

            assert (
                fenetre.progression_label.text()
                == "Bloc 0/4 — "
                "Reformulation en cours…"
            )

            # Un bloc terminé : la barre avance
            # d'UN PAS ENTIER.
            fenetre.sur_progression_passe(1, 4)

            assert (
                fenetre.progression_barre.value()
                == 1
            )

            assert (
                fenetre.progression_label.text()
                == "Bloc 1/4 — "
                "Reformulation en cours…"
            )

            fenetre.sur_progression_passe(2, 4)

            assert (
                fenetre.progression_barre.value()
                == 2
            )

        finally:

            fenetre._terminer_zone_progression()

    def test_couleurs_serie_5(
        self,
        fenetre
    ):
        """
        §23 : morceau PLEIN #2563eb, lueur
        d'accent #3b9eff — aucune teinte ardoise.
        """

        style = (
            fenetre
            .progression_barre
            .styleSheet()
        )

        assert "#2563eb" in style
        assert "59,158,255" in style


#
# ==================================================
# Invariant 2 : temps écoulé en toute
# circonstance, quel que soit N.
# ==================================================
#

class TestInvariant2TempsEcoulé:

    def test_temps_affiche_pendant_toute_la_passe(
        self,
        fenetre
    ):
        """
        Le temps écoulé (m:ss, h:mm:ss au-delà
        d'une heure) est affiché dès le lancement
        et à chaque tic — pour N ≥ 2 comme pour
        N = 1.
        """

        #
        # Formats (§20).
        #
        assert (
            fenetre._formater_duree(65)
            == "1:05"
        )

        assert (
            fenetre._formater_duree(3665)
            == "1:01:05"
        )

        assert (
            fenetre._formater_duree_finale(115)
            == "01:55"
        )

        #
        # N ≥ 2 : visible dès le lancement.
        #
        fenetre._demarrer_zone_progression(3)

        try:

            assert (
                fenetre.progression_temps.text()
                .startswith(
                    "Temps écoulé : 0:0"
                )
            )

            # Une minute plus tard.
            fenetre._progression_depart = (
                time.monotonic() - 61
            )

            fenetre._maj_temps_progression()

            assert (
                fenetre.progression_temps.text()
                == "Temps écoulé : 1:01"
            )

        finally:

            fenetre._terminer_zone_progression()

        #
        # N = 1 : temps écoulé également présent.
        #
        fenetre._demarrer_zone_progression(1)

        try:

            assert (
                fenetre.progression_temps.text()
                .startswith(
                    "Temps écoulé : 0:0"
                )
            )

        finally:

            fenetre._terminer_zone_progression()

    def test_estimation_restante_des_le_premier_bloc(
        self,
        fenetre
    ):
        """
        §20 : dès qu'au moins un bloc est terminé,
        une estimation du temps restant (durée
        moyenne des blocs traités × blocs
        restants) est affichée, recalculée à
        chaque bloc.
        """

        assert (
            fenetre._formater_restant(45)
            == "~45 s restantes"
        )

        assert (
            fenetre._formater_restant(180)
            == "~3 min restantes"
        )

        fenetre._demarrer_zone_progression(4)

        try:

            # Aucun bloc terminé : pas d'estimation.
            fenetre._maj_temps_progression()

            assert not (
                fenetre
                .progression_reste
                .isVisibleTo(fenetre)
            )

            # Premier bloc : 60 secondes.
            instant = time.monotonic()

            fenetre._progression_echantillons = [
                instant
            ]

            fenetre._progression_depart = (
                instant - 60
            )

            fenetre._progression_base = 0

            fenetre._maj_temps_progression()

            # Moyenne 60 s × 3 restants = 3 min.
            assert (
                fenetre.progression_reste.text()
                == "~3 min restantes"
            )

            assert (
                fenetre
                .progression_reste
                .isVisibleTo(fenetre)
            )

        finally:

            fenetre._terminer_zone_progression()

    def test_message_final(
        self,
        fenetre
    ):
        """
        §20 : fin de traitement — « Reformulation
        terminée en mm:ss ».
        """

        fenetre._demarrer_zone_progression(2)

        fenetre._progression_depart = (
            time.monotonic() - 95
        )

        fenetre._terminer_zone_progression()

        assert (
            fenetre.progression_label.text()
            == "Reformulation terminée en 01:35"
        )


#
# ==================================================
# Invariant 3 : N = 1 — aucune barre
# déterminée ; temps écoulé + animation
# indéterminée.
# ==================================================
#

class TestInvariant3UnSeulBloc:

    def test_n_1_sans_barre_determinee(
        self,
        fenetre
    ):
        """
        N = 1 : la barre est en mode INDÉTERMINÉ
        (0,0 — pulse discret), jamais déterminée ;
        le libellé est « Reformulation en cours… »,
        le temps écoulé est affiché.
        """

        fenetre._demarrer_zone_progression(1)

        try:

            barre = fenetre.progression_barre

            assert barre.minimum() == 0
            assert barre.maximum() == 0

            assert (
                fenetre.progression_label.text()
                == "Reformulation en cours…"
            )

            assert (
                fenetre.progression_temps.text()
                .startswith("Temps écoulé :")
            )

        finally:

            fenetre._terminer_zone_progression()


#
# ==================================================
# Invariant 4 : aucune fraction plus fine que
# le bloc — jamais de pourcentage.
# ==================================================
#

class TestInvariant4PasDePourcentage:

    def test_aucun_pourcentage(
        self,
        fenetre
    ):
        """
        La barre n'affiche AUCUN texte (jamais de
        pourcentage), le libellé ne montre que des
        BLOCS ENTIERS « k/N » — jamais une
        fraction plus fine.
        """

        fenetre._demarrer_zone_progression(3)

        try:

            assert (
                fenetre
                .progression_barre
                .isTextVisible()
                is False
            )

            fenetre.sur_progression_passe(1, 3)
            fenetre.sur_progression_passe(2, 3)

            libelle = (
                fenetre
                .progression_label
                .text()
            )

            assert "%" not in libelle

            assert (
                fenetre.progression_barre.value()
                == 2
            )

            assert (
                fenetre.progression_label.text()
                == "Bloc 2/3 — "
                "Reformulation en cours…"
            )

        finally:

            fenetre._terminer_zone_progression()


#
# ==================================================
# Invariant 5 : après annulation puis relance,
# le décompte repart des blocs déjà validés.
# ==================================================
#

class TestInvariant5Reprise:

    def test_reprise_sans_perte(
        self,
        fenetre
    ):
        """
        §22 : le dénominateur du run est conservé
        après une interruption — à la relance, la
        barre et le libellé REPARTENT des blocs
        déjà faits (jamais recomptés à zéro) ; il
        est remis à zéro après une passe TERMINÉE.
        """

        # Première passe : 5 blocs, 2 traités
        # (UN événement de progression par bloc,
        # comme le worker réel), puis annulation.
        # Le dénominateur du run est posé par
        # _base_relance, comme dans
        # lancer_traitement.
        assert fenetre._base_relance(5) == 0

        fenetre._demarrer_zone_progression(5)

        fenetre.sur_progression_passe(1, 5)
        fenetre.sur_progression_passe(2, 5)

        fenetre._terminer_zone_progression(
            annulee=True
        )

        assert (
            fenetre.progression_label.text()
            == "Reformulation interrompue — "
            "2/5 bloc(s) reformulé(s)"
        )

        # Relance : 3 blocs restants — le
        # décompte repart des 2 déjà faits.
        base = fenetre._base_relance(3)

        assert base == 2

        fenetre._demarrer_zone_progression(3, base)

        try:

            assert (
                fenetre
                .progression_barre
                .maximum()
                == 5
            )

            assert (
                fenetre.progression_barre.value()
                == 2
            )

            assert (
                fenetre.progression_label.text()
                == "Bloc 2/5 — "
                "Reformulation en cours…"
            )

            fenetre.sur_progression_passe(1, 3)

            assert (
                fenetre.progression_barre.value()
                == 3
            )

            assert (
                fenetre.progression_label.text()
                == "Bloc 3/5 — "
                "Reformulation en cours…"
            )

        finally:

            fenetre._terminer_zone_progression()

        # Passe TERMINÉE : le run est clos — une
        # passe suivante repart de zéro. (Le
        # message de fin est modalisé : neutralisé
        # pour le test.)
        from services.traitements.moteur import (
            ResultatPasse
        )

        with patch(
            "ui.reformulation_window"
            ".QMessageBox.information"
        ):
            fenetre.sur_passe_terminee(
                ResultatPasse(statut="terminee")
            )

        assert (
            fenetre._base_relance(5) == 0
        )
