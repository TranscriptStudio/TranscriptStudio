"""
Sous-titres proposés par IA (P20.2 — feuille de
route v2 §P20) : UNE passe LLM par section de
l'ouvrage (« proposer 2 à 5 niveaux de sous-titres
sobres pour structurer ce texte »).

Les suggestions sont proposées à l'utilisateur,
VALIDABLES ET ÉDITABLES — JAMAIS insérées
automatiquement dans le document (l'insertion ne
se fait qu'après validation explicite, par
l'appelant UI).

Coût marginal : une passe par section, à la
demande.
"""

import re

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


PROMPT_SOUS_TITRES = """Tu es un rédacteur sobre qui structure un ouvrage.

À partir du texte d'une section d'un ouvrage (réunions d'une étude biblique), propose 2 à 5 niveaux de sous-titres sobres pour structurer ce texte.

Règles :
- 2 à 5 propositions maximum ;
- sous-titres sobres, descriptifs, sans fioriture ;
- un sous-titre par ligne, sans numérotation, sans puce, sans guillemets ;
- ne jamais réécrire le texte fourni : seuls des sous-titres ;
- écrire en français."""


NOMBRE_MIN_SUGGESTIONS = 2
NOMBRE_MAX_SUGGESTIONS = 5


def nettoyer_suggestions(texte: str) -> list:
    """
    Nettoie la réponse LLM en liste de sous-titres :
    une ligne par suggestion, numérotations et
    puces retirées, vides écartés — bornée à
    ``NOMBRE_MAX_SUGGESTIONS``.
    """

    suggestions = []

    for ligne in (texte or "").splitlines():

        nettoyee = re.sub(
            r"^\s*(?:\d+[.)]|[-*•])\s*",
            "",
            ligne.strip()
        ).strip().strip('"“”')

        if nettoyee:
            suggestions.append(nettoyee)

        if len(suggestions) >= NOMBRE_MAX_SUGGESTIONS:
            break

    return suggestions


class ServiceSousTitres:
    """
    Propose des sous-titres pour UNE section de
    l'ouvrage (un appel LLM) — la section = les
    textes fournis par l'appelant.
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

        # Prompt effectif du dernier appel (traçabilité).
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
        """
        Paramètres du bloc reformulation de l'étude
        (l'ouvrage est rédigé dans le style des
        reformulations).
        """

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
            temperatures.get(
                "reformulation",
                0.3
            )
        )

    def proposer(
        self,
        textes: list,
        annulation: Annulation = None
    ) -> tuple:
        """
        UNE passe LLM sur la section (liste de textes
        de paragraphes) : retourne
        ``(suggestions, stats)`` — suggestions =
        liste de 2 à 5 sous-titres nettoyés.

        RIEN n'est écrit dans le document : la
        suggestion revient à l'appelant, qui la
        soumet à validation (jamais d'insertion
        automatique).
        """

        textes = [
            t for t in (textes or []) if t and t.strip()
        ]

        if not textes:
            raise ValueError(
                "Section vide : aucun texte à structurer."
            )

        fournisseur, modele = self.resoudre()
        client = self._creer_client(fournisseur)

        contenu = "\n\n".join(textes)

        message = (
            "Texte de la section de l'ouvrage à "
            "structurer :\n\n"
            + contenu
        )

        self.dernier_prompt = PROMPT_SOUS_TITRES

        from services.prompts import hash_prompt

        self.dernier_prompt_hash = hash_prompt(
            PROMPT_SOUS_TITRES
        )

        resultat = client.completions(
            PROMPT_SOUS_TITRES,
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

        suggestions = nettoyer_suggestions(
            resultat.texte
        )

        return suggestions, stats
