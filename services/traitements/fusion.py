"""
Service de fusion de pensées assistée (P19.4,
feuille de route v2.1 §P19 ; **P19.4-bis**
ARBITRAGE_PROMPT_FUSION_2026-11-07a : le prompt
de fusion vit dans la BIBLIOTHÈQUE ÉDITABLE
``prompts/fusion.md`` — règle générale : aucun
prompt LLM codé en dur).

La fusion de pensées est une opération de
COMPOSITION DE L'OUVRAGE (page Ouvrage) : deux
paragraphes dont la pensée est très similaire
deviennent un seul paragraphe portant les
provenances multiples. L'assistance LLM proposée
ici envoie les PENSÉES CANDIDATES (textes,
locuteurs, réunions sources) au prompt de
fusion, qui PROPOSE un paragraphe unique —
l'utilisateur l'édite et le valide ; jamais
d'application automatique (invariant des
suggestions IA, spec navigation §9.7).

Résolution du prompt (règles P16-ter) : copie
locale de l'étude (parametres.fusion.prompt) si
elle existe, sinon la bibliothèque +
``prompts/fusion.md`` du dossier de paramétrage
(sans fichier : défaut embarqué
``resources/prompts/prompt_fusion_v2.md``).

Même résolution de CONFIGURATION que le moteur et
le service résumé pour le modèle (bloc
reformulation de l'étude — la fusion rédige dans
le style de l'ouvrage rédigé par reformulation),
température « reformulation », jamais envoyée à
un modèle qui ne la supporte pas.

Le prompt EFFECTIF (texte + hash court) est
consigné dans l'élément fusionné de ouvrage.json
(traçabilité P16-ter/P19.4-bis).
"""

from services.llm.catalogue import (
    CatalogueError,
    CatalogueLLM,
    effort_effectif,
)
from services.llm.client import (
    Annulation,
    ParametresCompletion,
    ResultatCompletion,
    creer_client,
)
from services.etude_io import EtudeOuverte
from services.prompts import (
    hash_prompt,
    lire_bibliotheque,
    USAGE_FUSION,
)
from services.traitements.moteur import (
    TEMPERATURE_REFORMULATION_DEFAUT,
)


class ServiceFusion:
    """
    Assistance LLM à la fusion de pensées :
    un appel, les deux textes en entrée + la
    consigne ; le résultat est une PROPOSITION
    (jamais écrite dans le document sans
    validation explicite de l'utilisateur).
    """

    def __init__(
        self,
        etude_ouverte: EtudeOuverte,
        parametres_app: dict = None,
        credential_store=None,
        catalogue: CatalogueLLM = None,
        client_factory=None,
        dossier_prompts=None
    ):
        self.etude = etude_ouverte

        self._parametres_app_bruts = parametres_app
        self._credential_store = credential_store
        self._catalogue = catalogue
        self._client_factory = client_factory

        # Dossier de la bibliothèque de prompts
        # (injectable pour les tests ; défaut :
        # dossier de paramétrage de l'app).
        self._dossier_prompts = dossier_prompts

        # Prompt effectif du dernier appel (traçabilité
        # texte + hash, P19.4-bis : consigné dans
        # ouvrage.json par l'appelant).
        self.dernier_prompt = ""
        self.dernier_prompt_hash = ""

    #
    # Configuration (mêmes règles que le moteur).
    #

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
            CredentialStore
        )

        return CredentialStore(
            APP_DATA_DIR / "settings.json"
        )

    def _catalogue_courant(self) -> CatalogueLLM:

        if self._catalogue is not None:
            return self._catalogue

        from services.llm.catalogue import (
            charger_catalogue
        )

        return charger_catalogue()

    def _parametres_bloc(self) -> dict:
        """
        Paramètres du bloc reformulation de l'étude
        (le style de l'ouvrage est celui des
        reformulations — la fusion rédige dans la
        même maison) : modèle et température.
        """

        return (
            self.etude.parametres.reformulation
        )

    def prompt_effectif(self) -> str:
        """
        Prompt de fusion EFFECTIF (règles P16-ter,
        P19.4-bis) : copie locale de l'étude
        (``parametres.fusion.prompt``) si elle
        existe, sinon la bibliothèque
        ``prompts/fusion.md`` du dossier de
        paramétrage, sinon le DÉFAUT EMBARQUÉ
        (``resources/prompts/prompt_fusion_v2.md``
        — jamais modifié).
        """

        bloc = (
            self.etude.parametres.fusion or {}
        )

        prompt = bloc.get("prompt")

        if prompt:
            return prompt

        return lire_bibliotheque(
            USAGE_FUSION,
            self._dossier_prompts
        )[0]

    def resoudre(self):
        """
        Résout (fournisseur, modèle) : fournisseur
        des réglages app ; modèle surchargé par
        l'étude (parametres.reformulation.modele)
        s'il existe chez ce fournisseur, sinon
        modèle des réglages.
        """

        catalogue = self._catalogue_courant()
        app = self._parametres_app()

        fournisseur = (
            catalogue.chercher_fournisseur(
                app.get("fournisseur")
            )
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

    def temperature_effective(self) -> float:
        """
        Surcharge étude si définie, sinon réglage app
        (température « reformulation »), sinon 0.3.
        """

        surcharge = (
            self._parametres_bloc().get("temperature")
        )

        if surcharge is not None:
            return float(surcharge)

        app = self._parametres_app()

        temperatures = app.get("temperatures", {})

        valeur = temperatures.get(
            "reformulation",
            app.get(
                "temperature",
                TEMPERATURE_REFORMULATION_DEFAUT
            ),
        )

        return float(valeur)

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

    def _parametres_completion(
        self,
        modele,
        temperature: float
    ) -> ParametresCompletion:
        """
        Même règle que le moteur : la température
        n'est envoyée que si le modèle la supporte ;
        l'effort de raisonnement accepté suit le
        défaut du modèle.
        """

        config = self._parametres_app()

        effort = effort_effectif(
            modele,
            config.get("effort_raisonnement")
        )

        return ParametresCompletion(
            modele=modele.id,
            temperature=(
                temperature
                if modele.capacite_temperature
                else None
            ),
            max_tokens=(
                config.get("max_tokens") or None
            ),
            effort_raisonnement=effort,
        )

    #
    # Appel.
    #

    def message_fusion(
        self,
        texte_1: str,
        texte_2: str,
        source_1: str = "",
        source_2: str = ""
    ) -> str:
        """
        Message utilisateur : les PENSÉES
        CANDIDATES (textes, locuteurs, réunions
        sources) — le prompt système (bibliothèque
        prompts/fusion.md) porte les instructions.
        """

        parties = []

        if source_1:
            parties.append(f"Source 1 : {source_1}")

        parties.append(
            "Premier paragraphe :\n"
            + (texte_1 or "").strip()
        )

        if source_2:
            parties.append(f"Source 2 : {source_2}")

        parties.append(
            "Deuxième paragraphe :\n"
            + (texte_2 or "").strip()
        )

        return "\n\n".join(parties)

    def proposer(
        self,
        texte_1: str,
        texte_2: str,
        source_1: str = "",
        source_2: str = "",
        annulation: Annulation = None
    ) -> ResultatCompletion:
        """
        Propose le paragraphe fusionné : UN appel
        LLM avec le prompt de FUSION (bibliothèque
        éditable, P19.4-bis) comme prompt système
        et les pensées candidates (textes,
        locuteurs, réunions sources) comme message
        utilisateur.

        Le résultat ne touche JAMAIS le document
        ouvrage : c'est une proposition rapportée à
        l'utilisateur (édition et validation
        explicites dans le dialogue de fusion).

        Le prompt EFFECTIF est consigné dans
        ``self.dernier_prompt`` / ``self.dernier_prompt_hash``
        (traçabilité texte + hash dans ouvrage.json,
        P19.4-bis).
        """

        fournisseur, modele = self.resoudre()

        client = self._creer_client(fournisseur)

        prompt_systeme = self.prompt_effectif()

        self.dernier_prompt = prompt_systeme
        self.dernier_prompt_hash = hash_prompt(
            prompt_systeme
        )

        message = self.message_fusion(
            texte_1,
            texte_2,
            source_1,
            source_2
        )

        parametres = self._parametres_completion(
            modele,
            self.temperature_effective()
        )

        return client.completions(
            prompt_systeme,
            [
                {
                    "role": "user",
                    "content": message,
                }
            ],
            parametres,
            annulation=annulation
        )
