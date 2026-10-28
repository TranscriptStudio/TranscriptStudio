"""
Service du bloc Résumé (P17.1, feuille de route §4).

Périmètre : la réunion. La source est au choix à
chaque lancement — transcription brute corrigée ou
reformulations validées — et la source utilisée est
stockée avec le résultat (contrat §8).

Une réunion longue n'entre pas en un seul appel :
la source est traitée en 3 à 5 gros segments avec
léger chevauchement (notes de segment), puis
assemblée en un résumé final unique ; une source
courte passe en un seul appel.

L'outillage d'édition est celui du moteur commun :
chaque exécution ou édition crée une version
(jamais d'écrasement), relance complète avec
consigne, relance ciblée sur sélection (contexte
identique + versions antérieures), validation.
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
    ResultatCompletion,
    creer_client,
)
from services.decoupage import blocs_actifs
from services.etude_io import (
    EtudeOuverte,
    EtudeError,
    ajouter_version_resume,
    fichier_projet_v1,
    sauvegarder_etude,
)
from services.traitements.journal import (
    RESULTAT_ERREUR,
    TYPE_RESUME,
)
from services.traitements.moteur import (
    TEMPERATURE_RESUME_DEFAUT,
)


SOURCE_BRUTE = "brute_corrigee"
SOURCE_REFORMULEES = "reformulations_valides"
SOURCES_RESUME = (SOURCE_BRUTE, SOURCE_REFORMULEES)

#
# Au-delà de ce volume, la source est segmentée
# (3 à 5 segments avec chevauchement). En dessous,
# un seul appel suffit à tous les modèles du
# catalogue par défaut.
#
SEUIL_MONO_SEGMENT_TOKENS = 24000

SEGMENTS_MIN = 3
SEGMENTS_MAX = 5

#
# Chevauchement entre segments (en paragraphes) :
# léger, pour la continuité des pensées à cheval
# sur deux segments.
#
CHEVAUCHEMENT_PARAGRAPHES = 2


class ErreurSource(EtudeError):
    """
    La source demandée n'est pas disponible (ex. :
    aucune reformulation validée pour la réunion).
    """

    pass


def texte_source(
    etude_ouverte: EtudeOuverte,
    reunion: str,
    source: str
) -> str:
    """
    Assemble le texte source d'un résumé selon le
    choix fait au lancement.

    - ``brute_corrigee`` : textes des blocs actifs de
      la segmentation (ordre chronologique) ;
    - ``reformulations_valides`` : dernières versions
      validées des reformulations, dans l'ordre des
      blocs (erreur si aucune n'est validée).
    """

    if source not in SOURCES_RESUME:
        raise ErreurSource(
            f"Source de résumé inconnue : {source!r}"
        )

    if reunion not in etude_ouverte.reunions:
        raise ErreurSource(f"Réunion inconnue : {reunion}")

    parties = []

    for bloc in blocs_actifs(etude_ouverte, reunion):

        if source == SOURCE_BRUTE:
            parties.append(bloc.source)
            continue

        resultat = (
            etude_ouverte.reformulations.get(bloc.fid)
        )

        if not resultat or not resultat.versions:
            continue

        texte_valide = None

        for version in reversed(resultat.versions):

            if (
                version.validation
                and version.validation.statut
                == "valide"
            ):
                texte_valide = version.texte
                break

        if texte_valide is not None:
            parties.append(texte_valide)

    if source == SOURCE_REFORMULEES and not parties:
        raise ErreurSource(
            "Aucune reformulation validée pour la "
            f"réunion {reunion} : validez d'abord des "
            "blocs, ou choisissez la transcription "
            "brute corrigée comme source."
        )

    return "\n\n".join(parties)


def _paragraphes(texte: str) -> list:
    """
    Paragraphes non vides du texte (les résultats
    normalisés portent un seul \\n par saut de
    paragraphe ; les sources de segmentation peuvent
    encore en porter deux).
    """

    return [
        morceau.strip()
        for morceau
        in texte.replace("\r", "").split("\n")
        if morceau.strip()
    ]


def segmenter_source(texte: str) -> list:
    """
    Découpe la source en 1 à 5 segments aux frontières
    de paragraphes, avec léger chevauchement.

    Déterministe : jamais au milieu d'un paragraphe.
    Retour : liste de textes de segments (en ordre).
    """

    paragraphes = _paragraphes(texte)

    tokens = estimer_tokens(texte)

    if tokens <= SEUIL_MONO_SEGMENT_TOKENS:
        return ["\n".join(paragraphes)]

    nb_segments = max(
        SEGMENTS_MIN,
        min(
            SEGMENTS_MAX,
            -(-tokens // SEUIL_MONO_SEGMENT_TOKENS)
        )
    )

    par_segment = max(
        1,
        -(-len(paragraphes) // nb_segments)
    )

    segments = []

    debut = 0

    while debut < len(paragraphes):

        fin = min(
            len(paragraphes),
            debut + par_segment
        )

        segments.append(
            "\n".join(paragraphes[debut:fin])
        )

        debut = fin

    #
    # Chevauchement léger : les derniers paragraphes
    # d'un segment rappellent le début du suivant —
    # sauf pour le premier segment.
    #
    avec_chevauchement = [segments[0]]

    for precedent, suivant in zip(
        segments,
        segments[1:]
    ):

        queue = _paragraphes(precedent)[
            -CHEVAUCHEMENT_PARAGRAPHES:
        ]

        avec_chevauchement.append(
            "\n".join(queue)
            + "\n"
            + suivant
        )

    return avec_chevauchement


class ServiceResume:
    """
    Génération du résumé d'une réunion (P17.1).

    Même résolution de configuration que le moteur
    (fournisseur des réglages app, modèle surchargé
    par l'étude, température 0.2 par défaut
    surchargeable, jamais envoyée à un modèle qui ne
    la supporte pas).
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

    def _parametres_resume(self) -> dict:

        return self.etude.parametres.resume

    def resoudre(self):
        """
        Résout (fournisseur, modèle) : fournisseur des
        réglages app ; modèle surchargé par l'étude
        (parametres.resume.modele) s'il existe chez ce
        fournisseur, sinon modèle des réglages.
        """

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

        modele_id = self._parametres_resume().get(
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
        (température « résumé »), sinon 0.2.
        """

        surcharge = (
            self._parametres_resume().get("temperature")
        )

        if surcharge is not None:
            return float(surcharge)

        app = self._parametres_app()

        temperatures = app.get("temperatures", {})

        valeur = temperatures.get(
            "resume",
            app.get(
                "temperature",
                TEMPERATURE_RESUME_DEFAUT
            )
        )

        return float(valeur)

    def longueur_cible(self, lancement: list = None):
        """
        Longueur cible en mots (paramétrable au
        lancement, défaut de l'étude 650-700).
        """

        if lancement:
            return (
                int(lancement[0]),
                int(lancement[1])
            )

        longueurs = (
            self._parametres_resume().get(
                "longueur_cible_mots"
            )
            or [650, 700]
        )

        return int(longueurs[0]), int(longueurs[1])

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

    #
    # Estimation avant lancement (coût affiché puis
    # validé par l'utilisateur).
    #

    def estimer(
        self,
        reunion: str,
        source: str,
        longueur_cible: list = None
    ) -> dict:

        _fournisseur, modele = self.resoudre()

        texte = texte_source(
            self.etude,
            reunion,
            source
        )

        prompt = (
            self._parametres_resume().get("prompt", "")
        )

        segments = segmenter_source(texte)

        tokens_in = estimer_tokens(prompt)

        for segment in segments:
            tokens_in += estimer_tokens(segment)

        if len(segments) > 1:
            #
            # Assemblage final : les notes de segments
            # (condensées) reviennent en contexte.
            #
            tokens_in += tokens_in // 2

        minimum, maximum = self.longueur_cible(
            longueur_cible
        )

        tokens_out = maximum * 3 // 2

        return {
            "nb_segments": len(segments),
            "source": source,
            "modele": modele.nom_affiche,
            "tokens_source": estimer_tokens(texte),
            "tokens_in_estimes": tokens_in,
            "tokens_out_estimes": tokens_out,
            "cout_estime": cout_estime(
                modele,
                tokens_in,
                tokens_out
            ),
        }

    #
    # Génération.
    #

    def _instruction_longueur(self, longueur) -> str:

        minimum, maximum = longueur

        return (
            "Longueur cible pour ce résumé : "
            f"{minimum} à {maximum} mots."
        )

    def _appeler(
        self,
        client,
        modele,
        prompt_systeme: str,
        message: str,
        annulation
    ) -> ResultatCompletion:

        return client.completions(
            prompt_systeme,
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
                effort_raisonnement=(
                    self._parametres_app().get(
                        "effort_raisonnement"
                    )
                    if modele.capacite_effort_raisonnement
                    else None
                ),
            ),
            annulation=annulation
        )

    def generer(
        self,
        reunion: str,
        source: str = None,
        longueur_cible: list = None,
        consigne: str = None,
        annulation: Annulation = None
    ):
        """
        Génère le résumé de la réunion (nouvelle
        version, source stockée avec le résultat).

        Retour : (version, stats cumulées des appels).
        """

        if source is None:
            source = (
                self._parametres_resume().get(
                    "source_defaut"
                )
                or SOURCE_REFORMULEES
            )

        texte = texte_source(self.etude, reunion, source)

        longueur = self.longueur_cible(longueur_cible)

        prompt = (
            self._parametres_resume().get("prompt", "")
        )

        fournisseur, modele = self.resoudre()
        client = self._creer_client(fournisseur)

        stats = {
            "duree_ms": 0,
            "tokens_in": 0,
            "tokens_out": 0,
            "cout_estime": 0.0,
        }

        segments = segmenter_source(texte)

        if len(segments) == 1:

            message = self._message_final(
                texte,
                longueur,
                consigne
            )

            resultat = self._appeler(
                client,
                modele,
                prompt,
                message,
                annulation
            )

            self._cumuler(stats, resultat)

            return (
                self._consigner(
                    reunion,
                    source,
                    resultat.texte,
                    stats,
                    origine="generation",
                    consigne=consigne
                ),
                stats
            )

        #
        # Source longue : notes de segment, puis
        # assemblage final.
        #
        notes = []

        for index, segment in enumerate(segments, 1):

            message = (
                "Voici le segment "
                f"{index} sur {len(segments)} du document "
                "à résumer :\n\n" + segment + "\n\n"
                "Extraire de ce segment les pensées "
                "essentielles, les passages bibliques "
                "cités et les applications spirituelles, "
                "sous forme de notes denses (pas de "
                "prose finale) : ces notes serviront à "
                "rédiger le résumé complet du document."
            )

            resultat = self._appeler(
                client,
                modele,
                prompt,
                message,
                annulation
            )

            self._cumuler(stats, resultat)

            notes.append(resultat.texte)

        message = self._message_final(
            "\n\n".join(
                f"Notes du segment {index} :\n{note}"
                for index, note
                in enumerate(notes, 1)
            ),
            longueur,
            consigne,
            notes=True
        )

        resultat = self._appeler(
            client,
            modele,
            prompt,
            message,
            annulation
        )

        self._cumuler(stats, resultat)

        return (
            self._consigner(
                reunion,
                source,
                resultat.texte,
                stats,
                origine="generation",
                consigne=consigne
            ),
            stats
        )

    def _message_final(
        self,
        contenu: str,
        longueur,
        consigne: str,
        notes: bool = False
    ) -> str:

        parties = []

        entete = (
            "Notes extraites du document à résumer "
            "(par segments) :\n\n"
            if notes
            else "Document à résumer :\n\n"
        )

        parties.append(entete + contenu)

        parties.append(
            self._instruction_longueur(longueur)
        )

        if consigne:
            parties.append(
                "Consigne : " + consigne
            )

        return "\n\n".join(parties)

    #
    # Relances (même outillage que la reformulation).
    #

    def _versions_anterieures(self, reunion) -> list:

        resultat = self.etude.resumes.get(reunion)

        if not resultat:
            return []

        return [
            (version.numero, version.texte)
            for version in resultat.versions
        ]

    def relancer(
        self,
        reunion: str,
        consigne: str = None,
        annulation: Annulation = None
    ):
        """
        Relance complète : le contexte reçoit la
        source de la version courante, sa formulation
        et toutes ses versions antérieures (pour ne
        pas tourner en rond) + la consigne libre.
        """

        resultat = self.etude.resumes.get(reunion)

        if not resultat or not resultat.versions:
            raise EtudeError(
                f"Aucun résumé pour la réunion {reunion} : "
                "générez-le d'abord."
            )

        courante = resultat.versions[-1]

        texte = texte_source(
            self.etude,
            reunion,
            courante.source
        )

        longueur = self.longueur_cible()
        prompt = (
            self._parametres_resume().get("prompt", "")
        )

        fournisseur, modele = self.resoudre()
        client = self._creer_client(fournisseur)

        message = self._message_final(
            texte,
            longueur,
            consigne
        )

        message += (
            "\n\nFormulation actuelle du résumé :\n"
            + courante.texte
        )

        anterieures = self._versions_anterieures(
            reunion
        )

        if anterieures:

            historique = "\n\n".join(
                f"Version {numero} : {texte}"
                for numero, texte in anterieures
            )

            message += (
                "\n\nVersions antérieures du résumé "
                "(ne pas reproduire leurs défauts) :\n"
                + historique
            )

        stats = {
            "duree_ms": 0,
            "tokens_in": 0,
            "tokens_out": 0,
            "cout_estime": 0.0,
        }

        appel = self._appeler(
            client,
            modele,
            prompt,
            message,
            annulation
        )

        self._cumuler(stats, appel)

        return (
            self._consigner(
                reunion,
                courante.source,
                appel.texte,
                stats,
                origine="relance",
                consigne=consigne
            ),
            stats
        )

    def relancer_selection(
        self,
        reunion: str,
        selection: dict,
        consigne: str = None,
        annulation: Annulation = None
    ):
        """
        Relance ciblée sur une sélection du résumé :
        contexte identique + formulation courante et
        versions antérieures ; seule la portion visée
        est retravaillée, le reste est conservé tel
        quel (la version contient le résumé entier).
        """

        resultat = self.etude.resumes.get(reunion)

        if not resultat or not resultat.versions:
            raise EtudeError(
                f"Aucun résumé pour la réunion {reunion} : "
                "générez-le d'abord."
            )

        courante = resultat.versions[-1]

        texte = texte_source(
            self.etude,
            reunion,
            courante.source
        )

        longueur = self.longueur_cible()
        prompt = (
            self._parametres_resume().get("prompt", "")
        )

        fournisseur, modele = self.resoudre()
        client = self._creer_client(fournisseur)

        message = self._message_final(
            texte,
            longueur,
            consigne
        )

        message += (
            "\n\nFormulation actuelle du résumé :\n"
            + courante.texte
        )

        anterieures = self._versions_anterieures(
            reunion
        )

        if anterieures:

            historique = "\n\n".join(
                f"Version {numero} : {texte}"
                for numero, texte in anterieures
            )

            message += (
                "\n\nVersions antérieures du résumé "
                "(ne pas reproduire leurs défauts) :\n"
                + historique
            )

        message += (
            "\n\nRetravailler uniquement le passage "
            f"délimité (offsets caractères "
            f"{selection.get('debut')} à "
            f"{selection.get('fin')}) ; le reste du "
            "résumé est conservé tel quel. Le résultat "
            "est le résumé complet, retravaillé "
            "partiellement."
        )

        stats = {
            "duree_ms": 0,
            "tokens_in": 0,
            "tokens_out": 0,
            "cout_estime": 0.0,
        }

        appel = self._appeler(
            client,
            modele,
            prompt,
            message,
            annulation
        )

        self._cumuler(stats, appel)

        return (
            self._consigner(
                reunion,
                courante.source,
                appel.texte,
                stats,
                origine="relance_ciblee",
                consigne=consigne
            ),
            stats
        )

    #
    # Internes.
    #

    @staticmethod
    def _cumuler(stats: dict, resultat) -> None:

        stats["duree_ms"] += resultat.duree_ms
        stats["tokens_in"] += resultat.tokens_in
        stats["tokens_out"] += resultat.tokens_out
        stats["cout_estime"] += resultat.cout_estime

    def _consigner(
        self,
        reunion: str,
        source: str,
        texte: str,
        stats: dict,
        origine: str,
        consigne: str = None
    ):

        try:

            version = ajouter_version_resume(
                self.etude,
                reunion,
                texte,
                source,
                stats=dict(stats),
                origine=origine,
                consigne=consigne
            )

        except Exception as e:

            self.etude.journal.ajouter(
                TYPE_RESUME,
                reunion=reunion,
                resultat=RESULTAT_ERREUR,
                message=f"Résumé non consigné : {e}"
            )

            raise

        sauvegarder_etude(self.etude)

        return version


def source_a_evolve(
    etude_ouverte: EtudeOuverte,
    reunion: str,
    version_resume
) -> bool:
    """
    Avertissement feuille de route §4 : la source
    d'un résumé a-t-elle évolué depuis sa
    génération ? (reformulations validées plus
    récentes pour la source reformulée ; projet v1
    modifié pour la brute corrigée).

    Aucune mise à jour automatique : signalement
    seulement.
    """

    horodatage_version = version_resume.horodatage

    if version_resume.source == SOURCE_REFORMULEES:

        for resultat in (
            etude_ouverte.reformulations.values()
        ):

            for version in resultat.versions:

                if (
                    version.validation
                    and version.validation.statut
                    == "valide"
                    and (
                        version.horodatage
                        > horodatage_version
                    )
                ):
                    return True

        return False

    #
    # Source brute corrigée : le projet v1 a-t-il
    # été modifié après la génération ?
    #
    chemin = fichier_projet_v1(
        etude_ouverte,
        reunion
    )

    if chemin is None or not chemin.exists():
        return False

    return (
        chemin.stat().st_mtime
        > horodatage_vers_epoch(horodatage_version)
    )


def horodatage_vers_epoch(horodatage: str) -> float:

    from datetime import datetime

    try:
        return datetime.fromisoformat(
            horodatage
        ).timestamp()
    except (ValueError, TypeError):
        return 0.0
