# tests/unit/test_p20_4_export_docx.py
"""
P20.4 — Export DOCX STRUCTURÉ du document ouvrage
édité : styles Titre 1 / sous-titres, métadonnées
de réunion en note ou annexe selon réglage ;
fidèle à la structure éditée.
"""

import os

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

import pytest

from docx import Document as DocxDocument

from models.ouvrage import (
    ElementOuvrage,
    ProvenanceParagraphe,
    TYPE_PARAGRAPHE,
    TYPE_SEPARATEUR,
    TYPE_SOUS_TITRE,
    TYPE_TITRE_1,
    DocumentOuvrage,
)
from services.export_ouvrage import (
    exporter_document_docx,
)
from services.settings import SettingsManager


def _prov(reunion, fid, numero, date="2026-10-13", locuteurs="Philippe"):
    return ProvenanceParagraphe(
        reunion=reunion,
        fid=fid,
        numero_reunion=numero,
        date_reunion=date,
        locuteurs=locuteurs,
        numero_version=1,
        horodatage_version="2026-10-13",
    )


def _document() -> DocumentOuvrage:

    doc = DocumentOuvrage(titre="Évangile de Luc")

    doc.elements.append(
        ElementOuvrage(
            id="t1_1",
            type=TYPE_TITRE_1,
            texte="Chapitre 1",
        )
    )

    doc.elements.append(
        ElementOuvrage(
            id="st1",
            type=TYPE_SOUS_TITRE,
            texte="La naissance",
        )
    )

    doc.elements.append(
        ElementOuvrage(
            id="p1",
            type=TYPE_PARAGRAPHE,
            texte="« Première pensée » du bloc 1.",
            provenances=[_prov("luc1b", 1, 1)],
        )
    )

    doc.elements.append(
        ElementOuvrage(
            id="sep1",
            type=TYPE_SEPARATEUR,
        )
    )

    doc.elements.append(
        ElementOuvrage(
            id="p2",
            type=TYPE_PARAGRAPHE,
            texte="Seconde pensée du bloc 2.",
            provenances=[_prov("luc2a", 2, 2, date="2026-10-20")],
        )
    )

    return doc


def _styles(chemin):
    doc = DocxDocument(str(chemin))
    return [
        (p.style.name, p.text)
        for p in doc.paragraphs
    ]


class TestExportDocxStructure:

    def test_styles_titre1_sous_titres(self, tmp_path):

        doc = _document()

        chemin = exporter_document_docx(
            doc,
            tmp_path / "ouvrage.docx",
            metadonnees="note",
            bible="Bible — Traduction J. N. Darby révisée",
        )

        assert chemin.is_file()

        entrees = _styles(chemin)

        styles = {
            texte: style
            for style, texte in entrees
        }

        # Titre de l'ouvrage (Heading 0/Title).
        assert entrees[0][0] in (
            "Title",
            "Heading 0",
        )

        # Titre 1 = style Titre 1, sous-titre =
        # Heading 2.
        assert styles["Chapitre 1"] == "Heading 1"
        assert styles["La naissance"] == "Heading 2"

        # Guillemets normalisés « … ».
        assert any(
            "“Première pensée”" in texte
            for _s, texte in entrees
        )

        # Bible de référence mentionnée.
        assert any(
            "Bible de référence" in texte
            for _s, texte in entrees
        )

    def test_metadonnees_en_note(self, tmp_path):

        doc = _document()

        chemin = exporter_document_docx(
            doc,
            tmp_path / "ouvrage.docx",
            metadonnees="note"
        )

        docx = DocxDocument(str(chemin))

        notes = [
            p for p in docx.paragraphs
            if p.runs and p.runs[0].italic
        ]

        textes_notes = [" ".join(p.text.split()) for p in notes]

        # Une note par paragraphe, avec la
        # provenance (réunion, date, bloc).
        assert any(
            "R1" in t and "2026-10-13" in t and "bloc 1" in t
            for t in textes_notes
        )

        assert any(
            "R2" in t and "2026-10-20" in t
            for t in textes_notes
        )

        # Pas d'annexe.
        assert not any(
            "Annexe" in p.text
            for p in docx.paragraphs
        )

    def test_metadonnees_en_annexe(self, tmp_path):

        doc = _document()

        chemin = exporter_document_docx(
            doc,
            tmp_path / "ouvrage.docx",
            metadonnees="annexe"
        )

        docx = DocxDocument(str(chemin))

        # Annexe en fin de document.
        assert any(
            p.text.startswith("Annexe")
            and p.style.name == "Heading 1"
            for p in docx.paragraphs
        )

        # Les réunions y figurent.
        assert any(
            "R1" in p.text and "luc1b" in p.text
            for p in docx.paragraphs
        )

        assert any(
            "R2" in p.text and "luc2a" in p.text
            for p in docx.paragraphs
        )

        # Pas de note italique sous les paragraphes.
        assert not any(
            p.runs and p.runs[0].italic and "bloc" in p.text
            for p in docx.paragraphs
        )

    def test_reglage_note_ou_annexe(self, tmp_path):

        settings = SettingsManager(
            str(tmp_path / "reglages")
        )

        # Défaut : note.
        assert settings.get_export_ouvrage_prefs()[
            "metadonnees"
        ] == "note"

        settings.set_export_ouvrage_prefs(
            {"metadonnees": "annexe"}
        )

        recharge = SettingsManager(
            str(tmp_path / "reglages")
        )

        assert recharge.get_export_ouvrage_prefs()[
            "metadonnees"
        ] == "annexe"


class TestUiBouton:

    def test_bouton_export_docx(self, tmp_path):
        """
        Page Ouvrage : le bouton « Export DOCX
        structuré… » existe (le flux complet passe
        par des dialogues modaux, testés à part).
        """

        import os as _os

        _os.environ.setdefault(
            "QT_QPA_PLATFORM",
            "offscreen"
        )

        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()

        if app is None:
            app = QApplication([])

        from services.etude_io import (
            ajouter_version_reformulation,
            ouvrir_etude,
            sauvegarder_etude,
            valider_version_reformulation,
        )
        from services.ouvrage_document import (
            generer_document,
            sauvegarder_ouvrage,
        )
        from services.settings import SettingsManager
        from tests.unit.test_reformulation_ui import (
            construire_etude_test,
        )
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

        try:

            assert (
                fenetre.export_docx_button.text()
                == "📄 Export DOCX structuré…"
            )

        finally:
            fenetre.close()
