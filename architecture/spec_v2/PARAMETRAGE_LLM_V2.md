
# Spécification — Paramétrage LLM de l'application (v2 — P15)

Ce document définit l'architecture du service LLM et l'UI de paramétrage (fournisseurs, modèles, clés). Il fait autorité pour l'implémentation de P15.

## 1. Décisions de conception (atelier, 2026-10-27)

1. **Multi-fournisseurs** dès la v2 — la qualité de reformulation est le cœur de l'app, comparer des modèles est une capacité produit.
2. **Familles d'API, pas intégration par fournisseur** : deux adaptateurs seulement — `openai_compatible` (OpenAI, Mistral, Groq, DeepSeek, xAI, OpenRouter, serveur local Ollama/LM Studio…) et `anthropic` (Claude). Chaque fournisseur du catalogue déclare sa famille.
3. **Catalogue embarqué + extensible** (même philosophie que le résolveur FFmpeg P8) : liste par défaut fournie avec l'app, éditable par l'utilisateur.
4. **Fournisseur par défaut : OpenAI**, sélectionnable et modifiable librement.
5. **Capacités déclarées par modèle** : l'UI s'adapte (un modèle sans température n'affiche pas le réglage).

## 2. Modèle de données (catalogue — réglages de l'app)

```json
{
  "catalogue_version": 1,
  "fournisseurs": [
    {
      "id": "openai",
      "nom": "OpenAI",
      "famille_api": "openai_compatible",
      "base_url": "https://api.openai.com/v1",
      "endpoint_infos_compte": "available",     // "available" | "none"
      "modeles": [
        {
          "id": "gpt-4.1",
          "nom_affiche": "GPT-4.1",
          "capacites": { "temperature": true, "max_contexte_tokens": 1000000 },
          "prix": { "in_par_million": 2.0, "out_par_million": 8.0 }
        }
      ]
    },
    {
      "id": "mistral",
      "nom": "Mistral AI",
      "famille_api": "openai_compatible",
      "base_url": "https://api.mistral.ai/v1",
      "endpoint_infos_compte": "available",
      "modeles": [ { "id": "mistral-large-latest", "nom_affiche": "Mistral Large", "capacites": { "temperature": true, "max_contexte_tokens": 128000 }, "prix": { "in_par_million": 2.0, "out_par_million": 6.0 } } ]
    },
    {
      "id": "anthropic",
      "nom": "Anthropic",
      "famille_api": "anthropic",
      "base_url": "https://api.anthropic.com",
      "endpoint_infos_compte": "none",
      "modeles": [ { "id": "claude-sonnet-4", "nom_affiche": "Claude Sonnet 4", "capacites": { "temperature": true, "max_contexte_tokens": 200000 }, "prix": { "in_par_million": 3.0, "out_par_million": 15.0 } } ]
    }
  ]
}
```

- le catalogue est **éditable** : ajouter un fournisseur (id, famille, base URL, modèles), un modèle (id, capacités, prix) ; la mise à jour des prix se fait là — c'est le « catalogue de coûts » référencé par le contrat format étude (stats de version, coûts estimés) ;
- **aucune clé API en clair** : une clé par fournisseur, stockée via le `CredentialStore` v1 (jamais dans le JSON, jamais journalisée) ;
- un fournisseur ajouté manuellement avec une base URL locale (Ollama, LM Studio) fonctionne sans clé.

## 3. UI de paramétrage (boîte de réglages de l'app, onglet LLM)

Structure analogue à l'onglet ElevenLabs existant (pattern v1 : sélection fournisseur → clé → état du compte).

1. **Liste déroulante Fournisseur** (catalogue) ;
2. **Champ clé API** (masqué) + bouton « Tester la clé » : appel léger de validation (ex. liste des modèles) → état `valide / invalide / non testée` ;
3. **Infos de compte** (si `endpoint_infos_compte: available`) : affichage des informations exposées par l'API du fournisseur (solde, quota ou équivalent, selon disponibilité) — sinon, seul l'état de validité s'affiche ;
4. **Liste déroulante Modèle** (modèles du fournisseur, avec version) ;
5. **Réglages du modèle, adaptés aux capacités déclarées** : température (masquée si non supportée), curseur `max_tokens` plafonné au contexte du modèle ; un onglet avancé par modèle n'existe pas — la v2 se limite aux réglages utiles au prompt ;
6. **Gestion du catalogue** : bouton « Modifier le catalogue » (ajout/édition fournisseur et modèle, mise à jour des prix).

Sélection mémorisée : fournisseur + modèle par défaut de l'app ; chaque étude peut surcharger le choix (paramètres de l'étude, contrat §10) — typiquement pour comparer deux modèles sur la même étude sans changer le réglage global.

## 4. Service LLM (`services/llm_service.py`)

- interface unique : `completions(prompt, contexte, parametres, streaming=...)` ;
- adaptateur par famille (`openai_compatible`, `anthropic`) : traduction requête/réponse, gestion du streaming ;
- **comptage de tokens et estimation de coût** avant chaque passe (barre de lancement + barre supérieure de la page Reformulation) et après (stats par version du bloc, contrat format étude §7) — prix lus dans le catalogue ;
- **réseau** : timeout, relance auto. (backoff) sur erreur transitoire, message d'erreur clair (clé invalide, quota, réseau) — jamais d'exception brute à l'écran ;
- aucune modification des projets/études en cas d'échec d'appel : le résultat absent est simplement une version non créée.

## 5. Règles d'invariance (à tester unitairement)

1. Aucune clé API n'apparaît en clair dans un fichier, un log ou l'UI (hors champ masqué) — CredentialStore obligatoire.
2. L'UI n'affiche jamais un réglage non déclaré dans les capacités du modèle courant.
3. Le catalogue par défaut est reconstituable (réinitialisable) sans perdre les fournisseurs ajoutés par l'utilisateur.
4. Un appel LLM qui échoue ne modifie aucun document de l'étude.
5. Les coûts estimés utilisent toujours le prix courant du catalogue ; les stats déjà enregistrées ne sont pas recalculées rétroactivement.