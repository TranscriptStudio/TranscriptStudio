"""
Synthèse d'étude (P17.2, feuille de route §4) :
mécanisme transverse de contexte de niveau 2.

Générée à partir des textes validés (résumé validé
d'une réunion à défaut de rien, sinon ses
reformulations validées), dans l'ordre des réunions
de l'étude. Régénérable à la demande ; la mise à
jour automatique se déclenche quand une réunion
devient entièrement validée (dernier bloc validé —
déclencheur « validation_bloc » du contrat §9).

Plafonnée en tokens (parametre synthese.tokens_max,
défaut 1 500) : la consigne de longueur est passée
au prompt ; la source est tronquée par le haut
(les réunions les plus récentes sont conservées),
même logique que la troncation C1 du moteur.
"""

from services.llm.catalogue import (
    CatalogueError,
    CatalogueLLM,
    cout_estime,
    estimer_tokens,
)
from services.llm.client import (
    Annulation,
    ParametresCompletion,
    creer_client,
)
from services.decoupage import blocs_actifs
from services.etude_io import (
    EtudeOuverte,
    EtudeError,
    ajouter_version_synthese,
    sauvegarder_etude,
)
from services.traitements.journal import (
    RESULTAT_ERREUR,
    TYPE_SYNTHESE,
)

TOKENS_SYNTHESE_DEFAUT = 1500

#
# Budget d'entrée de la synthèse : au-delà, les
# réunions les plus anciennes sortent du contexte
# (troncation par le haut — les plus récentes
# restent, elles portent l'état courant de l'étude).
#
SOURCE_SYNTHESE_MAX_TOKENS = 80000

PROMPT_SYNTHESE = """Tu es le gardien de la mémoire d'une étude biblique qui regroupe plusieurs réunions sur un même thème (un livre ou un passage de la Bible).

À partir des textes validés des réunions (résumés ou reformulations), tu produis une synthèse d'étude destinée à servir de contexte aux traitements des réunions suivantes : le modèle qui reformule ou résume une nouvelle réunion la recevra pour savoir ce qui a déjà été développé.

Ta synthèse est une note de travail compacte, structurée en rubriques brèves :

1. Thème et plan général de l'étude (livre étudié, progression des réunions).
2. Pensées déjà développées (liste dense, une ligne par pensée, avec la réunion où elle est apparue si utile).
3. Versets et passages bibliques déjà cités ou commentés (références seules, en liste).
4. Vocabulaire et expressions récurrents de l'étude (mots-clés, images récurrentes).

Règles :
- ne jamais introduire une pensée absente des textes fournis ;
- pas de citation biblique longue : références seules ;
- pas de style narratif : liste denses et utiles ;
- rester très compact : la synthèse entière doit rester nettement en dessous de la longueur demandée ;
- écrire en français."""


def reunion_entierement_validee(
    etude_ouverte: EtudeOuverte,
    reunion: str
) -> bool:
    """
    Une réunion est entièrement validée quand
    chacun de ses blocs actifs possède une version
    validée.
    """

    blocs = blocs_actifs(etude_ouverte, reunion)

    if not blocs:
        return False

    for bloc in blocs:

        resultat = (
            etude_ouverte.reformulations.get(bloc.fid)
        )

        valide = False

        if resultat:

            for version in reversed(resultat.versions):

                if (
                    version.validation
                    and version.validation.statut
                    == "valide"
                ):
                    valide = True
                    break

        if not valide:
            return False

    return True


def _texte_valide(resultat) -> str:

    if not resultat or not resultat.versions:
        return None

    for version in reversed(resultat.versions):

        if (
            version.validation
            and version.validation.statut == "valide"
        ):
            return version.texte

    return None


def texte_reunion_valide(
    etude_ouverte: EtudeOuverte,
    reunion: str
) -> str:
    """
    Texte validé d'une réunion pour la synthèse :
    le résumé validé s'il existe (plus compact),
    sinon la concaténation des reformulations
    validées.
    """

    resume = _texte_valide(
        etude_ouverte.resumes.get(reunion)
    )

    if resume:
        return resume

    parties = []

    for bloc in blocs_actifs(etude_ouverte, reunion):

        texte = _texte_valide(
            etude_ouverte.reformulations.get(bloc.fid)
        )

        if texte:
            parties.append(texte)

    return "\n\n".join(parties) or None


def assembler_source_synthese(
    etude_ouverte: EtudeOuverte,
    budget_tokens: int = SOURCE_SYNTHESE_MAX_TOKENS
) -> list:
    """
    Source de la synthèse : textes validés des
    réunions dans l'ordre de l'étude ; troncation
    par le haut si le budget est dépassé (les
    réunions les plus récentes restent).

    Retour : liste (réunion, texte) en ordre.
    """

    ordre = list(
        etude_ouverte.etude.ordre_reunions
    )

    retenues = []
    tokens = 0

    for reunion in reversed(ordre):

        texte = texte_reunion_valide(
            etude_ouverte,
            reunion
        )

        if not texte:
            continue

        tokens_texte = estimer_tokens(texte)

        if (
            retenues
            and tokens + tokens_texte > budget_tokens
        ):
            break

        retenues.append((reunion, texte))
        tokens += tokens_texte

    return list(reversed(retenues))


class ServiceSynthese:
    """
    Génération de la synthèse d'étude (P17.2) :
    même résolution de configuration que le moteur
    (modèle surchargeable par l'étude dans
    parametres.synthese.modele).
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

    def _parametres_synthese(self) -> dict:

        return self.etude.parametres.synthese

    def tokens_max(self) -> int:

        return int(
            self._parametres_synthese().get(
                "tokens_max"
            )
            or TOKENS_SYNTHESE_DEFAUT
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

        modele_id = self._parametres_synthese().get(
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

    def estimer(self) -> dict:
        """
        Estimation affichée avant la régénération
        manuelle (coût marginal, affiché quand même).
        """

        _fournisseur, modele = self.resoudre()

        reunions = assembler_source_synthese(self.etude)

        tokens_in = (
            estimer_tokens(PROMPT_SYNTHESE)
            + sum(
                estimer_tokens(texte)
                for _reunion, texte in reunions
            )
        )

        tokens_out = self.tokens_max()

        return {
            "nb_reunions": len(reunions),
            "modele": modele.nom_affiche,
            "tokens_in_estimes": tokens_in,
            "tokens_out_estimes": tokens_out,
            "cout_estime": cout_estime(
                modele,
                tokens_in,
                tokens_out
            ),
        }

    def generer(
        self,
        declencheur: str = "manuel",
        annulation: Annulation = None
    ):
        """
        Génère une nouvelle version de la synthèse
        d'étude (contrat §9 : versionnée, jamais
        écrasée).

        Retour : (version, stats de l'appel).
        """

        reunions = assembler_source_synthese(self.etude)

        if not reunions:
            raise EtudeError(
                "Aucun texte validé dans l'étude : "
                "validez d'abord des blocs ou un résumé."
            )

        fournisseur, modele = self.resoudre()
        client = self._creer_client(fournisseur)

        contenu = "\n\n".join(
            f"=== Réunion {reunion} (texte validé) ===\n"
            + texte
            for reunion, texte in reunions
        )

        message = (
            "Textes validés des réunions de l'étude, "
            "dans l'ordre de l'étude :\n\n"
            + contenu
            + "\n\nLongueur maximale de la synthèse : "
            f"{self.tokens_max()} tokens."
        )

        resultat = client.completions(
            PROMPT_SYNTHESE,
            [
                {
                    "role": "user",
                    "content": message,
                }
            ],
            ParametresCompletion(
                modele=modele.id
            ),
            annulation=annulation
        )

        stats = {
            "duree_ms": resultat.duree_ms,
            "tokens_in": resultat.tokens_in,
            "tokens_out": resultat.tokens_out,
            "cout_estime": resultat.cout_estime,
        }

        try:

            version = ajouter_version_synthese(
                self.etude,
                resultat.texte,
                declencheur=declencheur,
                stats=stats
            )

        except Exception as e:

            self.etude.journal.ajouter(
                TYPE_SYNTHESE,
                resultat=RESULTAT_ERREUR,
                message=(
                    f"Synthèse non consignée : {e}"
                ),
                stats=stats
            )

            raise

        sauvegarder_etude(self.etude)

        return version, stats
