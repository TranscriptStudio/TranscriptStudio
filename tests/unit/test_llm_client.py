"""
Tests unitaires du service LLM (P15.1) : clients par
famille d'API, streaming, usage/coût, relance,
annulation, messages d'erreur clairs.

Aucun appel réseau réel : la session HTTP est
injectée et factice.

Règles d'invariance couvertes :
- règle 1 : aucune clé API n'apparaît en clair
  dans un message d'erreur (jamais dans un log,
  l'UI ne montre que le champ masqué) ;
- règle 4 : un appel qui échoue ne modifie aucun
  document — le service ne fait qu'élever une
  erreur claire, il n'écrit rien du tout ;
- règle 5 : le coût estimé suit le prix courant du
  catalogue.
"""

import json

import pytest
import requests

from services.llm.catalogue import (
    FournisseurCatalogue,
    ModeleCatalogue,
    catalogue_par_defaut,
)
from services.llm.client import (
    Annulation,
    ErreurLLM,
    ParametresCompletion,
    creer_client,
)


CLE = "sk-test-123456789"


class FausseReponse:
    """
    Réponse HTTP factice : statut, lignes du flux
    SSE (pour POST) ou corps texte/json (pour GET).
    """

    def __init__(
        self,
        statut=200,
        lignes=None,
        texte="",
        donnees_json=None
    ):
        self.status_code = statut
        self._lignes = lignes or []
        self.text = texte
        self._donnees_json = donnees_json

    def iter_lines(self, decode_unicode=True):
        return iter(list(self._lignes))

    def json(self):
        return self._donnees_json


class FausseSession:
    """
    Session requests factice : enregistre les
    appels, rejoue les réponses ou exceptions
    fournies.
    """

    def __init__(self, reponses=None):
        self.appels = []
        self._reponses = list(reponses or [])

    def _prochaine(self, methode, url, headers, charge):

        self.appels.append({
            "methode": methode,
            "url": url,
            "headers": headers or {},
            "json": charge,
        })

        element = self._reponses.pop(0)

        if isinstance(element, Exception):
            raise element

        return element

    def post(
        self,
        url,
        headers=None,
        json=None,
        stream=False,
        timeout=None
    ):
        return self._prochaine(
            "POST", url, headers, json
        )

    def get(self, url, headers=None, timeout=None):
        return self._prochaine(
            "GET", url, headers, None
        )


def _sse_openai(morceaux, usage=None):
    """
    Flux SSE openai_compatible : deltas, usage
    final, [DONE].
    """

    lignes = []

    for morceau in morceaux:
        lignes.append(
            "data: "
            + json.dumps({
                "choices": [
                    {"delta": {"content": morceau}}
                ]
            })
        )

    chunk_final = {"choices": []}

    if usage is not None:
        chunk_final["usage"] = usage

    lignes.append("data: " + json.dumps(chunk_final))
    lignes.append("data: [DONE]")

    return lignes


def _fournisseur_openai():
    return catalogue_par_defaut().chercher_fournisseur(
        "openai"
    )


def _parametres(**surcharges):
    parametres = ParametresCompletion(
        modele="gpt-4.1",
        temperature=0.3,
    )

    for cle, valeur in surcharges.items():
        setattr(parametres, cle, valeur)

    return parametres


class TestClientOpenAICompatible:

    def test_completion_streaming(self):
        lignes = _sse_openai(
            ["Bon", "jour", " le ", "monde."],
            usage={
                "prompt_tokens": 100,
                "completion_tokens": 50,
            }
        )

        session = FausseSession(
            [FausseReponse(statut=200, lignes=lignes)]
        )

        client = creer_client(
            _fournisseur_openai(),
            CLE,
            session=session,
        )

        recus = []

        resultat = client.completions(
            "Prompt système.",
            [
                {"role": "user", "content": "Texte."}
            ],
            _parametres(),
            streaming_callback=recus.append,
        )

        assert resultat.texte == "Bonjour le monde."
        assert "".join(recus) == "Bonjour le monde."

        assert resultat.tokens_in == 100
        assert resultat.tokens_out == 50
        assert resultat.duree_ms >= 0

        #
        # Coût estimé aux prix du catalogue :
        # gpt-4.1 = 2.0 in / 8.0 out par million.
        #
        assert resultat.cout_estime == pytest.approx(
            (2.0 * 100 + 8.0 * 50) / 1_000_000
        )

        #
        # Requête envoyée : system + messages, clé
        # en en-tête Bearer, streaming.
        #
        appel = session.appels[0]

        assert appel["url"] == (
            "https://api.openai.com/v1/chat/completions"
        )

        assert appel["headers"]["Authorization"] == (
            f"Bearer {CLE}"
        )

        assert appel["json"]["model"] == "gpt-4.1"
        assert appel["json"]["stream"] is True
        assert appel["json"]["temperature"] == 0.3

        assert appel["json"]["messages"][0] == {
            "role": "system",
            "content": "Prompt système.",
        }

        assert appel["json"]["messages"][1] == {
            "role": "user",
            "content": "Texte.",
        }

    def test_effort_raisonnement_dans_la_requete(self):
        """
        L'effort de raisonnement mémorisé est bien
        transmis à l'API (reasoning_effort) ; None
        n'envoie JAMAIS la clé (défaut de l'API).
        """

        lignes = _sse_openai(["Ok."])

        session = FausseSession(
            [FausseReponse(statut=200, lignes=lignes)]
        )

        client = creer_client(
            _fournisseur_openai(),
            CLE,
            session=session,
        )

        client.completions(
            "Prompt système.",
            [{"role": "user", "content": "Texte."}],
            _parametres(effort_raisonnement="xhigh"),
        )

        appel = session.appels[0]

        assert appel["json"]["reasoning_effort"] == (
            "xhigh"
        )

        #
        # Sans effort : la clé est absente de la
        # requête (l'API garde son propre défaut).
        #
        session2 = FausseSession(
            [FausseReponse(statut=200, lignes=lignes)]
        )

        client2 = creer_client(
            _fournisseur_openai(),
            CLE,
            session=session2,
        )

        client2.completions(
            "Prompt système.",
            [{"role": "user", "content": "Texte."}],
            _parametres(),
        )

        assert "reasoning_effort" not in (
            session2.appels[0]["json"]
        )

    def test_usage_absent_estimation_locale(self):
        lignes = _sse_openai(["a" * 100])

        session = FausseSession(
            [FausseReponse(statut=200, lignes=lignes)]
        )

        client = creer_client(
            _fournisseur_openai(),
            CLE,
            session=session,
        )

        resultat = client.completions(
            None,
            [{"role": "user", "content": "x"}],
            _parametres(),
        )

        # Estimation heuristique (~1 token / 4
        # caractères) quand l'API ne renvoie pas
        # l'usage.
        assert resultat.tokens_out == 25
        assert resultat.tokens_in > 0

    def test_cle_invalide_sans_retry_ni_fuite(self):
        """
        Règles 1 et 4 : erreur claire, pas de
        relance, et la clé ne fuit jamais dans le
        message — même si le corps de la réponse
        la contenait.
        """

        corps = json.dumps({
            "error": {
                "message": (
                    "Incorrect API key provided: "
                    f"{CLE}. You can find your API key."
                )
            }
        })

        session = FausseSession([
            FausseReponse(statut=401, texte=corps)
        ])

        client = creer_client(
            _fournisseur_openai(),
            CLE,
            session=session,
        )

        with pytest.raises(ErreurLLM) as infos:
            client.completions(
                None,
                [{"role": "user", "content": "x"}],
                _parametres(),
            )

        assert infos.value.type == "cle_invalide"

        # Aucune relance sur une clé invalide.
        assert len(session.appels) == 1

        # La clé ne figure jamais dans le message
        # (règle d'invariance 1).
        assert CLE not in str(infos.value)
        assert CLE not in infos.value.message
        assert "***" in infos.value.message

        # Message clair, orienté utilisateur.
        assert "invalide" in infos.value.message

    def test_reseau_puis_succes(self):
        """
        Erreur transitoire : relance automatique
        avec backoff, puis succès.
        """

        lignes = _sse_openai(["Ok."])

        session = FausseSession([
            requests.exceptions.ConnectionError("boom"),
            FausseReponse(statut=200, lignes=lignes),
        ])

        attentes = []

        client = creer_client(
            _fournisseur_openai(),
            CLE,
            session=session,
            attente=attentes.append,
        )

        resultat = client.completions(
            None,
            [{"role": "user", "content": "x"}],
            _parametres(),
        )

        assert resultat.texte == "Ok."
        assert len(session.appels) == 2

        # Un échec transitoire = une attente de 1 s
        # (le doublement à 2 s intervient au
        # deuxième échec consécutif).
        assert attentes == [1.0]

    def test_quota_eteint_les_tentatives(self):
        session = FausseSession([
            FausseReponse(
                statut=429,
                texte=json.dumps(
                    {"error": {"message": "Rate limit"}}
                ),
            )
        ] * 3)

        client = creer_client(
            _fournisseur_openai(),
            CLE,
            session=session,
            attente=lambda _s: None,
        )

        with pytest.raises(ErreurLLM) as infos:
            client.completions(
                None,
                [{"role": "user", "content": "x"}],
                _parametres(),
            )

        assert infos.value.type == "quota"
        assert len(session.appels) == 3

    def test_annulation_avant_l_appel(self):
        session = FausseSession([])

        client = creer_client(
            _fournisseur_openai(),
            CLE,
            session=session,
        )

        annulation = Annulation()
        annulation.annuler()

        with pytest.raises(ErreurLLM) as infos:
            client.completions(
                None,
                [{"role": "user", "content": "x"}],
                _parametres(),
                annulation=annulation,
            )

        assert infos.value.type == "annulation"

        # Annulation propre : aucun appel parti.
        assert len(session.appels) == 0

    def test_annulation_en_cours_de_flux(self):
        lignes = [
            "data: " + json.dumps({
                "choices": [
                    {"delta": {"content": "a"}}
                ]
            }),
            "data: " + json.dumps({
                "choices": [
                    {"delta": {"content": "b"}}
                ]
            }),
            "data: " + json.dumps({
                "choices": [
                    {"delta": {"content": "c"}}
                ]
            }),
        ]

        session = FausseSession([
            FausseReponse(statut=200, lignes=lignes)
        ])

        client = creer_client(
            _fournisseur_openai(),
            CLE,
            session=session,
        )

        annulation = Annulation()

        def au_morceau(morceau):
            if morceau == "b":
                annulation.annuler()

        with pytest.raises(ErreurLLM) as infos:
            client.completions(
                None,
                [{"role": "user", "content": "x"}],
                _parametres(),
                streaming_callback=au_morceau,
                annulation=annulation,
            )

        assert infos.value.type == "annulation"

    def test_sans_cle_serveur_local(self):
        """
        Un fournisseur ajouté manuellement avec une
        base URL locale fonctionne sans clé.
        """

        fournisseur = FournisseurCatalogue(
            id="ollama",
            nom="Ollama",
            famille_api="openai_compatible",
            base_url="http://localhost:11434/v1",
            modeles=[
                ModeleCatalogue(
                    id="llama3",
                    nom_affiche="Llama 3",
                    capacites={"temperature": True},
                    prix={
                        "in_par_million": 0.0,
                        "out_par_million": 0.0,
                    },
                )
            ],
            origine="utilisateur",
        )

        lignes = _sse_openai(["Réponse."])

        session = FausseSession([
            FausseReponse(statut=200, lignes=lignes)
        ])

        client = creer_client(
            fournisseur,
            "",
            session=session,
        )

        resultat = client.completions(
            None,
            [{"role": "user", "content": "x"}],
            ParametresCompletion(modele="llama3"),
        )

        assert resultat.texte == "Réponse."

        # Pas d'en-tête Authorization sans clé.
        appel = session.appels[0]

        assert "Authorization" not in appel["headers"]

        # Modèle absent du catalogue des prix :
        # coût nul, pas d'exception.
        assert resultat.cout_estime == 0.0

    def test_tester_connexion(self):
        session = FausseSession([
            FausseReponse(
                statut=200,
                donnees_json={
                    "data": [
                        {"id": "gpt-4.1"},
                        {"id": "gpt-4o"},
                    ]
                },
            )
        ])

        client = creer_client(
            _fournisseur_openai(),
            CLE,
            session=session,
        )

        resultat = client.tester_connexion()

        assert resultat["ok"] is True
        assert resultat["modeles"] == [
            "gpt-4.1",
            "gpt-4o",
        ]
        assert "2 modèle(s)" in resultat["message"]

        assert session.appels[0]["url"] == (
            "https://api.openai.com/v1/models"
        )

    def test_tester_connexion_cle_invalide(self):
        session = FausseSession([
            FausseReponse(statut=401, texte="{}")
        ])

        client = creer_client(
            _fournisseur_openai(),
            CLE,
            session=session,
        )

        with pytest.raises(ErreurLLM) as infos:
            client.tester_connexion()

        assert infos.value.type == "cle_invalide"

    def test_tester_connexion_reessaie_erreur_serveur(self):
        """
        Un 504 transitoire est relancé : une clé
        valide n'est pas signalée invalide pour
        une panne passagère du fournisseur.
        """
        session = FausseSession([
            FausseReponse(statut=504, texte="{}"),
            FausseReponse(
                statut=200,
                donnees_json={
                    "data": [
                        {"id": "gpt-6.1-terra"}
                    ]
                },
            ),
        ])

        attentes = []

        client = creer_client(
            _fournisseur_openai(),
            CLE,
            session=session,
            attente=attentes.append,
        )

        resultat = client.tester_connexion()

        assert resultat["ok"] is True
        assert len(session.appels) == 2
        assert len(attentes) == 1

    def test_tester_connexion_erreur_serveur_epuisee(self):
        """
        Le 504 persistant remonte une erreur
        réseau, pas « clé invalide » — le message
        final reste celui du dernier statut.
        """
        session = FausseSession([
            FausseReponse(statut=504, texte="{}"),
            FausseReponse(statut=504, texte="{}"),
            FausseReponse(statut=504, texte="{}"),
        ])

        client = creer_client(
            _fournisseur_openai(),
            CLE,
            session=session,
            attente=lambda _s: None,
        )

        with pytest.raises(ErreurLLM) as infos:
            client.tester_connexion()

        assert infos.value.type == "reseau"
        assert "504" in infos.value.message
        assert len(session.appels) == 3


class TestClientAnthropic:

    def _fournisseur(self):
        return (
            catalogue_par_defaut()
            .chercher_fournisseur("anthropic")
        )

    def _evenements(self, texte, tokens_in, tokens_out):
        lignes = [
            "data: " + json.dumps({
                "type": "message_start",
                "message": {
                    "usage": {
                        "input_tokens": tokens_in
                    }
                },
            }),
            "data: " + json.dumps({
                "type": "content_block_delta",
                "delta": {"text": texte},
            }),
            "data: " + json.dumps({
                "type": "message_delta",
                "usage": {
                    "output_tokens": tokens_out
                },
            }),
            "data: " + json.dumps({
                "type": "message_stop"
            }),
        ]

        return lignes

    def test_tester_connexion_reessaie_erreur_serveur(self):
        """
        Un 503 transitoire est relancé chez
        anthropic aussi : la clé n'est pas
        signalée invalide.
        """
        session = FausseSession([
            FausseReponse(statut=503, texte="{}"),
            FausseReponse(
                statut=200,
                donnees_json={
                    "data": [
                        {"id": "claude-sonnet-5-5"}
                    ]
                },
            ),
        ])

        client = creer_client(
            self._fournisseur(),
            CLE,
            session=session,
            attente=lambda _s: None,
        )

        resultat = client.tester_connexion()

        assert resultat["ok"] is True
        assert len(session.appels) == 2

    def test_completion_streaming(self):
        session = FausseSession([
            FausseReponse(
                statut=200,
                lignes=self._evenements(
                    "Réponse sobre.",
                    tokens_in=200,
                    tokens_out=40,
                )
            )
        ])

        client = creer_client(
            self._fournisseur(),
            CLE,
            session=session,
        )

        recus = []

        resultat = client.completions(
            "Prompt système.",
            [{"role": "user", "content": "Texte."}],
            ParametresCompletion(
                modele="claude-sonnet-4",
                max_tokens=1024,
            ),
            streaming_callback=recus.append,
        )

        assert resultat.texte == "Réponse sobre."
        assert recus == ["Réponse sobre."]

        assert resultat.tokens_in == 200
        assert resultat.tokens_out == 40

        # claude-sonnet-4 : 3.0 in / 15.0 out.
        assert resultat.cout_estime == pytest.approx(
            (3.0 * 200 + 15.0 * 40) / 1_000_000
        )

        appel = session.appels[0]

        assert appel["url"] == (
            "https://api.anthropic.com/v1/messages"
        )

        assert appel["headers"]["x-api-key"] == CLE

        assert appel["headers"]["anthropic-version"]

        # Le prompt système est séparé (champ
        # system), max_tokens obligatoire appliqué.
        assert appel["json"]["system"] == (
            "Prompt système."
        )

        assert appel["json"]["max_tokens"] == 1024
        assert appel["json"]["messages"] == [
            {"role": "user", "content": "Texte."}
        ]

    def test_max_tokens_defaut(self):
        session = FausseSession([
            FausseReponse(
                statut=200,
                lignes=self._evenements("x", 1, 1)
            )
        ])

        client = creer_client(
            self._fournisseur(),
            CLE,
            session=session,
        )

        client.completions(
            None,
            [{"role": "user", "content": "x"}],
            ParametresCompletion(
                modele="claude-sonnet-4"
            ),
        )

        assert session.appels[0]["json"][
            "max_tokens"
        ] == 4096

    def test_erreur_everement(self):
        lignes = [
            "data: " + json.dumps({
                "type": "error",
                "error": {
                    "message": "overloaded_error"
                },
            })
        ]

        session = FausseSession([
            FausseReponse(statut=200, lignes=lignes)
        ])

        client = creer_client(
            self._fournisseur(),
            CLE,
            session=session,
        )

        with pytest.raises(ErreurLLM) as infos:
            client.completions(
                None,
                [{"role": "user", "content": "x"}],
                ParametresCompletion(
                    modele="claude-sonnet-4"
                ),
            )

        assert "overloaded_error" in infos.value.message
        assert CLE not in infos.value.message


class TestCreationClient:

    def test_famille_inconnue(self):
        fournisseur = FournisseurCatalogue(
            id="x",
            nom="X",
            famille_api="inconnue",
            base_url="https://x.example",
        )

        with pytest.raises(ErreurLLM) as infos:
            creer_client(fournisseur, "")

        assert infos.value.type == "autre"
