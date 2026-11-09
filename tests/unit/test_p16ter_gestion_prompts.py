"""
Tests P16-ter — gestion des prompts (spec
UI_GESTION_PROMPTS_V2_2026-10-31a.md).

Les six invariants de la spec (§6) :

1. les défauts embarqués ne sont jamais
   modifiés (la réinitialisation SEULEMENT
   supprime le fichier de bibliothèque) ;
2. bibliothèque = dossier de paramétrage,
   un usage sans fichier vaut le défaut embarqué,
   aucune lecture ne crée de fichier ;
3. la bibliothèque ne touche JAMAIS une étude
   existante (seules les nouvelles études
   héritent) ;
4. le mode étude édite la COPIE LOCALE
   uniquement ; « Promulguer » écrit le texte
   local dans le fichier bibliothèque, après
   confirmation, et rien d'autre ;
5. chaque version LLM mémorise le texte effectif
   du prompt et son hash court ; l'historique
   existant n'est pas rétroactivement modifié ;
6. l'import charge uniquement l'usage affiché et
   n'écrit rien avant « Enregistrer » ; l'export
   écrit exactement le texte de l'éditeur
   (.md/.txt) ; aucun des deux ne touche une étude.
"""

import hashlib
import json
import os

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

from pathlib import Path

import pytest

from PySide6.QtWidgets import (
    QApplication,
    QMessageBox,
)

from services.prompts import (
    PromptsError,
    USAGE_REFORMULATION,
    USAGE_RESUME,
    chemin_bibliotheque,
    ecrire_bibliotheque,
    hash_prompt,
    lire_bibliotheque,
    lire_defaut_embarque,
    reinitialiser_bibliotheque,
)
from services.etude_io import (
    ajouter_reunion,
    creer_etude,
    ouvrir_etude,
    parametres_par_defaut,
    sauvegarder_etude,
)
from services.llm.catalogue import (
    catalogue_par_defaut,
)
from services.settings import SettingsManager
from services.resources import resource_path
from tests.unit.test_moteur_traitements import (
    ClientFactice,
    fabriquer_moteur,
    creer_etude_avec_blocs,
    creer_projet_v1,
)
from tests.unit.test_resume_synthese import (
    ServiceResume,
    ClientFactice as ClientResumeFactice,
    creer_etude_reunions,
    fabriquer_service,
)


PROMPT_A = "PROMPT BIBLIOTHEQUE A — reformulation."
PROMPT_B = "PROMPT BIBLIOTHEQUE B — autre texte."


def empreinte(chemin: Path) -> str:

    return hashlib.sha256(
        chemin.read_bytes()
    ).hexdigest()


@pytest.fixture(scope="module")
def qapp():

    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    yield application


#
# Invariants 1 et 2 : défauts embarqués et
# bibliothèque du dossier de paramétrage.
#


class TestBibliotheque:

    def test_sans_fichier_vaut_defaut_embarque(
        self, tmp_path
    ):
        """
        Invariant 2 : un usage sans fichier vaut le
        défaut embarqué, et la lecture ne crée
        RIEN.
        """

        dossier = tmp_path / "prompts"

        texte, personnalise = lire_bibliotheque(
            USAGE_REFORMULATION,
            dossier
        )

        assert personnalise is False
        assert texte == lire_defaut_embarque(
            USAGE_REFORMULATION
        )

        # Aucun fichier créé, aucun dossier créé.
        assert not dossier.exists()

    def test_fichier_de_bibliotheque_prime(
        self, tmp_path
    ):

        dossier = tmp_path / "prompts"

        ecrire_bibliotheque(
            USAGE_REFORMULATION,
            PROMPT_A,
            dossier
        )

        texte, personnalise = lire_bibliotheque(
            USAGE_REFORMULATION,
            dossier
        )

        assert personnalise is True
        assert texte == PROMPT_A

        # L'autre usage reste au défaut embarqué.
        autre, personnalise_autre = (
            lire_bibliotheque(
                USAGE_RESUME,
                dossier
            )
        )

        assert personnalise_autre is False
        assert autre == lire_defaut_embarque(
            USAGE_RESUME
        )

    def test_defauts_embarques_intouches(
        self, tmp_path
    ):
        """
        Invariant 1 : écrire, réinitialiser,
        importer et exporter ne modifient JAMAIS
        les défauts embarqués de resources/prompts/.
        """

        chemin_reformulation = resource_path(
            "resources/prompts/"
            "prompt_reformulation_v2.md"
        )

        chemin_resume = resource_path(
            "resources/prompts/"
            "prompt_resume_v2.md"
        )

        avant = (
            empreinte(chemin_reformulation),
            empreinte(chemin_resume),
        )

        dossier = tmp_path / "prompts"

        ecrire_bibliotheque(
            USAGE_REFORMULATION,
            PROMPT_A,
            dossier
        )

        reinitialiser_bibliotheque(
            USAGE_REFORMULATION,
            dossier
        )

        ecrire_bibliotheque(
            USAGE_RESUME,
            PROMPT_B,
            dossier
        )

        apres = (
            empreinte(chemin_reformulation),
            empreinte(chemin_resume),
        )

        assert avant == apres

    def test_reinitialiser_supprime_le_fichier(
        self, tmp_path
    ):
        """
        Invariant 1 : « Réinitialiser » supprime le
        fichier de bibliothèque et RIEN d'autre.
        """

        dossier = tmp_path / "prompts"

        ecrire_bibliotheque(
            USAGE_REFORMULATION,
            PROMPT_A,
            dossier
        )

        chemin = chemin_bibliotheque(
            USAGE_REFORMULATION,
            dossier
        )

        assert reinitialiser_bibliotheque(
            USAGE_REFORMULATION,
            dossier
        ) is True

        assert not chemin.exists()

        # Déjà au défaut : seconde réinitialisation
        # sans effet, retour False.
        assert reinitialiser_bibliotheque(
            USAGE_REFORMULATION,
            dossier
        ) is False

        texte, personnalise = lire_bibliotheque(
            USAGE_REFORMULATION,
            dossier
        )

        assert personnalise is False
        assert texte == lire_defaut_embarque(
            USAGE_REFORMULATION
        )

    def test_usage_inconnu_refuse(self, tmp_path):

        with pytest.raises(PromptsError):
            lire_bibliotheque("inconnu", tmp_path)

        with pytest.raises(PromptsError):
            ecrire_bibliotheque(
                "inconnu",
                "texte",
                tmp_path
            )

    def test_hash_court(self):
        """
        Le hash court (8 caractères hexadécimaux,
        SHA-256) est stable, insensible aux retours
        Windows et sensible au texte.
        """

        assert len(hash_prompt(PROMPT_A)) == 8

        assert all(
            caractere in "0123456789abcdef"
            for caractere in hash_prompt(PROMPT_A)
        )

        assert hash_prompt(PROMPT_A) == (
            hash_prompt(f"\r\n{PROMPT_A}\r\n")
        )

        assert hash_prompt(PROMPT_A) != (
            hash_prompt(PROMPT_B)
        )

        assert hash_prompt("") == ""


#
# Invariant 3 : la bibliothèque hérite aux
# NOUVELLES études, jamais aux existantes.
#


class TestEtudeEtBibliotheque:

    def test_parametres_defaut_heritent(
        self, tmp_path
    ):

        dossier = tmp_path / "prompts"

        ecrire_bibliotheque(
            USAGE_REFORMULATION,
            PROMPT_A,
            dossier
        )

        parametres = parametres_par_defaut(
            dossier_prompts=dossier
        )

        assert (
            parametres.reformulation["prompt"]
            == PROMPT_A
        )

        # L'usage sans fichier reste au défaut.
        assert (
            parametres.resume["prompt"]
            == lire_defaut_embarque(USAGE_RESUME)
        )

    def test_bibliotheque_ne_touche_pas_une_etude(
        self, tmp_path, monkeypatch
    ):
        """
        Invariant 3 : une étude EXISTANTE garde son
        prompt actif ; une étude NOUVELLE hérite de
        la bibliothèque modifiée.
        """

        dossier = tmp_path / "prompts"

        ecrire_bibliotheque(
            USAGE_REFORMULATION,
            PROMPT_A,
            dossier
        )

        def initial_isole(usage, dossier_prompts=None):
            return lire_bibliotheque(
                usage,
                dossier
            )[0]

        monkeypatch.setattr(
            "services.etude_io.prompt_initial",
            initial_isole
        )

        etude = creer_etude(
            tmp_path / "Etude",
            "Évangile de Luc"
        )

        # P18.7e : la copie locale du prompt est figée dans
        # le tier de la réunion à l'attachement.
        projet = creer_projet_v1(tmp_path, "projet_a")
        nom = ajouter_reunion(etude, projet)

        assert (
            etude.tier_de(nom).parametres.reformulation[
                "prompt"
            ]
            == PROMPT_A
        )

        sauvegarder_etude(etude)

        # La bibliothèque évolue...
        ecrire_bibliotheque(
            USAGE_REFORMULATION,
            PROMPT_B,
            dossier
        )

        # ... l'étude existante ne bouge pas (son tier
        # garde le prompt figé).
        rouverte = ouvrir_etude(
            tmp_path / "Etude"
        )

        assert (
            rouverte.tier_de(nom).parametres.reformulation[
                "prompt"
            ]
            == PROMPT_A
        )

        # ... une nouvelle étude hérite de B.
        etude2 = creer_etude(
            tmp_path / "Etude2",
            "Deuxième étude"
        )

        projet2 = creer_projet_v1(tmp_path, "projet_b")
        nom2 = ajouter_reunion(etude2, projet2)

        assert (
            etude2.tier_de(nom2).parametres.reformulation[
                "prompt"
            ]
            == PROMPT_B
        )


#
# Invariant 5 : traçabilité des versions.
#


class TestVersionsMemorisentLePrompt:

    def test_reformulation(self, tmp_path):
        """
        La version de reformulation mémorise le
        texte effectif et le hash court du prompt
        (passe).
        """

        etude, nom = creer_etude_avec_blocs(
            tmp_path,
            nb_blocs=1
        )

        prompt = "PROMPT MOTEUR EFFECTIF 01"

        etude.parametres.reformulation["prompt"] = (
            prompt
        )

        client = ClientFactice(
            fournisseur=(
                catalogue_par_defaut()
                .chercher_fournisseur("openai")
            ),
            cle="",
        )

        moteur = fabriquer_moteur(etude, nom, client)

        moteur.traiter_reunion()

        couple = next(
            iter(etude.reformulations)
        )

        fid = couple[1]

        version = (
            etude.reformulation_de(nom, fid).versions[-1]
        )

        assert version.stats["prompt"] == prompt
        assert version.stats["prompt_hash"] == (
            hash_prompt(prompt)
        )

        # Le texte persisté sur disque porte aussi
        # le hash.
        # P18.7 : le résultat vit dans le tier de la
        # réunion, nommé par le FID (nu).
        chemin = (
            etude.tier_de(nom).dossier
            / "traitements"
            / "reformulation"
            / f"{fid}.json"
        )

        donnees = json.loads(
            chemin.read_text(encoding="utf-8")
        )

        assert (
            donnees["versions"][-1]["stats"][
                "prompt_hash"
            ]
            == hash_prompt(prompt)
        )

    def test_resume(self, tmp_path):
        """
        La version de résumé mémorise le texte
        effectif et le hash court du prompt
        (génération).
        """

        etude, reunions = creer_etude_reunions(
            tmp_path
        )

        prompt = "PROMPT RESUME EFFECTIF 02"

        etude.parametres.resume["prompt"] = prompt

        client = ClientResumeFactice()

        service = fabriquer_service(
            ServiceResume,
            etude,
            client
        )

        version, _stats = service.generer(
            reunions[0],
            source="brute_corrigee"
        )

        assert version.stats["prompt"] == prompt
        assert version.stats["prompt_hash"] == (
            hash_prompt(prompt)
        )


#
# Panneau de gestion — invariant 4 (mode étude)
# et invariant 6 (import/export).
#


@pytest.mark.qt
class TestPanneauBibliotheque:

    def _panneau(self, qapp, tmp_path):

        from ui.gestion_prompts_dialog import (
            MODE_BIBLIOTHEQUE,
            PanneauGestionPrompts,
        )

        dossier = tmp_path / "prompts"

        panneau = PanneauGestionPrompts(
            mode=MODE_BIBLIOTHEQUE,
            dossier_prompts=dossier
        )

        return panneau, dossier

    def test_enregistrement_et_indicateurs(
        self, qapp, tmp_path
    ):

        panneau, dossier = self._panneau(
            qapp,
            tmp_path
        )

        # Aucun fichier : origine = défaut embarqué.
        assert "défaut" in (
            panneau.origine_label.text()
        )

        panneau.prompt_edit.setPlainText(PROMPT_A)

        assert panneau.enregistrer() is True

        chemin = chemin_bibliotheque(
            USAGE_REFORMULATION,
            dossier
        )

        assert chemin.read_text(
            encoding="utf-8"
        ) == PROMPT_A

        # Origine = fichier bibliothèque, éditeur et
        # bibliothèque identiques après écriture.
        assert str(chemin) in (
            panneau.origine_label.text()
        )

        assert "identiques" in (
            panneau.divergence_label.text()
        )

        # Rien de changé : un second enregistrement
        # n'écrit plus.
        assert panneau.enregistrer() is False

    def test_reinitialisation_confirmee(
        self, qapp, tmp_path, monkeypatch
    ):

        panneau, dossier = self._panneau(
            qapp,
            tmp_path
        )

        chemin = ecrire_bibliotheque(
            USAGE_REFORMULATION,
            PROMPT_A,
            dossier
        )

        panneau.recharger_editeur()

        def question_non(*args, **kwargs):
            return QMessageBox.StandardButton.No

        monkeypatch.setattr(
            "ui.gestion_prompts_dialog"
            ".QMessageBox.question",
            question_non
        )

        panneau.reinitialiser_defauts()

        # Refus : le fichier survit.
        assert chemin.exists()

        def question_oui(*args, **kwargs):
            return QMessageBox.StandardButton.Yes

        monkeypatch.setattr(
            "ui.gestion_prompts_dialog"
            ".QMessageBox.question",
            question_oui
        )

        panneau.reinitialiser_defauts()

        # Confirmé : le fichier est supprimé, le
        # défaut embarqué revient dans l'éditeur.
        assert not chemin.exists()

        assert panneau.prompt_edit.toPlainText() == (
            lire_defaut_embarque(USAGE_REFORMULATION)
        )

    def test_import_n_ecrit_rien(
        self, qapp, tmp_path, monkeypatch
    ):
        """
        Invariant 6 : l'import charge le fichier
        dans l'éditeur, AUCUNE écriture avant
        « Enregistrer ».
        """

        panneau, dossier = self._panneau(
            qapp,
            tmp_path
        )

        source = tmp_path / "a_importer.md"

        source.write_text(
            "PROMPT IMPORTE 03",
            encoding="utf-8"
        )

        monkeypatch.setattr(
            "ui.gestion_prompts_dialog"
            ".QFileDialog.getOpenFileName",
            lambda *args, **kwargs: (
                str(source),
                "",
            )
        )

        panneau.importer()

        assert panneau.prompt_edit.toPlainText() == (
            "PROMPT IMPORTE 03"
        )

        # Rien n'a été écrit dans la bibliothèque.
        assert not dossier.exists()

        # « Enregistrer » écrit alors l'usage.
        panneau.enregistrer()

        assert lire_bibliotheque(
            USAGE_REFORMULATION,
            dossier
        ) == ("PROMPT IMPORTE 03", True)

    def test_export_ecrit_exactement(
        self, qapp, tmp_path, monkeypatch
    ):
        """
        Invariant 6 : l'export écrit exactement le
        texte de l'éditeur au chemin choisi.
        """

        panneau, _dossier = self._panneau(
            qapp,
            tmp_path
        )

        panneau.prompt_edit.setPlainText(PROMPT_B)

        sortie = tmp_path / "sortie"
        sortie.mkdir()

        sortie = sortie / "prompt.txt"

        monkeypatch.setattr(
            "ui.gestion_prompts_dialog"
            ".QFileDialog.getSaveFileName",
            lambda *args, **kwargs: (
                str(sortie),
                "",
            )
        )

        panneau.exporter()

        assert sortie.read_text(
            encoding="utf-8"
        ) == PROMPT_B


@pytest.mark.qt
class TestPanneauEtude:

    def _panneau(self, qapp, tmp_path, monkeypatch):

        dossier = tmp_path / "prompts"

        ecrire_bibliotheque(
            USAGE_REFORMULATION,
            PROMPT_B,
            dossier
        )

        etude = creer_etude(
            tmp_path / "Etude",
            "Évangile de Luc"
        )

        etude.parametres.reformulation["prompt"] = (
            PROMPT_A
        )

        # P18.7e : la copie locale vit dans le tier de la
        # réunion — on en attache une.
        from services.etude_io import ajouter_reunion
        projet = creer_projet_v1(tmp_path, "projet_a")
        ajouter_reunion(etude, projet)

        from ui.gestion_prompts_dialog import (
            MODE_ETUDE,
            PanneauGestionPrompts,
        )

        panneau = PanneauGestionPrompts(
            mode=MODE_ETUDE,
            etude_ouverte=etude,
            usage_initial=USAGE_REFORMULATION,
            dossier_prompts=dossier
        )

        return panneau, etude, dossier

    def test_divergence_indiquee(
        self, qapp, tmp_path, monkeypatch
    ):
        """
        Invariant 4 : les indicateurs portent les
        hashs de la copie locale ET de la
        bibliothèque, avec la divergence.
        """

        panneau, _etude, _dossier = self._panneau(
            qapp,
            tmp_path,
            monkeypatch
        )

        divergence = panneau.divergence_label.text()

        assert hash_prompt(PROMPT_A) in divergence
        assert hash_prompt(PROMPT_B) in divergence
        assert "DIVERGENTES" in divergence.upper()

    def test_enregistrement_copie_locale_uniquement(
        self, qapp, tmp_path, monkeypatch
    ):
        """
        Invariant 4 : « Enregistrer » ne touche QUE
        les paramètres de l'étude — jamais la
        bibliothèque.
        """

        panneau, etude, dossier = self._panneau(
            qapp,
            tmp_path,
            monkeypatch
        )

        panneau.prompt_edit.setPlainText(
            "PROMPT LOCAL RETRAVAILLE 04"
        )

        assert panneau.enregistrer() is True

        assert (
            etude.parametres.reformulation[
                "prompt"
            ]
            == "PROMPT LOCAL RETRAVAILLE 04"
        )

        # Persisté dans le parametres.json DU TIER
        # (P18.7e).
        nom = etude.etude.ordre_reunions[0]
        donnees = json.loads(
            (
                etude.tier_de(nom).dossier
                / "parametres"
                / "parametres.json"
            ).read_text(encoding="utf-8")
        )

        assert donnees["reformulation"]["prompt"] == (
            "PROMPT LOCAL RETRAVAILLE 04"
        )

        # La bibliothèque ne change pas.
        assert lire_bibliotheque(
            USAGE_REFORMULATION,
            dossier
        ) == (PROMPT_B, True)

    def test_recharger_depuis_bibliotheque(
        self, qapp, tmp_path, monkeypatch
    ):
        """
        « Recharger » remplace l'éditeur (après
        confirmation), la copie locale ne change
        qu'à « Enregistrer ».
        """

        panneau, etude, dossier = self._panneau(
            qapp,
            tmp_path,
            monkeypatch
        )

        assert panneau.prompt_edit.toPlainText() != (
            PROMPT_B
        )

        def question_oui(*args, **kwargs):
            return QMessageBox.StandardButton.Yes

        monkeypatch.setattr(
            "ui.gestion_prompts_dialog"
            ".QMessageBox.question",
            question_oui
        )

        panneau.recharger_depuis_bibliotheque()

        assert panneau.prompt_edit.toPlainText() == (
            PROMPT_B
        )

        # Pas encore enregistré : la copie locale
        # garde A.
        assert (
            etude.parametres.reformulation[
                "prompt"
            ]
            == PROMPT_A
        )

        panneau.enregistrer()

        assert (
            etude.parametres.reformulation[
                "prompt"
            ]
            == PROMPT_B
        )

    def test_promulguer_ecrit_la_bibliotheque(
        self, qapp, tmp_path, monkeypatch
    ):
        """
        Invariant 4 : « Promulguer » écrit le texte
        local dans le fichier bibliothèque (après
        confirmation) et NE TOUCHE aucune étude
        de plus.
        """

        panneau, etude, dossier = self._panneau(
            qapp,
            tmp_path,
            monkeypatch
        )

        def question_oui(*args, **kwargs):
            return QMessageBox.StandardButton.Yes

        monkeypatch.setattr(
            "ui.gestion_prompts_dialog"
            ".QMessageBox.question",
            question_oui
        )

        panneau.promulguer()

        assert lire_bibliotheque(
            USAGE_REFORMULATION,
            dossier
        ) == (PROMPT_A, True)

        # La copie locale de l'étude est intacte.
        assert (
            etude.parametres.reformulation[
                "prompt"
            ]
            == PROMPT_A
        )


#
# Entrées : onglet « Prompts » des réglages,
# boutons « ⚙ Prompts » des pages.
#


@pytest.mark.qt
class TestEntreesUI:

    def test_onglet_prompts_reglages(
        self, qapp, tmp_path, monkeypatch
    ):

        from ui.settings_dialog import SettingsDialog

        dossier = tmp_path / "prompts"

        def initial_isole(usage, dossier_prompts=None):
            return lire_defaut_embarque(usage)

        # L'étude n'est pas concernée ici, mais les
        # réglages ne doivent rien écrire au réel :
        # la bibliothèque du panneau est détournée.
        monkeypatch.setattr(
            "services.etude_io.prompt_initial",
            initial_isole
        )

        settings = SettingsManager(
            str(tmp_path / "reglages")
        )

        dialogue = SettingsDialog(settings=settings)

        try:

            noms_onglets = [
                dialogue.tabs.tabText(index)
                for index in range(
                    dialogue.tabs.count()
                )
            ]

            assert "Prompts" in noms_onglets

            panneau = dialogue.prompts_panneau

            assert panneau.mode == "bibliotheque"

            panneau._dossier_prompts = dossier

            panneau.prompt_edit.setPlainText(PROMPT_A)

            dialogue.save_settings()

            assert lire_bibliotheque(
                USAGE_REFORMULATION,
                dossier
            ) == (PROMPT_A, True)

        finally:
            dialogue.close()

    def test_bouton_prompts_page_reformulation(
        self, qapp, tmp_path, monkeypatch
    ):
        """
        « ⚙ Prompts » vit à GAUCHE de « Traiter les
        blocs non validés » et ouvre le gestionnaire
        en mode étude, usage reformulation.
        """

        from tests.unit.test_reformulation_ui import (
            construire_etude_test,
        )
        from ui.reformulation_window import (
            ReformulationWindow,
        )
        import ui.gestion_prompts_dialog as module

        _p, _r, _e, nom = construire_etude_test(
            tmp_path
        )

        etude = ouvrir_etude(tmp_path / "Etude")

        fenetre = ReformulationWindow(
            etude,
            nom,
            settings=SettingsManager(
                str(tmp_path / "reglages")
            )
        )

        try:

            barre = fenetre.barre_outils.layout()

            index_prompts = barre.indexOf(
                fenetre.prompts_button
            )

            index_traiter = barre.indexOf(
                fenetre.traiter_button
            )

            assert index_prompts >= 0
            assert index_prompts < index_traiter

            assert fenetre.prompts_button.text() == (
                "⚙ Prompts"
            )

            ouvertures = []

            class GestionFactice:

                def __init__(
                    self,
                    parent=None,
                    mode=None,
                    etude_ouverte=None,
                    usage_initial=None,
                    dossier_prompts=None
                ):
                    ouvertures.append({
                        "mode": mode,
                        "etude": etude_ouverte,
                        "usage": usage_initial,
                    })

                def exec(self):
                    return True

            monkeypatch.setattr(
                module,
                "GestionPromptsDialog",
                GestionFactice
            )

            fenetre.ouvrir_gestion_prompts()

            assert ouvertures == [{
                "mode": "etude",
                "etude": etude,
                "usage": USAGE_REFORMULATION,
            }]

        finally:
            fenetre.close()

    def test_bouton_prompts_page_resume(
        self, qapp, tmp_path, monkeypatch
    ):

        from ui.resume_window import PageResume
        import ui.gestion_prompts_dialog as module

        etude, reunions = creer_etude_reunions(
            tmp_path
        )

        fenetre = PageResume(etude, reunions[0])

        try:

            assert fenetre.prompts_button.text() == (
                "⚙ Prompts"
            )

            ouvertures = []

            class GestionFactice:

                def __init__(
                    self,
                    parent=None,
                    mode=None,
                    etude_ouverte=None,
                    usage_initial=None,
                    dossier_prompts=None
                ):
                    ouvertures.append({
                        "mode": mode,
                        "etude": etude_ouverte,
                        "usage": usage_initial,
                    })

                def exec(self):
                    return True

            monkeypatch.setattr(
                module,
                "GestionPromptsDialog",
                GestionFactice
            )

            fenetre.ouvrir_gestion_prompts()

            assert ouvertures == [{
                "mode": "etude",
                "etude": etude,
                "usage": USAGE_RESUME,
            }]

        finally:
            fenetre.close()


#
# Libellés de version : le hash court du prompt
# devient visible (continuité P20-ter).
#


@pytest.mark.qt
class TestLibelleVersion:

    def test_hash_du_prompt_au_libelle(
        self, qapp, tmp_path
    ):

        from ui.reformulation_window import (
            ReformulationWindow,
        )
        from services.etude_io import (
            ajouter_version_reformulation,
        )
        from tests.unit.test_reformulation_ui import (
            construire_etude_test,
        )

        _p, _r, _e, nom = construire_etude_test(
            tmp_path
        )

        etude = ouvrir_etude(tmp_path / "Etude")

        fid = next(
            iter(etude.registre.entrees)
        )

        version = ajouter_version_reformulation(
            etude,
            fid,
            "Texte reformulé.",
            stats={
                "duree_ms": 5000,
                "tokens_in": 100,
                "tokens_out": 50,
                "cout_estime": 0.01,
                "prompt": "PROMPT EFFECTIF 05",
                "prompt_hash": hash_prompt(
                    "PROMPT EFFECTIF 05"
                ),
            }
        )

        plugin = ReformulationWindow(
            etude,
            nom,
            settings=SettingsManager(
                str(tmp_path / "reglages")
            )
        )

        try:

            libelle = plugin.libelle_version(version)

            assert (
                f"prompt {hash_prompt('PROMPT EFFECTIF 05')}"
                in libelle
            )

        finally:
            plugin.close()
