# services/llm/__init__.py
"""
Service LLM de TranscriptStudio v2 (P15).

Catalogue embarqué extensible + clients par
famille d'API (openai_compatible, anthropic),
streaming, usage/coût, relance et annulation.
"""

from services.llm.catalogue import (
    CatalogueError,
    CatalogueLLM,
    FournisseurCatalogue,
    ModeleCatalogue,
    catalogue_par_defaut,
    charger_catalogue,
    cout_estime,
    cout_estime_avant_passe,
    enregistrer_catalogue,
    estimer_tokens,
    reinitialiser_catalogue,
    reglages_affichables,
    valider_catalogue,
)
from services.llm.client import (
    Annulation,
    ClientAnthropic,
    ClientOpenAICompatible,
    ErreurLLM,
    LLMClient,
    ParametresCompletion,
    ResultatCompletion,
    creer_client,
)
