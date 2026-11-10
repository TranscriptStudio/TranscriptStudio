# tests/unit/test_p18_9bis_etude.py
"""
P18.9-bis — Correctifs de relecture 2 de la page
Étude (David, 2026-11-10) + conformité P20.6b, feuille
d'autorité SPEC_PAGE_ETUDE_ET_SYNTHESE_MODIFS_
2026-11-10b §7, invariants 15-19 (et 9-10 pour la
conformité P20.6b) :

15. gouttière gauche : exactement N labels numérotés
    1 à N pour N tuiles, alignés sur les rangées ;
    labels FIXES (seule la tuile se déplace au
    glisser-déposer) ; aucun label sans tuile ; le
    titre d'une tuile ne porte jamais de numéro ;
16. aucune info-bulle au survol de la zone des
    tuiles ou des tuiles ;
17. la page Étude n'affiche aucune version de Bible
    (ni badge d'en-tête, ni mention sous la synthèse) ;
18. les 4 actions haut droit sont de vrais boutons,
    « ... » supprimés de « ＋ Ajouter une réunion » et
    « (Re)générer la synthèse », et aucune info-bulle
    de l'app ne mentionne de référence de spec ;
19. « Renommer… » (clic droit) modifie uniquement le
    titre d'affichage de la réunion — jamais les noms
    de fichiers/dossiers ni les références de l'étude.

Conformité P20.6b (bug relevé en relecture 2) :
« Alimenter la synthèse globale » présent DÈS QU'une
réunion a des blocs validés, absent sinon, et
fonctionnel (invariants 9-10).
"""

import json
import os
import re
import shutil

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

import pytest

pytestmark = pytest.mark.qt

from PySide6.QtWidgets import (
    QApplication,
    QDoubleSpinBox,
    QLabel,
    QPushButton,
)

from services.etude_io import (
    ajouter_reunion,
    ajouter_version_reformulation,
    creer_etude,
    ouvrir_etude,
    sauvegarder_etude,
    valider_version_reformulation,
)
from services.settings import SettingsManager
from services.traitements.synthese import (
    reunion_a_blocs_valides,
    reunion_entierement_validee,
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


def _page_2_reunions(qapp, tmp_path):
    """
    Page Étude à DEUX réunions (ordre [n1, n2]).
    """

    _p, _pv, _e, n1 = construire_etude_test(tmp_path)

    etude = ouvrir_etude(tmp_path / "Etude")

    dossier2 = tmp_path / "reunion_2"
    shutil.copytree(tmp_path / "2026-10-13_Luc1b", dossier2)
    shutil.rmtree(
        dossier2 / "transcriptstudio",
        ignore_errors=True,
    )

    n2 = ajouter_reunion(etude, dossier2, "Chapitre 2")

    sauvegarder_etude(etude)

    from ui.etude_window import EtudeWindow

    fenetre = EtudeWindow(
        tmp_path / "Etude",
        settings=SettingsManager(str(tmp_path / "reglages")),
    )

    # L'étude de la fenêtre (objet ouvert par la page).
    return fenetre, tmp_path, fenetre.etude, [n1, n2]


def _valider_blocs(etude, nom, fids):
    for fid in fids:
        v = ajouter_version_reformulation(
            etude,
            nom,
            fid,
            f"Pensée du bloc {fid} de {nom}.",
        )
        valider_version_reformulation(
            etude,
            nom,
            fid,
            numero=v.numero,
            validateur="Test",
        )


def _fids_de(etude, nom):
    return [
        e.fid
        for e in etude.registre.entrees.values()
        if e.reunion == nom
    ]


def _labels_gouttiere(fenetre):
    return [
        fenetre.gouttiere_numeros.item(i).text()
        for i in range(fenetre.gouttiere_numeros.count())
    ]


class TestGouttierePositionnelle:
    """
    Invariant 15.
    """

    def test_labels_1_a_n(self, qapp, tmp_path):

        fenetre, _tmp, _e, noms = _page_2_reunions(
            qapp, tmp_path
        )

        try:

            assert (
                fenetre.reunions_liste.count()
                == len(noms)
            )

            # Exactement N labels, 1 à N dans l'ordre.
            assert _labels_gouttiere(fenetre) == [
                str(i + 1) for i in range(len(noms))
            ]

            # Aucun label sans tuile.
            assert (
                fenetre.gouttiere_numeros.count()
                == fenetre.reunions_liste.count()
            )

            # Chaque label aligné sur la rangée de sa
            # tuile (même hauteur).
            for i in range(len(noms)):
                item = fenetre.reunions_liste.item(i)
                label = fenetre.gouttiere_numeros.item(i)
                assert (
                    label.sizeHint().height()
                    == item.sizeHint().height()
                )

        finally:
            fenetre.close()

    def test_labels_fixes_au_reordonnancement(
        self, qapp, tmp_path
    ):

        fenetre, tmp_path, _e, noms = _page_2_reunions(
            qapp, tmp_path
        )

        try:

            inverse = list(reversed(noms))

            fenetre._persister_ordre(inverse)

            # L'ordre des réunions a changé...
            assert (
                fenetre.etude.etude.ordre_reunions
                == inverse
            )

            # ...mais les labels restent 1..N en place.
            assert _labels_gouttiere(fenetre) == [
                "1",
                "2",
            ]

            # Persistance à la réouverture.
            recharge = ouvrir_etude(tmp_path / "Etude")
            assert recharge.etude.ordre_reunions == inverse

        finally:
            fenetre.close()

    def test_tuile_sans_numero(self, qapp, tmp_path):

        fenetre, _tmp, _e, _noms = _page_2_reunions(
            qapp, tmp_path
        )

        try:

            for i in range(fenetre.reunions_liste.count()):
                item = fenetre.reunions_liste.item(i)
                tuile = fenetre.reunions_liste.itemWidget(
                    item
                )

                textes = [
                    label.text()
                    for label in tuile.findChildren(QLabel)
                ]

                # Le titre de la tuile ne porte JAMAIS
                # de numéro.
                assert not any(
                    re.fullmatch(
                        r"Réunion\s+\d+",
                        t.strip(),
                    )
                    for t in textes
                )

        finally:
            fenetre.close()


class TestAucuneInfoBulleZoneTuiles:
    """
    Invariant 16.
    """

    def test_pas_de_tooltip_zone_ni_tuile(self, qapp, tmp_path):

        fenetre, _tmp, _e, _noms = _page_2_reunions(
            qapp, tmp_path
        )

        try:

            assert fenetre.reunions_liste.toolTip() == ""

            for i in range(fenetre.reunions_liste.count()):
                item = fenetre.reunions_liste.item(i)
                tuile = fenetre.reunions_liste.itemWidget(
                    item
                )

                assert tuile.toolTip() == ""

        finally:
            fenetre.close()


class TestAucuneMentionBiblePageEtude:
    """
    Invariant 17.
    """

    def test_page_sans_bible(self, qapp, tmp_path):

        fenetre, _tmp, _e, _noms = _page_2_reunions(
            qapp, tmp_path
        )

        try:

            # Ni badge d'en-tête...
            assert not hasattr(
                fenetre,
                "badge_bible_label"
            )

            # ...ni aucune mention « Bible » dans les
            # labels de la page (dont le statut sous la
            # synthèse).
            textes = [
                label.text()
                for label in fenetre.findChildren(QLabel)
            ]

            assert not any(
                "Bible" in t for t in textes
            )

        finally:
            fenetre.close()


class TestBoutonsHautDroit:
    """
    Invariant 18.
    """

    def test_vrais_boutons_sans_points_de_suspension(
        self, qapp, tmp_path
    ):

        fenetre, _tmp, _e, _noms = _page_2_reunions(
            qapp, tmp_path
        )

        try:

            for bouton in (
                fenetre.ajouter_button,
                fenetre.ouvrage_button,
                fenetre.synthese_regenerer_button,
                fenetre.synthese_editer_button,
            ):
                assert isinstance(bouton, QPushButton)

            assert (
                fenetre.ajouter_button.text()
                == "＋ Ajouter une réunion"
            )

            assert (
                fenetre.synthese_regenerer_button.text()
                == "(Re)générer la synthèse"
            )

            # Info-bulle « (Re)générer » raccourcie,
            # sans référence de spec.
            tooltip = (
                fenetre.synthese_regenerer_button.toolTip()
            )

            assert "remplace" in tooltip.lower()
            assert not re.search(r"P\d", tooltip)

        finally:
            fenetre.close()

    def test_aucune_info_bulle_avec_reference_de_spec(
        self, qapp, tmp_path
    ):
        """
        Invariant 18 (généralisation de l'invariant 4) :
        aucune info-bulle de l'app (tous les appels
        setToolTip des sources ui/) ne mentionne de
        référence de spec (P18/P20/...).
        """

        import ast

        from ui import etude_window as module_ui

        dossier_ui = os.path.dirname(
            os.path.abspath(module_ui.__file__)
        )

        motif = re.compile(
            r"\bP\d{1,2}(\.\d+)?[a-z]?-bis\b"
            r"|\bP\d{1,2}\.\d+[a-z]?\b"
            r"|\bP\d{1,2}\b"
        )

        for nom in sorted(os.listdir(dossier_ui)):

            if not nom.endswith(".py"):
                continue

            source = open(
                os.path.join(dossier_ui, nom),
                encoding="utf-8",
            ).read()

            arbre = ast.parse(source)

            for noeud in ast.walk(arbre):

                if not isinstance(noeud, ast.Call):
                    continue

                fonction = noeud.func

                if not (
                    isinstance(fonction, ast.Attribute)
                    and fonction.attr == "setToolTip"
                ):
                    continue

                # Toutes les constantes chaîne passées
                # à setToolTip(...) forment l'info-bulle.
                for arg in (
                    list(noeud.args)
                    + [
                        kw.value for kw in noeud.keywords
                    ]
                ):
                    for sous in ast.walk(arg):
                        if isinstance(
                            sous,
                            ast.Constant,
                        ) and isinstance(sous.value, str):
                            assert not motif.search(
                                sous.value
                            ), (
                                f"{nom} : info-bulle avec "
                                f"référence de spec : "
                                f"{sous.value!r}"
                            )


class TestRenommerClicDroit:
    """
    Invariant 19.
    """

    def test_menu_renommer_present(self, qapp, tmp_path):

        fenetre, _tmp, _e, noms = _page_2_reunions(
            qapp, tmp_path
        )

        try:

            item = fenetre.reunions_liste.item(0)

            menu = fenetre._construire_menu_tuile(
                noms[0],
                item
            )

            textes = [a.text() for a in menu.actions()]

            assert "Renommer…" in textes

        finally:
            fenetre.close()

    def test_renommer_modifie_uniquement_le_titre(
        self, qapp, tmp_path, monkeypatch
    ):

        fenetre, tmp_path, etude, noms = (
            _page_2_reunions(qapp, tmp_path)
        )

        nom = noms[0]

        dossier_projet = tmp_path / nom
        empreinte = sorted(
            p.name for p in dossier_projet.iterdir()
        )

        ordre_avant = list(etude.etude.ordre_reunions)

        try:

            from unittest.mock import patch

            with patch(
                "PySide6.QtWidgets.QInputDialog.getText",
                staticmethod(
                    lambda *a, **k: ("Nouveau titre", True)
                ),
            ):
                fenetre._renommer_reunion(nom)

            # Titre d'affichage modifié...
            assert etude.reunions[nom].titre_1 == (
                "Nouveau titre"
            )

            # ...persisté dans reunions/<nom>.json...
            relue = json.loads(
                (
                    tmp_path / "Etude" / "reunions"
                    / f"{nom}.json"
                ).read_text(encoding="utf-8")
            )

            assert relue["titre_1"] == "Nouveau titre"

            # ...mais AUCUN nom de fichier/dossier ni
            # référence de l'étude n'a changé.
            assert sorted(
                p.name for p in dossier_projet.iterdir()
            ) == empreinte

            assert (
                etude.etude.ordre_reunions == ordre_avant
            )

            assert (
                (tmp_path / "Etude" / "reunions").exists()
            )

            # La tuile réaffichée porte le nouveau titre.
            item = fenetre.reunions_liste.item(0)
            tuile = fenetre.reunions_liste.itemWidget(item)

            textes = [
                label.text()
                for label in tuile.findChildren(QLabel)
            ]

            assert "Nouveau titre" in textes

        finally:
            fenetre.close()

    def test_titre_vide_refuse(self, qapp, tmp_path):

        from unittest.mock import patch

        fenetre, _tmp, etude, noms = _page_2_reunions(
            qapp, tmp_path
        )

        nom = noms[0]

        try:

            with patch(
                "PySide6.QtWidgets.QInputDialog.getText",
                staticmethod(
                    lambda *a, **k: ("   ", True)
                ),
            ):
                fenetre._renommer_reunion(nom)

            assert etude.reunions[nom].titre_1 != ""

        finally:
            fenetre.close()


class TestConformiteP206b:
    """
    Non-conformité P20.6b (relecture 2) : « Alimenter
    la synthèse globale » présent DÈS QU'une réunion a
    des blocs validés (invariant 9), absent sinon, et
    fonctionnel.
    """

    def test_predicat_reunion_a_blocs_valides(
        self, qapp, tmp_path
    ):

        fenetre, tmp_path, etude, noms = (
            _page_2_reunions(qapp, tmp_path)
        )

        try:

            n1, n2 = noms

            # Aucune validation : False (sans erreur).
            assert not reunion_a_blocs_valides(etude, n1)

            # Validation PARTIELLE de n1 (1 bloc sur
            # plusieurs) : True — c'est la conformité
            # P20.6b (« a des blocs validés »).
            fids1 = _fids_de(etude, n1)
            assert len(fids1) >= 1

            _valider_blocs(etude, n1, fids1[:1])

            assert reunion_a_blocs_valides(etude, n1)
            assert not reunion_entierement_validee(etude, n1)

            # Tous les blocs validés : True aussi.
            _valider_blocs(etude, n1, fids1[1:])
            assert reunion_entierement_validee(etude, n1)
            assert reunion_a_blocs_valides(etude, n1)

            # n2 sans aucune validation : False.
            assert not reunion_a_blocs_valides(etude, n2)

        finally:
            fenetre.close()

    def test_menu_alimenter_des_qu_a_des_blocs_valides(
        self, qapp, tmp_path
    ):

        fenetre, tmp_path, etude, noms = (
            _page_2_reunions(qapp, tmp_path)
        )

        try:

            n1, n2 = noms

            fids1 = _fids_de(etude, n1)

            # Validation partielle de n1.
            _valider_blocs(etude, n1, fids1[:1])

            sauvegarder_etude(etude)

            for i in range(fenetre.reunions_liste.count()):
                item = fenetre.reunions_liste.item(i)
                nom = item.data(0x0100)

                menu = fenetre._construire_menu_tuile(
                    nom, item
                )

                textes = [
                    a.text() for a in menu.actions()
                ]

                if nom == n1:
                    # Blocs validés (même partiellement)
                    # : l'entrée est présente.
                    assert (
                        "Alimenter la synthèse globale"
                        in textes
                    )
                else:
                    # Aucun bloc validé : absent.
                    assert (
                        "Alimenter la synthèse globale"
                        not in textes
                    )

        finally:
            fenetre.close()

    def test_alimenter_fonctionnel_avec_blocs_partiels(
        self, qapp, tmp_path
    ):
        """
        L'entrée de menu est FONCTIONNELLE : alimenter
        une réunion à blocs validés (même partiellement)
        fonctionne (ajout incrémental, invariants 9-10).
        """

        from services.llm.catalogue import (
            catalogue_par_defaut,
        )
        from services.llm.client import (
            ResultatCompletion,
        )
        from services.traitements.synthese import (
            ServiceSynthese,
        )

        fenetre, tmp_path, etude, noms = (
            _page_2_reunions(qapp, tmp_path)
        )

        try:

            n1, n2 = noms

            # n1 : un seul bloc validé (partiel).
            _valider_blocs(etude, n1, _fids_de(etude, n1)[:1])

            sauvegarder_etude(etude)

            class ClientFactice:

                def __init__(self):
                    self.appels = []

                def completions(
                    self,
                    prompt_systeme,
                    messages,
                    parametres,
                    streaming_callback=None,
                    annulation=None,
                ):
                    self.appels.append(prompt_systeme)

                    return ResultatCompletion(
                        texte="Contribution.",
                        tokens_in=10,
                        tokens_out=5,
                        duree_ms=5,
                        cout_estime=0.01,
                        modele=parametres.modele,
                        fournisseur="openai",
                    )

            class StoreFactice:

                def get_cle_llm(self, fournisseur_id):
                    return "cle"

            client = ClientFactice()

            service = ServiceSynthese(
                etude,
                parametres_app={
                    "fournisseur": "openai",
                    "modele": "gpt-4.1",
                },
                credential_store=StoreFactice(),
                catalogue=catalogue_par_defaut(),
                client_factory=(
                    lambda fournisseur, cle: client
                ),
                dossier_prompts=tmp_path / "prompts",
            )

            # Fonctionne malgré la validation partielle.
            version, stats, remplace = service.alimenter(n1)

            assert remplace is False
            assert version.texte
            assert n1 in etude.synthese.contributions

            # n2 sans bloc validé : refus.
            from services.etude_io import EtudeError

            with pytest.raises(EtudeError):
                service.alimenter(n2)

        finally:
            fenetre.close()
