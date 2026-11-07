"""
Tests P19.4 — fusion de pensées (feuille de
route v2.1 §P19) : deux paragraphes dont la
pensée est très similaire (même locuteur ou
locuteurs différents) deviennent UN SEUL
paragraphe portant les PROVENANCES MULTIPLES.

Opération de COMPOSITION DE L'OUVRAGE, jamais de
la page Reformulation (qui reste 1 bloc = 1
reformulation, sans exception d'attribution) ;
fusion manuelle ou assistée LLM (les deux textes
en entrée + consigne, résultat TOUJOURS validé
explicitement) ; réversible — dé-fusion : chaque
paragraphe reprend son texte, le paragraphe
fusionné est conservé dans l'historique de
l'ouvrage ; les fusions vivent dans le document
dérivé (les textes validés et le registre ne
bougent jamais).
"""

import os
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

import pytest

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QMessageBox,
)

from models.ouvrage import SOURCE_FUSION
from services.etude_io import (
    ajouter_version_reformulation,
    valider_version_reformulation,
)
from services.llm.catalogue import (
    catalogue_par_defaut,
)
from services.llm.client import ResultatCompletion
from services.ouvrage_document import (
    FusionPenseesError,
    charger_ouvrage,
    defusionner_pensees,
    fusionner_pensees,
    generer_document,
    sauvegarder_ouvrage,
)
from services.settings import SettingsManager
from services.traitements.fusion import (
    CONSIGNE_FUSION,
    ServiceFusion,
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


PARAMETRES_APP = {
    "fournisseur": "openai",
    "modele": "gpt-4.1",
    "temperature": 0.3,
    "temperatures": {
        "reformulation": 0.3,
    },
}


class StoreFactice:
    """
    CredentialStore factice : une clé par
    fournisseur.
    """

    def get_cle_llm(self, fournisseur_id):
        return f"cle-{fournisseur_id}"


class ClientFactice:
    """
    Client LLM factice : enregistre l'appel,
    renvoie une réponse fixe.
    """

    def __init__(self, reponse="Paragraphe fusionné par l'IA."):
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
            "temperature": parametres.temperature,
            "modele": parametres.modele,
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


@pytest.fixture
def etude_validee(qapp, tmp_path):
    """
    Étude d'une réunion de TROIS blocs, tous avec
    une reformulation VALIDÉE.
    """

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


@pytest.fixture
def document(etude_validee):
    """
    Document ouvrage généré (TROIS paragraphes en
    « Réserves »).
    """

    etude, _nom, fids, _tmp = etude_validee

    return generer_document(etude)


#
# ==================================================
# Services : fusion, provenances multiples, erreurs.
# ==================================================
#

class TestFusionDocument:

    def test_fusion_provenances_multiples(
        self,
        document,
        etude_validee
    ):
        """
        La fusion porte les provenances des DEUX
        paragraphes (FIDs multiples), prend la
        place du PREMIER dans l'ordre du document,
        et conserve l'instantané des originaux
        pour la dé-fusion.
        """

        etude, _n, fids, _t = etude_validee

        paragraphes = document.paragraphes()

        fusionne = fusionner_pensees(
            document,
            paragraphes[1].id,
            paragraphes[0].id,
            "Pensée unique, fusionnée."
        )

        assert fusionne.source == SOURCE_FUSION

        assert fusionne.texte == (
            "Pensée unique, fusionnée."
        )

        assert [
            p.fid for p in fusionne.provenances
        ] == [fids[0], fids[1]]

        # À la place du premier, ordre conservé.
        assert document.paragraphes() == [
            fusionne,
            paragraphes[2],
        ]

        # Instantané complet des originaux.
        instantanes = (
            fusionne.fusion["elements"]
        )

        assert [
            e["texte"] for e in instantanes
        ] == [
            f"Reformulation du bloc {fids[0]}",
            f"Reformulation du bloc {fids[1]}",
        ]

    def test_fusion_erreurs(
        self,
        document
    ):
        """
        Refus : id identiques, id inconnu, élément
        non paragraphe, texte fusionné vide.
        """

        p1, p2, _p3 = document.paragraphes()

        with pytest.raises(FusionPenseesError):
            fusionner_pensees(
                document,
                p1.id,
                p1.id,
                "Texte"
            )

        with pytest.raises(FusionPenseesError):
            fusionner_pensees(
                document,
                p1.id,
                "inconnu",
                "Texte"
            )

        from models.ouvrage import TYPE_TITRE_1

        chapitre = document.nouvel_id("t1")

        document.elements.insert(
            0,
            type(
                "E",
                (),
                {"id": chapitre,
                 "type": TYPE_TITRE_1}
            )(),
        )

        with pytest.raises(FusionPenseesError):
            fusionner_pensees(
                document,
                document.paragraphes()[1].id,
                chapitre,
                "Texte"
            )

        with pytest.raises(FusionPenseesError):
            fusionner_pensees(
                document,
                p1.id,
                p2.id,
                "   "
            )

    def test_fusion_imbriquee(
        self,
        document
    ):
        """
        Un paragraphe FUSIONNÉ peut être fusionné à
        son tour : les provenances s'accumulent
        (trois ici).
        """

        p1, p2, p3 = document.paragraphes()

        premiere = fusionner_pensees(
            document,
            p1.id,
            p2.id,
            "Première fusion."
        )

        seconde = fusionner_pensees(
            document,
            premiere.id,
            p3.id,
            "Seconde fusion."
        )

        assert len(seconde.provenances) == 3

        assert document.paragraphes() == [seconde]

    def test_ne_touche_ni_les_textes_ni_le_registre(
        self,
        document,
        etude_validee
    ):
        """
        Composition de l'OUVRAGE uniquement : ni
        les reformulations validées ni le registre
        de l'étude ne changent (jamais d'exception
        d'attribution sur la page Reformulation).
        """

        etude, _n, _fids, _t = etude_validee

        avant = {
            fid: (
                len(resultat.versions),
                [
                    version.texte
                    for version in (
                        resultat.versions
                    )
                ],
            )
            for fid, resultat in (
                etude.reformulations.items()
            )
        }

        fusionne = fusionner_pensees(
            document,
            document.paragraphes()[0].id,
            document.paragraphes()[1].id,
            "Fusion."
        )

        defusionner_pensees(
            document,
            fusionne.id
        )

        apres = {
            fid: (
                len(resultat.versions),
                [
                    version.texte
                    for version in (
                        resultat.versions
                    )
                ],
            )
            for fid, resultat in (
                etude.reformulations.items()
            )
        }

        assert avant == apres


#
# ==================================================
# Dé-fusion : réversibilité et historique.
# ==================================================
#

class TestDefusion:

    def test_defusion_restitue_les_textes(
        self,
        document,
        etude_validee
    ):
        """
        Chaque paragraphe REPREND son texte à sa
        place ; le paragraphe fusionné est conservé
        dans l'historique de l'ouvrage.
        """

        etude, _n, fids, _t = etude_validee

        p1, _p2, p3 = document.paragraphes()

        fusionne = fusionner_pensees(
            document,
            p1.id,
            document.paragraphes()[1].id,
            "Texte disparu du corps ? Non : historique."
        )

        retir = defusionner_pensees(
            document,
            fusionne.id
        )

        assert retir is fusionne

        paragraphes = document.paragraphes()

        assert len(paragraphes) == 3

        assert paragraphes[0].texte == (
            f"Reformulation du bloc {fids[0]}"
        )

        assert paragraphes[2].id == p3.id

        assert paragraphes[0].source != SOURCE_FUSION

        # Le texte fusionné n'est pas perdu.
        assert len(document.historique) == 1

        entree = document.historique[0]

        assert entree["paragraphe"]["texte"] == (
            "Texte disparu du corps ? "
            "Non : historique."
        )

        assert entree["horodatage"]

    def test_defusion_refuse_non_fusion(
        self,
        document
    ):
        """
        La dé-fusion exige un paragraphe issu d'une
        fusion (source « fusion »).
        """

        p1 = document.paragraphes()[0]

        with pytest.raises(FusionPenseesError):
            defusionner_pensees(document, p1.id)

        with pytest.raises(FusionPenseesError):
            defusionner_pensees(
                document,
                "inconnu"
            )

    def test_persistance_disque(
        self,
        document,
        etude_validee
    ):
        """
        Le snapshot de fusion vit dans
        ouvrage.json ; après dé-fusion, l'historique
        y vit aussi (écrire puis relire).
        """

        _e, _n, _f, tmp = etude_validee

        fusionne = fusionner_pensees(
            document,
            document.paragraphes()[0].id,
            document.paragraphes()[1].id,
            "Fusion persistée."
        )

        sauvegarder_ouvrage(
            document,
            tmp / "Etude"
        )

        relu = charger_ouvrage(tmp / "Etude")

        faux = relu.paragraphes()[0]

        assert faux.source == SOURCE_FUSION
        assert faux.fusion == fusionne.fusion

        defusionner_pensees(relu, faux.id)

        sauvegarder_ouvrage(relu, tmp / "Etude")

        relu2 = charger_ouvrage(tmp / "Etude")

        assert len(relu2.historique) == 1

        assert len(relu2.paragraphes()) == 3


#
# ==================================================
# Assistance LLM : les deux textes + la consigne.
# ==================================================
#

class TestServiceFusion:

    def service_test(self, etude, client):

        return ServiceFusion(
            etude,
            parametres_app=PARAMETRES_APP,
            credential_store=StoreFactice(),
            catalogue=catalogue_par_defaut(),
            client_factory=(
                lambda fournisseur, cle: client
            ),
        )

    def test_proposition_appel(
        self,
        document,
        etude_validee
    ):
        """
        UN appel : prompt système = prompt de
        reformulation de l'étude (style de
        l'ouvrage), message = les DEUX textes en
        entrée + la consigne ; résultat rapporté,
        rien n'est écrit dans le document.
        """

        etude, _n, fids, _t = etude_validee

        client = ClientFactice()

        service = self.service_test(etude, client)

        p1, p2, _p3 = document.paragraphes()

        resultat = service.proposer(
            p1.texte,
            p2.texte
        )

        assert (
            resultat.texte
            == "Paragraphe fusionné par l'IA."
        )

        appel = client.appels[0]

        assert appel["prompt_systeme"] == (
            etude.parametres
            .reformulation
            .get("prompt", "")
        )

        assert (
            f"Reformulation du bloc {fids[0]}"
            in appel["message"]
        )

        assert (
            f"Reformulation du bloc {fids[1]}"
            in appel["message"]
        )

        assert CONSIGNE_FUSION in appel["message"]

        # Aucune écriture dans le document.
        assert len(document.paragraphes()) == 3

    def test_configuration(
        self,
        etude_validee
    ):
        """
        Même résolution que le moteur : fournisseur
        des réglages app, modèle gpt-4.1,
        température « reformulation ».
        """

        etude, _n, _f, _t = etude_validee

        client = ClientFactice()

        service = self.service_test(etude, client)

        assert service.temperature_effective() == (
            0.3
        )

        service.proposer("Texte 1", "Texte 2")

        appel = client.appels[0]

        assert appel["modele"] == "gpt-4.1"

        assert appel["temperature"] == 0.3


#
# ==================================================
# Page Ouvrage : dialogue, boutons, rapport.
# ==================================================
#

class DialogueFactice:
    """
    Dialogue de fusion factice : accepte, renvoie
    un texte fusionné fixe, retient les éléments
    reçus et le service proposé.
    """

    instances = []

    def __init__(
        self,
        parent,
        element_1,
        element_2,
        service=None
    ):
        self.element_1 = element_1
        self.element_2 = element_2
        self.service = service
        self.texte = "Pensée fusionnée, manuellement."

        DialogueFactice.instances.append(self)

    def exec(self):
        return QDialog.DialogCode.Accepted

    def texte_fusionne(self):
        return self.texte


@pytest.fixture
def page(qapp, etude_validee):

    etude, _nom, _fids, tmp_path = (
        etude_validee
    )

    from ui.ouvrage_window import OuvrageWindow

    fenetre = OuvrageWindow(
        etude,
        settings=SettingsManager(
            str(tmp_path / "reglages")
        )
    )

    yield fenetre

    fenetre.close()


def selectionner(page, ids: list):
    """
    Sélectionne les éléments d'arborescence dont
    l'identifiant est dans ids (et rien d'autre).
    """

    page.arbre.clearSelection()

    def visiter(noeud):

        if noeud.data(
            0,
            Qt.ItemDataRole.UserRole
        ) in ids:
            noeud.setSelected(True)

        for j in range(noeud.childCount()):
            visiter(noeud.child(j))

    for i in range(page.arbre.topLevelItemCount()):
        visiter(page.arbre.topLevelItem(i))


class TestPageFusion:

    def test_boutons_selon_selection(
        self,
        page
    ):
        """
        « Fusionner » n'est actif qu'avec DEUX
        paragraphes sélectionnés ; « Dé-fusionner »
        qu'avec UN paragraphe fusionné.
        """

        page.generer_ouvrage()

        paragraphes = page.document.paragraphes()

        # Aucune sélection : rien d'actif.
        assert not page.fusion_button.isEnabled()
        assert not page.defusion_button.isEnabled()

        selectionner(
            page,
            [paragraphes[0].id]
        )

        assert not page.fusion_button.isEnabled()
        assert not page.defusion_button.isEnabled()

        selectionner(
            page,
            [
                paragraphes[0].id,
                paragraphes[2].id,
            ]
        )

        assert page.fusion_button.isEnabled()
        assert not page.defusion_button.isEnabled()

    def test_fusion_depuis_la_page(
        self,
        page
    ):
        """
        Le dialogue (factice) accepte : le document
        reçoit le paragraphe fusionné (provenances
        multiples, dé-fusion possible), la page est
        marquée modifiée, le rapport signale la
        fusion.
        """

        page.generer_ouvrage()

        paragraphes = page.document.paragraphes()

        selectionner(
            page,
            [
                paragraphes[1].id,
                paragraphes[0].id,
            ]
        )

        DialogueFactice.instances = []

        with patch(
            "ui.ouvrage_window"
            ".FusionPenseesDialog",
            DialogueFactice
        ):
            page.sur_fusion_pensees()

        assert len(DialogueFactice.instances) == 1

        dialogue = DialogueFactice.instances[0]

        assert dialogue.element_1 is paragraphes[0]

        assert (
            dialogue.service is not None
        ), "l'assistance IA doit être branchée"

        reste = page.document.paragraphes()

        assert len(reste) == 2

        fusionne = reste[0]

        assert fusionne.source == SOURCE_FUSION

        assert fusionne.texte == (
            "Pensée fusionnée, manuellement."
        )

        assert len(fusionne.provenances) == 2

        assert page.modifie is True

        # Rapport et manuscrit : fusion visible.
        rapport = (
            page.rapport_zone.toPlainText()
        )

        assert "Fusions de pensées : 1" in rapport

        libelle_manuscrit = (
            page.editeurs[fusionne.id]
            .findChild(type(page.titre_label))
            .text()
        )

        assert (
            "Fusion de pensées" in libelle_manuscrit
        )

    def test_annulation_ne_touche_a_rien(
        self,
        page
    ):
        """
        « Annuler » (dialogue rejeté) : le document
        du ouvrage reste intact.
        """

        page.generer_ouvrage()

        paragraphes = page.document.paragraphes()

        selectionner(
            page,
            [
                paragraphes[0].id,
                paragraphes[1].id,
            ]
        )

        class DialogueRefuse(DialogueFactice):
            def exec(self):
                return QDialog.DialogCode.Rejected

        with patch(
            "ui.ouvrage_window"
            ".FusionPenseesDialog",
            DialogueRefuse
        ):
            page.sur_fusion_pensees()

        assert len(page.document.paragraphes()) == 3

        assert page.modifie is False

    def test_defusion_depuis_la_page(
        self,
        page,
        etude_validee
    ):
        """
        Fusion puis dé-fusion confirmée : les deux
        paragraphes d'origine reprennent leur texte
        et leur place ; le texte fusionné vit dans
        l'historique (signalé au rapport).
        """

        etude, _n, fids, _t = etude_validee

        page.generer_ouvrage()

        paragraphes = page.document.paragraphes()

        selectionner(
            page,
            [
                paragraphes[0].id,
                paragraphes[1].id,
            ]
        )

        with patch(
            "ui.ouvrage_window"
            ".FusionPenseesDialog",
            DialogueFactice
        ):
            page.sur_fusion_pensees()

        fusionne = page.document.paragraphes()[0]

        selectionner(page, [fusionne.id])

        assert page.defusion_button.isEnabled()

        with patch(
            "ui.ouvrage_window"
            ".QMessageBox.question",
            return_value=(
                QMessageBox.StandardButton.Yes
            ),
        ):
            page.sur_defusion()

        paragraphes = page.document.paragraphes()

        assert len(paragraphes) == 3

        assert paragraphes[0].texte == (
            f"Reformulation du bloc {fids[0]}"
        )

        assert paragraphes[1].texte == (
            f"Reformulation du bloc {fids[1]}"
        )

        assert len(page.document.historique) == 1

        rapport = page.rapport_zone.toPlainText()

        assert "Historique : 1" in rapport

        # Plus rien de fusionné : bouton éteint et
        # rapport sans fusions vives.
        selectionner(page, [paragraphes[0].id])

        assert not page.defusion_button.isEnabled()

        assert (
            "Fusions de pensées : "
            not in rapport
        )


#
# ==================================================
# Dialogue : fusion manuelle et assistance IA.
# ==================================================
#

class TestDialogueFusion:

    def dialogue(self, qapp, document):

        from ui.fusion_pensees_dialog import (
            FusionPenseesDialog,
        )

        p1, p2, _p3 = document.paragraphes()

        return FusionPenseesDialog(
            None,
            p1,
            p2,
            service=object(),
        )

    def test_contenu_initial(
        self,
        qapp,
        document,
        etude_validee
    ):
        """
        Le texte fusionné est PRÉREMPLI avec les
        deux textes_joint (matériau d'une fusion
        manuelle) ; « Annuler » ne produit rien.
        """

        etude, _n, fids, _t = etude_validee

        dialogue = self.dialogue(qapp, document)

        assert dialogue.texte_fusionne() == (
            f"Reformulation du bloc {fids[0]}"
            "\n\n"
            f"Reformulation du bloc {fids[1]}"
        )

        assert dialogue.service is not None

        assert not (
            dialogue.assistance_button.isHidden()
        )

    def test_assistance_sans_service(
        self,
        qapp,
        document
    ):
        """
        Sans service LLM fourni, le bouton
        d'assistance est masqué (fusion manuelle
        toujours possible).
        """

        from ui.fusion_pensees_dialog import (
            FusionPenseesDialog,
        )

        p1, p2, _p3 = document.paragraphes()

        dialogue = FusionPenseesDialog(
            None,
            p1,
            p2,
        )

        assert (
            dialogue.assistance_button.isHidden()
        )

    def test_assistance_object_editeur(
        self,
        qapp,
        document
    ):
        """
        La proposition de l'IA remplit l'éditeur
        (prête à éditer / accepter, rien
        d'automatique).
        """

        dialogue = self.dialogue(qapp, document)

        resultat = ResultatCompletion(
            texte="Proposition de l'IA, éditable."
        )

        dialogue.sur_assistance_terminee(resultat)

        assert dialogue.texte_fusionne() == (
            "Proposition de l'IA, éditable."
        )

        # L'utilisateur peut ajuster avant acceptation.
        dialogue.editeur_fusion.setPlainText(
            "Ajusté à la main."
        )

        assert dialogue.texte_fusionne() == (
            "Ajusté à la main."
        )


#
# ==================================================
# Jamais de la page Reformulation.
# ==================================================
#

class TestReformulationEpargnee:

    def test_fusion_absente_de_la_reformulation(
        self
    ):
        """
        La fusion de pensées est une opération de
        composition de l'OUVRAGE : la page
        Reformulation (1 bloc = 1 reformulation,
        alignés, sans exception d'attribution) n'en
        connaît aucun point d'entrée.
        """

        import ui.ouvrage_window as module_ouvrage
        from ui import reformulation_window
        module_reformulation = reformulation_window


        source = Path(
            module_reformulation.__file__
        ).read_text(encoding="utf-8")

        assert (
            "fusionner_pensees" not in source
        )
        assert (
            "FusionPenseesDialog" not in source
        )

        # L'inverse est vrai : l'ouvrage l'utilise.
        source_ouvrage = Path(
            module_ouvrage.__file__
        ).read_text(encoding="utf-8")

        assert (
            "fusionner_pensees" in source_ouvrage
        )
