# tests/unit/test_p20_5_reference_cq.py
"""
P20.5 — Référence de contrôle qualité par portée
(décision David du 2026-11-09) :

(a) volet Réunion : sélecteur de la version de
    Bible persisté DANS LE TIER (repli : défaut des
    réglages de l'app) ; avertissement de
    versification ; AUCUN effet rétroactif sur les
    blocs déjà validés ;
(b) volet Ouvrage : référence d'uniformité persistée
    dans ouvrage.json, JAMAIS réécrite vers les
    tiers (§8bis du CONTRAT_STOCKAGE_REUNIONS) ; le
    badge Bible de la page Étude et celui de la page
    Ouvrage affichent la version ouvrage dès
    qu'elle est choisie.
"""

import hashlib
import json
import os
from unittest.mock import patch

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

import pytest

pytestmark = pytest.mark.qt

from PySide6.QtWidgets import QApplication

from services.etude_io import (
    ajouter_version_reformulation,
    ouvrir_etude,
    sauvegarder_etude,
    valider_version_reformulation,
)
from services.ouvrage_document import (
    charger_ouvrage,
    generer_document,
    sauvegarder_ouvrage,
)
from services.settings import SettingsManager
from tests.unit.test_p18_5 import OSIS_DARBY, OSIS_DARBYR
from tests.unit.test_reformulation_ui import (
    construire_etude_test,
    construire_projet_test,
)


@pytest.fixture(scope="module")
def qapp():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    yield application


def _hash_dossier(dossier):
    empreintes = {}

    for chemin in sorted(dossier.rglob("*")):

        if chemin.is_file():
            empreintes[str(chemin.relative_to(dossier))] = (
                hashlib.sha256(
                    chemin.read_bytes()
                ).hexdigest()
            )

    return empreintes


def _page_reunion(qapp, tmp_path):
    """
    Page Réunion rattachée à une étude, avec UN
    bloc validé (pour tester l'absence d'effet
    rétroactif).
    """

    from ui.reunion_window import ReunionWindow

    _p, _pv, etude, nom = construire_etude_test(
        tmp_path
    )

    fids = [
        e.fid
        for e in etude.registre.entrees.values()
        if e.reunion == nom
    ]

    v = ajouter_version_reformulation(
        etude,
        nom,
        fids[0],
        "Reformulation validée du bloc.",
    )

    valider_version_reformulation(
        etude,
        nom,
        fids[0],
        numero=v.numero,
        validateur="Test",
    )

    sauvegarder_etude(etude)

    etude_disco = ouvrir_etude(tmp_path / "Etude")

    fenetre = ReunionWindow(
        _pv,
        settings=SettingsManager(
            str(tmp_path / "reglages")
        ),
        etude=etude_disco,
        nom=nom,
    )

    return fenetre, etude_disco, nom, tmp_path


class TestSelecteurReunion:
    """
    P20.5a : sélecteur Bible du volet Réunion,
    persisté au tier, aucun effet rétroactif.
    """

    def test_persiste_au_tier(self, qapp, tmp_path):

        fenetre, etude_disco, nom, tmp_path = (
            _page_reunion(qapp, tmp_path)
        )

        try:

            # Version courante = darbyR (défaut).
            assert (
                fenetre._version_bible_courante()
                == "darbyR"
            )

            dossier_projet = (
                tmp_path / "2026-10-13_Luc1b"
            )

            # Empreinte des traitements AVANT.
            tier_avant = _hash_dossier(
                dossier_projet / "transcriptstudio"
            )

            with patch(
                "ui.reunion_window.QMessageBox.information"
            ) as information:

                index = fenetre.bible_select.findData(
                    "segond1910"
                )

                fenetre.bible_select.setCurrentIndex(
                    index
                )

                QApplication.processEvents()

            # Persisté au tier.
            recharge = ouvrir_etude(
                tmp_path / "Etude"
            )

            assert (
                recharge.tier_de(nom)
                .parametres.bible["version"]
                == "segond1910"
            )

            # Avertissement de versification
            # (Segond 1910 ≠ Darby).
            assert information.called

            # AUCUN effet rétroactif : les
            # traitements (reformulations validées)
            # n'ont pas bougé — seuls les paramètres
            # du tier ont changé.
            tier_apres = _hash_dossier(
                dossier_projet / "transcriptstudio"
            )

            # Seuls les paramètres du tier ont
            # changé — jamais les traitements.
            changes = {
                cle
                for cle in tier_apres
                if tier_avant.get(cle) != tier_apres.get(cle)
            }

            assert changes <= {
                "parametres" + os.sep + "parametres.json"
            }

            for cle in tier_avant:
                if (
                    cle.startswith("traitements")
                    or cle.startswith("blocs")
                ):
                    assert tier_apres[cle] == tier_avant[cle]

        finally:
            fenetre.close()

    def test_meme_versification_pas_d_avertissement(
        self,
        qapp,
        tmp_path
    ):

        fenetre, _e, _n, _t = _page_reunion(
            qapp,
            tmp_path
        )

        try:

            with patch(
                "ui.reunion_window.QMessageBox.information"
            ) as information:

                index = fenetre.bible_select.findData(
                    "darby"
                )

                fenetre.bible_select.setCurrentIndex(
                    index
                )

                QApplication.processEvents()

            # darby et darbyR partagent la
            # versification « Darby » : pas
            # d'avertissement.
            assert not information.called

        finally:
            fenetre.close()

    def test_repli_defaut_app_sans_tier(
        self,
        qapp,
        tmp_path
    ):
        """
        Repli : sans tier (réunion autonome non
        encore ouverte), le sélecteur retombe sur
        le défaut des réglages de l'app (darbyR).
        """

        from ui.reunion_window import ReunionWindow

        _projet, projet_v1 = construire_projet_test(
            tmp_path
        )

        fenetre = ReunionWindow(
            projet_v1,
            settings=SettingsManager(
                str(tmp_path / "reglages")
            ),
        )

        try:

            assert (
                fenetre._version_bible_courante()
                == "darbyR"
            )

        finally:
            fenetre.close()


class TestReferenceOuvrage:
    """
    P20.5b : référence d'uniformité au niveau
    ouvrage, persistée dans ouvrage.json, jamais
    réécrite vers les tiers ; badges.
    """

    def _page_ouvrage(self, qapp, tmp_path):

        from ui.ouvrage_window import OuvrageWindow

        _p, _pv, etude, nom = construire_etude_test(
            tmp_path
        )

        fids = [
            e.fid
            for e in etude.registre.entrees.values()
            if e.reunion == nom
        ]

        for fid in fids:

            v = ajouter_version_reformulation(
                etude,
                nom,
                fid,
                f"Pensée du bloc {fid}. En Jean 8.1, Jésus dit…",
            )

            valider_version_reformulation(
                etude,
                nom,
                fid,
                numero=v.numero,
                validateur="Test",
            )

        sauvegarder_etude(etude)

        etude_disco = ouvrir_etude(tmp_path / "Etude")

        document = generer_document(etude_disco)

        sauvegarder_ouvrage(
            document,
            etude_disco.dossier
        )

        fenetre = OuvrageWindow(
            etude_disco,
            settings=SettingsManager(
                str(tmp_path / "reglages")
            ),
        )

        return fenetre, etude_disco, tmp_path

    def test_persistee_dans_ouvrage_json(self, qapp, tmp_path):

        fenetre, etude_disco, tmp_path = (
            self._page_ouvrage(qapp, tmp_path)
        )

        try:

            dossier_projet = (
                tmp_path / "2026-10-13_Luc1b"
            )

            tier_avant = _hash_dossier(
                dossier_projet / "transcriptstudio"
            )

            # Aucune référence choisie au départ.
            assert fenetre._texte_badge_bible_ouvrage() == ""

            index = fenetre.bible_select.findData(
                "segond1910"
            )

            fenetre.bible_select.setCurrentIndex(index)

            QApplication.processEvents()

            # Persistée dans ouvrage.json.
            recharge = charger_ouvrage(
                etude_disco.dossier
            )

            assert (
                recharge.reference_bible == "segond1910"
            )

            # Badge ouvrage affiché dès le choix.
            assert (
                fenetre._texte_badge_bible_ouvrage()
                == "Bible : Segond 1910"
            )

            # JAMAIS réécrite vers les tiers (§8bis).
            tier_apres = _hash_dossier(
                dossier_projet / "transcriptstudio"
            )

            assert tier_apres == tier_avant

        finally:
            fenetre.close()

    def test_page_etude_ne_affiche_plus_la_version_ouvrage(
        self,
        qapp,
        tmp_path
    ):
        """
        P18.9-bis.c (amende P20.5) : même quand une
        version ouvrage est choisie, la page Étude
        n'affiche PLUS aucune version de Bible (la page
        Ouvrage garde son badge).
        """

        from ui.etude_window import EtudeWindow

        fenetre, etude_disco, tmp_path = (
            self._page_ouvrage(qapp, tmp_path)
        )

        try:

            fenetre.bible_select.setCurrentIndex(
                fenetre.bible_select.findData("darby")
            )

            QApplication.processEvents()

            # Badge ouvrage toujours affiché (P20.5b).
            assert (
                fenetre._texte_badge_bible_ouvrage()
                == "Bible : Darby"
            )

            page_etude = EtudeWindow(
                tmp_path / "Etude",
                settings=SettingsManager(
                    str(tmp_path / "reglages2")
                ),
            )

            try:

                # P18.9-bis.c : aucun badge Bible sur la
                # page Étude, même avec version ouvrage.
                assert not hasattr(
                    page_etude,
                    "badge_bible_label"
                )

            finally:
                page_etude.close()

        finally:
            fenetre.close()

    def test_reverifier_versets(self, qapp, tmp_path):
        """
        « Re-vérifier les versets » : contrôle local
        contre la référence d'uniformité ; écarts de
        versification = information.
        """

        fenetre, etude_disco, tmp_path = (
            self._page_ouvrage(qapp, tmp_path)
        )

        try:

            dossier_bibles = tmp_path / "bibles"
            dossier_bibles.mkdir()

            (dossier_bibles / "Darby.osis.xml").write_text(
                OSIS_DARBY,
                encoding="utf-8"
            )

            (dossier_bibles / "DarbyR.osis.xml").write_text(
                OSIS_DARBYR,
                encoding="utf-8"
            )

            from services.jnd import charger_bible

            bible_darby = charger_bible(
                dossier_bibles / "Darby.osis.xml"
            )

            bible_darbyR = charger_bible(
                dossier_bibles / "DarbyR.osis.xml"
            )

            # Référence ouvrage = darby (Jean 8.1
            # existe), contrôle contre darby.
            fenetre.bible_select.setCurrentIndex(
                fenetre.bible_select.findData("darby")
            )

            QApplication.processEvents()

            with patch(
                "services.bibles.charger_bible_version",
                lambda v, dossier=None: bible_darby,
            ), patch(
                "services.bibles.autres_versions_installees",
                lambda v, dossier=None: {"darbyR": bible_darbyR},
            ), patch(
                "ui.ouvrage_window.QMessageBox.information"
            ):

                fenetre.reverifier_versets()

            rapport = "\n".join(fenetre._versets_rapport)

            # Jean 8.1 existe dans darby : aucun
            # écart.
            assert "0 écart(s)" in rapport

            # Puis contrôle contre darbyR (Jean 8.1
            # absent) : écart = information.
            fenetre.bible_select.setCurrentIndex(
                fenetre.bible_select.findData("darbyR")
            )

            QApplication.processEvents()

            with patch(
                "services.bibles.charger_bible_version",
                lambda v, dossier=None: bible_darbyR,
            ), patch(
                "services.bibles.autres_versions_installees",
                lambda v, dossier=None: {"darby": bible_darby},
            ), patch(
                "ui.ouvrage_window.QMessageBox.information"
            ):

                fenetre.reverifier_versets()

            rapport = "\n".join(fenetre._versets_rapport)

            assert "Jean 8.1" in rapport
            assert "introuvable" in rapport
            assert "existe dans : Darby" in rapport
            assert "information" in rapport

        finally:
            fenetre.close()
