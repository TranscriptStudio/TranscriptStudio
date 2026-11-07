"""
Tests P19.4-bis (ARBITRAGE_PROMPT_FUSION_
2026-11-07a.md — VALIDÉ) : le prompt de fusion
assistée vit dans la BIBLIOTHÈQUE ÉDITABLE
``prompts/fusion.md``, au même titre que
reformulation et résumé.

Règles testées (conditions de l'arbitrage, qui
reprend les règles P16-ter de
UI_GESTION_PROMPTS_V2) :

- usage « fusion » au catalogue de la bibliothèque
  (libellé « Fusion de pensées »), défaut embarqué
  fourni (reconstituable si le fichier est
  supprimé) ;
- fichier texte brut, bibliothèque du dossier de
  paramétrage (lecture = défaut embarqué si
  fichier absent, jamais de création à la lecture) ;
- copie locale par étude (les NOUVELLES études
  héritent, les études EXISTANTES ne sont jamais
  touchées — bloc ``fusion`` OPTIONNEL des
  paramètres) ;
- le prompt EFFECTIF reçoit les pensées candidates
  (textes, locuteurs, réunions sources) ;
- traçabilité TEXTE + HASH : chaque fusion assistée
  enregistre le prompt utilisé et son hash court
  dans ouvrage.json ;
- la proposition LLM reste éditable et jamais
  auto-appliquée (inchangé, P19.4).
"""

import os
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

import pytest

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QMessageBox,
)

from models.etude import ParametresEtude
from models.ouvrage import SOURCE_FUSION
from services.etude_schema import (
    EtudeFormatError,
    valider_parametres,
)
from services.ouvrage_document import (
    defusionner_pensees,
    fusionner_pensees,
    generer_document,
    sauvegarder_ouvrage,
)
from services.prompts import (
    LIBELLES_USAGES,
    ecrire_bibliotheque,
    hash_prompt,
    lire_bibliotheque,
    lire_defaut_embarque,
    reinitialiser_bibliotheque,
    USAGE_FUSION,
    USAGE_REFORMULATION,
    USAGE_RESUME,
)
from services.traitements.fusion import (
    ServiceFusion,
)
from tests.unit.test_reformulation_ui import (
    construire_etude_test,
)


PARAMETRES_APP = {
    "fournisseur": "openai",
    "modele": "gpt-4.1",
    "temperature": 0.3,
    "temperatures": {
        "reformulation": 0.3,
    },
}


class StoreFactice:

    def get_cle_llm(self, fournisseur_id):
        return f"cle-{fournisseur_id}"


class ClientFactice:

    def __init__(self, reponse="Proposition IA"):
        self.appels = []
        self.reponse = reponse

    def completions(
        self,
        prompt_systeme,
        messages,
        parametres,
        streaming_callback=None,
        annulation=None
    ):
        self.appels.append({
            "prompt_systeme": prompt_systeme,
            "message": messages[0]["content"],
        })

        return type(
            "R",
            (),
            {
                "texte": self.reponse,
                "modele": parametres.modele,
                "fournisseur": "openai",
                "tokens_in": 12,
                "tokens_out": 6,
                "duree_ms": 4,
                "cout_estime": 0.01,
            },
        )()


@pytest.fixture(scope="module")
def qapp():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    yield application


@pytest.fixture
def etude_validee(qapp, tmp_path):
    """
    Étude d'une réunion de TROIS blocs, tous avec
    une reformulation VALIDÉE.
    """

    from services.etude_io import (
        ajouter_version_reformulation,
        valider_version_reformulation,
    )

    _p, _pv, etude, nom = (
        construire_etude_test(tmp_path)
    )

    fids = [
        entree.fid
        for entree in (
            etude.registre.entrees.values()
        )
        if entree.reunion == nom
    ]

    for fid in fids:

        version = ajouter_version_reformulation(
            etude,
            fid,
            f"Reformulation du bloc {fid}"
        )

        valider_version_reformulation(
            etude,
            fid,
            version.numero,
            "Test"
        )

    return etude, nom, fids, tmp_path


def service_test(etude, client, dossier_prompts=None):

    from services.llm.catalogue import (
        catalogue_par_defaut,
    )

    return ServiceFusion(
        etude,
        parametres_app=PARAMETRES_APP,
        credential_store=StoreFactice(),
        catalogue=catalogue_par_defaut(),
        client_factory=(
            lambda fournisseur, cle: client
        ),
        dossier_prompts=dossier_prompts,
    )


#
# ==================================================
# Bibliothèque : usage « fusion ».
# ==================================================
#

class TestBibliotheque:

    def test_usage_et_libelle(self):
        """
        L'usage « fusion » existe, libellé
        « Fusion de pensées » (P19.4-bis),
        aux côtés de reformulation et résumé.
        """

        assert LIBELLES_USAGES[USAGE_FUSION] == (
            "Fusion de pensées"
        )

        assert (
            USAGE_REFORMULATION
            in LIBELLES_USAGES
        )
        assert (
            USAGE_RESUME in LIBELLES_USAGES
        )

    def test_defaut_embarque_fourni(self):
        """
        L'app fournit TOUJOURS un prompt de fusion
        par défaut reconstituable
        (resources/prompts/prompt_fusion_v2.md) :
        aucune génération LLM sans fichier de
        bibliothèque.
        """

        texte = lire_defaut_embarque(USAGE_FUSION)

        assert texte.strip()
        assert "paragraphe" in texte.lower()
        assert "pensée" in texte.lower()

    def test_bibliotheque_et_reinitialisation(
        self,
        tmp_path
    ):
        """
        Sans fichier : défaut embarqué
        (personnalisé False). Écrit : valeur
        courante de la bibliothèque.
        « Réinitialiser » se contente de
        SUPPRIMER le fichier.
        """

        texte, personnalise = lire_bibliotheque(
            USAGE_FUSION,
            tmp_path
        )

        assert not personnalise
        assert texte == lire_defaut_embarque(
            USAGE_FUSION
        )

        chemin = ecrire_bibliotheque(
            USAGE_FUSION,
            "Prompt de fusion personnalisé.",
            tmp_path
        )

        assert chemin.name == "fusion.md"

        texte, personnalise = lire_bibliotheque(
            USAGE_FUSION,
            tmp_path
        )

        assert personnalise
        assert texte == (
            "Prompt de fusion personnalisé."
        )

        assert reinitialiser_bibliotheque(
            USAGE_FUSION,
            tmp_path
        ) is True

        texte, personnalise = lire_bibliotheque(
            USAGE_FUSION,
            tmp_path
        )

        assert not personnalise
        assert texte == lire_defaut_embarque(
            USAGE_FUSION
        )


#
# ==================================================
# Copie locale par étude (bloc fusion optionnel).
# ==================================================
#

class TestCopieLocaleEtude:

    def test_nouvelle_etude_herite(
        self,
        etude_validee
    ):
        """
        Les NOUVELLES études héritent du prompt de
        fusion (bibliothèque à défaut du défaut
        embarqué) : bloc ``parametres.fusion``.
        """

        etude, _n, _f, _t = etude_validee

        bloc = etude.parametres.fusion

        assert bloc
        assert bloc["prompt"] == (
            lire_defaut_embarque(USAGE_FUSION)
        )

        # Round-trip : le bloc vit dans
        # parametres.json (to_dict/from_dict).
        relu = ParametresEtude.from_dict(
            etude.parametres.to_dict()
        )

        assert (
            relu.fusion["prompt"]
            == bloc["prompt"]
        )

    def test_etude_anterieure_sans_bloc(self):
        """
        Une étude ANTERIEURE (paramètres sans bloc
        fusion) se charge SANS erreur — bloc lu
        vide, la bibliothèque sert de repli ; et
        la validation l'accepte.
        """

        data = {
            "reformulation": {
                "prompt": "P",
                "modele": "m",
                "fenetre_glissante_tokens": 2000,
            },
            "resume": {
                "prompt": "P",
                "modele": "m",
                "longueur_cible_mots": [650, 700],
                "source_defaut": (
                    "reformulations_valides"
                ),
            },
            "synthese": {
                "tokens_max": 1500,
                "modele": "m",
            },
            "controle_qualite": {},
            "llm": {"fournisseurs": []},
        }

        # Validation : absence acceptée.
        valider_parametres(dict(data))

        parametres = ParametresEtude.from_dict(
            data
        )

        assert parametres.fusion == {}

    def test_validation_bloc_fusion(self):

        data = {
            "reformulation": {
                "prompt": "P",
                "modele": "m",
                "fenetre_glissante_tokens": 2000,
            },
            "resume": {
                "prompt": "P",
                "modele": "m",
                "longueur_cible_mots": [650, 700],
                "source_defaut": (
                    "reformulations_valides"
                ),
            },
            "synthese": {
                "tokens_max": 1500,
                "modele": "m",
            },
            "controle_qualite": {},
            "llm": {"fournisseurs": []},
            "fusion": {"prompt": "Maison."},
        }

        valider_parametres(dict(data))

        data["fusion"] = "pas un dict"

        with pytest.raises(EtudeFormatError):
            valider_parametres(dict(data))

        data["fusion"] = {"prompt": 3}

        with pytest.raises(EtudeFormatError):
            valider_parametres(dict(data))


#
# ==================================================
# Prompt effectif : copie locale > bibliothèque >
# défaut embarqué.
# ==================================================
#

class TestPromptEffectif:

    def test_copie_locale_prioritaire(
        self,
        etude_validee
    ):
        """
        La copie LOCALE de l'étude prime le prompt
        envoyé (l'édition locale ne modifie jamais
        la bibliothèque globale).
        """

        etude, _n, _f, _t = etude_validee

        etude.parametres.fusion[
            "prompt"
        ] = "Fusion maison de l'étude."

        client = ClientFactice()

        service = service_test(etude, client)

        assert service.prompt_effectif() == (
            "Fusion maison de l'étude."
        )

        service.proposer("Texte 1", "Texte 2")

        assert client.appels[0][
            "prompt_systeme"
        ] == "Fusion maison de l'étude."

        assert service.dernier_prompt_hash == (
            hash_prompt(
                "Fusion maison de l'étude."
            )
        )

    def test_bibliotheque_puis_defaut(
        self,
        etude_validee,
        tmp_path
    ):
        """
        Sans copie locale (étude antérieure) : la
        BIBLIOTHÈQUE fait foi ; sans fichier de
        bibliothèque : le DÉFAUT EMBARQUÉ.
        """

        etude, _n, _f, _t = etude_validee

        etude.parametres.fusion = {}

        client = ClientFactice()

        service = service_test(
            etude,
            client,
            dossier_prompts=tmp_path
        )

        assert service.prompt_effectif() == (
            lire_defaut_embarque(USAGE_FUSION)
        )

        ecrire_bibliotheque(
            USAGE_FUSION,
            "Bibliothèque de fusion.",
            tmp_path
        )

        assert service.prompt_effectif() == (
            "Bibliothèque de fusion."
        )

        service.proposer("Texte 1", "Texte 2")

        assert client.appels[0][
            "prompt_systeme"
        ] == "Bibliothèque de fusion."

    def test_pensees_candidates_avec_sources(
        self,
        etude_validee
    ):
        """
        Le prompt reçoit les pensées candidates :
        textes, locuteurs et réunions sources.
        """

        etude, nom, fids, _t = etude_validee

        client = ClientFactice()

        service = service_test(etude, client)

        service.proposer(
            "Pensée du premier paragraphe.",
            "Pensée similaire du second.",
            source_1=(
                "R1 · Philippe · bloc "
                f"{fids[0]}"
            ),
            source_2=(
                "R1 · Daniel · bloc "
                f"{fids[1]}"
            ),
        )

        message = client.appels[0]["message"]

        assert (
            "Pensée du premier paragraphe."
            in message
        )

        assert (
            "Pensée similaire du second."
            in message
        )

        assert (
            f"Source 1 : R1 · Philippe · bloc "
            f"{fids[0]}"
            in message
        )

        assert (
            f"Source 2 : R1 · Daniel · bloc "
            f"{fids[1]}"
            in message
        )


#
# ==================================================
# Traçabilité texte + hash dans ouvrage.json.
# ==================================================
#

class TestTraceabilite:

    def test_stats_consignees(
        self,
        qapp,
        etude_validee
    ):
        """
        Une fusion ASSISTÉE enregistre le prompt
        EFFECTIF (texte + hash court) dans
        ouvrage.json, avec modèle et coûts ; une
        fusion MANUELLE n'enregistre rien (pas de
        prompt LLM).
        """

        etude, _n, _f, tmp = etude_validee

        document = generer_document(etude)

        p1, p2, _p3 = document.paragraphes()

        # Fusion manuelle : pas de stats.
        manuelle = fusionner_pensees(
            document,
            p1.id,
            p2.id,
            "Fusion manuelle."
        )

        assert "stats" not in manuelle.fusion

        # Fusion assistée : stats complètes.
        client = ClientFactice()

        service = service_test(etude, client)

        resultat = service.proposer(
            "Texte 1",
            "Texte 2",
            source_1="R1 · Philippe",
            source_2="R1 · Daniel",
        )

        stats = {
            "prompt": service.dernier_prompt,
            "prompt_hash": (
                service.dernier_prompt_hash
            ),
            "modele": resultat.modele,
            "fournisseur": resultat.fournisseur,
            "tokens_in": resultat.tokens_in,
            "tokens_out": resultat.tokens_out,
            "cout_estime": resultat.cout_estime,
        }

        paragraphes = document.paragraphes()

        assistee = fusionner_pensees(
            document,
            paragraphes[0].id,
            paragraphes[1].id,
            "Fusion assistée.",
            stats=stats
        )

        assert assistee.fusion["stats"] == stats

        assert stats["prompt"] == (
            lire_defaut_embarque(USAGE_FUSION)
        )

        assert stats["prompt_hash"] == hash_prompt(
            stats["prompt"]
        )

        # Persistance dans ouvrage.json.
        sauvegarder_ouvrage(document, tmp / "Etude")

        from services.ouvrage_document import (
            charger_ouvrage,
        )

        relu = charger_ouvrage(tmp / "Etude")

        fusionne = relu.paragraphes()[-1]

        assert fusionne.source == SOURCE_FUSION
        assert (
            fusionne.fusion["stats"]["prompt"]
            == stats["prompt"]
        )

        # Dé-fusion : l'instantané complet (stats
        # comprises) vit dans l'historique.
        defusionner_pensees(relu, fusionne.id)

        entree = relu.historique[-1]

        assert entree["paragraphe"]["fusion"][
            "stats"
        ]["prompt_hash"] == stats["prompt_hash"]

    def test_page_consigne_les_stats(
        self,
        qapp,
        etude_validee
    ):
        """
        La PAGE Ouvrage transmet les stats du
        dialogue (assistance employée) à la fusion
        ; le manuscrit montre le hash court du
        prompt au paragraphe fusionné assisté ;
        l'avertissement de RÉGÉNÉRATION mentionne
        les fusions (Inv. B de
        ARBITRAGE_P19_4_FUSION_REGENERATION).
        """

        from services.settings import SettingsManager
        from ui.ouvrage_window import OuvrageWindow

        etude, _n, _f, tmp = etude_validee

        PROMPT_ETUDE = (
            "Prompt de fusion de l'étude."
        )

        page = OuvrageWindow(
            etude,
            settings=SettingsManager(
                str(tmp / "reglages")
            )
        )

        page.generer_ouvrage()

        paragraphes = page.document.paragraphes()

        p1, p2, _p3 = paragraphes

        class DialogueAssiste:
            """
            Dialogue factice : fusion issue d'une
            ASSISTANCE LLM (stats texte + hash).
            """

            def __init__(
                self,
                parent,
                element_1,
                element_2,
                service=None
            ):
                pass

            def exec(self):
                return (
                    QDialog.DialogCode.Accepted
                )

            def texte_fusionne(self):
                return "Fusion assistée, éditée."

            def stats(self):
                return {
                    "prompt": PROMPT_ETUDE,
                    "prompt_hash": hash_prompt(
                        PROMPT_ETUDE
                    ),
                    "modele": "gpt-4.1",
                }

        PROMPT_ETUDE = (
            "Prompt de fusion de l'étude."
        )

        # Sélection des deux premiers paragraphes.
        from PySide6.QtCore import Qt

        def selectionner(ids):

            page.arbre.clearSelection()

            def visiter(noeud):

                if noeud.data(
                    0,
                    Qt.ItemDataRole.UserRole
                ) in ids:
                    noeud.setSelected(True)

                for j in range(noeud.childCount()):
                    visiter(noeud.child(j))

            for i in range(
                page.arbre.topLevelItemCount()
            ):
                visiter(
                    page.arbre.topLevelItem(i)
                )

        selectionner([p1.id, p2.id])

        with patch(
            "ui.ouvrage_window"
            ".FusionPenseesDialog",
            DialogueAssiste
        ):
            page.sur_fusion_pensees()

        fusionne = (
            page.document.paragraphes()[0]
        )

        assert fusionne.source == SOURCE_FUSION

        assert fusionne.fusion["stats"][
            "prompt_hash"
        ] == hash_prompt(
            "Prompt de fusion de l'étude."
        )

        # Manuscrit : hash court visible.
        libelle = (
            page.editeurs[fusionne.id]
            .findChild(type(page.titre_label))
            .text()
        )

        attendu = (
            "prompt "
            + hash_prompt(PROMPT_ETUDE)
        )

        assert attendu in libelle

        # Avertissement de régénération : les
        # FUSIONS sont mentionnées (Inv. B de
        # ARBITRAGE_P19_4_FUSION_REGENERATION).
        avertissements = []

        def faux_warning(
            parent,
            titre,
            texte,
            *args,
            **kwargs
        ):
            avertissements.append((titre, texte))
            return (
                QMessageBox.StandardButton.No
            )

        with patch(
            "ui.ouvrage_window"
            ".QMessageBox.warning",
            new=faux_warning,
        ):
            page.generer_ouvrage()

        assert avertissements, (
            "la régénération doit avertir"
        )

        assert "FUSIONS" in avertissements[0][1]

        page.close()


#
# ==================================================
# ⚙ Prompts : entrée « Fusion de pensées ».
# ==================================================
#

class TestGestionPrompts:

    def test_entree_fusion_au_selecteur(
        self,
        qapp,
        etude_validee,
        tmp_path
    ):
        """
        ⚙ Prompts (mode étude) montre l'usage
        « Fusion de pensées » dans le
        sélecteur ; en mode étude, l'édition
        ENREGISTRE la copie locale (paramètres de
        l'étude).
        """

        from ui.gestion_prompts_dialog import (
            GestionPromptsDialog,
            MODE_ETUDE,
        )

        etude, _n, _f, _t = etude_validee

        dialogue = GestionPromptsDialog(
            mode=MODE_ETUDE,
            etude_ouverte=etude,
            usage_initial=USAGE_FUSION,
            dossier_prompts=(
                tmp_path / "prompts"
            ),
        )

        try:

            panneau = dialogue.panneau

            libelles = [
                panneau.usage_combo
                .itemText(i)
                for i in range(
                    panneau.usage_combo.count()
                )
            ]

            assert (
                "Fusion de pensées" in libelles
            )

            assert (
                panneau.usage_combo
                .currentData()
                == USAGE_FUSION
            )

            # L'éditeur montre la copie locale de
            # l'étude (défaut embarqué hérité).
            assert (
                panneau
                .prompt_edit
                .toPlainText()
                == lire_defaut_embarque(
                    USAGE_FUSION
                )
            )

            # Édition puis Enregistrer : copie
            # locale uniquement.
            panneau.prompt_edit.setPlainText(
                "Fusion spéciale de cette étude."
            )

            assert (
                panneau.enregistrer() is True
            )

            assert (
                etude.parametres
                .fusion["prompt"]
                == (
                    "Fusion spéciale de cette "
                    "étude."
                )
            )

            # L'assistance utilise la nouvelle
            # copie locale.
            client = ClientFactice()

            service = service_test(etude, client)

            assert service.prompt_effectif() == (
                "Fusion spéciale de cette étude."
            )

        finally:
            dialogue.close()
