"""
Tests unitaires du contrôle qualité local (P16.4).

Feuille de route §5 : sans LLM, indicateurs
seulement — jamais de modification automatique du
texte. Périmètre P16 : rapport de longueur (§5.1)
et interdits stylistiques (§5.3) ; les références
(§5.2) et citations JND (§5.4) arrivent en P18.
"""

from services.controle_qualite import (
    INTERDITS_STYLISTIQUES_DEFAUT,
    SEUIL_LONGUEUR_POURCENT,
    compter_mots,
    controles_bloc,
    interdits_stylistiques,
    rapport_longueur,
)


class TestCompterMots:

    def test_comptage_simple(self):
        assert compter_mots("un deux trois") == 3
        assert compter_mots("") == 0
        assert compter_mots(None) == 0
        assert compter_mots("   ") == 0

    def test_ponctuation_collee(self):
        # La ponctuation isolée compte (cohérent des
        # deux côtés pour le ratio).
        assert compter_mots("Il dit : « viens » !") == 7
        assert compter_mots("Il dit: «viens» !") == 4


class TestRapportLongueur:
    """
    §5.1 : mots résultat vs mots source ;
    avertissement si le résultat dépasse ~120 %.
    """

    def test_conforme(self):
        source = " ".join(["mot"] * 100)
        resultat = " ".join(["mot"] * 110)

        rapport = rapport_longueur(source, resultat)

        assert rapport["mots_source"] == 100
        assert rapport["mots_resultat"] == 110
        assert rapport["ratio_pourcent"] == 110
        assert rapport["avertissement"] is False

    def test_avertissement_au_dela_du_seuil(self):
        source = " ".join(["mot"] * 100)
        resultat = " ".join(["mot"] * 121)

        rapport = rapport_longueur(source, resultat)

        assert rapport["ratio_pourcent"] == 121
        assert rapport["avertissement"] is True
        assert "plus longue" in rapport["message"]

    def test_seuil_exact_pas_d_alerte(self):
        source = " ".join(["mot"] * 100)
        resultat = " ".join(["mot"] * 120)

        rapport = rapport_longueur(source, resultat)

        assert rapport["ratio_pourcent"] == 120
        assert rapport["avertissement"] is False

    def test_source_vide(self):
        rapport = rapport_longueur("", "quelque chose")

        assert rapport["ratio_pourcent"] is None
        assert rapport["avertissement"] is False

    def test_resultat_vide(self):
        rapport = rapport_longueur("des mots", "")

        assert rapport["ratio_pourcent"] == 0
        assert rapport["avertissement"] is False


class TestInterditsStylistiques:
    """
    §5.3 : recherche locale, insensible à la casse,
    dans une liste éditable.
    """

    def test_recherche_insensible_a_la_casse(self):
        resultats = interdits_stylistiques(
            "L'ORATEUR a dit que l'orateur "
            "reviendrait.",
            ["l'orateur"]
        )

        assert len(resultats) == 1
        assert resultats[0]["occurrences"] == 2

    def test_liste_par_defaut(self):
        texte = (
            "Nous avons vu que l'orateur parlait, "
            "et le frère a répondu ; il convient de "
            "noter la nuance."
        )

        resultats = interdits_stylistiques(
            texte,
            INTERDITS_STYLISTIQUES_DEFAUT
        )

        motifs = [r["motif"] for r in resultats]

        assert "nous avons vu que" in motifs
        assert "l'orateur" in motifs
        assert "le frère" in motifs
        assert "il convient de" in motifs

        # Tri par occurrences décroissantes.
        occurrences = [
            r["occurrences"] for r in resultats
        ]

        assert occurrences == sorted(
            occurrences,
            reverse=True
        )

    def test_aucun_trouve(self):
        resultats = interdits_stylistiques(
            "Un texte sobre.",
            INTERDITS_STYLISTIQUES_DEFAUT
        )

        assert resultats == []

    def text_liste_vide_ou_motifs_vides(self):
        assert interdits_stylistiques("texte", []) == []
        assert interdits_stylistiques("texte", [""]) == []
        assert interdits_stylistiques("", ["motif"]) == []


class TestControlesBloc:
    """
    Indicateur discret de la page Reformulation
    (spec UI §4) : longueur + interdits.
    """

    def test_conforme(self):
        controles = controles_bloc(
            " ".join(["mot"] * 100),
            " ".join(["mot"] * 90)
        )

        assert controles["nb_alertes"] == 0
        assert controles["longueur"]["avertissement"] is False
        assert controles["interdits"] == []
        assert "aucun" in controles["message_interdits"]

    def test_alertes_cumulees(self):
        controles = controles_bloc(
            " ".join(["mot"] * 10),
            "L'orateur a longuement développé. "
            "Nous avons vu que c'était long. "
            + " ".join(["mot"] * 20)
        )

        # 1 alerte de longueur (le résultat dépasse
        # 120 % de la source) + 2 interdits.
        assert controles["longueur"]["avertissement"] is True
        assert len(controles["interdits"]) == 2
        assert controles["nb_alertes"] == 3

    def test_liste_EDItable_depuis_parametres(self):
        controles = controles_bloc(
            "source de dix mots",
            "Le turlututu a parlé.",
            controle_qualite={
                "interdits_stylistiques": [
                    "turlututu"
                ]
            }
        )

        assert [c["motif"] for c in controles["interdits"]] == [
            "turlututu"
        ]

    def test_parametres_vides_repli_defauts(self):
        controles = controles_bloc(
            "source",
            "L'orateur parle.",
            controle_qualite={}
        )

        assert len(controles["interdits"]) == 1
