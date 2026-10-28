# tests/unit/test_p18_5.py
"""
Tests P18.5 — téléchargeur de Bibles intégré,
version retenue par étude, gestion des
versifications (spec BIBLE_JND_V2_2026-10-28b.md,
fait autorité ; skill v19/v20).

Règles d'invariance de la spec §5 :

1. un fichier Bible ne vit JAMAIS dans le dépôt
   git ni dans un dossier d'étude ;
2. une étude existante sans bloc ``bible``
   s'ouvre sans migration et utilise le défaut
   (darbyR) ;
3. le contrôle qualité travaille TOUJOURS contre
   la version retenue par l'étude ;
4. un téléchargement interrompu (réseau ou
   annulation) ne laisse AUCUN fichier partiel ;
5. changer la version retenue ne re-traite rien
   automatiquement.

Plus : validation minimale des fichiers (§2.6),
import manuel (§2.4), écart de versification =
information consultable, jamais une décision (§4).
"""

import io
import json
import os
import subprocess
import zipfile
from pathlib import Path

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

import pytest

from services.bibles import (
    ErreurBible,
    VERSIONS_BIBLE,
    VERSION_BIBLE_DEFAUT,
    bible_de_l_etude,
    autres_versions_installees,
    chemin_version,
    installer_fichier,
    telecharger_bible,
    valider_fichier_bible,
    version_bible_etude,
    version_installee,
)
from services.controle_qualite import (
    controle_references,
)
from services.jnd import charger_bible


#
# Extraits OSIS fictifs (versets réels tronqués
# pour le test ; milestone et conteneur).
#

OSIS_DARBY = """<?xml version="1.0" encoding="UTF-8"?>
<osis xmlns="http://www.crosswire.org/OSIS/namespace">
  <osisText osisIDWork="JND">
    <div type="book" osisID="Gen">
      <chapter osisID="Gen 1">
        <verse osisID="Gen 1.1">Au commencement, Dieu créa les cieux et la terre.</verse>
      </chapter>
      <chapter osisID="Gen 2">
        <verse sID="Gen 2.4"/>
        Voici les origines des cieux et de la terre.
        <verse eID="Gen 2.4"/>
      </chapter>
    </div>
    <div type="book" osisID="John">
      <chapter osisID="John 8">
        <verse osisID="John 8.1">Et Jésus s'en alla sur la montagne des oliviers.</verse>
        <verse osisID="John 8.2">Et le matin, il revint au temple.</verse>
      </chapter>
    </div>
  </osisText>
</osis>
"""

#
# La révisée : mêmes livres, mais Jean 8.1
# n'existe pas ici (versification différente).
#

OSIS_DARBYR = """<?xml version="1.0" encoding="UTF-8"?>
<osis xmlns="http://www.crosswire.org/OSIS/namespace">
  <osisText osisIDWork="JNDR">
    <div type="book" osisID="Gen">
      <chapter osisID="Gen 1">
        <verse osisID="Gen 1.1">Au commencement, Dieu créa les cieux et la terre.</verse>
      </chapter>
    </div>
    <div type="book" osisID="John">
      <chapter osisID="John 8">
        <verse osisID="John 8.2">Et le matin, il revint au temple.</verse>
      </chapter>
    </div>
  </osisText>
</osis>
"""


@pytest.fixture
def dossier(tmp_path):

    dossier = tmp_path / "bibles"

    dossier.mkdir()

    return dossier


@pytest.fixture
def bibles_installees(dossier):
    """
    Deux versions fictives installées dans un
    dossier injectable : la Darby (avec Jean 8.1)
    et la révisée (sans Jean 8.1).
    """

    (dossier / "Darby.osis.xml").write_text(
        OSIS_DARBY,
        encoding="utf-8"
    )

    (dossier / "DarbyR.osis.xml").write_text(
        OSIS_DARBYR,
        encoding="utf-8"
    )

    return dossier


def _ecrire_osis(chemin, contenu=OSIS_DARBY):

    chemin.write_text(contenu, encoding="utf-8")

    return chemin


#
# ============================================================
# Règle 1 — jamais dans le dépôt git ni dans une étude.
# ============================================================
#


class TestRegleUn:

    def test_fichiers_bible_ignores_par_git(self):

        #
        # Le dépôt ne suivra jamais un fichier Bible
        # installé (règle 1 : .gitignore, comme
        # FFmpeg).
        #
        racine = Path(__file__).parents[2]

        resultat = subprocess.run(
            [
                "git",
                "-C",
                str(racine),
                "check-ignore",
                "-q",
                "resources/bible/Darby.osis.xml",
            ],
            capture_output=True,
        )

        assert resultat.returncode == 0

    def test_installation_hors_dossier_etude(
        self,
        tmp_path,
        dossier
    ):

        from tests.unit.test_reformulation_ui import (
            construire_etude_test,
        )

        _p, _v, _e, _n = construire_etude_test(
            tmp_path
        )

        source = _ecrire_osis(
            tmp_path / "Darby.osis.xml"
        )

        installer_fichier(
            "darby",
            source,
            dossier=dossier
        )

        #
        # Le fichier vit dans le dossier des Bibles,
        # AUCUN .osis.xml n'apparaît dans l'étude.
        #
        assert chemin_version(
            "darby",
            dossier
        ).is_file()

        etude = list(
            (tmp_path / "Etude").rglob("*.osis.xml")
        )

        assert etude == []


#
# ============================================================
# Règle 2 — défaut darbyR, sans migration.
# ============================================================
#


class TestRegleDeux:

    def test_defaut_darbyR(self):

        from models.etude import ParametresEtude

        assert VERSION_BIBLE_DEFAUT == "darbyR"

        assert version_bible_etude(
            ParametresEtude()
        ) == "darbyR"

    def test_version_inconnue_retombe_sur_defaut(
        self
    ):

        from models.etude import ParametresEtude

        parametres = ParametresEtude()

        parametres.bible = {
            "version": "colombe"
        }

        assert version_bible_etude(
            parametres
        ) == "darbyR"

    def test_etude_sans_bloc_sans_migration(
        self, tmp_path
    ):
        """
        Une étude existante (sans bloc bible)
        s'ouvre sans erreur, sans migration du
        fichier, et utilise le défaut.
        """

        from services.etude_io import (
            ouvrir_etude,
        )
        from tests.unit.test_reformulation_ui import (
            construire_etude_test,
        )

        _p, _v, _e, nom = construire_etude_test(
            tmp_path
        )

        chemin = (
            tmp_path
            / "Etude"
            / "parametres"
            / "parametres.json"
        )

        data = json.loads(
            chemin.read_text(encoding="utf-8")
        )

        data.pop("bible", None)

        chemin.write_text(
            json.dumps(data, ensure_ascii=False),
            encoding="utf-8"
        )

        etude = ouvrir_etude(tmp_path / "Etude")

        assert etude.parametres.bible == {}

        assert version_bible_etude(
            etude.parametres
        ) == "darbyR"

        #
        # Aucune migration : le fichier sur disque
        # n'a pas été réécrit avec un bloc bible.
        #
        relue = json.loads(
            chemin.read_text(encoding="utf-8")
        )

        assert "bible" not in relue

    def test_schema_avec_et_sans_bloc_bible(self):

        from services.etude_schema import (
            valider_parametres,
        )
        from services.etude_io import (
            parametres_par_defaut,
        )

        data = parametres_par_defaut().to_dict()

        data.pop("bible", None)

        # Sans bloc : valide (études antérieures).
        valider_parametres(dict(data))

        # Bloc bien formé : valide.
        data["bible"] = {"version": "darby"}

        valider_parametres(data)

        # Bloc mal formé : refusé.
        data["bible"] = {"version": 1910}

        with pytest.raises(Exception):
            valider_parametres(data)


#
# ============================================================
# Règle 3 — le contrôle qualité utilise TOUJOURS la
# version de l'étude.
# ============================================================
#


class TestRegleTrois:

    def _reference(self, libelle):

        from services.jnd import (
            extraire_references,
        )

        return extraire_references(libelle)[0]

    def test_bible_de_l_etude(
        self,
        tmp_path,
        bibles_installees
    ):

        from models.etude import ParametresEtude

        parametres = ParametresEtude()

        parametres.bible = {"version": "darby"}

        bible = bible_de_l_etude(
            None,
            parametres=parametres,
            dossier=bibles_installees
        )

        reference = self._reference("Jean 8.1")

        assert bible is not None

        assert (
            bible.texte_reference(reference)
            .startswith("Et Jésus s'en alla")
        )

        #
        # La même référence n'existe pas dans la
        # révisée : c'est la version RETENUE qui
        # décide, jamais un ordre de fichiers.
        #
        parametres.bible = {"version": "darbyR"}

        bible_r = bible_de_l_etude(
            None,
            parametres=parametres,
            dossier=bibles_installees
        )

        assert bible_r is not None

        assert not bible_r.texte_reference(
            reference
        )

    def test_controle_contre_la_version_retenue(
        self, bibles_installees
    ):

        from models.etude import ParametresEtude

        parametres = ParametresEtude()

        parametres.bible = {"version": "darby"}

        bible = bible_de_l_etude(
            None,
            parametres=parametres,
            dossier=bibles_installees
        )

        resultat = controle_references(
            "Un texte sans référence.",
            "Le Seigneur l'a dit (Jean 8.1).",
            bible=bible,
        )

        ajoutee = resultat["ajoutees"][0]

        assert ajoutee["reference"] == "Jean 8.1"

        assert "extrait_jnd" in ajoutee

        assert "autres_versifications" not in (
            ajoutee
        )


#
# ============================================================
# Règle 4 — aucun fichier partiel après interruption.
# ============================================================
#


class TestRegleQuatre:

    def _contenu_dossier(self, dossier):

        return sorted(
            p.name for p in dossier.iterdir()
        )

    def test_annulation_utilisateur(
        self, dossier
    ):

        with pytest.raises(ErreurBible):

            telecharger_bible(
                "darby",
                annulation=lambda: True,
                dossier=dossier,
            )

        assert self._contenu_dossier(
            dossier
        ) == []

    def test_panne_reseau(
        self, dossier, monkeypatch
    ):

        import urllib.request

        class ReponseInterrompue:
            """
            Une réponse qui lâche au milieu du
            transfert (premier bloc servi, panne au
            suivant).
            """

            headers = {"Content-Length": "1000000"}

            def __init__(self):

                self._servi = False

            def read(self, taille):

                if not self._servi:
                    self._servi = True
                    return b"<zip incomplet"
                    # pragma: no cover

                raise OSError(
                    "connexion interrompue"
                )

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        monkeypatch.setattr(
            urllib.request,
            "urlopen",
            lambda *a, **k: ReponseInterrompue(),
        )

        with pytest.raises(ErreurBible):

            telecharger_bible(
                "darby",
                dossier=dossier,
            )

        assert self._contenu_dossier(
            dossier
        ) == []

    def test_archive_sans_osis(
        self, dossier, tmp_path, monkeypatch
    ):

        #
        # Un zip qui ne contient pas d'OSIS : refusé,
        # aucune trace.
        #
        zip_vide = tmp_path / "vide.zip"

        with zipfile.ZipFile(
            zip_vide,
            "w"
        ) as archive:
            archive.writestr(
                "lisez-moi.txt",
                "rien d'utile",
            )

        monkeypatch.setitem(
            VERSIONS_BIBLE["darby"],
            "url_zip",
            zip_vide.as_uri(),
        )

        with pytest.raises(ErreurBible):

            telecharger_bible(
                "darby",
                dossier=dossier,
            )

        assert self._contenu_dossier(
            dossier
        ) == []


#
# ============================================================
# Téléchargement nominal (file://) et import manuel.
# ============================================================
#


class TestTelechargementEtImport:

    def test_telechargement_nominal(
        self, dossier, tmp_path, monkeypatch
    ):

        zip_bible = tmp_path / "Darby-osis.zip"

        with zipfile.ZipFile(
            zip_bible,
            "w"
        ) as archive:
            archive.writestr(
                "Darby.osis.xml",
                OSIS_DARBY,
            )

        monkeypatch.setitem(
            VERSIONS_BIBLE["darby"],
            "url_zip",
            zip_bible.as_uri(),
        )

        progres = []

        chemin = telecharger_bible(
            "darby",
            progression=lambda lus, total: progres.append(
                (lus, total)
            ),
            dossier=dossier,
        )

        assert chemin.is_file()

        assert version_installee(
            "darby",
            dossier
        )

        assert progres

        #
        # Aucun partiel ni zip résiduel.
        #
        assert sorted(
            p.name for p in dossier.iterdir()
        ) == ["Darby.osis.xml"]

    def test_segond1910_import_manuel(self):

        with pytest.raises(ErreurBible) as erreur:

            telecharger_bible("segond1910")

        assert "Charger depuis un fichier" in str(
            erreur.value
        )

    def test_import_manuel_valide(
        self, tmp_path, dossier
    ):

        source = _ecrire_osis(
            tmp_path / "ma-bible.xml"
        )

        chemin = installer_fichier(
            "segond1910",
            source,
            dossier=dossier,
        )

        assert chemin == chemin_version(
            "segond1910",
            dossier
        )

        bible = charger_bible(chemin)

        assert bible.versets

    def test_import_non_osis_refuse(
        self, tmp_path, dossier
    ):

        source = tmp_path / "faux.txt"

        source.write_text(
            "ceci n'est pas de l'OSIS",
            encoding="utf-8"
        )

        with pytest.raises(ErreurBible):

            installer_fichier(
                "darby",
                source,
                dossier=dossier,
            )

        assert not chemin_version(
            "darby",
            dossier
        ).exists()

    def test_import_osis_vide_refuse(
        self, tmp_path, dossier
    ):

        osis_vide = (
            '<?xml version="1.0"?>'
            '<osis xmlns='
            '"http://www.crosswire.org/OSIS/namespace">'
            "<osisText/></osis>"
        )

        source = tmp_path / "vide.osis.xml"

        source.write_text(osis_vide, encoding="utf-8")

        ok, message = valider_fichier_bible(source)

        assert not ok

        with pytest.raises(ErreurBible):

            installer_fichier(
                "darby",
                source,
                dossier=dossier,
            )

        assert not chemin_version(
            "darby",
            dossier
        ).exists()


#
# ============================================================
# §4 — versifications différentes : information
# consultable, jamais une décision automatique.
# ============================================================
#


class TestVersifications:

    def _bibles(self, dossier):

        retenue = charger_bible(
            chemin_version("darbyR", dossier)
        )

        autres = autres_versions_installees(
            "darbyR",
            dossier,
        )

        return retenue, autres

    def test_reference_absente_de_la_version_retenue(
        self, bibles_installees
    ):

        retenue, autres = self._bibles(
            bibles_installees
        )

        assert "darby" in autres

        resultat = controle_references(
            "Un texte sans référence.",
            "Le Seigneur l'a dit (Jean 8.1).",
            bible=retenue,
            autres_versions=autres,
        )

        ajoutee = resultat["ajoutees"][0]

        assert "extrait_jnd" not in ajoutee

        autres_trouves = ajoutee[
            "autres_versifications"
        ]

        assert autres_trouves[0]["version"] == (
            "darby"
        )

        assert autres_trouves[0][
            "extrait"
        ].startswith("Et Jésus s'en alla")

        assert "autre versification" in (
            resultat["message"]
        )

    def test_citation_versification(
        self, bibles_installees
    ):

        retenue, autres = self._bibles(
            bibles_installees
        )

        resultat = controle_references(
            "Un texte sans référence.",
            "« Et Jésus s'en alla sur la montagne "
            "des oliviers » (Jean 8.1).",
            bible=retenue,
            autres_versions=autres,
        )

        citation = [
            c for c in resultat["citations"]
            if c["reference"] == "Jean 8.1"
        ][0]

        assert citation["statut"] == "jnd_absente"

        assert citation[
            "autres_versifications"
        ][0]["version"] == "darby"

        assert "autre versification" in (
            resultat["message"]
        )

    def test_sans_autres_versions_installees(
        self, bibles_installees
    ):

        #
        # Rien à consulter : l'information
        # d'écart reste honnête, sans invention.
        #
        retenue, _ = self._bibles(
            bibles_installees
        )

        resultat = controle_references(
            "Un texte sans référence.",
            "Le Seigneur l'a dit (Jean 8.1).",
            bible=retenue,
        )

        ajoutee = resultat["ajoutees"][0]

        assert "autres_versifications" not in (
            ajoutee
        )

        assert "autre versification" not in (
            resultat["message"]
        )


#
# ============================================================
# Règle 5 — changer la version ne re-traite rien.
# ============================================================
#


class TestRegleCinq:

    def test_changement_de_version_ne_retraite_rien(
        self, tmp_path
    ):

        from services.etude_io import (
            ajouter_version_reformulation,
            ouvrir_etude,
            sauvegarder_etude,
        )
        from tests.unit.test_reformulation_ui import (
            construire_etude_test,
        )

        _p, _v, etude, nom = construire_etude_test(
            tmp_path
        )

        ajouter_version_reformulation(
            etude,
            1,
            "Reformulation du premier bloc.",
            modele="mistral-test",
        )

        sauvegarder_etude(etude)

        etude.parametres.bible = {
            "version": "darby"
        }

        sauvegarder_etude(etude)

        relue = ouvrir_etude(tmp_path / "Etude")

        #
        # La nouvelle version retenue est en place.
        #
        assert version_bible_etude(
            relue.parametres
        ) == "darby"

        #
        # Les reformulations, résumés et journal
        # sont intacts : rien n'a été re-traité.
        #
        resultat = relue.reformulations.get(1)

        assert resultat is not None

        assert resultat.versions[-1].texte == (
            "Reformulation du premier bloc."
        )

        assert relue.resumes == {}

        journal = (
            tmp_path
            / "Etude"
            / "traitements"
            / "journal_operations.json"
        )

        if journal.is_file():

            contenu = journal.read_text(
                encoding="utf-8"
            )

            assert "bible" not in contenu.lower()


#
# ============================================================
# UI — onglet Bibles des réglages, déroulant des
# paramètres d'étude (spec §2, §3).
# ============================================================
#


@pytest.fixture
def qapp():

    from PySide6.QtWidgets import QApplication

    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    yield application


class TestUIBibles:

    def test_onglet_bibles_des_reglages(
        self, qapp
    ):

        from ui.settings_dialog import (
            SettingsDialog,
        )

        dialogue = SettingsDialog()

        onglets = [
            dialogue.tabs.tabText(i)
            for i in range(dialogue.tabs.count())
        ]

        assert "Bibles" in onglets

        #
        # Les trois versions du catalogue sont
        # listées ; Segond 1910 (sans URL directe)
        # n'a pas de bouton « Télécharger ».
        #
        for identifiant in VERSIONS_BIBLE:

            assert identifiant in (
                dialogue._bible_etats
            )

        assert "telecharger" in (
            dialogue._bible_boutons["darby"]
        )

        assert "telecharger" in (
            dialogue._bible_boutons["darbyR"]
        )

        assert "telecharger" not in (
            dialogue._bible_boutons["segond1910"]
        )

        assert "fichier" in (
            dialogue._bible_boutons["segond1910"]
        )

        dialogue.close()

    def test_deroulant_parametres_etude(
        self, qapp, tmp_path
    ):

        from ui.parametres_etude_dialog import (
            ParametresEtudeDialog,
        )
        from services.etude_io import (
            ouvrir_etude,
        )
        from tests.unit.test_reformulation_ui import (
            construire_etude_test,
        )

        _p, _v, _e, _n = construire_etude_test(
            tmp_path
        )

        etude = ouvrir_etude(tmp_path / "Etude")

        dialogue = ParametresEtudeDialog(etude)

        #
        # Valeur chargée = version retenue par
        # l'étude (défaut darbyR ici).
        #
        combo = dialogue.version_bible_combo

        assert combo.currentData() == "darbyR"

        combo.setCurrentIndex(
            combo.findData("darby")
        )

        dialogue.enregistrer()

        assert etude.parametres.bible == {
            "version": "darby"
        }
