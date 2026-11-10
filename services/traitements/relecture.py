"""
Passes LLM à la demande des aides à la relecture
(P20.3 : incohérences/redondances par section ;
P20.6g : confirmation des pensées redondantes sur
la seule liste candidate ; P20.3 : passe optionnelle
sur les familles d'expressions).

SIGNALEMENT UNIQUEMENT, JAMAIS DE RÉÉCRITURE :
les rapports sont des alertes pour l'utilisateur,
aucune réécriture automatique, aucun remplacement
suggéré.
"""

from services.llm.catalogue import (
    CatalogueError,
    CatalogueLLM,
    catalogue_par_defaut,
    effort_effectif,
)
from services.llm.client import (
    Annulation,
    ParametresCompletion,
    creer_client,
)
from services.etude_io import EtudeOuverte
from services.prompts import hash_prompt


PROMPT_COHERENCE_SECTION = """Tu es un relecteur attentif d'un ouvrage collectif (réunions d'une étude biblique, reformulées).

Analyse la section suivante (texte d'un chapitre de l'ouvrage) et signale :
- les incohérences (contradictions, ruptures de ton, confusions de sens) ;
- les redondances (pensées déjà dites, redites) ;
- les sujets récurrents mal assumés.

Règles :
- SIGNALEMENT UNIQUEMENT : ne réécris rien, ne propose aucun remplacement ;
- une ligne par signalement, sobre et précis ;
- si la section est cohérente, réponds « Aucun signalement. » ;
- écrire en français."""

PROMPT_CONFIRMATION_REDONDANCES = """Tu es un relecteur d'un ouvrage collectif. On te soumet des groupes de phrases courtes (pensées) présélectionnés localement comme potentiellement redondantes.

Pour chaque groupe, confirme ou infirme la redondance (les pensées disent-elles la même chose ?) :
- une ligne par groupe : « Groupe N : confirmé » ou « Groupe N : non confirmé » ;
- SIGNALEMENT UNIQUEMENT : ne réécris rien ;
- écrire en français."""

PROMPT_FAMILLES_EXPRESSIONS = """Tu es un relecteur d'un ouvrage collectif. On te soumet des familles d'expressions récurrentes (variantes regroupées par mots communs), détectées localement.

Pour chaque famille, confirme ou infirme qu'il s'agit bien d'un tic de reformulation (et non d'une insistance légitime du thème) :
- une ligne par famille : « Famille N : confirmé » ou « Famille N : non confirmé » ;
- SIGNALEMENT UNIQUEMENT : ne propose aucun remplacement ;
- écrire en français."""


class ServiceRelecture:
    """
    Passes LLM à la demande (aides à la relecture,
    P20.3/P20.6g) — mêmes règles de résolution de
    configuration que le moteur.
    """

    def __init__(
        self,
        etude_ouverte: EtudeOuverte,
        parametres_app: dict = None,
        credential_store=None,
        catalogue: CatalogueLLM = None,
        client_factory=None
    ):
        self.etude = etude_ouverte
        self._parametres_app_bruts = parametres_app
        self._credential_store = credential_store
        self._catalogue = catalogue
        self._client_factory = client_factory

        self.dernier_prompt = ""
        self.dernier_prompt_hash = ""

    def _parametres_app(self) -> dict:

        if self._parametres_app_bruts is not None:
            return self._parametres_app_bruts

        from services.settings import SettingsManager

        return SettingsManager().get_llm_config()

    def _credential(self):

        if self._credential_store is not None:
            return self._credential_store

        from services.app_paths import APP_DATA_DIR
        from services.credential_store import (
            CredentialStore,
        )

        return CredentialStore(
            APP_DATA_DIR / "settings.json"
        )

    def _catalogue_courant(self) -> CatalogueLLM:

        if self._catalogue is not None:
            return self._catalogue

        return catalogue_par_defaut()

    def _parametres_bloc(self) -> dict:
        return (
            self.etude.parametres.reformulation
        )

    def resoudre(self):

        catalogue = self._catalogue_courant()
        app = self._parametres_app()

        fournisseur = catalogue.chercher_fournisseur(
            app.get("fournisseur")
        )

        if fournisseur is None:
            raise CatalogueError(
                "Aucun fournisseur LLM configuré : "
                "vérifiez les réglages."
            )

        modele_id = self._parametres_bloc().get(
            "modele"
        )

        modele = None

        if modele_id:
            modele = (
                fournisseur.chercher_modele(modele_id)
            )

        if modele is None:
            modele = fournisseur.chercher_modele(
                app.get("modele")
            )

        if modele is None and fournisseur.modeles:
            modele = fournisseur.modeles[0]

        if modele is None:
            raise CatalogueError(
                f"Aucun modèle chez {fournisseur.nom} : "
                "vérifiez les réglages."
            )

        return fournisseur, modele

    def _creer_client(self, fournisseur):

        fabrique = self._client_factory

        if fabrique is None:
            fabrique = creer_client

        if fournisseur.necessite_cle:
            cle = (
                self._credential().get_cle_llm(
                    fournisseur.id
                )
            )
        else:
            cle = ""

        return fabrique(fournisseur, cle)

    def temperature_effective(self) -> float:

        surcharge = (
            self._parametres_bloc().get("temperature")
        )

        if surcharge is not None:
            return float(surcharge)

        app = self._parametres_app()

        temperatures = app.get("temperatures", {})

        return float(
            temperatures.get("reformulation", 0.3)
        )

    def _appeler(
        self,
        prompt: str,
        message: str,
        annulation: Annulation = None
    ) -> tuple:

        fournisseur, modele = self.resoudre()
        client = self._creer_client(fournisseur)

        self.dernier_prompt = prompt
        self.dernier_prompt_hash = hash_prompt(prompt)

        resultat = client.completions(
            prompt,
            [
                {
                    "role": "user",
                    "content": message,
                }
            ],
            ParametresCompletion(
                modele=modele.id,
                temperature=(
                    self.temperature_effective()
                    if modele.capacite_temperature
                    else None
                ),
                max_tokens=(
                    self._parametres_app().get(
                        "max_tokens"
                    )
                    or None
                ),
                effort_raisonnement=effort_effectif(
                    modele,
                    self._parametres_app().get(
                        "effort_raisonnement"
                    )
                ),
            ),
            annulation=annulation
        )

        stats = {
            "duree_ms": resultat.duree_ms,
            "tokens_in": resultat.tokens_in,
            "tokens_out": resultat.tokens_out,
            "cout_estime": resultat.cout_estime,
            "modele": modele.id,
            "prompt_hash": self.dernier_prompt_hash,
        }

        return resultat.texte, stats

    def analyser_section(
        self,
        textes: list,
        annulation: Annulation = None
    ) -> tuple:
        """
        P20.3 : passe LLM à la demande sur UNE
        section — incohérences et redondances.
        Retour : ``(rapport, stats)``. Signalement
        uniquement.
        """

        textes = [
            t for t in (textes or []) if t and t.strip()
        ]

        if not textes:
            raise ValueError(
                "Section vide : rien à analyser."
            )

        return self._appeler(
            PROMPT_COHERENCE_SECTION,
            "Texte de la section de l'ouvrage à "
            "analyser :\n\n" + "\n\n".join(textes),
            annulation=annulation
        )

    def confirmer_redondances(
        self,
        groupes: list,
        annulation: Annulation = None
    ) -> tuple:
        """
        P20.6g : confirmation LLM à la demande sur la
        SEULE liste candidate (présélection locale
        déjà faite) — groupes de phrases courtes
        potentiellement redondantes.
        """

        if not groupes:
            raise ValueError(
                "Aucun groupe candidat à confirmer."
            )

        lignes = []

        for i, groupe in enumerate(groupes, 1):

            lignes.append(
                f"Groupe {i} :\n"
                + "\n".join(
                    f"- {p}"
                    for p in groupe.get("phrases", [])
                )
            )

        return self._appeler(
            PROMPT_CONFIRMATION_REDONDANCES,
            "Groupes de pensées présélectionnés comme "
            "potentiellement redondants :\n\n"
            + "\n\n".join(lignes),
            annulation=annulation
        )

    def confirmer_familles(
        self,
        familles: list,
        annulation: Annulation = None
    ) -> tuple:
        """
        P20.3 : passe LLM OPTIONNELLE à la demande sur
        la seule liste des familles candidates
        (variantes d'expressions récurrentes).
        """

        if not familles:
            raise ValueError(
                "Aucune famille candidate."
            )

        lignes = []

        for i, famille in enumerate(familles, 1):

            lignes.append(
                f"Famille {i} : "
                + " / ".join(famille.get("expressions", []))
            )

        return self._appeler(
            PROMPT_FAMILLES_EXPRESSIONS,
            "Familles d'expressions récurrentes "
            "(variantes) détectées localement :\n\n"
            + "\n".join(lignes),
            annulation=annulation
        )
