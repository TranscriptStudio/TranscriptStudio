# services/llm/catalogue.py
"""
Catalogue LLM de l'application (P15).

Spécification de référence : PARAMETRAGE_LLM_V2.md.

- **Catalogue embarqué + extensible** (même philosophie
  que le résolveur FFmpeg P8) : liste par défaut fournie
  avec l'app, éditable par l'utilisateur ;
- deux **familles d'API** seulement : ``openai_compatible``
  (OpenAI, Mistral, Groq, DeepSeek, xAI, OpenRouter, serveur
  local Ollama/LM Studio...) et ``anthropic`` ;
- chaque fournisseur déclare sa famille ; chaque modèle
  déclare ses **capacités** (température supportée ou non,
  contexte maximal) et ses **prix** (le « catalogue de
  coûts » du contrat format étude) ;
- le catalogue est stocké dans le dossier de paramétrage
  de l'app ; la **réinitialisation reconstitue les
  fournisseurs par défaut sans perdre les fournisseurs
  ajoutés par l'utilisateur** (règle d'invariance 3).

Aucune clé API ici : les clés vivent dans le
CredentialStore (une par fournisseur).
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from services.resources import resource_path


FAMILLES_API = (
    "openai_compatible",
    "anthropic",
)

ORIGINE_DEFAUT = "defaut"
ORIGINE_UTILISATEUR = "utilisateur"

FICHIER_CATALOGUE = "catalogue_llm.json"


class CatalogueError(Exception):
    """
    Erreur de catalogue : structure invalide,
    fournisseur ou modèle introuvable.
    """

    pass


@dataclass
class ModeleCatalogue:
    """
    Un modèle d'un fournisseur du catalogue, avec
    ses capacités déclarées et ses prix.
    """

    id: str
    nom_affiche: str
    capacites: dict = field(default_factory=dict)
    prix: dict = field(default_factory=dict)
    origine: str = ORIGINE_DEFAUT

    def to_dict(self) -> dict:

        return {
            "id": self.id,
            "nom_affiche": self.nom_affiche,
            "capacites": dict(self.capacites),
            "prix": dict(self.prix),
            "origine": self.origine,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ModeleCatalogue":

        return cls(
            id=data["id"],
            nom_affiche=data.get(
                "nom_affiche",
                data["id"]
            ),
            capacites=dict(
                data.get("capacites", {})
            ),
            prix=dict(data.get("prix", {})),
            origine=data.get(
                "origine",
                ORIGINE_DEFAUT
            ),
        )

    @property
    def capacite_temperature(self) -> bool:

        return bool(
            self.capacites.get(
                "temperature",
                False
            )
        )

    @property
    def max_contexte_tokens(self):

        return self.capacites.get(
            "max_contexte_tokens"
        )

    @property
    def capacite_effort_raisonnement(self) -> bool:

        return bool(
            self.capacites.get(
                "effort_raisonnement",
                False
            )
        )


@dataclass
class FournisseurCatalogue:
    """
    Un fournisseur du catalogue : famille d'API,
    base URL, éventuel endpoint d'infos de compte,
    modèles.
    """

    id: str
    nom: str
    famille_api: str
    base_url: str
    endpoint_infos_compte: str = "none"
    modeles: list = field(default_factory=list)
    origine: str = ORIGINE_DEFAUT

    def to_dict(self) -> dict:

        return {
            "id": self.id,
            "nom": self.nom,
            "famille_api": self.famille_api,
            "base_url": self.base_url,
            "endpoint_infos_compte": (
                self.endpoint_infos_compte
            ),
            "origine": self.origine,
            "modeles": [
                modele.to_dict()
                for modele in self.modeles
            ],
        }

    @classmethod
    def from_dict(
        cls,
        data: dict
    ) -> "FournisseurCatalogue":

        return cls(
            id=data["id"],
            nom=data.get("nom", data["id"]),
            famille_api=data["famille_api"],
            base_url=data["base_url"],
            endpoint_infos_compte=data.get(
                "endpoint_infos_compte",
                "none"
            ),
            modeles=[
                ModeleCatalogue.from_dict(modele)
                for modele
                in data.get("modeles", [])
            ],
            origine=data.get(
                "origine",
                ORIGINE_DEFAUT
            ),
        )

    def chercher_modele(self, modele_id: str):

        for modele in self.modeles:

            if modele.id == modele_id:
                return modele

        return None

    @property
    def necessite_cle(self) -> bool:
        """
        Un fournisseur ajouté manuellement avec une
        base URL locale (Ollama, LM Studio) fonctionne
        sans clé.
        """

        return not (
            "localhost" in self.base_url
            or "127.0.0.1" in self.base_url
        )


@dataclass
class CatalogueLLM:
    """
    Le catalogue complet : liste de fournisseurs,
    version du format.
    """

    catalogue_version: int = 1
    fournisseurs: list = field(default_factory=list)

    def to_dict(self) -> dict:

        return {
            "catalogue_version": (
                self.catalogue_version
            ),
            "fournisseurs": [
                fournisseur.to_dict()
                for fournisseur
                in self.fournisseurs
            ],
        }

    @classmethod
    def from_dict(
        cls,
        data: dict
    ) -> "CatalogueLLM":

        return cls(
            catalogue_version=data.get(
                "catalogue_version",
                1
            ),
            fournisseurs=[
                FournisseurCatalogue.from_dict(
                    fournisseur
                )
                for fournisseur
                in data.get("fournisseurs", [])
            ],
        )

    def chercher_fournisseur(
        self,
        fournisseur_id: str
    ):

        for fournisseur in self.fournisseurs:

            if fournisseur.id == fournisseur_id:
                return fournisseur

        return None

    def chercher_modele(
        self,
        fournisseur_id: str,
        modele_id: str
    ):

        fournisseur = self.chercher_fournisseur(
            fournisseur_id
        )

        if fournisseur is None:
            return None

        return fournisseur.chercher_modele(
            modele_id
        )

    def ajouter_fournisseur(
        self,
        fournisseur: FournisseurCatalogue
    ) -> None:

        if (
            self.chercher_fournisseur(
                fournisseur.id
            )
            is not None
        ):
            raise CatalogueError(
                f"Un fournisseur nommé "
                f"{fournisseur.id!r} existe déjà"
            )

        self.fournisseurs.append(fournisseur)


def catalogue_par_defaut() -> CatalogueLLM:
    """
    Le catalogue embarqué (resource
    resources/llm/catalogue_defaut.json) :
    OpenAI, Mistral, Anthropic avec les modèles,
    capacités et prix de la spécification.
    """

    chemin = resource_path(
        "resources/llm/catalogue_defaut.json"
    )

    with open(
        chemin,
        "r",
        encoding="utf-8"
    ) as fichier:
        data = json.load(fichier)

    return CatalogueLLM.from_dict(data)


def valider_catalogue(catalogue: CatalogueLLM) -> None:
    """
    Cohérence du catalogue : familles connues,
    identifiants uniques, prix présents.
    """

    ids_vus = set()

    for fournisseur in catalogue.fournisseurs:

        if not fournisseur.id:
            raise CatalogueError(
                "Fournisseur sans identifiant"
            )

        if fournisseur.id in ids_vus:
            raise CatalogueError(
                f"Fournisseur en doublon : "
                f"{fournisseur.id}"
            )

        ids_vus.add(fournisseur.id)

        if fournisseur.famille_api not in FAMILLES_API:
            raise CatalogueError(
                f"{fournisseur.id} : famille "
                f"inconnue "
                f"{fournisseur.famille_api!r}"
            )

        if not fournisseur.base_url:
            raise CatalogueError(
                f"{fournisseur.id} : base_url requis"
            )

        modeles_vus = set()

        for modele in fournisseur.modeles:

            if not modele.id:
                raise CatalogueError(
                    f"{fournisseur.id} : modèle "
                    "sans identifiant"
                )

            if modele.id in modeles_vus:
                raise CatalogueError(
                    f"{fournisseur.id} : modèle en "
                    f"doublon {modele.id}"
                )

            modeles_vus.add(modele.id)

            for cle_prix in (
                "in_par_million",
                "out_par_million"
            ):

                if cle_prix not in modele.prix:
                    raise CatalogueError(
                        f"{fournisseur.id}/{modele.id} : "
                        f"prix {cle_prix} requis"
                    )


def charger_catalogue(chemin=None) -> CatalogueLLM:
    """
    Charge le catalogue utilisateur (dossier de
    paramétrage de l'app) ; à défaut, le catalogue
    embarqué.
    """

    if chemin is None:

        from services.app_paths import APP_DATA_DIR

        chemin = APP_DATA_DIR / FICHIER_CATALOGUE

    chemin = Path(chemin)

    if not chemin.exists():
        return catalogue_par_defaut()

    try:

        with open(
            chemin,
            "r",
            encoding="utf-8"
        ) as fichier:
            data = json.load(fichier)

        catalogue = CatalogueLLM.from_dict(data)

    except (json.JSONDecodeError, KeyError) as e:
        raise CatalogueError(
            f"Catalogue illisible ({chemin}) : {e}"
        )

    valider_catalogue(catalogue)

    return catalogue


def enregistrer_catalogue(
    catalogue: CatalogueLLM,
    chemin=None
) -> Path:
    """
    Sauvegarde le catalogue dans le dossier de
    paramétrage de l'app.
    """

    valider_catalogue(catalogue)

    if chemin is None:

        from services.app_paths import APP_DATA_DIR

        chemin = APP_DATA_DIR / FICHIER_CATALOGUE

    chemin = Path(chemin)

    chemin.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        chemin,
        "w",
        encoding="utf-8"
    ) as fichier:
        json.dump(
            catalogue.to_dict(),
            fichier,
            ensure_ascii=False,
            indent=2
        )

    return chemin


def reinitialiser_catalogue(chemin=None) -> CatalogueLLM:
    """
    Règle d'invariance 3 : reconstitue le catalogue
    par défaut **sans perdre les fournisseurs ajoutés
    par l'utilisateur**.

    Les entrées d'origine « defaut » sont remplacées
    par l'embarqué ; les entrées « utilisateur » sont
    conservées telles quelles.
    """

    defaut = catalogue_par_defaut()

    if chemin is None:

        from services.app_paths import APP_DATA_DIR

        chemin = APP_DATA_DIR / FICHIER_CATALOGUE

    chemin = Path(chemin)

    conservees = []

    if chemin.exists():

        try:

            actuel = charger_catalogue(chemin)

            conservees = [
                fournisseur
                for fournisseur
                in actuel.fournisseurs
                if fournisseur.origine
                == ORIGINE_UTILISATEUR
            ]

        except CatalogueError:
            conservees = []

    nouveau = CatalogueLLM(
        catalogue_version=defaut.catalogue_version,
        fournisseurs=(
            list(defaut.fournisseurs)
            + conservees
        ),
    )

    enregistrer_catalogue(nouveau, chemin)

    return nouveau


def cout_estime(
    modele: ModeleCatalogue,
    tokens_in: int,
    tokens_out: int
) -> float:
    """
    Coût estimé (devise du fournisseur, généralement $)
    d'un appel, aux prix courants du catalogue.
    """

    prix_in = float(
        modele.prix.get("in_par_million", 0.0)
    )

    prix_out = float(
        modele.prix.get("out_par_million", 0.0)
    )

    return (
        prix_in * tokens_in
        + prix_out * tokens_out
    ) / 1_000_000.0


def estimer_tokens(texte: str) -> int:
    """
    Estimation locale du nombre de tokens d'un texte
    (avant passe, pour l'affichage du coût estimé).

    Heurrique : environ un token pour quatre
    caractères, typique des tokeniseurs BPE pour le
    français ; les tokens réels sont toujours pris
    dans la réponse de l'API pour les stats stockées.
    """

    if not texte:
        return 0

    return max(1, len(texte) // 4)


def cout_estime_avant_passe(
    catalogue: CatalogueLLM,
    fournisseur_id: str,
    modele_id: str,
    tokens_in_estimes: int,
    tokens_out_estimes: int
) -> float:
    """
    Coût estimé d'un appel avant la passe, aux prix
    courants du catalogue (PARAMETRAGE_LLM_V2 §4) :
    alimente la barre de lancement et la barre
    supérieure de la page Reformulation.
    """

    modele = catalogue.chercher_modele(
        fournisseur_id,
        modele_id
    )

    if modele is None:
        raise CatalogueError(
            f"Modèle {modele_id!r} introuvable "
            f"chez le fournisseur {fournisseur_id!r}"
        )

    return cout_estime(
        modele,
        tokens_in_estimes,
        tokens_out_estimes
    )


def reglages_affichables(
    modele: ModeleCatalogue
) -> dict:
    """
    Règle d'invariance 2 : l'UI n'affiche jamais un
    réglage non déclaré dans les capacités du modèle
    courant.

    Retourne la liste des réglages applicables au
    modèle, avec leurs bornes :
    - ``temperature`` : présent si le modèle le
      supporte ;
    - ``max_tokens`` : plafonné au contexte du
      modèle ;
    - ``effort_raisonnement`` : présent si le modèle
      le déclare.
    """

    reglages = {}

    if modele.capacite_temperature:
        reglages["temperature"] = {}

    max_contexte = modele.max_contexte_tokens

    reglages["max_tokens"] = {
        "maximum": (
            int(max_contexte)
            if max_contexte
            else None
        )
    }

    if modele.capacite_effort_raisonnement:
        reglages["effort_raisonnement"] = {}

    return reglages
