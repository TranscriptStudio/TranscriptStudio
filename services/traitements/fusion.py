"""
Service de fusion de pensées assistée (P19.4,
feuille de route v2.1 §P19).

La fusion de pensées est une opération de
COMPOSITION DE L'OUVRAGE (page Ouvrage) : deux
paragraphes dont la pensée est très similaire
deviennent un seul paragraphe portant les
provenances multiples. L'assistance LLM proposée
ici est une **relance avec les deux textes en
entrée + consigne** : elle PROPOSE un paragraphe
fusionné, l'utilisateur l'édite et le valide —
jamais d'application automatique (invariant des
suggestions IA, spec navigation §9.7).

Même résolution de configuration que le moteur et
le service résumé : fournisseur des réglages app,
modèle surchargé par l'étude (paramètres du bloc
reformulation — la fusion rédige dans le style de
l'ouvrage rédigé par reformulation), température
« reformulation », jamais envoyée à un modèle qui
ne la supporte pas.
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
from services.traitements.moteur import (
    TEMPERATURE_REFORMULATION_DEFAUT,
)


CONSIGNE_FUSION = (
    "Les deux paragraphes ci-dessous appartiennent "
    "au même ouvrage et expriment la même pensée. "
    "Rédige le paragraphe UNIQUE qui la porte : "
    "chaque pensée est conservée une seule fois, "
    "sans doublon ni répétition, en respectant "
    "les règles de style et de fidélité de "
    "l'ouvrage.\n"
    "Rends uniquement le paragraphe fusionné, "
    "sans titre, sans commentaire."
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
        client_factory=None
    ):
        self.etude = etude_ouverte

        self._parametres_app_bruts = parametres_app
        self._credential_store = credential_store
        self._catalogue = catalogue
        self._client_factory = client_factory

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
        même maison).
        """

        return (
            self.etude.parametres.reformulation
        )

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
        texte_2: str
    ) -> str:
        """
        Message utilisateur : les deux textes en
        entrée + la consigne (P19.4).
        """

        return (
            "Premier paragraphe :\n"
            + (texte_1 or "").strip()
            + "\n\n"
            "Deuxième paragraphe :\n"
            + (texte_2 or "").strip()
            + "\n\n"
            + CONSIGNE_FUSION
        )

    def proposer(
        self,
        texte_1: str,
        texte_2: str,
        annulation: Annulation = None
    ) -> ResultatCompletion:
        """
        Propose le paragraphe fusionné : UN appel
        LLM avec le prompt de reformulation de
        l'étude (style et fidélité de l'ouvrage)
        comme prompt système, les deux textes + la
        consigne comme message utilisateur.

        Le résultat ne touche JAMAIS le document
        ouvrage : c'est une proposition rapportée à
        l'utilisateur (édition et validation
        explicites dans le dialogue de fusion).
        """

        fournisseur, modele = self.resoudre()

        client = self._creer_client(fournisseur)

        prompt_systeme = (
            self._parametres_bloc().get(
                "prompt", ""
            )
        )

        message = self.message_fusion(
            texte_1,
            texte_2
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
