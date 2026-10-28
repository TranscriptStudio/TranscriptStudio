"""
Tests unitaires du format étude v2 (P14.1).

Objet : models/etude.py, services/etude_schema.py,
services/etude_io.py, services/timecodes.py.

Couvre les cinq règles d'invariance du contrat
CONTRAT_FORMAT_ETUDE_V2.md §12 :
1. ouvrir une étude ne modifie jamais un projet v1 ;
2. un FID désigne pour toujours le même discours, les
   versions ne s'écrasent pas ;
3. retirer une réunion ne touche ni le projet v1 ni le
   registre FID ;
4. déplacer le dossier étude reste sûr (relatif, puis
   absolu, puis relocalisation) ;
5. un projet v1 peut être référencé par plusieurs études.
"""

import hashlib
import json
from pathlib import Path

import pytest

from models.etude import (
    BlocParole,
    DecoupageReunion,
    OrigineBloc,
    PositionsBloc,
)
from services.etude_io import (
    EtudeError,
    ajouter_reunion,
    ajouter_version_reformulation,
    ajouter_version_resume,
    ajouter_version_synthese,
    attribuer_fid,
    creer_etude,
    deplacer_reunion,
    enregistrer_decoupage,
    marquer_fid_inactif,
    normaliser_sauts_paragraphe,
    ouvrir_etude,
    relocaliser_reunion,
    retirer_reunion,
    sauvegarder_etude,
    valider_version_reformulation,
    valider_version_resume,
)
from services.etude_schema import (
    EtudeFormatError,
    valider_etude,
    valider_registre_fid,
    valider_reunion,
)
from services.timecodes import formater_timecode, lire_timecode


def creer_projet_v1(dossier_parent: Path, nom: str) -> Path:
    """
    Crée un faux projet v1 : un dossier avec un
    project.sttproj minimal.
    """

    dossier = dossier_parent / nom
    dossier.mkdir(parents=True)

    donnees = {
        "project_format_version": 1,
        "name": nom,
        "audio_file": "audio.wav",
        "transcription_id": None,
        "language_code": "fr",
        "duration_seconds": 100.0,
        "modified": False,
        "speakers": [
            {"id": "speaker_0", "name": "Philippe", "color": "#123456"}
        ],
        "words": [],
        "blocks": [],
        "original_elevenlabs_response": {},
    }

    chemin = dossier / "project.sttproj"

    with open(chemin, "w", encoding="utf-8") as fichier:
        json.dump(donnees, fichier, ensure_ascii=False)

    return dossier


def empreinte(chemin: Path) -> str:
    """
    Empreinte SHA-256 d'un fichier (règle 1 : le
    fichier ne doit pas changer).
    """

    return hashlib.sha256(
        chemin.read_bytes()
    ).hexdigest()


class TestTimecodes:

    def test_format_lecture(self):
        assert formater_timecode(151.4) == "00:02:31.400"
        assert lire_timecode("00:02:31.400") == pytest.approx(151.4)
        assert lire_timecode("00:45:12") == pytest.approx(2712.0)
        assert lire_timecode("01:00:00.500") == pytest.approx(3600.5)

    def test_round_trip(self):
        for secondes in (0.0, 1.999, 63.456, 3725.123):
            assert (
                lire_timecode(formater_timecode(secondes))
                == pytest.approx(secondes)
            )

    def test_negatif_refuse(self):
        with pytest.raises(ValueError):
            formater_timecode(-1.0)

    def test_timecode_invalide(self):
        with pytest.raises(ValueError):
            lire_timecode("abc")

    def test_normalisation_sauts(self):
        assert (
            normaliser_sauts_paragraphe("a\r\n\r\nb\n\n\nc")
            == "a\nb\nc"
        )


class TestCreationEtude:

    def test_structure_dossier(self, tmp_path):
        etude = creer_etude(
            tmp_path / "Etude_Luc",
            "Évangile de Luc"
        )

        dossier = tmp_path / "Etude_Luc"

        assert (dossier / "etude.json").exists()
        assert (dossier / "reunions").is_dir()
        assert (dossier / "blocs" / "journal-fid.json").exists()
        assert (dossier / "blocs" / "decoupage").is_dir()
        assert (dossier / "traitements" / "reformulation").is_dir()
        assert (dossier / "traitements" / "resume").is_dir()
        assert (dossier / "synthese" / "synthese.json").exists()
        assert (dossier / "parametres" / "parametres.json").exists()

        donnees = json.loads(
            (dossier / "etude.json").read_text(encoding="utf-8")
        )

        assert donnees["etude_format_version"] == 1
        assert donnees["titre"] == "Évangile de Luc"
        assert donnees["theme"] == "livre"
        assert donnees["ordre_reunions"] == []

    def test_creation_dossier_non_vide(self, tmp_path):
        """
        ARBITRAGE_CREATION_ETUDE : une étude peut se
        créer dans un dossier non vide (placer
        l'étude à côté des projets référencés) ;
        rien d'existant n'est modifié ni supprimé.
        """
        dossier = tmp_path / "existant"
        dossier.mkdir()
        (dossier / "bricolage.txt").write_text("x")
        (dossier / "projet_v1").mkdir()
        (dossier / "projet_v1" / "project.sttproj").write_text(
            "projet"
        )

        creer_etude(dossier, "Étude")

        assert (dossier / "etude.json").is_file()
        assert (dossier / "reunions").is_dir()

        # Aucun fichier existant n'est touché.
        assert (
            dossier / "bricolage.txt"
        ).read_text(encoding="utf-8") == "x"

        assert (
            dossier / "projet_v1" / "project.sttproj"
        ).read_text(encoding="utf-8") == "projet"

    def test_creation_refuse_dossier_deja_etude(self, tmp_path):
        """
        Un dossier contenant déjà etude.json est
        une étude : jamais d'écrasement — l'étude
        existante reste intacte.
        """
        dossier = tmp_path / "deja_etude"
        creer_etude(dossier, "Première étude")

        with pytest.raises(EtudeError) as infos:
            creer_etude(dossier, "Deuxième étude")

        assert "etude.json" in str(infos.value)

        donnees = json.loads(
            (dossier / "etude.json").read_text(
                encoding="utf-8"
            )
        )

        assert donnees["titre"] == "Première étude"

    def test_creation_refuse_conflit_de_nom(self, tmp_path):
        """
        Un fichier existant occupant l'emplacement
        d'un sous-dossier de l'étude bloque la
        création — erreur claire et rien d'écrit.
        """
        dossier = tmp_path / "conflit"
        dossier.mkdir()
        (dossier / "blocs").write_text("un fichier")

        with pytest.raises(EtudeError) as infos:
            creer_etude(dossier, "Étude")

        assert "blocs" in str(infos.value)

        # Rien n'a été écrit : ni l'étude, ni ses
        # sous-dossiers ; le fichier d'origine est
        # intact.
        assert not (dossier / "etude.json").exists()
        assert not (dossier / "reunions").exists()
        assert not (dossier / "synthese").exists()

        assert (
            dossier / "blocs"
        ).read_text(encoding="utf-8") == "un fichier"

    def test_messages_incluent_l_aide(self, tmp_path):
        """
        ARBITRAGE_CREATION_ETUDE point 4 : les
        messages d'erreur guident l'utilisateur —
        « Saisissez plutôt un nom de nouveau dossier
        pour créer l'étude dedans. »
        """
        deja_etude = tmp_path / "deja_etude"
        creer_etude(deja_etude, "Première étude")

        with pytest.raises(EtudeError) as infos_etude:
            creer_etude(deja_etude, "Deuxième étude")

        assert "nouveau dossier" in str(infos_etude.value)

        conflit = tmp_path / "conflit"
        conflit.mkdir()
        (conflit / "blocs").write_text("un fichier")

        with pytest.raises(EtudeError) as infos_conflit:
            creer_etude(conflit, "Étude")

        assert "nouveau dossier" in str(infos_conflit.value)
        assert "Rien n'a été écrit" in str(infos_conflit.value)

    def test_parametres_par_defaut(self, tmp_path):
        etude = creer_etude(tmp_path / "E", "Étude")

        donnees = json.loads(
            (
                tmp_path / "E" / "parametres"
                / "parametres.json"
            ).read_text(encoding="utf-8")
        )

        reformulation = donnees["reformulation"]

        assert "Agent" in reformulation["prompt"]
        assert reformulation["fenetre_glissante_tokens"] == 2000
        assert donnees["resume"]["source_defaut"] == (
            "reformulations_valides"
        )
        assert donnees["resume"]["longueur_cible_mots"] == [650, 700]
        assert donnees["synthese"]["tokens_max"] == 1500
        assert "puissamment" in (
            donnees["controle_qualite"]["lexique_emphase"]
        )
        assert donnees["llm"]["fournisseurs"][0][
            "cle_ref"
        ] == "credential_store"

        # Aucune clé API en clair nulle part.
        contenu = json.dumps(donnees)
        assert "sk-" not in contenu


class TestSchema:

    def test_etude_theme_invalide(self):
        with pytest.raises(EtudeFormatError):
            valider_etude({
                "etude_format_version": 1,
                "titre": "T",
                "theme": "autre",
                "gabarit_titre_1": "G",
                "ordre_reunions": [],
                "creation": "2026-10-27T14:30:00",
                "modification": "2026-10-27T14:30:00",
            })

    def test_etude_cle_absente(self):
        with pytest.raises(EtudeFormatError):
            valider_etude({
                "etude_format_version": 1,
                "titre": "T",
                "theme": "livre",
            })

    def test_etude_doublon_reunions(self):
        with pytest.raises(EtudeFormatError):
            valider_etude({
                "etude_format_version": 1,
                "titre": "T",
                "theme": "livre",
                "gabarit_titre_1": "G",
                "ordre_reunions": ["a", "a"],
                "creation": "2026-10-27T14:30:00",
                "modification": "2026-10-27T14:30:00",
            })

    def test_etude_version_future(self):
        with pytest.raises(EtudeFormatError):
            valider_etude({
                "etude_format_version": 2,
                "titre": "T",
                "theme": "livre",
                "gabarit_titre_1": "G",
                "ordre_reunions": [],
                "creation": "2026-10-27T14:30:00",
                "modification": "2026-10-27T14:30:00",
            })

    def test_reunion_date_invalide(self):
        with pytest.raises(EtudeFormatError):
            valider_reunion({
                "reference": "a.json",
                "chemin_projet": "../a",
                "date": "13/10/2026",
                "numero": 1,
                "titre_1": "T",
                "resume_valide": False,
            })

    def test_registre_fid_incoherent(self):
        with pytest.raises(EtudeFormatError):
            valider_registre_fid({
                "prochain_fid": 1,
                "fid_attribues": {
                    "5": {
                        "reunion": "a",
                        "cree": "2026-10-27T14:30:00",
                        "actif": True,
                        "fin": None,
                    }
                },
            })

    def test_ouverture_dossier_sans_etude(self, tmp_path):
        with pytest.raises(EtudeFormatError):
            ouvrir_etude(tmp_path)

    def test_fichier_corrompu(self, tmp_path):
        etude = creer_etude(tmp_path / "E", "Étude")
        sauvegarder_etude(etude)

        chemin = tmp_path / "E" / "etude.json"
        donnees = json.loads(chemin.read_text(encoding="utf-8"))
        del donnees["titre"]
        chemin.write_text(
            json.dumps(donnees),
            encoding="utf-8"
        )

        with pytest.raises(EtudeFormatError):
            ouvrir_etude(tmp_path / "E")


class TestReunions:

    def test_ajout_et_ouverture(self, tmp_path):
        projet = creer_projet_v1(tmp_path, "2026-10-13_Luc1b")

        etude = creer_etude(tmp_path / "Etude", "Évangile de Luc")
        nom = ajouter_reunion(etude, projet, "Chapitre 1")
        sauvegarder_etude(etude)

        assert nom == "2026-10-13_luc1b"
        assert etude.etude.ordre_reunions == [nom]

        reouverte = ouvrir_etude(tmp_path / "Etude")

        assert reouverte.etude.ordre_reunions == [nom]
        assert reouverte.reunion_joignable(nom)
        assert reouverte.chemins_resolus[nom] == projet.resolve()

        donnees = json.loads(
            (
                tmp_path / "Etude" / "reunions"
                / f"{nom}.json"
            ).read_text(encoding="utf-8")
        )

        assert donnees["reference"] == f"{nom}.json"
        assert donnees["numero"] == 1
        assert donnees["titre_1"] == "Chapitre 1"

    def test_doublon_refuse(self, tmp_path):
        projet = creer_projet_v1(tmp_path, "projet_a")

        etude = creer_etude(tmp_path / "E", "Étude")
        ajouter_reunion(etude, projet)

        with pytest.raises(EtudeError):
            ajouter_reunion(etude, projet)

    def test_ordre_et_deplacement(self, tmp_path):
        projet_a = creer_projet_v1(tmp_path, "projet_a")
        projet_b = creer_projet_v1(tmp_path, "projet_b")
        projet_c = creer_projet_v1(tmp_path, "projet_c")

        etude = creer_etude(tmp_path / "E", "Étude")
        ajouter_reunion(etude, projet_a)
        ajouter_reunion(etude, projet_b)
        nom_c = ajouter_reunion(etude, projet_c)

        assert etude.etude.ordre_reunions == [
            "projet_a",
            "projet_b",
            "projet_c",
        ]

        deplacer_reunion(etude, nom_c, 0)

        assert etude.etude.ordre_reunions == [
            "projet_c",
            "projet_a",
            "projet_b",
        ]

    def test_ajout_refuse_projet_sans_sttproj(self, tmp_path):
        dossier = tmp_path / "pas_un_projet"
        dossier.mkdir()

        etude = creer_etude(tmp_path / "E", "Étude")

        with pytest.raises(EtudeError):
            ajouter_reunion(etude, dossier)


class TestFIDEtVersions:
    """
    Règle d'invariance 2 : un FID, une fois attribué,
    désigne pour toujours le même discours ; les
    versions ne s'écrasent pas.
    """

    def _etude_avec_reunion(self, tmp_path):
        projet = creer_projet_v1(tmp_path, "projet_a")
        etude = creer_etude(tmp_path / "E", "Étude")
        nom = ajouter_reunion(etude, projet)
        return etude, nom

    def test_fid_sequentiels_jamais_reutilises(self, tmp_path):
        etude, nom = self._etude_avec_reunion(tmp_path)

        fid1 = attribuer_fid(etude, nom)
        fid2 = attribuer_fid(etude, nom)

        assert (fid1, fid2) == (1, 2)

        marquer_fid_inactif(etude, fid1)

        fid3 = attribuer_fid(etude, nom)

        assert fid3 == 3

        # Le FID inactif reste au registre, avec sa fin.
        entree = etude.registre.entrees[fid1]

        assert entree.actif is False
        assert entree.fin is not None

    def test_versions_reformulation_historique_complet(self, tmp_path):
        etude, nom = self._etude_avec_reunion(tmp_path)

        fid = attribuer_fid(etude, nom)

        ajouter_version_reformulation(
            etude,
            fid,
            "Première reformulation."
        )

        ajouter_version_reformulation(
            etude,
            fid,
            "Deuxième reformulation.",
            type_version="relance",
            consigne="plus concis",
            stats={
                "duree_ms": 8400,
                "tokens_in": 3120,
                "tokens_out": 1180,
                "cout_estime": 0.012,
            },
        )

        sauvegarder_etude(etude)

        reouverte = ouvrir_etude(tmp_path / "E")

        resultat = reouverte.reformulations[fid]

        assert [
            version.numero
            for version in resultat.versions
        ] == [1, 2]

        assert resultat.versions[0].texte == (
            "Première reformulation."
        )
        assert resultat.versions[1].type == "relance"
        assert resultat.versions[1].stats["cout_estime"] == (
            0.012
        )
        assert resultat.versions[1].validation is None

        # Une édition manuelle ajoute une version, sans stats.
        ajouter_version_reformulation(
            reouverte,
            fid,
            "Troisième, corrigée à la main.",
            type_version="edition_manuelle",
        )

        assert len(reouverte.reformulations[fid].versions) == 3
        assert reouverte.reformulations[fid].versions[
            2
        ].stats is None

    def test_validation_portee_par_version(self, tmp_path):
        etude, nom = self._etude_avec_reunion(tmp_path)

        fid = attribuer_fid(etude, nom)

        ajouter_version_reformulation(etude, fid, "V1")
        ajouter_version_reformulation(etude, fid, "V2")

        valider_version_reformulation(
            etude,
            fid,
            numero=1,
            validateur="David"
        )

        resultat = etude.reformulations[fid]

        assert resultat.versions[0].validation.statut == (
            "valide"
        )
        assert resultat.versions[0].validation.validateur == (
            "David"
        )
        assert resultat.versions[1].validation is None

    def test_validation_version_inconnue(self, tmp_path):
        etude, nom = self._etude_avec_reunion(tmp_path)

        fid = attribuer_fid(etude, nom)

        ajouter_version_reformulation(etude, fid, "V1")

        with pytest.raises(EtudeError):
            valider_version_reformulation(
                etude,
                fid,
                numero=9,
                validateur="David"
            )

    def test_resume_et_synthese(self, tmp_path):
        projet = creer_projet_v1(tmp_path, "projet_a")

        etude = creer_etude(tmp_path / "E", "Étude")
        nom = ajouter_reunion(etude, projet)

        ajouter_version_resume(
            etude,
            nom,
            "Résumé v1",
            source="brute_corrigee"
        )

        ajouter_version_resume(
            etude,
            nom,
            "Résumé v2",
            source="reformulations_valides"
        )

        valider_version_resume(
            etude,
            nom,
            numero=2,
            validateur="David"
        )

        assert etude.reunions[nom].resume_valide is True

        ajouter_version_synthese(
            etude,
            "Pensée déjà développée.",
            declencheur="validation_bloc"
        )

        sauvegarder_etude(etude)

        reouverte = ouvrir_etude(tmp_path / "E")

        assert [
            version.source
            for version in reouverte.resumes[nom].versions
        ] == [
            "brute_corrigee",
            "reformulations_valides",
        ]

        assert reouverte.resumes[nom].versions[
            1
        ].validation.statut == "valide"

        assert reouverte.synthese.versions[0].declencheur == (
            "validation_bloc"
        )

    def test_decoupage(self, tmp_path):
        projet = creer_projet_v1(tmp_path, "projet_a")

        etude = creer_etude(tmp_path / "E", "Étude")
        nom = ajouter_reunion(etude, projet)

        fid = attribuer_fid(etude, nom)

        decoupage = DecoupageReunion(
            reunion=nom,
            blocs=[
                BlocParole(
                    fid=fid,
                    locuteurs=["Philippe"],
                    positions=PositionsBloc(
                        debut="00:02:31.400",
                        fin="00:04:12.100"
                    ),
                    source="Texte du bloc.",
                    origine=OrigineBloc(),
                )
            ],
        )

        enregistrer_decoupage(etude, decoupage)
        sauvegarder_etude(etude)

        reouverte = ouvrir_etude(tmp_path / "E")

        bloc = reouverte.decoupages[nom].blocs[0]

        assert bloc.fid == fid
        assert bloc.positions.debut == "00:02:31.400"
        assert bloc.source == "Texte du bloc."

    def test_decoupage_fid_d_autre_reunion_refuse(self, tmp_path):
        projet_a = creer_projet_v1(tmp_path, "projet_a")
        projet_b = creer_projet_v1(tmp_path, "projet_b")

        etude = creer_etude(tmp_path / "E", "Étude")
        nom_a = ajouter_reunion(etude, projet_a)
        nom_b = ajouter_reunion(etude, projet_b)

        fid_a = attribuer_fid(etude, nom_a)

        decoupage = DecoupageReunion(
            reunion=nom_b,
            blocs=[
                BlocParole(
                    fid=fid_a,
                    locuteurs=["Philippe"],
                    positions=PositionsBloc(),
                    source="x",
                    origine=OrigineBloc(),
                )
            ],
        )

        with pytest.raises(EtudeError):
            enregistrer_decoupage(etude, decoupage)


class TestInvariance1:
    """
    Ouvrir une étude ne modifie jamais aucun projet v1
    référencé (hors journal des opérations créé par un
    prétraitement).
    """

    def test_ouverture_projet_intact(self, tmp_path):
        projet = creer_projet_v1(tmp_path, "projet_a")

        sttproj = projet / "project.sttproj"
        avant = empreinte(sttproj)

        etude = creer_etude(tmp_path / "E", "Étude")
        ajouter_reunion(etude, projet)
        sauvegarder_etude(etude)

        for _ in range(2):
            etude = ouvrir_etude(tmp_path / "E")
            sauvegarder_etude(etude)

        assert empreinte(sttproj) == avant

        # Aucun fichier ajouté au dossier projet v1.
        assert sorted(p.name for p in projet.iterdir()) == [
            "project.sttproj"
        ]


class TestInvariance3:
    """
    La suppression d'une réunion de l'étude retire sa
    référence et ses résultats d'étude, mais ne touche
    ni le projet v1 ni le registre FID.
    """

    def test_retrait_reunion(self, tmp_path):
        projet = creer_projet_v1(tmp_path, "projet_a")

        sttproj = projet / "project.sttproj"
        avant = empreinte(sttproj)

        etude = creer_etude(tmp_path / "E", "Étude")
        nom = ajouter_reunion(etude, projet)

        fid = attribuer_fid(etude, nom)

        decoupage = DecoupageReunion(
            reunion=nom,
            blocs=[
                BlocParole(
                    fid=fid,
                    locuteurs=["Philippe"],
                    positions=PositionsBloc(),
                    source="x",
                    origine=OrigineBloc(),
                )
            ],
        )

        enregistrer_decoupage(etude, decoupage)

        ajouter_version_reformulation(etude, fid, "R1")
        ajouter_version_resume(
            etude,
            nom,
            "Résumé",
            source="brute_corrigee"
        )

        sauvegarder_etude(etude)

        retirer_reunion(etude, nom)
        sauvegarder_etude(etude)

        # Référence et résultats retirés.
        dossier = tmp_path / "E"

        assert not (
            dossier / "reunions" / f"{nom}.json"
        ).exists()

        assert not (
            dossier / "blocs" / "decoupage"
            / f"{nom}.json"
        ).exists()

        assert not (
            dossier / "traitements" / "resume"
            / f"{nom}.json"
        ).exists()

        assert not (
            dossier / "traitements" / "reformulation"
            / f"{fid}.json"
        ).exists()

        assert etude.etude.ordre_reunions == []

        # Le registre FID garde l'attribution, active.
        assert fid in etude.registre.entrees
        assert etude.registre.entrees[fid].actif is True

        # Le projet v1 est intact.
        assert empreinte(sttproj) == avant

        reouverte = ouvrir_etude(dossier)
        assert reouverte.etude.ordre_reunions == []


class TestInvariance4:
    """
    Déplacer le dossier étude reste sûr : les chemins se
    résolvent par ordre relatif, puis absolu, puis
    relocalisation.
    """

    def test_deplacement_ensemble(self, tmp_path):
        """
        Déplacer l'étude et son projet ensemble : le
        chemin relatif suit.
        """

        racine = tmp_path / "racine"
        projet = creer_projet_v1(racine, "projet_a")

        etude = creer_etude(racine / "E", "Étude")
        nom = ajouter_reunion(etude, projet)
        sauvegarder_etude(etude)

        nouveau_racine = tmp_path / "deplace"
        nouveau_racine.mkdir()

        (racine / "E").rename(nouveau_racine / "E")
        projet.rename(nouveau_racine / "projet_a")

        reouverte = ouvrir_etude(nouveau_racine / "E")

        assert reouverte.reunion_joignable(nom)
        assert (
            reouverte.chemins_resolus[nom]
            == (nouveau_racine / "projet_a").resolve()
        )

    def test_deplacement_etude_seule_fallback_absolu(self, tmp_path):
        """
        Déplacer l'étude seule : le chemin relatif casse,
        le chemin absolu historique prend le relais.
        """

        projet = creer_projet_v1(tmp_path, "projet_a")

        etude = creer_etude(tmp_path / "E", "Étude")
        nom = ajouter_reunion(etude, projet)
        sauvegarder_etude(etude)

        (tmp_path / "E").rename(tmp_path / "ailleurs")

        reouverte = ouvrir_etude(tmp_path / "ailleurs")

        assert reouverte.reunion_joignable(nom)
        assert not reouverte.reunions_introuvables

    def test_projet_introuvable_mode_degrade(self, tmp_path):
        """
        Projet supprimé : l'étude s'ouvre quand même en
        mode dégradé, sans bloquer les autres réunions.
        """

        projet_a = creer_projet_v1(tmp_path, "projet_a")
        projet_b = creer_projet_v1(tmp_path, "projet_b")

        etude = creer_etude(tmp_path / "E", "Étude")
        ajouter_reunion(etude, projet_a)
        nom_b = ajouter_reunion(etude, projet_b)
        sauvegarder_etude(etude)

        import shutil

        shutil.rmtree(projet_a)

        reouverte = ouvrir_etude(tmp_path / "E")

        assert reouverte.reunions_introuvables == ["projet_a"]
        assert reouverte.reunion_joignable(nom_b)
        assert not reouverte.reunion_joignable("projet_a")

    def test_relocalisation_guidee(self, tmp_path):
        """
        Un projet déplacé est relocalisé explicitement :
        la référence est mise à jour et persistée.
        """

        projet = creer_projet_v1(tmp_path, "projet_a")

        etude = creer_etude(tmp_path / "E", "Étude")
        nom = ajouter_reunion(etude, projet)
        sauvegarder_etude(etude)

        nouveau = tmp_path / " archives_projet".strip()
        nouveau.mkdir()
        projet.rename(nouveau / "projet_a")

        reouverte = ouvrir_etude(tmp_path / "E")
        assert reouverte.reunions_introuvables == [nom]

        relocaliser_reunion(
            reouverte,
            nom,
            nouveau / "projet_a"
        )

        sauvegarder_etude(reouverte)

        encore = ouvrir_etude(tmp_path / "E")

        assert not encore.reunions_introuvables
        assert encore.reunion_joignable(nom)


class TestInvariance5:
    """
    Un projet v1 peut être référencé par plusieurs
    études simultanément.
    """

    def test_deux_etudes_meme_projet(self, tmp_path):
        projet = creer_projet_v1(tmp_path, "projet_a")
        avant = empreinte(projet / "project.sttproj")

        etude_1 = creer_etude(tmp_path / "E1", "Étude 1")
        nom_1 = ajouter_reunion(etude_1, projet)

        etude_2 = creer_etude(tmp_path / "E2", "Étude 2")
        nom_2 = ajouter_reunion(etude_2, projet)

        sauvegarder_etude(etude_1)
        sauvegarder_etude(etude_2)

        reouverture_1 = ouvrir_etude(tmp_path / "E1")
        reouverture_2 = ouvrir_etude(tmp_path / "E2")

        assert reouverture_1.reunion_joignable(nom_1)
        assert reouverture_2.reunion_joignable(nom_2)

        assert empreinte(projet / "project.sttproj") == avant
