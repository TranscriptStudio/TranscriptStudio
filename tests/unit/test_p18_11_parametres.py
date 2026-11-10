# tests/unit/test_p18_11_parametres.py
"""
P18.11 — Allègement du dialogue « Paramètres de
l'étude » + abrogation de la surcharge d'étude
(relecture 3 de David, 2026-11-10 ; feuille
d'autorité SPEC_PAGE_ETUDE_ET_SYNTHESE_MODIFS_
2026-11-10b §8, invariants 20-22 ; contrat de
stockage réunions §8/§9 amendés) :

20. le dialogue « Paramètres de l'étude » n'expose
    aucun paramètre LLM (modèle, température) ni
    aucun prompt ;
21. il n'existe aucune surcharge d'étude de
    paramètres LLM ni de prompt : la synthèse
    d'étude utilise exclusivement les paramètres
    LLM globaux de l'app et le prompt courant de la
    bibliothèque (prompts/synthese_etude.md, lu
    directement — plus de copie locale d'étude) ;
    les opérations d'une réunion utilisent les
    paramètres du tier ; la version de synthèse
    mémorise toujours texte + hash (P20.6c) ;
22. les volets LLM éventuellement présents dans
    parametres\\parametres.json d'une étude créée
    avant P18.11 sont ignorés et jamais réécrits ;
    les champs conservés gardent leur sémantique,
    leur portée et leur persistance actuelles.

P18.11e : le mécanisme ⚙ Prompts
(UI_GESTION_PROMPTS_V2) est inchangé — non testé
ici (couvert par test_p16ter_gestion_prompts.py).
"""

import json
import os
from unittest.mock import patch

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

import pytest

pytestmark = pytest.mark.qt

from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
)

from services.etude_io import (
    ajouter_version_reformulation,
    creer_etude,
    ouvrir_etude,
    parametres_etude_v2_dict,
    sauvegarder_etude,
    valider_version_reformulation,
)
from services.etude_schema import (
    valider_parametres_etude_hors_llm,
)
from services.llm.catalogue import (
    catalogue_par_defaut,
)
from services.llm.client import (
    ResultatCompletion,
)
from services.prompts import (
    USAGE_SYNTHESE_ETUDE,
    ecrire_bibliotheque,
    hash_prompt,
    lire_bibliotheque,
)
from services.settings import SettingsManager
from services.traitements.synthese import (
    ServiceSynthese,
)
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
def page(qapp, tmp_path):
    from ui.etude_window import EtudeWindow

    _p, _pv, etude, _nom = construire_etude_test(tmp_path)

    fenetre = EtudeWindow(
        tmp_path / "Etude",
        settings=SettingsManager(str(tmp_path / "reglages")),
    )

    yield fenetre, tmp_path

    fenetre.close()


class ClientFactice:

    def __init__(self, reponse="Synthèse factice."):
        self.appels = []
        self.reponse = reponse

    def completions(
        self,
        prompt_systeme,
        messages,
        parametres,
        streaming_callback=None,
        annulation=None,
    ):
        self.appels.append({
            "prompt_systeme": prompt_systeme,
            "message": messages[0]["content"],
        })

        return ResultatCompletion(
            texte=self.reponse,
            tokens_in=10,
            tokens_out=5,
            duree_ms=5,
            cout_estime=0.01,
            modele=parametres.modele,
            fournisseur="openai",
        )


class StoreFactice:

    def get_cle_llm(self, fournisseur_id):
        return f"cle-{fournisseur_id}"


PARAMETRES_APP = {
    "fournisseur": "openai",
    "modele": "gpt-4.1",
    "temperature": 0.3,
    "max_tokens": None,
}


def _service(etude, client, tmp_path, app=None):
    return ServiceSynthese(
        etude,
        parametres_app=app or PARAMETRES_APP,
        credential_store=StoreFactice(),
        catalogue=catalogue_par_defaut(),
        client_factory=lambda fournisseur, cle: client,
        dossier_prompts=tmp_path / "prompts",
    )


def _etude_avec_reunion_validee(tmp_path):
    """
    Étude d'une réunion dont tous les blocs sont
    validés (éligible à l'alimentation de synthèse).
    """

    _p, _pv, etude, nom = construire_etude_test(tmp_path)

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
            f"Pensée du bloc {fid}.",
        )
        valider_version_reformulation(
            etude,
            nom,
            fid,
            numero=v.numero,
            validateur="Test",
        )

    sauvegarder_etude(etude)

    return ouvrir_etude(tmp_path / "Etude"), nom


class TestInvariant20:
    """
    Invariant 20 : le dialogue n'expose aucun
    paramètre LLM (modèle, température) ni aucun
    prompt.
    """

    def test_dialogue_sans_widgets_llm(self, page):

        from ui.parametres_etude_dialog import (
            ParametresEtudeDialog,
        )

        fenetre, _tmp = page

        dialogue = ParametresEtudeDialog(
            fenetre.etude,
            parent=fenetre,
        )

        try:

            # Aucun champ prompt / modèle / température.
            for attr in (
                "prompt_reformulation_edit",
                "modele_reformulation_edit",
                "temperature_reformulation_spin",
                "prompt_resume_edit",
                "modele_resume_edit",
                "temperature_resume_spin",
            ):
                assert not hasattr(dialogue, attr), attr

            # Aucun QDoubleSpinBox (température) dans
            # tout le dialogue.
            assert (
                dialogue.findChildren(QDoubleSpinBox)
                == []
            )

            # Les seuls QComboBox sont thème, source du
            # résumé et version Bible (pas de menu
            # « Modèle »).
            combos = dialogue.findChildren(QComboBox)
            assert len(combos) == 3

            # Champs conservés présents.
            for attr in (
                "titre_etude_edit",
                "theme_combo",
                "contexte_fenetre_check",
                "fenetre_spin",
                "contexte_synthese_check",
                "longueur_min_spin",
                "longueur_max_spin",
                "source_defaut_combo",
                "version_bible_combo",
                "propagation_label",
                "interdits_edit",
            ):
                assert hasattr(dialogue, attr), attr

            # Le champ « Fenêtre glissante (tokens) »
            # est conservé À CÔTÉ de la case fenêtre
            # glissante (même ligne horizontale).
            ligne = dialogue.contexte_fenetre_check.parent()
            assert ligne is not None
            assert (
                dialogue.fenetre_spin.parent() is ligne
            )

        finally:
            dialogue.close()

    def test_enregistrer_ne_touche_pas_les_llm_du_tier(
        self, page
    ):
        """
        L'enregistrement du dialogue ne propage QUE
        les champs conservés vers les tiers — jamais
        les paramètres LLM ni les prompts du tier.
        """

        from ui.parametres_etude_dialog import (
            ParametresEtudeDialog,
        )

        fenetre, tmp_path = page

        etude = fenetre.etude
        nom = next(iter(etude.tiers))

        tier = etude.tier_de(nom)

        tier.parametres.reformulation["prompt"] = (
            "PROMPT DU TIER"
        )
        tier.parametres.reformulation["modele"] = "modele-tier"
        tier.parametres.reformulation["temperature"] = 0.9
        tier.parametres.resume["prompt"] = "PROMPT RÉSUMÉ TIER"

        dialogue = ParametresEtudeDialog(
            etude,
            parent=fenetre,
        )

        try:

            dialogue.fenetre_spin.setValue(4321)
            dialogue.contexte_fenetre_check.setChecked(
                False
            )

            with patch(
                "PySide6.QtWidgets.QMessageBox.question",
                staticmethod(lambda *a, **k: 0),
            ):
                dialogue.enregistrer()

            params_tier = tier.parametres

            # Champs conservés propagés.
            assert (
                params_tier.reformulation[
                    "fenetre_glissante_tokens"
                ]
                == 4321
            )
            assert params_tier.reformulation["contexte"][
                "fenetre_glissante"
            ] is False

            # Paramètres LLM/prompts du tier INTACTS.
            assert (
                params_tier.reformulation["prompt"]
                == "PROMPT DU TIER"
            )
            assert (
                params_tier.reformulation["modele"]
                == "modele-tier"
            )
            assert (
                params_tier.reformulation["temperature"]
                == 0.9
            )
            assert (
                params_tier.resume["prompt"]
                == "PROMPT RÉSUMÉ TIER"
            )

        finally:
            dialogue.close()


class TestInvariant21:
    """
    Invariant 21 : aucune surcharge d'étude de
    paramètres LLM ni de prompt — la synthèse
    utilise exclusivement les réglages de l'app.
    """

    def test_synthese_utilise_les_reglages_app(self, tmp_path):
        """
        Même avec un volet synthèse LLM en mémoire sur
        l'étude, resoudre() et tokens_max() utilisent
        UNIQUEMENT les réglages de l'app.
        """

        etude, _nom = _etude_avec_reunion_validee(tmp_path)

        # Volet LLM « étude » en mémoire : ignoré.
        etude.parametres.synthese["modele"] = (
            "modele-etude-a-ignorer"
        )
        etude.parametres.synthese["tokens_max"] = 999

        client = ClientFactice()

        service = _service(
            etude,
            client,
            tmp_path,
            app={
                "fournisseur": "openai",
                "modele": "gpt-4.1",
                "max_tokens": 2222,
            },
        )

        fournisseur, modele = service.resoudre()

        assert fournisseur.id == "openai"
        assert modele.id == "gpt-4.1"

        assert service.tokens_max() == 2222

        # Sans max_tokens dans l'app : défaut embarqué.
        service2 = _service(etude, client, tmp_path)

        assert service2.tokens_max() == 1500

    def test_prompt_lu_directement_dans_la_bibliotheque(
        self, tmp_path
    ):
        """
        Le prompt de synthèse est lu directement dans
        la bibliothèque (prompts/synthese_etude.md) ;
        modifier la bibliothèque change la génération
        suivante — aucune copie locale d'étude.
        """

        etude, nom = _etude_avec_reunion_validee(tmp_path)

        client = ClientFactice()

        service = _service(etude, client, tmp_path)

        # Prompt courant = bibliothèque (défaut embarqué
        # tant que pas de fichier).
        assert service.prompt_effectif() == (
            lire_bibliotheque(
                USAGE_SYNTHESE_ETUDE,
                tmp_path / "prompts",
            )[0]
        )

        # Édition dans la bibliothèque des réglages.
        ecrire_bibliotheque(
            USAGE_SYNTHESE_ETUDE,
            "Nouveau prompt de synthèse modifié.",
            dossier=tmp_path / "prompts",
        )

        assert service.prompt_effectif() == (
            "Nouveau prompt de synthèse modifié."
        )

        # La génération suivante l'utilise.
        service.alimenter(nom)

        assert (
            client.appels[0]["prompt_systeme"]
            == "Nouveau prompt de synthèse modifié."
        )

    def test_version_synthese_memorise_texte_et_hash(
        self, tmp_path
    ):
        """
        P20.6c/P18.11c : la version de synthèse
        mémorise toujours le texte ET le hash du
        prompt utilisé.
        """

        etude, nom = _etude_avec_reunion_validee(tmp_path)

        client = ClientFactice()

        service = _service(etude, client, tmp_path)

        version, stats, _remplace = service.alimenter(nom)

        # alimenter() ajoute le marqueur de section.
        assert "Synthèse factice." in version.texte
        assert version.stats is not None
        assert version.stats["prompt_hash"] == (
            hash_prompt(service.prompt_effectif())
        )
        assert stats["prompt_hash"] == (
            hash_prompt(service.prompt_effectif())
        )

        # Persisté dans synthese.json et relu.
        relue = ouvrir_etude(tmp_path / "Etude")

        derniere = relue.synthese.versions[-1]

        assert "Synthèse factice." in derniere.texte
        assert derniere.stats["prompt_hash"] == (
            hash_prompt(service.prompt_effectif())
        )

    def test_operations_reunion_utilisent_le_tier(
        self, tmp_path
    ):
        """
        Les opérations sur les traitements d'une
        réunion utilisent les paramètres DU TIER
        (inchangé, §8) — l'étude n'en a plus à
        surcharger.
        """

        etude, nom = _etude_avec_reunion_validee(tmp_path)

        tier = etude.tier_de(nom)

        tier.parametres.reformulation["temperature"] = 0.42

        assert (
            etude.parametres_traitement_de(nom)
            .reformulation["temperature"]
            == 0.42
        )


class TestInvariant22:
    """
    Invariant 22 : volets LLM d'une étude antérieure
    ignorés à la lecture et jamais réécrits ; champs
    conservés persistés tels quels.
    """

    def test_fichier_sans_volets_llm(self, tmp_path):

        _p, _pv, etude, _nom = construire_etude_test(tmp_path)

        etude.parametres.synthese["tokens_max"] = 777
        etude.parametres.llm["fournisseurs"] = []

        sauvegarder_etude(etude)

        chemin = (
            tmp_path / "Etude" / "parametres"
            / "parametres.json"
        )

        donnees = json.loads(
            chemin.read_text(encoding="utf-8")
        )

        # Aucun volet LLM dans le fichier de l'étude.
        assert "synthese" not in donnees
        assert "llm" not in donnees
        assert "prompt" not in donnees["reformulation"]
        assert "modele" not in donnees["reformulation"]
        assert "temperature" not in donnees["reformulation"]
        assert "prompt" not in donnees["resume"]
        assert "modele" not in donnees["resume"]
        assert "temperature" not in donnees["resume"]

        # Le validateur hors-LLM l'accepte.
        valider_parametres_etude_hors_llm(donnees)

        # Le tier, lui, garde ses paramètres complets
        # (LLM compris) — inchangé.
        tier = etude.tier_de(_nom)
        assert tier.parametres.reformulation["prompt"]
        assert tier.parametres.reformulation["modele"]

    def test_volets_llm_anciens_ignores_et_elagues(
        self, tmp_path
    ):
        """
        Un parametres.json d'étude créé avant P18.11
        (avec volets LLM) s'ouvre sans erreur : les
        volets LLM sont ignorés à la lecture et jamais
        réécrits (élagués à la prochaine écriture) —
        aucune migration dédiée.
        """

        _p, _pv, etude, nom = construire_etude_test(tmp_path)

        sauvegarder_etude(etude)

        chemin = (
            tmp_path / "Etude" / "parametres"
            / "parametres.json"
        )

        donnees = json.loads(
            chemin.read_text(encoding="utf-8")
        )

        # Simule un fichier antérieur avec volets LLM.
        donnees["synthese"] = {
            "tokens_max": 4242,
            "modele": "modele-avant",
        }
        donnees["llm"] = {
            "fournisseurs": [
                {
                    "nom": "mistral",
                    "url": "https://api.mistral.ai/v1",
                    "cle_ref": "credential_store",
                }
            ]
        }
        donnees["reformulation"]["prompt"] = "ANCIEN PROMPT"
        donnees["reformulation"]["modele"] = "m-avant"
        donnees["reformulation"]["temperature"] = 0.9
        donnees["reformulation"][
            "fenetre_glissante_tokens"
        ] = 3210

        chemin.write_text(
            json.dumps(donnees),
            encoding="utf-8"
        )

        # Lecture : OK, volets LLM ignorés.
        relue = ouvrir_etude(tmp_path / "Etude")

        assert relue.parametres.synthese["tokens_max"] == 1500
        assert (
            relue.parametres.reformulation[
                "fenetre_glissante_tokens"
            ]
            == 3210
        )

        # Jamais réécrits : la sauvegarde élague les
        # volets LLM du fichier.
        sauvegarder_etude(relue)

        apres = json.loads(
            chemin.read_text(encoding="utf-8")
        )

        assert "synthese" not in apres
        assert "llm" not in apres
        assert "prompt" not in apres["reformulation"]
        assert "modele" not in apres["reformulation"]
        assert "temperature" not in apres["reformulation"]
        assert (
            apres["reformulation"][
                "fenetre_glissante_tokens"
            ]
            == 3210
        )

    def test_champs_conserves_persistes_via_dialogue(
        self, page
    ):
        """
        Les champs conservés gardent leur persistance :
        édités dans le dialogue, persistés dans
        parametres.json de l'étude, relus à la
        réouverture.
        """

        from ui.parametres_etude_dialog import (
            ParametresEtudeDialog,
        )

        fenetre, tmp_path = page

        etude = fenetre.etude

        dialogue = ParametresEtudeDialog(
            etude,
            parent=fenetre,
        )

        try:

            dialogue.titre_etude_edit.setText(
                "Évangile selon Marc"
            )
            dialogue.theme_combo.setCurrentIndex(
                dialogue.theme_combo.findData("libre")
            )
            dialogue.fenetre_spin.setValue(5000)
            dialogue.contexte_fenetre_check.setChecked(
                False
            )
            dialogue.contexte_synthese_check.setChecked(
                False
            )
            dialogue.longueur_min_spin.setValue(200)
            dialogue.longueur_max_spin.setValue(300)
            dialogue.source_defaut_combo.setCurrentIndex(
                dialogue.source_defaut_combo.findData(
                    "brute_corrigee"
                )
            )
            dialogue.interdits_edit.setPlainText(
                "trop\nvraiment"
            )

            with patch(
                "PySide6.QtWidgets.QMessageBox.question",
                staticmethod(lambda *a, **k: 0),
            ):
                dialogue.enregistrer()

        finally:
            dialogue.close()

        chemin = (
            tmp_path / "Etude" / "parametres"
            / "parametres.json"
        )

        donnees = json.loads(
            chemin.read_text(encoding="utf-8")
        )

        assert donnees["reformulation"] == {
            "fenetre_glissante_tokens": 5000,
            "contexte": {
                "fenetre_glissante": False,
                "synthese_etude": False,
            },
        }
        assert donnees["resume"] == {
            "longueur_cible_mots": [200, 300],
            "source_defaut": "brute_corrigee",
        }
        assert donnees["controle_qualite"][
            "interdits_stylistiques"
        ] == ["trop", "vraiment"]

        # Relus à la réouverture.
        relue = ouvrir_etude(tmp_path / "Etude")

        assert relue.etude.titre == "Évangile selon Marc"
        assert relue.etude.theme == "libre"
        assert (
            relue.parametres.reformulation[
                "fenetre_glissante_tokens"
            ]
            == 5000
        )
        assert relue.parametres.reformulation["contexte"] == {
            "fenetre_glissante": False,
            "synthese_etude": False,
        }
        assert relue.parametres.resume[
            "longueur_cible_mots"
        ] == [200, 300]
        assert (
            relue.parametres.resume["source_defaut"]
            == "brute_corrigee"
        )
        assert relue.parametres.controle_qualite[
            "interdits_stylistiques"
        ] == ["trop", "vraiment"]

        # Le dialogue réouvert les réaffiche.
        dialogue2 = ParametresEtudeDialog(
            relue,
            parent=fenetre,
        )

        try:

            assert (
                dialogue2.titre_etude_edit.text()
                == "Évangile selon Marc"
            )
            assert dialogue2.fenetre_spin.value() == 5000
            assert (
                dialogue2.contexte_fenetre_check.isChecked()
                is False
            )
            assert (
                dialogue2.contexte_synthese_check.isChecked()
                is False
            )
            assert dialogue2.longueur_min_spin.value() == 200
            assert dialogue2.longueur_max_spin.value() == 300

        finally:
            dialogue2.close()

    def test_writer_hors_llm(self, tmp_path):
        """
        Le writer v2 de l'étude n'émet aucun volet LLM.
        """

        _p, _pv, etude, _nom = construire_etude_test(tmp_path)

        dict_v2 = parametres_etude_v2_dict(etude.parametres)

        assert set(dict_v2.keys()) == {
            "reformulation",
            "resume",
            "controle_qualite",
            "bible",
        }

        for volet in dict_v2.values():
            assert "prompt" not in volet
            assert "modele" not in volet
            assert "temperature" not in volet

        valider_parametres_etude_hors_llm(dict_v2)
