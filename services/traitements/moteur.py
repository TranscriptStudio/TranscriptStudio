# services/traitements/moteur.py
"""
Moteur de traitement (P15.3).

Spécification de référence : SPEC_MOTEUR_P15_V2.md
(fait autorité), CONTRAT_FORMAT_ETUDE_V2.md §7/§10.

Rôles (spec §1) :
1. assemblage du contexte de chaque appel LLM ;
2. exécution séquentielle des unités dans l'ordre
   chronologique ;
3. stockage des résultats versionnés (contrat §7) ;
4. log des opérations (journal.py, P15.4) ;
5. le contrôle qualité local est hors périmètre
   (P16.4/P18).

Décisions d'atelier intégrées (2026-10-27) :
- B1 : estimation de coût puis coût réel affiché en
  fin de première passe totale (fait office de
  confirmation) ; aucune confirmation pour les
  reformulations par bloc ;
- B2 : annulation à mi-passe = arrêt propre, tout ce
  qui est déjà produit est conservé ;
- B3 : aucune cascade — jamais de reprise
  automatique des blocs suivants ;
- C1 : débordement de contexte = troncation par le
  haut (blocs les plus anciens de la fenêtre
  d'abord) ; jamais la synthèse d'étude, jamais
  l'unité courante, jamais le prompt système ;
- C2 : températures par défaut dans les réglages de
  l'app (reformulation 0.3, résumé 0.2),
  surchargeables par étude — jamais codées en dur
  dans le moteur.

Le moteur n'écrit jamais un résultat partiel : la
version n'est créée qu'après l'aboutissement de
l'appel (règle d'invariance 1 de la spec).
"""

import time
from dataclasses import dataclass, field

from services.llm.catalogue import (
    CatalogueError,
    CatalogueLLM,
    cout_estime,
    estimer_tokens,
)
from services.llm.client import (
    Annulation,
    ErreurLLM,
    ParametresCompletion,
    ResultatCompletion,
    creer_client,
)
from services.decoupage import blocs_actifs
from services.etude_io import (
    EtudeOuverte,
    ajouter_version_reformulation,
    sauvegarder_etude,
)
from services.traitements.journal import (
    RESULTAT_ERREUR,
    RESULTAT_SUCCES,
    TYPE_ANNULATION_PASSE,
    TYPE_ERREUR_API,
    TYPE_PASSE_COMPLETE,
)


#
# Défauts des températures (décision C2) : jamais
# codées en dur dans les appels — elles vivent dans
# les réglages de l'app (surchargeables par étude).
#

TEMPERATURE_REFORMULATION_DEFAUT = 0.3
TEMPERATURE_RESUME_DEFAUT = 0.2

FENETRE_GLISSANTE_DEFAUT = 2000

CIBLE_SANS_RESULTAT = "sans_resultat"
CIBLE_NON_VALIDES = "non_valides"


class ErreurContexte(Exception):
    """
    L'unité courante (avec le prompt système) ne
    tient pas dans la fenêtre du modèle : le bloc
    doit passer par sous-découpage (P14.4).

    Erreur propre : le bloc est signalé, la passe
    s'arrête sans rien corrompre.
    """

    pass


@dataclass
class ContexteAssemble:
    """
    Contexte d'un appel LLM : prompt système,
    message utilisateur assemblé, FID de la fenêtre
    glissante utilisée (consignés dans la version,
    contrat §7) et tokens estimés.
    """

    prompt_systeme: str
    message: str
    fids_contexte: list = field(default_factory=list)
    tokens_estimes: int = 0


@dataclass
class ResultatPasse:
    """
    Bilan d'une passe : statut (terminee, annulee,
    erreur), blocs traités, coût réel total,
    durée totale.
    """

    statut: str = "terminee"
    nb_traites: int = 0
    cout_total: float = 0.0
    duree_ms: int = 0
    message: str = ""
    fid_erreur: int = None


class MoteurTraitements:
    """
    Moteur agnostique du bloc : assemblage,
    exécution, annulation, reprise et log sont
    communs ; seuls prompt système, périmètre de
    l'unité et paramètres varient (Reformulation en
    P15, Résumé en P17).
    """

    def __init__(
        self,
        etude_ouverte: EtudeOuverte,
        nom_reunion: str,
        parametres_app: dict = None,
        credential_store=None,
        catalogue: CatalogueLLM = None,
        client_factory=None
    ):
        self.etude = etude_ouverte
        self.reunion = nom_reunion

        self._parametres_app_bruts = parametres_app
        self._credential_store = credential_store
        self._catalogue = catalogue
        self._client_factory = client_factory

        if self.reunion not in self.etude.reunions:
            raise CatalogueError(
                f"Réunion inconnue : {self.reunion}"
            )

    #
    # Résolution de la configuration.
    #

    def _parametres_app(self) -> dict:
        """
        Paramètres LLM de l'app (injectables pour les
        tests) ; à défaut, réglages courants.
        """

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
        (contrat §10 : valeurs actives, surchargeables).
        """

        return (
            self.etude.parametres.reformulation
        )

    def resoudre(self):
        """
        Résout (fournisseur, modèle) : fournisseur des
        réglages de l'app ; modèle surchargé par l'étude
        (contrat §10) s'il existe chez ce fournisseur,
        sinon modèle des réglages.
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
        Règle d'invariance 5 de la spec : température
        effective = surcharge étude si définie, sinon
        réglage app ; jamais une valeur codée en dur
        dans le moteur.
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
            )
        )

        return float(valeur)

    def _budget_fenetre(self) -> int:

        return int(
            self._parametres_bloc().get(
                "fenetre_glissante_tokens"
            )
            or FENETRE_GLISSANTE_DEFAUT
        )

    def _contexte_active(self, cle: str) -> bool:
        """
        Cases de contexte du bloc (feuille de route
        §3.1 : la synthèse d'étude sert « aux blocs
        qui le cochent ») ; absentes d'une étude
        créée avant P17 : activées par défaut.
        """

        contexte = (
            self._parametres_bloc().get("contexte")
            or {}
        )

        return bool(contexte.get(cle, True))

    def _contexte_fenetre(
        self,
        bloc,
        seulement_validees: bool
    ) -> list:
        """
        Fenêtre glissante — vide si la case de
        contexte est décochée.
        """

        if not self._contexte_active(
            "fenetre_glissante"
        ):
            return []

        return self._fenetre_glissante(
            bloc,
            seulement_validees
        )

    #
    # Fenêtre glissante et assemblage (spec §2).
    #

    def _texte_dernier_resultat(
        self,
        fid: int,
        seulement_validees: bool
    ):

        resultat = self.etude.reformulations.get(fid)

        if not resultat or not resultat.versions:
            return None

        if not seulement_validees:
            return resultat.versions[-1].texte

        for version in reversed(resultat.versions):

            if (
                version.validation
                and version.validation.statut == "valide"
            ):
                return version.texte

        return None

    def _blocs_actifs(self) -> list:

        return blocs_actifs(
            self.etude,
            self.reunion
        )

    def _blocs_precedents(self, bloc) -> list:
        """
        Blocs actifs antérieurs au bloc courant dans
        l'ordre chronologique.
        """

        actifs = self._blocs_actifs()

        return actifs[:actifs.index(bloc)]

    def _fenetre_glissante(
        self,
        bloc,
        seulement_validees: bool
    ) -> list:
        """
        N derniers résultats antérieurs au bloc,
        dans la limite du budget de la fenêtre
        glissante (paramétrable, ~2 000 tokens).

        Résultats **produits** en passe complète
        (frais, non validés) ; résultats **validés**
        lors des relances/reprises.

        Retour : liste (fid, texte) en ordre
        chronologique.
        """

        budget = self._budget_fenetre()

        retenus = []

        tokens_cumules = 0

        for precedent in reversed(
            self._blocs_precedents(bloc)
        ):

            texte = self._texte_dernier_resultat(
                precedent.fid,
                seulement_validees
            )

            if texte is None:
                continue

            tokens = estimer_tokens(texte)

            if (
                retenus
                and tokens_cumules + tokens > budget
            ):
                break

            retenus.append((precedent.fid, texte))

            tokens_cumules += tokens

        return list(reversed(retenus))

    def _texte_synthese(self):

        if not self._contexte_active(
            "synthese_etude"
        ):
            return None

        dernieres = self.etude.synthese.versions

        if not dernieres:
            return None

        return dernieres[-1].texte

    def _message(
        self,
        bloc,
        fenetre: list,
        synthese,
        consigne: str,
        texte_courant: str,
        versions_bloc: list,
        selection: dict
    ) -> str:
        """
        Message utilisateur assemblé, dans l'ordre de
        la spec §2 : synthèse d'étude → fenêtre
        glissante → unité courante (+ formulation
        courante et versions antérieures pour une
        relance ciblée) → consigne libre éventuelle.
        """

        parties = []

        if synthese:
            parties.append(
                "Synthèse de l'étude :\n" + synthese
            )

        if fenetre:

            extraits = "\n\n".join(
                f"— {texte}"
                for _fid, texte in fenetre
            )

            parties.append(
                "Reformulations précédentes "
                "(continuité de style) :\n" + extraits
            )

        parties.append(
            "Texte à reformuler :\n" + bloc.source
        )

        if texte_courant:

            parties.append(
                "Formulation actuelle du bloc :\n"
                + texte_courant
            )

        if versions_bloc:

            historique = "\n\n".join(
                f"Version {numero} : {texte}"
                for numero, texte in versions_bloc
            )

            parties.append(
                "Versions antérieures du bloc :\n"
                + historique
            )

        if selection is not None:

            parties.append(
                "Reformuler uniquement le passage "
                f"délimité (offsets caractères "
                f"{selection.get('debut')} à "
                f"{selection.get('fin')}) ; le reste du "
                "bloc est conservé tel quel."
            )

        if consigne:
            parties.append("Consigne : " + consigne)

        return "\n\n".join(parties)

    def assembler_contexte(
        self,
        bloc,
        seulement_validees: bool = False,
        consigne: str = None,
        selection: dict = None
    ) -> ContexteAssemble:
        """
        Assemble le contexte d'un appel : budget
        explicite puis, en cas de débordement,
        **troncation par le haut** (décision C1) :

        1. retirer de la fenêtre glissante les blocs
           les plus anciens en premier ;
        2. jamais la synthèse d'étude, jamais l'unité
           courante, jamais le prompt système ;
        3. si l'unité courante seule + prompt dépasse
           la fenêtre du modèle : erreur propre, le
           bloc est signalé (sous-découpage requis).
        """

        _fournisseur, modele = self.resoudre()

        max_contexte = (
            modele.max_contexte_tokens or 1_000_000
        )

        prompt_systeme = (
            self._parametres_bloc().get("prompt", "")
        )

        synthese = self._texte_synthese()

        fenetre = self._contexte_fenetre(
            bloc,
            seulement_validees
        )

        texte_courant = None
        versions_bloc = []

        if selection is not None:

            resultat = (
                self.etude.reformulations.get(bloc.fid)
            )

            if resultat and resultat.versions:
                texte_courant = (
                    resultat.versions[-1].texte
                )

                versions_bloc = [
                    (version.numero, version.texte)
                    for version in resultat.versions
                ]

        def construire(fenetre_courante):

            message = self._message(
                bloc,
                fenetre_courante,
                synthese,
                consigne,
                texte_courant,
                versions_bloc,
                selection
            )

            total = (
                estimer_tokens(prompt_systeme)
                + estimer_tokens(message)
            )

            return message, total

        message, total = construire(fenetre)

        #
        # Troncation par le haut : les plus anciens
        # de la fenêtre d'abord, jusqu'à tenir.
        #
        while total > max_contexte and fenetre:

            fenetre = fenetre[1:]

            message, total = construire(fenetre)

        if total > max_contexte:

            raise ErreurContexte(
                f"Le bloc {bloc.fid} seul ne tient pas "
                f"dans la fenêtre du modèle "
                f"({modele.nom_affiche}, "
                f"{max_contexte} tokens) : il doit "
                "passer par sous-découpage."
            )

        return ContexteAssemble(
            prompt_systeme=prompt_systeme,
            message=message,
            fids_contexte=[
                fid for fid, _texte in fenetre
            ],
            tokens_estimes=total,
        )

    #
    # Estimation de coût avant passe (B1).
    #

    def blocs_a_traiter(
        self,
        cible: str = CIBLE_SANS_RESULTAT
    ) -> list:
        """
        Blocs actifs à traiter :
        - ``sans_resultat`` (défaut) : ceux qui
          n'ont encore aucun résultat — relancer une
          passe saute les blocs déjà traités (règle
          d'invariance 6, reprise spec §3.3) ;
        - ``non_valides`` : commande explicite
          « traiter les blocs non validés » (spec
          §4) — ceux dont la dernière version
          n'est pas validée.
        """

        actifs = self._blocs_actifs()

        if cible == CIBLE_NON_VALIDES:

            a_traiter = []

            for bloc in actifs:

                resultat = (
                    self.etude.reformulations.get(
                        bloc.fid
                    )
                )

                validee = (
                    resultat
                    and resultat.versions
                    and resultat.versions[-1].validation
                    and (
                        resultat.versions[-1]
                        .validation.statut
                        == "valide"
                    )
                )

                if not validee:
                    a_traiter.append(bloc)

            return a_traiter

        return [
            bloc
            for bloc in actifs
            if not self._a_un_resultat(bloc.fid)
        ]

    def _a_un_resultat(self, fid: int) -> bool:

        resultat = self.etude.reformulations.get(fid)

        return bool(
            resultat and resultat.versions
        )

    def estimer_passe(
        self,
        cible: str = CIBLE_SANS_RESULTAT
    ) -> dict:
        """
        Estimation de coût d'une passe aux prix
        courants du catalogue (affichée avant la
        première passe totale — fait office de
        confirmation, décision B1).
        """

        _fournisseur, modele = self.resoudre()

        prompt_systeme = (
            self._parametres_bloc().get("prompt", "")
        )

        synthese = self._texte_synthese() or ""

        budget_fenetre = self._budget_fenetre()

        fenetre_activee = self._contexte_active(
            "fenetre_glissante"
        )

        tokens_in = 0
        tokens_out = 0

        for bloc in self.blocs_a_traiter(cible):

            unite = estimer_tokens(bloc.source)

            fenetre = min(
                budget_fenetre,
                max(0, tokens_in)
            ) if fenetre_activee else 0

            tokens_in += (
                estimer_tokens(prompt_systeme)
                + estimer_tokens(synthese)
                + fenetre
                + unite
            )

            # Sortie estimée de l'ordre de l'unité :
            # la reformulation condense l'oral, mais
            # l'estimation vise le plancher de coût.
            tokens_out += unite

        return {
            "nb_blocs": len(
                self.blocs_a_traiter(cible)
            ),
            "modele": modele.nom_affiche,
            "tokens_in_estimes": tokens_in,
            "tokens_out_estimes": tokens_out,
            "cout_estime": cout_estime(
                modele,
                tokens_in,
                tokens_out
            ),
        }

    #
    # Client LLM.
    #

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
        La température n'est envoyée que si le modèle
        la supporte (capacités du catalogue) —
        décision C2. L'effort de raisonnement suit la
        même règle : mémorisé dans les réglages LLM
        de l'app, envoyé uniquement si le modèle le
        déclare (None = défaut de l'API).
        """

        effort = None

        if modele.capacite_effort_raisonnement:

            effort = self._parametres_app().get(
                "effort_raisonnement"
            )

        config = self._parametres_app()

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
    # Exécution séquentielle (spec §3).
    #

    def _appeler(
        self,
        client,
        contexte: ContexteAssemble,
        parametres: ParametresCompletion,
        annulation: Annulation
    ) -> ResultatCompletion:

        return client.completions(
            contexte.prompt_systeme,
            [
                {
                    "role": "user",
                    "content": contexte.message,
                }
            ],
            parametres,
            annulation=annulation
        )

    def _consigner_resultat(
        self,
        bloc,
        resultat: ResultatCompletion,
        type_version: str,
        contexte: ContexteAssemble,
        consigne: str = None,
        selection: dict = None
    ):

        version = ajouter_version_reformulation(
            self.etude,
            bloc.fid,
            resultat.texte,
            type_version=type_version,
            consigne=consigne,
            selection=selection,
            stats={
                "duree_ms": resultat.duree_ms,
                "tokens_in": resultat.tokens_in,
                "tokens_out": resultat.tokens_out,
                "cout_estime": (
                    resultat.cout_estime
                ),
            },
            contexte=contexte.fids_contexte,
        )

        sauvegarder_etude(self.etude)

        return version

    def traiter_reunion(
        self,
        annulation: Annulation = None,
        progression=None,
        cible: str = CIBLE_SANS_RESULTAT
    ) -> ResultatPasse:
        """
        Exécute une passe séquentielle sur les blocs
        à traiter, dans l'ordre chronologique.

        - annulation (B2) : arrêt propre à la fin de
          l'appel en cours (son résultat est conservé
          s'il aboutit) ; tout résultat déjà produit
          est conservé ;
        - défaillance API (spec §3.4) : après les
          relances du client, arrêt propre de la
          passe, erreur consignée au log ;
        - reprise : relancer une passe saute les
          blocs déjà traités (règle d'invariance 6) ;
        - aucune cascade (B3) : rien n'est relancé
          automatiquement après validation.
        """

        debut = time.monotonic()

        fournisseur, modele = self.resoudre()

        client = self._creer_client(fournisseur)

        blocs = self.blocs_a_traiter(cible)

        parametres = self._parametres_completion(
            modele,
            self.temperature_effective()
        )

        traites = 0
        cout_total = 0.0
        tokens_in_total = 0
        tokens_out_total = 0

        for bloc in blocs:

            if (
                annulation is not None
                and annulation.demandee
            ):
                return self._terminer_annulation(
                    modele,
                    traites,
                    cout_total,
                    debut,
                    fid_arret=bloc.fid
                )

            contexte = self.assembler_contexte(
                bloc,
                seulement_validees=False
            )

            try:

                resultat = self._appeler(
                    client,
                    contexte,
                    parametres,
                    annulation
                )

            except ErreurLLM as e:

                if e.type == "annulation":
                    return self._terminer_annulation(
                        modele,
                        traites,
                        cout_total,
                        debut,
                        fid_arret=bloc.fid
                    )

                return self._terminer_erreur(
                    modele,
                    traites,
                    cout_total,
                    tokens_in_total,
                    tokens_out_total,
                    debut,
                    fid_erreur=bloc.fid,
                    message=e.message
                )

            self._consigner_resultat(
                bloc,
                resultat,
                "passe",
                contexte
            )

            traites += 1
            cout_total += resultat.cout_estime
            tokens_in_total += resultat.tokens_in
            tokens_out_total += resultat.tokens_out

            if progression is not None:
                progression(bloc.fid, traites, len(blocs))

        duree_ms = int(
            (time.monotonic() - debut) * 1000
        )

        self.etude.journal.ajouter(
            TYPE_PASSE_COMPLETE,
            fid=None,
            reunion=self.reunion,
            modele=modele.id,
            resultat=RESULTAT_SUCCES,
            stats={
                "duree_ms": duree_ms,
                "tokens_in": tokens_in_total,
                "tokens_out": tokens_out_total,
                "cout_estime": cout_total,
            },
            extras={
                "statut": "terminee",
                "nb_blocs": len(blocs),
                "cout_total": cout_total,
                "cible": cible,
            }
        )

        return ResultatPasse(
            statut="terminee",
            nb_traites=traites,
            cout_total=cout_total,
            duree_ms=duree_ms,
        )

    def _terminer_annulation(
        self,
        modele,
        traites: int,
        cout_total: float,
        debut,
        fid_arret: int
    ) -> ResultatPasse:
        """
        B2 : arrêt propre — tout résultat déjà
        produit est conservé ; l'annulation est
        consignée au log.
        """

        duree_ms = int(
            (time.monotonic() - debut) * 1000
        )

        self.etude.journal.ajouter(
            TYPE_ANNULATION_PASSE,
            fid=fid_arret,
            reunion=self.reunion,
            modele=modele.id,
            resultat=RESULTAT_SUCCES,
            message=(
                f"Passe interrompue — {traites} "
                "bloc(s) traité(s), résultats conservés."
            ),
            extras={
                "blocs_traites": traites,
                "cout_total": cout_total,
            }
        )

        return ResultatPasse(
            statut="annulee",
            nb_traites=traites,
            cout_total=cout_total,
            duree_ms=duree_ms,
            message=(
                f"Passe interrompue — {traites} "
                "bloc(s) traité(s)."
            )
        )

    def _terminer_erreur(
        self,
        modele,
        traites: int,
        cout_total: float,
        tokens_in: int,
        tokens_out: int,
        debut,
        fid_erreur: int,
        message: str
    ) -> ResultatPasse:
        """
        Spec §3.4 : après retry, arrêt propre de la
        passe — erreur consignée avec le message du
        fournisseur ; les résultats déjà produits
        sont conservés.
        """

        duree_ms = int(
            (time.monotonic() - debut) * 1000
        )

        self.etude.journal.ajouter(
            TYPE_ERREUR_API,
            fid=fid_erreur,
            reunion=self.reunion,
            modele=modele.id,
            resultat=RESULTAT_ERREUR,
            message=message
        )

        self.etude.journal.ajouter(
            TYPE_PASSE_COMPLETE,
            fid=None,
            reunion=self.reunion,
            modele=modele.id,
            resultat=RESULTAT_ERREUR,
            message=message,
            stats={
                "duree_ms": duree_ms,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cout_estime": cout_total,
            },
            extras={
                "statut": "erreur",
                "nb_blocs": traites,
                "fid_erreur": fid_erreur,
                "cout_total": cout_total,
            }
        )

        return ResultatPasse(
            statut="erreur",
            nb_traites=traites,
            cout_total=cout_total,
            duree_ms=duree_ms,
            message=message,
            fid_erreur=fid_erreur
        )

    def traiter_bloc(
        self,
        fid: int,
        consigne: str = None,
        selection: dict = None,
        annulation: Annulation = None
    ):
        """
        Reformulation d'un seul bloc (relance complète
        ou ciblée sur sélection) : aucune
        confirmation (B1), exécution directe.

        Fenêtre glissante : uniquement les résultats
        **validés** lors des relances (spec §2).
        Relance ciblée : contexte identique + la
        formulation courante et toutes les versions
        antérieures du bloc.

        Retourne la version créée ; lève ErreurLLM
        (après retry et consignation au log) en cas
        de défaillance.
        """

        bloc = next(
            (
                bloc
                for bloc in self._blocs_actifs()
                if bloc.fid == fid
            ),
            None
        )

        if bloc is None:
            raise CatalogueError(
                f"Bloc {fid} absent de la segmentation "
                f"active de {self.reunion}"
            )

        fournisseur, modele = self.resoudre()

        client = self._creer_client(fournisseur)

        parametres = self._parametres_completion(
            modele,
            self.temperature_effective()
        )

        contexte = self.assembler_contexte(
            bloc,
            seulement_validees=True,
            consigne=consigne,
            selection=selection
        )

        type_version = (
            "relance_ciblee"
            if selection is not None
            else "relance"
        )

        try:

            resultat = self._appeler(
                client,
                contexte,
                parametres,
                annulation
            )

        except ErreurLLM as e:

            if e.type != "annulation":

                self.etude.journal.ajouter(
                    TYPE_ERREUR_API,
                    fid=fid,
                    reunion=self.reunion,
                    modele=modele.id,
                    resultat=RESULTAT_ERREUR,
                    message=e.message
                )

            raise

        return self._consigner_resultat(
            bloc,
            resultat,
            type_version,
            contexte,
            consigne=consigne,
            selection=selection
        )
