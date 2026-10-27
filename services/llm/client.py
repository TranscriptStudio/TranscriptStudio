# services/llm/client.py
"""
Service LLM (P15.1) : client abstrait et
implémentations par famille d'API.

Spécification de référence : PARAMETRAGE_LLM_V2.md §4,
FEUILLE_DE_ROUTE_V2.md §3.2.

- interface unique : ``completions(prompt_systeme,
  messages, parametres, streaming)`` ;
- un adaptateur par famille : ``openai_compatible``
  (OpenAI, Mistral, Groq, DeepSeek, xAI, OpenRouter,
  serveur local Ollama/LM Studio) et ``anthropic`` ;
- **streaming** pour l'affichage progressif ;
- **usage** (tokens réels de la réponse) et **coût
  estimé** lu dans le catalogue ;
- **réseau** : timeout, relance automatique avec backoff
  sur erreur transitoire (429, 5xx, connexion), message
  d'erreur clair (clé invalide, quota, réseau) — jamais
  d'exception brute à l'écran ;
- **annulation** propre en cours de passe ;
- un appel qui échoue ne modifie aucun document de
  l'étude (le résultat absent est simplement une version
  non créée — règle d'invariance 4) : ce service n'écrit
  rien, il retourne ou lève.

Aucune clé n'est jamais journalisée ni inclue dans un
message d'erreur (règle d'invariance 1).
"""

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import requests

from services.llm.catalogue import (
    FournisseurCatalogue,
    ModeleCatalogue,
    cout_estime,
    estimer_tokens,
)


TYPES_ERREUR = (
    "cle_invalide",
    "quota",
    "reseau",
    "timeout",
    "annulation",
    "autre",
)


class ErreurLLM(Exception):
    """
    Erreur LLM au message clair (clé invalide,
    quota, réseau...), jamais d'exception brute.

    La clé API ne figure jamais dans le message
    (règle d'invariance 1 : aucun secret en clair
    dans un fichier, un log ou l'UI).
    """

    def __init__(self, type_erreur: str, message: str):

        self.type = type_erreur
        self.message = message

        super().__init__(message)


class Annulation:
    """
    Demande d'annulation d'une passe : le moteur
    positionne ``demandee`` (ou appelle ``annuler()``),
    le client s'arrête proprement entre deux chunks.
    """

    def __init__(self):
        self.demandee = False

    def annuler(self):
        self.demandee = True


@dataclass
class ParametresCompletion:
    """
    Paramètres d'un appel de complétion : modèle
    cible et réglages optionnels (adaptés aux
    capacités déclarées du modèle).
    """

    modele: str
    temperature: float = None
    max_tokens: int = None
    effort_raisonnement: str = None


@dataclass
class ResultatCompletion:
    """
    Résultat d'une complétion : texte produit,
    usage réel renvoyé par l'API, durée de l'appel
    et coût estimé aux prix courants du catalogue.

    Ces valeurs alimentent les stats de version du
    contrat format étude §7 (jamais recalculées
    rétroactivement — règle d'invariance 5).
    """

    texte: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    duree_ms: int = 0
    cout_estime: float = 0.0
    modele: str = ""
    fournisseur: str = ""


def _sanitiser(texte: str, cle: str) -> str:
    """
    Retire toute trace de la clé d'un message
    (défense en profondeur : les messages sont
    construits par nos soins, sans clé).
    """

    if not cle or not texte:
        return texte

    return str(texte).replace(cle, "***")


class LLMClient(ABC):
    """
    Client abstrait : une complétion par appel,
    en streaming, avec relance sur erreur
    transitoire et annulation propre.
    """

    timeout_secondes = 120

    def __init__(
        self,
        fournisseur: FournisseurCatalogue,
        cle_api: str,
        session=None,
        attente=None,
        tentatives: int = 3,
        delai_retry: float = 1.0
    ):
        self.fournisseur = fournisseur
        self.cle_api = cle_api or ""
        self.session = session or requests.Session()
        self.attente = attente or time.sleep
        self.tentatives = max(1, tentatives)
        self.delai_retry = delai_retry

    def completions(
        self,
        prompt_systeme: str,
        messages: list,
        parametres: ParametresCompletion,
        streaming_callback=None,
        annulation: Annulation = None
    ) -> ResultatCompletion:
        """
        Exécute une complétion avec relance
        automatique sur erreur transitoire.

        ``messages`` : liste de dicts
        ``{"role": "user"|"assistant", "content": str}``
        — le contexte assemblé par le moteur (P15.3),
        dernière unité comprise.
        """

        debut = time.monotonic()

        derniere_erreur = None

        for tentative in range(self.tentatives):

            if annulation is not None and annulation.demandee:
                raise ErreurLLM(
                    "annulation",
                    "Traitement annulé avant l'appel."
                )

            try:

                texte, tokens_in, tokens_out = (
                    self._executer(
                        prompt_systeme,
                        messages,
                        parametres,
                        streaming_callback,
                        annulation
                    )
                )

                duree_ms = int(
                    (time.monotonic() - debut) * 1000
                )

                return self._construire_resultat(
                    texte,
                    tokens_in,
                    tokens_out,
                    duree_ms,
                    messages,
                    parametres
                )

            except ErreurLLM as e:

                if e.type == "annulation":
                    raise

                derniere_erreur = e

                if not self._est_transitoire(e.type):
                    raise

                if tentative < self.tentatives - 1:
                    self.attente(self.delai_retry)
                    self.delai_retry = (
                        self.delai_retry * 2
                    )

        raise derniere_erreur

    def _construire_resultat(
        self,
        texte: str,
        tokens_in: int,
        tokens_out: int,
        duree_ms: int,
        messages: list,
        parametres: ParametresCompletion
    ) -> ResultatCompletion:

        modele = self.fournisseur.chercher_modele(
            parametres.modele
        )

        cout = 0.0

        if modele is not None:
            cout = cout_estime(
                modele,
                tokens_in,
                tokens_out
            )

        return ResultatCompletion(
            texte=texte,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            duree_ms=duree_ms,
            cout_estime=cout,
            modele=parametres.modele,
            fournisseur=self.fournisseur.id,
        )

    @staticmethod
    def _est_transitoire(type_erreur: str) -> bool:

        return type_erreur in ("quota", "reseau", "timeout")

    def _erreur_http(
        self,
        statut: int,
        corps: str
    ) -> ErreurLLM:
        """
        Traduit un statut HTTP en erreur claire.
        """

        detail = ""

        try:

            donnees = json.loads(corps)

            message = (
                donnees.get("error", {})
                .get("message", "")
                if isinstance(
                    donnees.get("error"),
                    dict
                )
                else donnees.get(
                    "error",
                    ""
                )
            )

            if isinstance(message, str) and message:
                detail = message[:200]

        except (ValueError, TypeError, AttributeError):
            detail = ""

        detail = _sanitiser(detail, self.cle_api)

        nom = self.fournisseur.nom

        if statut in (401, 403):

            return ErreurLLM(
                "cle_invalide",
                (
                    f"Clé API invalide ou expirée pour "
                    f"{nom}. Vérifiez la clé dans les "
                    "paramètres."
                    + (f" ({detail})" if detail else "")
                )
            )

        if statut == 429:

            return ErreurLLM(
                "quota",
                (
                    f"Quota ou limite d'appels atteinte "
                    f"chez {nom}. La tentative sera "
                    "relancée automatiquement."
                    + (f" ({detail})" if detail else "")
                )
            )

        if statut == 404:

            return ErreurLLM(
                "autre",
                (
                    f"Modèle ou adresse introuvable chez "
                    f"{nom} (404). Vérifiez le modèle et "
                    f"la base URL du fournisseur."
                    + (f" ({detail})" if detail else "")
                )
            )

        return ErreurLLM(
            "reseau",
            (
                f"Erreur serveur {statut} chez {nom}. "
                "La tentative sera relancée "
                "automatiquement."
                + (f" ({detail})" if detail else "")
            )
        )

    def _verifier_annulation(self, annulation):

        if (
            annulation is not None
            and annulation.demandee
        ):
            raise ErreurLLM(
                "annulation",
                "Traitement annulé par l'utilisateur."
            )

    @abstractmethod
    def _executer(
        self,
        prompt_systeme: str,
        messages: list,
        parametres: ParametresCompletion,
        streaming_callback,
        annulation
    ):
        """
        Famille-specific : exécute l'appel en
        streaming et retourne
        (texte, tokens_in, tokens_out).
        """

        pass

    @abstractmethod
    def tester_connexion(self):
        """
        Validation légère de la clé (liste des
        modèles) pour le bouton « Tester la clé »
        des réglages.
        """

        pass


class ClientOpenAICompatible(LLMClient):
    """
    Adaptateur de la famille openai_compatible :
    OpenAI, Mistral, Groq, DeepSeek, xAI,
    OpenRouter, serveurs locaux Ollama/LM Studio.

    POST {base_url}/chat/completions, streaming
    SSE, usage renvoyé dans le dernier chunk.
    """

    def _entetes(self) -> dict:

        entetes = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }

        if self.cle_api:
            entetes["Authorization"] = (
                f"Bearer {self.cle_api}"
            )

        return entetes

    def _executer(
        self,
        prompt_systeme: str,
        messages: list,
        parametres: ParametresCompletion,
        streaming_callback,
        annulation
    ):

        messages_requete = []

        if prompt_systeme:
            messages_requete.append({
                "role": "system",
                "content": prompt_systeme,
            })

        messages_requete.extend(messages)

        charge = {
            "model": parametres.modele,
            "messages": messages_requete,
            "stream": True,
            "stream_options": {
                "include_usage": True
            },
        }

        if parametres.temperature is not None:
            charge["temperature"] = (
                parametres.temperature
            )

        if parametres.max_tokens is not None:
            charge["max_tokens"] = (
                parametres.max_tokens
            )

        if parametres.effort_raisonnement is not None:
            charge["reasoning_effort"] = (
                parametres.effort_raisonnement
            )

        url = (
            f"{self.fournisseur.base_url.rstrip('/')}"
            "/chat/completions"
        )

        try:

            reponse = self.session.post(
                url,
                headers=self._entetes(),
                json=charge,
                stream=True,
                timeout=self.timeout_secondes,
            )

        except requests.exceptions.Timeout as e:
            raise ErreurLLM(
                "timeout",
                _sanitiser(
                    f"Délai dépassé en joignant "
                    f"{self.fournisseur.nom} "
                    "(le réseau est lent ou le modèle "
                    "long à répondre).",
                    self.cle_api,
                )
            ) from e

        except requests.exceptions.RequestException as e:
            raise ErreurLLM(
                "reseau",
                _sanitiser(
                    f"Impossible de joindre "
                    f"{self.fournisseur.nom}. Vérifiez "
                    "votre connexion internet et la base "
                    "URL du fournisseur.",
                    self.cle_api,
                )
            ) from e

        if reponse.status_code != 200:
            raise self._erreur_http(
                reponse.status_code,
                reponse.text
            )

        return self._lire_flux_sse(
            reponse,
            streaming_callback,
            annulation
        )

    def _lire_flux_sse(
        self,
        reponse,
        streaming_callback,
        annulation
    ):
        """
        Lit le flux SSE : deltas de texte, puis
        usage dans le chunk final.
        """

        morceaux = []
        tokens_in = None
        tokens_out = None

        for ligne in reponse.iter_lines(
            decode_unicode=True
        ):

            self._verifier_annulation(annulation)

            if not ligne:
                continue

            if not ligne.startswith("data:"):
                continue

            donnees = ligne[len("data:"):].strip()

            if donnees == "[DONE]":
                break

            try:
                chunk = json.loads(donnees)
            except ValueError:
                continue

            usage = chunk.get("usage")

            if isinstance(usage, dict):
                tokens_in = usage.get(
                    "prompt_tokens",
                    tokens_in
                )
                tokens_out = usage.get(
                    "completion_tokens",
                    tokens_out
                )

            choixs = chunk.get("choices") or []

            if not choixs:
                continue

            delta = choixs[0].get("delta", {})
            morceau = delta.get("content")

            if morceau:

                morceaux.append(morceau)

                if streaming_callback:
                    streaming_callback(morceau)

        texte = "".join(morceaux)

        #
        # Usage absent de la réponse : estimation
        # locale (les stats stockées préciseront
        # toujours l'usage réel quand l'API le
        # fournit).
        #
        if tokens_in is None:
            tokens_in = estimer_tokens(texte)

        if tokens_out is None:
            tokens_out = estimer_tokens(texte)

        return texte, tokens_in, tokens_out

    def tester_connexion(self):
        """
        Validation légère de la clé : GET /models,
        avec relance sur erreur transitoire (5xx,
        quota) — une clé valide ne doit pas être
        signalée invalide pour une panne passagère
        du fournisseur.
        """

        url = (
            f"{self.fournisseur.base_url.rstrip('/')}"
            "/models"
        )

        for tentative in range(self.tentatives):

            try:

                reponse = self.session.get(
                    url,
                    headers=self._entetes(),
                    timeout=30,
                )

            except requests.exceptions.RequestException as e:
                raise ErreurLLM(
                    "reseau",
                    _sanitiser(
                        f"Impossible de joindre "
                        f"{self.fournisseur.nom}. Vérifiez "
                        "votre connexion internet et la base "
                        "URL du fournisseur.",
                        self.cle_api,
                    )
                ) from e

            if reponse.status_code == 200:
                break

            erreur = self._erreur_http(
                reponse.status_code,
                reponse.text
            )

            if (
                not self._est_transitoire(erreur.type)
                or tentative == self.tentatives - 1
            ):
                raise erreur

            self.attente(self.delai_retry)

        modeles = []

        try:

            donnees = reponse.json()

            for modele in donnees.get("data", []):

                identifiant = modele.get("id")

                if identifiant:
                    modeles.append(identifiant)

        except (ValueError, AttributeError):
            modeles = []

        return {
            "ok": True,
            "message": (
                f"Connexion validée : "
                f"{len(modeles)} modèle(s) accessible(s) "
                f"chez {self.fournisseur.nom}."
            ),
            "modeles": modeles,
        }


class ClientAnthropic(LLMClient):
    """
    Adaptateur de la famille anthropic : POST
    {base_url}/v1/messages, streaming d'événements,
    usage dans message_start / message_delta.
    """

    VERSION_API = "2023-06-01"

    def _entetes(self) -> dict:

        return {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "anthropic-version": self.VERSION_API,
            "x-api-key": self.cle_api,
        }

    def _executer(
        self,
        prompt_systeme: str,
        messages: list,
        parametres: ParametresCompletion,
        streaming_callback,
        annulation
    ):

        charge = {
            "model": parametres.modele,
            # max_tokens est obligatoire chez
            # Anthropic : défaut raisonnable si le
            # modèle ne le déclare pas.
            "max_tokens": (
                parametres.max_tokens or 4096
            ),
            "messages": list(messages),
            "stream": True,
        }

        if prompt_systeme:
            charge["system"] = prompt_systeme

        if parametres.temperature is not None:
            charge["temperature"] = (
                parametres.temperature
            )

        url = (
            f"{self.fournisseur.base_url.rstrip('/')}"
            "/v1/messages"
        )

        try:

            reponse = self.session.post(
                url,
                headers=self._entetes(),
                json=charge,
                stream=True,
                timeout=self.timeout_secondes,
            )

        except requests.exceptions.Timeout as e:
            raise ErreurLLM(
                "timeout",
                _sanitiser(
                    f"Délai dépassé en joignant "
                    f"{self.fournisseur.nom}.",
                    self.cle_api,
                )
            ) from e

        except requests.exceptions.RequestException as e:
            raise ErreurLLM(
                "reseau",
                _sanitiser(
                    f"Impossible de joindre "
                    f"{self.fournisseur.nom}. Vérifiez "
                    "votre connexion internet et la base "
                    "URL du fournisseur.",
                    self.cle_api,
                )
            ) from e

        if reponse.status_code != 200:
            raise self._erreur_http(
                reponse.status_code,
                reponse.text
            )

        return self._lire_evenements(
            reponse,
            streaming_callback,
            annulation
        )

    def _lire_evenements(
        self,
        reponse,
        streaming_callback,
        annulation
    ):
        """
        Lit les événements SSE d'Anthropic :
        message_start (usage.input_tokens),
        content_block_delta (texte),
        message_delta (usage.output_tokens),
        message_stop.
        """

        morceaux = []
        tokens_in = None
        tokens_out = None

        for ligne in reponse.iter_lines(
            decode_unicode=True
        ):

            self._verifier_annulation(annulation)

            if not ligne:
                continue

            if not ligne.startswith("data:"):
                continue

            donnees = ligne[len("data:"):].strip()

            try:
                evenement = json.loads(donnees)
            except ValueError:
                continue

            type_evenement = evenement.get("type")

            if type_evenement == "message_start":

                usage = (
                    evenement
                    .get("message", {})
                    .get("usage", {})
                )

                tokens_in = usage.get(
                    "input_tokens",
                    tokens_in
                )

            elif type_evenement == "content_block_delta":

                morceau = (
                    evenement
                    .get("delta", {})
                    .get("text")
                )

                if morceau:

                    morceaux.append(morceau)

                    if streaming_callback:
                        streaming_callback(morceau)

            elif type_evenement == "message_delta":

                usage = evenement.get("usage", {})

                tokens_out = usage.get(
                    "output_tokens",
                    tokens_out
                )

            elif type_evenement == "message_stop":
                break

            elif type_evenement == "error":

                raise ErreurLLM(
                    "autre",
                    _sanitiser(
                        evenement.get(
                            "error", {}
                        ).get("message", "Erreur."),
                        self.cle_api,
                    )
                )

        texte = "".join(morceaux)

        if tokens_in is None:
            tokens_in = estimer_tokens(texte)

        if tokens_out is None:
            tokens_out = estimer_tokens(texte)

        return texte, tokens_in, tokens_out

    def tester_connexion(self):
        """
        Validation légère de la clé : GET /v1/models,
        avec relance sur erreur transitoire (5xx,
        quota) — une clé valide ne doit pas être
        signalée invalide pour une panne passagère
        du fournisseur.
        """

        url = (
            f"{self.fournisseur.base_url.rstrip('/')}"
            "/v1/models"
        )

        for tentative in range(self.tentatives):

            try:

                reponse = self.session.get(
                    url,
                    headers=self._entetes(),
                    timeout=30,
                )

            except requests.exceptions.RequestException as e:
                raise ErreurLLM(
                    "reseau",
                    _sanitiser(
                        f"Impossible de joindre "
                        f"{self.fournisseur.nom}.",
                        self.cle_api,
                    )
                ) from e

            if reponse.status_code == 200:
                break

            erreur = self._erreur_http(
                reponse.status_code,
                reponse.text
            )

            if (
                not self._est_transitoire(erreur.type)
                or tentative == self.tentatives - 1
            ):
                raise erreur

            self.attente(self.delai_retry)

        modeles = []

        try:

            donnees = reponse.json()

            for modele in donnees.get("data", []):
                identifiant = modele.get("id")
                if identifiant:
                    modeles.append(identifiant)

        except (ValueError, AttributeError):
            modeles = []

        return {
            "ok": True,
            "message": (
                f"Connexion validée : "
                f"{len(modeles)} modèle(s) accessible(s) "
                f"chez {self.fournisseur.nom}."
            ),
            "modeles": modeles,
        }


def creer_client(
    fournisseur: FournisseurCatalogue,
    cle_api: str,
    session=None,
    attente=None,
    tentatives: int = 3,
    delai_retry: float = 1.0
) -> LLMClient:
    """
    Crée le client correspondant à la famille
    d'API du fournisseur.
    """

    arguments = {
        "fournisseur": fournisseur,
        "cle_api": cle_api,
        "session": session,
        "attente": attente,
        "tentatives": tentatives,
        "delai_retry": delai_retry,
    }

    if fournisseur.famille_api == "openai_compatible":
        return ClientOpenAICompatible(**arguments)

    if fournisseur.famille_api == "anthropic":
        return ClientAnthropic(**arguments)

    raise ErreurLLM(
        "autre",
        (
            f"Famille d'API inconnue pour "
            f"{fournisseur.nom} : "
            f"{fournisseur.famille_api!r}"
        )
    )
