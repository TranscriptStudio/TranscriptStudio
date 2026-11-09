"""
Tests P19.1 — modèle de données du document
ouvrage (feuille de route v2.1 §P19).

Contrats couverts :

- **génération** : le document est initialisé à
  partir des reformulations VALIDÉES, réunion
  par réunion (ordre de l'étude), chaque réunion
  dans son ORDRE D'OUVRAGE ; chaque paragraphe
  porte sa provenance (FID, réunion, numéro,
  date, version utilisée) ;
- **structure manuelle** : la génération ne crée
  AUCUN chapitre — tout est en « Réserves »
  jusqu'à ce que des titres soient ajoutés à la
  main ;
- **régénération complète** : elle ÉCRASE le
  document existant (jamais de mise à jour
  incrémentale) ;
- **vie propre** : divergence signalée (« réunion
  re-reformulée depuis la génération ») quand
  une version plus récente existe — le document
  dérivé n'est jamais touché automatiquement ;
- **persistance** : ouvrage.json dans le dossier
  de l'étude, aller-retour complet, erreurs de
  format refusées.
"""

import json
from pathlib import Path

import pytest

from models.ouvrage import (
    DocumentOuvrage,
    ElementOuvrage,
    OuvrageFormatError,
    TYPE_PARAGRAPHE,
    TYPE_TITRE_1,
)
from services.decoupage import (
    definir_ordre_ouvrage,
    generer_decoupage,
)
from services.etude_io import (
    ajouter_reunion,
    ajouter_version_reformulation,
    creer_etude,
    enregistrer_decoupage,
    ouvrir_etude,
    sauvegarder_etude,
    valider_version_reformulation,
)
from services.ouvrage_document import (
    charger_ouvrage,
    chemin_ouvrage,
    generer_document,
    reformulees_depuis_generation,
    reunions_non_placees,
    sauvegarder_ouvrage,
)
from tests.unit.test_fusion_ordre_ouvrage import (
    creer_projet_v1,
    projet_trois_blocs,
)


@pytest.fixture
def etude_deux_reunions(tmp_path):
    """
    Étude de DEUX réunions, chacune avec un
    découpage de trois blocs :

    - réunion 1 : ordre d'ouvrage INVERSÉ
      (3, 2, 1), reformulations validées sur les
      trois blocs ;
    - réunion 2 : ordre chronologique (1, 2, 3),
      reformulations validées sur les blocs 1
      et 2 seulement (le 3 reste non validé :
      il ne doit PAS entrer dans l'ouvrage).
    """

    etude = creer_etude(
        tmp_path / "Etude",
        "Évangile de Luc"
    )

    noms = {}
    fids_par_reunion = {}

    for nom_dossier in (
        "2026-10-13_Luc1b",
        "2026-10-20_Luc2a",
    ):

        projet_v1 = creer_projet_v1(
            tmp_path,
            nom_dossier
        )

        nom = ajouter_reunion(etude, projet_v1)

        decoupage = generer_decoupage(
            etude,
            nom,
            projet_trois_blocs()
        )

        enregistrer_decoupage(etude, decoupage)

        noms[nom_dossier] = nom

        fids = [
            entree.fid
            for entree in (
                etude.registre.entrees.values()
            )
            if entree.reunion == nom
        ]

        fids_par_reunion[nom] = sorted(fids)

    reunion_1 = noms["2026-10-13_Luc1b"]
    reunion_2 = noms["2026-10-20_Luc2a"]

    # Ordre d'ouvrage INVERSÉ pour la réunion 1.
    definir_ordre_ouvrage(
        etude,
        reunion_1,
        list(reversed(fids_par_reunion[reunion_1]))
    )

    # Reformulations validées : trois blocs pour
    # la réunion 1, deux sur trois pour la 2.
    for nom, fids in (
        fids_par_reunion.items()
    ):

        for rang, fid in enumerate(fids):

            if nom == reunion_2 and rang == 2:
                continue

            version = ajouter_version_reformulation(
                etude,
                nom,
                fid,
                f"Reformulation {nom} bloc {fid}",
            )

            valider_version_reformulation(
                etude,
                nom,
                fid,
                version.numero,
                "Test"
            )

    sauvegarder_etude(etude)

    return etude, reunion_1, reunion_2, (
        fids_par_reunion
    )


#
# ==================================================
# Génération (P19.3 : initialisation du document).
# ==================================================
#

class TestGeneration:

    def test_titre_et_paragraphes(
        self,
        etude_deux_reunions
    ):
        """
        Le document porte le titre de l'étude ; un
        paragraphe PAR BLOC VALIDÉ, dans l'ordre
        des réunions de l'étude puis l'ordre
        d'ouvrage de chaque réunion ; les blocs non
        validés ne figurent JAMAIS dans l'ouvrage.
        """

        etude, r1, r2, fids = (
            etude_deux_reunions
        )

        document = generer_document(etude)

        assert document.titre == (
            "Évangile de Luc"
        )

        paragraphes = document.paragraphes()

        # 3 (réunion 1) + 2 (réunion 2 : le bloc
        # non validé est absent).
        assert len(paragraphes) == 5

        # Ordre d'ouvrage inversé de la réunion 1.
        assert [
            p.provenances[0].fid
            for p in paragraphes[:3]
        ] == list(reversed(fids[r1]))

        # Ordre chronologique de la réunion 2.
        assert [
            p.provenances[0].fid
            for p in paragraphes[3:]
        ] == sorted(fids[r2])[:2]

        # Textes et ordre des réunions.
        assert (
            paragraphes[0].provenances[0].reunion
            == r1
        )

        assert (
            paragraphes[3].provenances[0].reunion
            == r2
        )

    def test_provenance_complete(
        self,
        etude_deux_reunions
    ):
        """
        Chaque paragraphe porte sa provenance
        complète : réunion, FID, numéro et date de
        réunion (métadonnées NON structurelles),
        numéro de la version validée utilisée.
        """

        etude, r1, _r2, fids = (
            etude_deux_reunions
        )

        document = generer_document(etude)

        paragraphe = document.paragraphes()[0]

        reunion = etude.reunions[r1]

        provenance = paragraphe.provenances[0]

        assert provenance.reunion == r1
        assert provenance.fid in fids[r1]
        assert (
            provenance.numero_reunion
            == reunion.numero
        )
        assert (
            provenance.date_reunion
            == reunion.date
        )
        assert provenance.numero_version == 1

        assert paragraphe.texte == (
            f"Reformulation {r1} bloc "
            f"{provenance.fid}"
        )

    def test_tout_en_reserves_a_la_generation(
        self,
        etude_deux_reunions
    ):
        """
        La génération ne crée AUCUN chapitre (les
        titres sont ajoutés MANUELLEMENT) : tous
        les paragraphes sont en « Réserves », et
        les deux réunions sont non placées.
        """

        etude, _r1, _r2, _fids = (
            etude_deux_reunions
        )

        document = generer_document(etude)

        assert len(
            document.paragraphes_reserves()
        ) == 5

        assert set(
            reunions_non_placees(document, etude)
        ) == {_r1, _r2}

    def test_instantane_de_generation(
        self,
        etude_deux_reunions
    ):
        """
        L'instantané de génération consigne, par
        réunion, le numéro, la date, le nombre de
        paragraphes et les versions utilisées —
        y compris les réunions sans texte validé.
        """

        etude, r1, r2, _fids = (
            etude_deux_reunions
        )

        document = generer_document(etude)

        assert document.generation is not None
        assert document.generation["horodatage"]

        snapshot = document.generation["reunions"]

        assert snapshot[r1]["paragraphes"] == 3
        assert snapshot[r2]["paragraphes"] == 2

        assert snapshot[r1]["numero"] == (
            etude.reunions[r1].numero
        )

        assert snapshot[r1]["date"] == (
            etude.reunions[r1].date
        )

        # La version utilisée est la version
        # validée, pas la dernière absolue.
        assert all(
            v["numero"] == 1
            for v in snapshot[r1]["versions"].values()
        )

    def test_reunion_sans_decoupage(
        self,
        tmp_path
    ):
        """
        Une réunion sans découpage (audio préparé
        non transcrit, ou segmentation absente) ne
        produit AUCUN paragraphe et n'empêche pas
        la génération : elle figure à zéro
        paragraphe dans l'instantané.
        """

        etude = creer_etude(
            tmp_path / "Etude",
            "Étude"
        )

        projet_v1 = creer_projet_v1(
            tmp_path,
            "2026-10-13_Luc1b"
        )

        ajouter_reunion(etude, projet_v1)

        document = generer_document(etude)

        assert document.paragraphes() == []

        snapshot = document.generation["reunions"]

        assert len(snapshot) == 1

        seul = list(snapshot.values())[0]

        assert seul["paragraphes"] == 0


#
# ==================================================
# Structure manuelle et Réserves.
# ==================================================
#class TestStructureManuelle:

    def test_chapitre_place_les_paragraphes(
        self,
        etude_deux_reunions
    ):
        """
        Un titre de chapitre inséré AVANT les
        paragraphes les place : ils sortent des
        Réserves, la réunion n'est plus « non
        placée » ; un identifiant stable unique
        est attribué.
        """

        etude, r1, r2, _fids = (
            etude_deux_reunions
        )

        document = generer_document(etude)

        id_titre = document.nouvel_id("t1")

        document.elements.insert(
            0,
            ElementOuvrage(
                id=id_titre,
                type=TYPE_TITRE_1,
                texte="Chapitre 1",
            )
        )

        assert (
            document.paragraphes_reserves() == []
        )

        placees = reunions_non_placees(
            document,
            etude
        )

        assert set(placees) == set()

        assert document.element(
            id_titre
        ).texte == "Chapitre 1"

    def test_nouvel_id_unique(
        self,
        etude_deux_reunions
    ):
        """
        ``nouvel_id`` n'écrase jamais un
        identifiant existant.
        """

        etude, _r1, _r2, _fids = (
            etude_deux_reunions
        )

        document = generer_document(etude)

        assert document.nouvel_id("p") == "p6"
        assert document.nouvel_id("t1") == "t11"


#
# ==================================================
# Régénération complète (écrase) et vie propre.
# ==================================================
#

class TestRegeneration:

    def test_regeneration_ecrase_tout(
        self,
        etude_deux_reunions
    ):
        """
        P19.3 : la régénération complète ÉCRASE le
        document existant — éditions, chapitres et
        paragraphes ajoutés à la main disparaissent
        (l'avertissement relève de l'UI).
        """

        etude, _r1, _r2, _fids = (
            etude_deux_reunions
        )

        document = generer_document(etude)

        document.elements.insert(
            0,
            ElementOuvrage(
                id="t11",
                type=TYPE_TITRE_1,
                texte="Chapitre manuel",
            )
        )

        document.paragraphes()[0].texte = (
            "Édition manuelle"
        )

        document.elements.append(
            ElementOuvrage(
                id="p100",
                type=TYPE_PARAGRAPHE,
                texte="Paragraphe manuel",
                provenances=(
                    document
                    .paragraphes()[0]
                    .provenances
                ),
                source="saisie",
            )
        )

        horodatage_avant = (
            document.generation["horodatage"]
        )

        document = generer_document(etude)

        assert len(document.elements) == 5
        assert document.element("t11") is None
        assert document.element("p100") is None

        assert (
            document.paragraphes()[0].texte
            != "Édition manuelle"
        )

        assert (
            document.generation["horodatage"]
            >= horodatage_avant
        )

    def test_reformulee_depuis_generation(
        self,
        etude_deux_reunions
    ):
        """
        Signalement de divergence : une version
        PLUS RÉCENTE que celle utilisée à la
        génération (validée ou non — passe,
        relance, édition manuelle) signale « réunion
        re-reformulée » ; les blocs inchangés ne
        sont jamais signalés. Le document dérivé
        n'est PAS touché.
        """

        etude, r1, _r2, fids = (
            etude_deux_reunions
        )

        document = generer_document(etude)

        assert (
            reformulees_depuis_generation(
                document,
                etude
            )
            == []
        )

        fid = sorted(fids[r1])[0]

        ajouter_version_reformulation(
            etude,
            r1,
            fid,
            "Nouvelle passe non validée"
        )

        signalements = (
            reformulees_depuis_generation(
                document,
                etude
            )
        )

        assert len(signalements) == 1

        assert signalements[0]["fid"] == fid
        assert (
            signalements[0]["reunion"] == r1
        )
        assert (
            signalements[0]
            ["version_generation"] == 1
        )
        assert (
            signalements[0]
            ["version_courante"] == 2
        )

        # Le document dérivé n'est jamais touché.
        assert (
            document.paragraphes()[0].texte
            != "Nouvelle passe non validée"
        )


#
# ==================================================
# Persistance : ouvrage.json.
# ==================================================
#

class TestPersistance:

    def test_absent_puis_round_trip(
        self,
        etude_deux_reunions,
        tmp_path
    ):
        """
        Sans génération, ouvrage.json n'existe pas
        (charger retourne None) ; après
        sauvegarde, l'aller-retour restitue le
        document À L'IDENTIQUE (structure,
        provenances, instantané).
        """

        etude, _r1, _r2, _fids = (
            etude_deux_reunions
        )

        dossier = etude.dossier

        assert charger_ouvrage(dossier) is None
        assert not chemin_ouvrage(dossier).is_file()

        document = generer_document(etude)

        sauvegarder_ouvrage(document, dossier)

        relu = charger_ouvrage(dossier)

        assert relu.to_dict() == document.to_dict()

        # Identités STABLES conservées.
        assert [
            e.id for e in relu.elements
        ] == [
            e.id for e in document.elements
        ]

        # L'étude relue depuis le disque trouve son
        # ouvrage (intégration étude ↔ ouvrage).
        sauvegarder_etude(etude)

        etude_relue = ouvrir_etude(dossier)

        relu2 = charger_ouvrage(
            etude_relue.dossier
        )

        assert relu2 is not None
        assert len(relu2.paragraphes()) == 5

    def test_format_invalide_refuse(
        self,
        etude_deux_reunions
    ):
        """
        Un ouvrage.json corrompu ou d'une version de
        format non gérée est REFUSÉ
        (OuvrageFormatError — même famille que les
        erreurs de format du dossier étude).
        """

        etude, _r1, _r2, _fids = (
            etude_deux_reunions
        )

        dossier = etude.dossier

        chemin = chemin_ouvrage(dossier)

        # Version de format inconnue.
        chemin.write_text(
            json.dumps({
                "format_version": 99,
                "titre": "X",
                "elements": [],
            }),
            encoding="utf-8"
        )

        with pytest.raises(OuvrageFormatError):
            charger_ouvrage(dossier)

        # Type d'élément inconnu.
        chemin.write_text(
            json.dumps({
                "format_version": 1,
                "titre": "X",
                "generation": None,
                "elements": [
                    {
                        "id": "e1",
                        "type": "alien",
                        "texte": "…"
                    }
                ],
            }),
            encoding="utf-8"
        )

        with pytest.raises(OuvrageFormatError):
            charger_ouvrage(dossier)

        # Identifiants en double.
        chemin.write_text(
            json.dumps({
                "format_version": 1,
                "titre": "X",
                "generation": None,
                "elements": [
                    {
                        "id": "e1",
                        "type": "titre_1",
                        "texte": "A"
                    },
                    {
                        "id": "e1",
                        "type": "titre_1",
                        "texte": "B"
                    },
                ],
            }),
            encoding="utf-8"
        )

        with pytest.raises(OuvrageFormatError):
            charger_ouvrage(dossier)

        # Fichier illisible.
        chemin.write_text(
            "{pas du json",
            encoding="utf-8"
        )

        with pytest.raises(OuvrageFormatError):
            charger_ouvrage(dossier)
