"""
Synthèse d'étude repensée (P20.6 — décisions David
du 2026-11-09 ; feuille d'autorité
SPEC_PAGE_ETUDE_ET_SYNTHESE_MODIFS_2026-11-09d §3,
invariants 8-14) :

- **abrogation** de la génération automatique à la
  validation d'une réunion (P17.2) : l'alimentation
  est STRICTEMENT MANUELLE ;
- **alimentation incrémentale manuelle** : la
  contribution d'une réunion à blocs validés est
  AJOUTÉE à la synthèse existante (jamais de
  re-génération implicite du reste) ; ré-alimenter
  une réunion déjà intégrée REMPLACE exactement sa
  contribution (avec avertissement) ;
- **mémoire des contributions** (réunions +
  empreinte des blocs validés pris en compte) ;
- **prompt dédié éditable** dans la bibliothèque
  des réglages (``prompts/synthese_etude.md``,
  défaut embarqué ``resources/prompts/
  prompt_synthese_etude.md``) — format cible :
  phrases courtes résumant chaque pensée d'un
  interlocuteur, avec le locuteur identifiable ;
- **P18.11c** : la synthèse d'étude utilise
  EXCLUSIVEMENT les réglages de l'app — paramètres
  LLM globaux + prompt courant de la bibliothèque
  (lu directement, plus de copie locale d'étude) ;
  la version mémorise toujours le texte et le hash
  utilisés (P20.6c) ;
- **« (Re)générer »** : remplacement INTÉGRAL de la
  synthèse par celle de toutes les réunions à blocs
  validés (avertissement + confirmation côté UI) ;
- **injection de contexte conservée** (P20.6f) : la
  synthèse reste injectable comme contexte dans la
  reformulation des blocs cochés (mécanisme P15
  inchangé — voir services.traitements.moteur).

La synthèse reste versionnée (contrat §9 : jamais
écrasée — chaque alimentation/régénération ajoute
une version).
"""

import hashlib
import re

from services.llm.catalogue import (
    CatalogueError,
    CatalogueLLM,
    catalogue_par_defaut,
    cout_estime,
    estimer_tokens,
    effort_effectif,
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
from services.prompts import (
    USAGE_SYNTHESE_ETUDE,
    hash_prompt,
    lire_bibliotheque,
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


def marquer_reunion(nom: str) -> str:
    """
    Marqueur de section d'une contribution de
    réunion dans la synthèse.
    """

    return f"=== Réunion {nom} ==="


_MOTIF_MARQUEUR = re.compile(
    r"^=== Réunion (.+?) ===\s*$",
    re.MULTILINE,
)


def extraire_blocs(texte: str) -> dict:
    """
    Extrait les contributions par réunion d'un
    texte de synthèse : ``{nom: bloc}`` (dans
    l'ordre du texte). Sans marqueur : ``{}``.
    """

    blocs = {}

    positions = list(
        _MOTIF_MARQUEUR.finditer(texte or "")
    )

    for i, match in enumerate(positions):

        nom = match.group(1)

        fin = (
            positions[i + 1].start()
            if i + 1 < len(positions)
            else len(texte)
        )

        blocs[nom] = texte[match.start():fin].strip()

    return blocs


def assembler_blocs(blocs: dict, ordre: list) -> str:
    """
    Réassemble un texte de synthèse à partir des
    contributions (dans l'ordre donné, puis les
    autres dans l'ordre du dict).
    """

    vus = set()
    morceaux = []

    for nom in list(ordre) + list(blocs):

        if nom in vus or nom not in blocs:
            continue

        vus.add(nom)
        morceaux.append(blocs[nom])

    return "\n\n".join(morceaux).strip()


def empreinte_blocs(etude_ouverte, reunion: str) -> str:
    """
    Empreinte (hash court) des blocs validés d'une
    réunion pris en compte dans la synthèse :
    SHA-256 sur les FIDs et textes validés actifs.
    """

    blocs = blocs_actifs(etude_ouverte, reunion)

    morceaux = []

    for bloc in blocs:

        texte = texte_reunion_valide_bloc(
            etude_ouverte,
            reunion,
            bloc.fid
        )

        morceaux.append(
            f"{bloc.fid}:{texte or ''}"
        )

    return hashlib.sha256(
        "\n".join(morceaux).encode("utf-8")
    ).hexdigest()[:16]


def reunion_entierement_validee(
    etude_ouverte: EtudeOuverte,
    reunion: str
) -> bool:
    """
    Une réunion est entièrement validée quand
    chacun de ses blocs actifs possède une version
    validée (P20.6b : seules ces réunions alimentent
    la synthèse).
    """

    blocs = blocs_actifs(etude_ouverte, reunion)

    if not blocs:
        return False

    for bloc in blocs:

        resultat = (
            etude_ouverte.reformulation_de(
                reunion,
                bloc.fid
            )
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


def texte_reunion_valide_bloc(
    etude_ouverte,
    reunion: str,
    fid: int
) -> str:

    resultat = (
        etude_ouverte.reformulation_de(reunion, fid)
    )

    if not resultat or not resultat.versions:
        return None

    for version in reversed(resultat.versions):

        if (
            version.validation
            and version.validation.statut == "valide"
        ):
            return version.texte

    return None


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


def reunion_a_blocs_valides(
    etude_ouverte: EtudeOuverte,
    reunion: str
) -> bool:
    """
    P20.6b (conformité, relecture 2 du 10/11) : la
    réunion A des blocs validés — au moins un de ses
    blocs actifs possède une version validée.

    Aucun découpage (réunion non transcrite) → False,
    sans erreur.
    """

    try:
        blocs = blocs_actifs(etude_ouverte, reunion)
    except Exception:
        return False

    for bloc in blocs:

        if _texte_valide(
            etude_ouverte.reformulation_de(reunion, bloc.fid)
        ):
            return True

    return False


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
        etude_ouverte.resume_de(reunion)
    )

    if resume:
        return resume

    parties = []

    for bloc in blocs_actifs(etude_ouverte, reunion):

        texte = texte_reunion_valide_bloc(
            etude_ouverte,
            reunion,
            bloc.fid
        )

        if texte:
            parties.append(texte)

    return "\n\n".join(parties) or None


def reunions_a_blocs_valides(etude_ouverte) -> list:
    """
    P20.6 : les réunions de l'étude dont les blocs
    sont TOUS validés — seules éligibles à
    l'alimentation de la synthèse (manuelle) et au
    « (Re)générer ».
    """

    return [
        nom
        for nom in etude_ouverte.etude.ordre_reunions
        if reunion_entierement_validee(etude_ouverte, nom)
    ]


def assembler_source_synthese(
    etude_ouverte: EtudeOuverte,
    budget_tokens: int = SOURCE_SYNTHESE_MAX_TOKENS,
    reunions: list = None
) -> list:
    """
    Source de la synthèse : textes validés des
    réunions (par défaut : celles à blocs validés,
    P20.6) dans l'ordre de l'étude ; troncation par
    le haut si le budget est dépassé.

    Retour : liste (réunion, texte) en ordre.
    """

    if reunions is None:
        ordre = reunions_a_blocs_valides(etude_ouverte)
    else:
        ordre = [
            nom for nom in (
                etude_ouverte.etude.ordre_reunions
            )
            if nom in reunions
        ]

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
    Synthèse d'étude repensée (P20.6) : alimentation
    manuelle incrémentale (``alimenter``) et
    régénération complète (``generer``), prompt
    dédié éditable (bibliothèque).
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
        # (injectable pour les tests).
        self._dossier_prompts = dossier_prompts

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

    def prompt_effectif(self) -> str:
        """
        P20.6a/P18.11c : prompt DÉDIÉ de la synthèse
        d'étude — lu DIRECTEMENT dans la bibliothèque
        ``prompts/synthese_etude.md`` (défaut embarqué
        si absent) ; plus de copie locale d'étude.
        """

        return lire_bibliotheque(
            USAGE_SYNTHESE_ETUDE,
            self._dossier_prompts
        )[0]

    def tokens_max(self) -> int:
        """
        P18.11c : budget de sortie de la synthèse —
        réglages de l'app UNIQUEMENT (``max_tokens``),
        défaut embarqué sinon. Plus de surcharge
        d'étude.
        """

        return int(
            self._parametres_app().get("max_tokens")
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

        #
        # P18.11c : la synthèse utilise EXCLUSIVEMENT les
        # réglages de l'app — plus de surcharge d'étude
        # (paramètres LLM globaux uniquement).
        #
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

    def _appeler(
        self,
        message: str,
        annulation: Annulation = None
    ):
        """
        UN appel LLM avec le prompt dédié éditable.
        """

        fournisseur, modele = self.resoudre()
        client = self._creer_client(fournisseur)

        prompt = self.prompt_effectif()

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
            "prompt_hash": self.dernier_prompt_hash,
        }

        return resultat.texte, stats

    def estimer(self, reunions: list = None) -> dict:
        """
        Estimation affichée avant l'alimentation /
        la régénération (coût marginal, affiché quand
        même).
        """

        _fournisseur, modele = self.resoudre()

        sources = assembler_source_synthese(
            self.etude,
            reunions=reunions
        )

        tokens_in = (
            estimer_tokens(self.prompt_effectif())
            + sum(
                estimer_tokens(texte)
                for _reunion, texte in sources
            )
        )

        tokens_out = self.tokens_max()

        return {
            "nb_reunions": len(sources),
            "modele": modele.nom_affiche,
            "tokens_in_estimes": tokens_in,
            "tokens_out_estimes": tokens_out,
            "cout_estime": cout_estime(
                modele,
                tokens_in,
                tokens_out
            ),
        }

    def _consigner(
        self,
        texte: str,
        declencheur: str,
        stats: dict,
        contributions_maj: dict
    ):
        """
        Ajoute une version de synthèse et mémorise
        les contributions (P20.6c).
        """

        try:

            version = ajouter_version_synthese(
                self.etude,
                texte,
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

        for reunion, contribution in (
            contributions_maj.items()
        ):
            self.etude.synthese.contributions[reunion] = (
                contribution
            )

        sauvegarder_etude(self.etude)

        return version

    def alimenter(
        self,
        reunion: str,
        annulation: Annulation = None
    ):
        """
        P20.6b : alimentation manuelle incrémentale
        d'UNE réunion — réservée aux réunions à
        blocs validés. La contribution est AJOUTÉE à
        la synthèse existante (jamais de
        re-génération implicite du reste) ; si la
        réunion a DÉJÀ contribué, sa contribution est
        REMPLACÉE exactement (l'appelant affiche
        l'avertissement).

        Retour : ``(version, stats, remplace)``.
        """

        #
        # P20.6b (conformité, relecture 2 du 10/11) :
        # dès qu'une réunion a des blocs validés.
        #
        if not reunion_a_blocs_valides(
            self.etude,
            reunion
        ):
            raise EtudeError(
                f"La réunion « {reunion} » n'a aucun "
                "bloc validé : elle ne peut pas "
                "alimenter la synthèse."
            )

        texte = texte_reunion_valide(self.etude, reunion)

        if not texte:
            raise EtudeError(
                f"Aucun texte validé pour la réunion "
                f"« {reunion} »."
            )

        message = (
            f"Contribution de la réunion « {reunion} » "
            "à la synthèse globale de l'étude "
            f"(texte validé) :\n\n{texte}\n\n"
            "Produis UNIQUEMENT cette contribution, au "
            "format demandé, précédée du marqueur "
            f"« {marquer_reunion(reunion)} »."
        )

        reponse, stats = self._appeler(
            message,
            annulation=annulation
        )

        # Fusion dans la synthèse courante : bloc
        # remplacé si déjà présent, ajouté sinon.
        courante = (
            self.etude.synthese.versions[-1].texte
            if self.etude.synthese.versions
            else ""
        )

        blocs = extraire_blocs(courante)

        remplace = reunion in blocs

        blocs[reunion] = (
            f"{marquer_reunion(reunion)}\n"
            + reponse.strip()
        ).strip()

        ordre = list(
            self.etude.etude.ordre_reunions
        )

        texte_final = assembler_blocs(blocs, ordre)

        contribution = {
            "empreinte": empreinte_blocs(
                self.etude,
                reunion
            ),
            "blocs": [
                bloc.fid
                for bloc in blocs_actifs(
                    self.etude,
                    reunion
                )
            ],
            "horodatage": version_horodatage(),
            "declencheur": "alimentation",
        }

        version = self._consigner(
            texte_final,
            "alimentation",
            stats,
            {reunion: contribution}
        )

        return version, stats, remplace

    def generer(
        self,
        declencheur: str = "manuel",
        annulation: Annulation = None
    ):
        """
        P20.6d : « (Re)générer » — remplacement
        INTÉGRAL de la synthèse par celle de TOUTES
        les réunions à blocs validés (l'avertissement
        et la confirmation relèvent de l'UI).

        Retour : (version, stats).
        """

        sources = assembler_source_synthese(self.etude)

        if not sources:
            raise EtudeError(
                "Aucune réunion à blocs validés dans "
                "l'étude : validez d'abord des blocs."
            )

        contenu = "\n\n".join(
            f"{marquer_reunion(reunion)}\n{texte}"
            for reunion, texte in sources
        )

        message = (
            "Textes validés des réunions de l'étude "
            "(toutes à blocs validés), dans l'ordre de "
            "l'étude :\n\n"
            + contenu
            + "\n\nLongueur maximale de la synthèse : "
            f"{self.tokens_max()} tokens."
        )

        reponse, stats = self._appeler(
            message,
            annulation=annulation
        )

        contributions = {
            reunion: {
                "empreinte": empreinte_blocs(
                    self.etude,
                    reunion
                ),
                "blocs": [
                    bloc.fid
                    for bloc in blocs_actifs(
                        self.etude,
                        reunion
                    )
                ],
                "horodatage": version_horodatage(),
                "declencheur": declencheur,
            }
            for reunion, _texte in sources
        }

        version = self._consigner(
            reponse,
            declencheur,
            stats,
            contributions
        )

        return version, stats

    def blocs_revalides(self) -> list:
        """
        P20.6c : réunions ayant contribué dont
        l'empreinte des blocs validés a CHANGÉ depuis
        la dernière alimentation — avertissement
        « blocs re-validés depuis la dernière
        alimentation ».
        """

        revalides = []

        for reunion, contribution in (
            self.etude.synthese.contributions.items()
        ):

            if reunion not in (
                self.etude.etude.ordre_reunions
            ):
                continue

            empreinte = empreinte_blocs(
                self.etude,
                reunion
            )

            if empreinte != contribution.get(
                "empreinte"
            ):
                revalides.append(reunion)

        return revalides


def version_horodatage() -> str:
    """
    Horodatage ISO courant (contributions).
    """

    from services.timecodes import horodatage_iso

    return horodatage_iso()
