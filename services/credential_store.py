"""
Credential Store Service

P6 : Stockage securise des cles API.
P15 : Credentials generiques — une cle par fournisseur LLM
(elevenlabs_api_key conserve comme nom historique).

Ce module fournit une abstraction pour le stockage des identifiants sensibles
comme la cle API ElevenLabs, en vue de migrer vers un stockage plus securise
(keystore systeme, etc.) tout en restant multiplateforme.

Pour l'instant, implémente un stockage basique avec migration depuis
settings.json, tout en préparant l'infrastructure pour des solutions
plus sécurisées à l'avenir.

**Sécurité** : jamais journaliser une clé ; les clés ne vivent
que dans ce store (règle d'invariance 1 du paramétrage LLM).
"""

import json
from pathlib import Path
from typing import Optional


CLE_ELEVENLABS = "elevenlabs_api_key"

#
# P15 : une clé par fournisseur LLM, stockée sous
# le nom llm_cle_<id> (identifiant de fournisseur
# du catalogue, stable). P16-bis 3ᵉ série
# (spec correctifs §17) : les credentials vivent
# dans leur PROPRE fichier (credentials.json) —
# settings.json est réécrit en entier par
# SettingsManager à chaque sauvegarde (réglages,
# projets/études récents, thème…) et effaçait les
# clés LLM qui y étaient écrites : c'est la cause
# de « la clé disparaît après enregistrement ».
#

PREFIXE_CLE_LLM = "llm_cle_"

FICHIER_CREDENTIALS = "credentials.json"


class CredentialStore:
    """
    Gestionnaire de stockage des identifiants sensibles.

    Actuellement utilise un stockage dans settings.json avec chiffrement possible,
    mais conçu pour être étendu vers des solutions système plus sécurisées.
    """

    def __init__(self, settings_file: Path):
        """
        Initialise le CredentialStore.

        Args:
            settings_file: Chemin historique vers
            settings.json — utilisé uniquement pour
            la migration initiale (P6/P15) ; les
            credentials vivent désormais dans
            credentials.json, à côté.
        """
        self.settings_file = Path(settings_file)

        self.fichier_credentials = (
            self.settings_file.parent
            / FICHIER_CREDENTIALS
        )

        self._credentials = {}
        self._load_credentials()

    def _load_credentials(self) -> None:
        """
        Charge les identifiants depuis
        credentials.json ; à défaut, migre les clés
        historiques de settings.json (clé ElevenLabs
        P6 + clés LLM P15).
        """
        if self.fichier_credentials.exists():
            try:
                with open(
                    self.fichier_credentials,
                    "r",
                    encoding="utf-8"
                ) as f:
                    data = json.load(f)

                self._credentials = {
                    nom: valeur
                    for nom, valeur in data.items()
                    if isinstance(
                        valeur,
                        (str, dict)
                    )
                }
            except (json.JSONDecodeError, IOError):
                self._credentials = {}

            return

        #
        # Première exécution : migration depuis
        # settings.json, puis écriture du fichier
        # dédié.
        #
        self._credentials = {CLE_ELEVENLABS: ""}

        if self.settings_file.exists():
            try:
                with open(
                    self.settings_file,
                    "r",
                    encoding="utf-8"
                ) as f:
                    settings = json.load(f)

                    self._credentials[CLE_ELEVENLABS] = (
                        settings.get(CLE_ELEVENLABS, "")
                    )

                    for nom, valeur in settings.items():
                        if (
                            nom.startswith(PREFIXE_CLE_LLM)
                            and isinstance(valeur, str)
                        ):
                            self._credentials[nom] = valeur
            except (json.JSONDecodeError, IOError):
                pass

        self._save_credentials()

    def _save_credentials(self) -> None:
        """
        Sauvegarde les identifiants dans le fichier
        dédié credentials.json — jamais dans
        settings.json (réécrit en entier par
        SettingsManager, qui ne connaît pas les
        credentials).
        """
        try:
            with open(
                self.fichier_credentials,
                "w",
                encoding="utf-8"
            ) as f:
                json.dump(
                    self._credentials,
                    f,
                    ensure_ascii=False,
                    indent=2
                )
        except (IOError, json.JSONDecodeError):
            # Si on ne peut pas sauvegarder, c'est un problème mais on ne veut pas
            # bloquer l'application
            pass

    #
    # Credentials génériques (P15 : une clé par fournisseur LLM).
    #

    def get_credential(self, nom: str) -> str:
        """
        Récupère un credential par son nom
        (chaîne vide si absent).
        """
        return self._credentials.get(nom, "")

    def set_credential(self, nom: str, valeur: str) -> None:
        """
        Définit un credential par son nom.
        """
        self._credentials[nom] = valeur or ""
        self._save_credentials()

    def delete_credential(self, nom: str) -> None:
        """
        Supprime un credential (le nom disparaît du store).
        """
        self._credentials.pop(nom, None)
        self._save_credentials()

    def has_credential(self, nom: str) -> bool:
        """
        Vérifie qu'un credential non vide est configuré.
        """
        valeur = self._credentials.get(nom, "")
        return bool(valeur and valeur.strip())

    #
    # Clé API ElevenLabs (interface historique conservée).
    #

    def get_api_key(self) -> str:
        """
        Récupère la clé API ElevenLabs.

        Returns:
            La clé API si elle existe, une chaîne vide sinon.
        """
        return self.get_credential(CLE_ELEVENLABS)

    def set_api_key(self, api_key: str) -> None:
        """
        Définit la clé API ElevenLabs.

        Args:
            api_key: La nouvelle clé API
        """
        self.set_credential(CLE_ELEVENLABS, api_key)

    def delete_api_key(self) -> None:
        """
        Supprime la clé API ElevenLabs.
        """
        self.delete_credential(CLE_ELEVENLABS)

    def has_api_key(self) -> bool:
        """
        Vérifie si une clé API est configurée.

        Returns:
            True si une clé non vide est configurée, False sinon.
        """
        return self.has_credential(CLE_ELEVENLABS)

    #
    # Clés LLM (P15) : une clé par fournisseur, jamais en clair
    # ailleurs que dans ce store.
    #

    def get_cle_llm(self, fournisseur_id: str) -> str:
        """
        Clé API du fournisseur LLM donné.
        """
        return self.get_credential(
            self.nom_cle_llm(fournisseur_id)
        )

    def set_cle_llm(
        self,
        fournisseur_id: str,
        cle: str
    ) -> None:
        """
        Définit la clé API du fournisseur LLM donné.
        Si la clé CHANGE, le dernier résultat de
        test (qui concernait l'ancienne clé) est
        invalidé.
        """

        if self.get_cle_llm(fournisseur_id) != (
            cle or ""
        ):
            self.effacer_statut_test(fournisseur_id)

        self.set_credential(
            self.nom_cle_llm(fournisseur_id),
            cle
        )

    def set_statut_test(
        self,
        fournisseur_id: str,
        texte: str,
        couleur: str
    ) -> None:
        """
        Mémorise le dernier résultat de « Tester la
        clé » d'un fournisseur (retour relecture §17 :
        il survit à la fermeture des réglages tant
        que la clé ne change pas). Le texte ne
        contient jamais la clé.
        """

        statuts = self._credentials.get(
            "statuts_test",
            {}
        )

        if not isinstance(statuts, dict):
            statuts = {}

        statuts[fournisseur_id] = {
            "texte": texte,
            "couleur": couleur,
        }

        self._credentials["statuts_test"] = statuts

        self._save_credentials()

    def get_statut_test(self, fournisseur_id: str):
        """
        Dernier résultat de test du fournisseur
        ({'texte', 'couleur'} ou None).
        """

        statuts = self._credentials.get(
            "statuts_test",
            {}
        )

        if not isinstance(statuts, dict):
            return None

        return statuts.get(fournisseur_id)

    def effacer_statut_test(
        self,
        fournisseur_id: str
    ) -> None:
        """
        Invalide le résultat de test d'un fournisseur
        (appelé quand sa clé change).
        """

        statuts = self._credentials.get(
            "statuts_test",
            {}
        )

        if not isinstance(statuts, dict):
            return

        if fournisseur_id in statuts:

            statuts.pop(fournisseur_id)

            self._credentials["statuts_test"] = (
                statuts
            )

            self._save_credentials()

    def has_cle_llm(self, fournisseur_id: str) -> bool:
        """
        Le fournisseur a-t-il une clé configurée ?
        """
        return self.has_credential(
            self.nom_cle_llm(fournisseur_id)
        )

    @staticmethod
    def nom_cle_llm(fournisseur_id: str) -> str:
        """
        Nom de stockage de la clé d'un fournisseur LLM.
        """

        return f"llm_cle_{fournisseur_id}"

    def migrate_legacy_key(self, legacy_key: Optional[str] = None) -> bool:
        """
        P6.2 : Migre une ancienne clé depuis un format hérité.

        Si une clé existe déjà dans le CredentialStore, ne fait rien.
        Sinon, si legacy_key est fourni, le migre.

        **Sécurité** : Ne jamais journaliser la clé.

        Args:
            legacy_key: Clé héritée à migrer (optionnel)

        Returns:
            True si une migration a eu lieu, False sinon
        """
        # Si on a déjà une clé, pas de migration nécessaire
        if self.has_api_key():
            return False

        # Si une clé héritée est fournie, la migrer
        if legacy_key and legacy_key.strip():
            # **Ne jamais journaliser la clé**
            self.set_api_key(legacy_key)
            return True

        return False

    def migrate_from_settings_manager(self, settings_manager) -> bool:
        """
        P6.2 : Migre une clé depuis SettingsManager vers CredentialStore.

        Cette méthode vérifie si SettingsManager a une clé API et la migre
        vers CredentialStore si ce n'est pas déjà fait.

        **Sécurité** : La clé est copiée puis supprimée de SettingsManager
        seulement après confirmation que CredentialStore l'a bien reçue.

        Args:
            settings_manager: Instance de SettingsManager

        Returns:
            True si une migration a eu lieu, False sinon
        """
        # Vérifier si SettingsManager a une clé
        legacy_key = settings_manager.get_api_key()

        if legacy_key and legacy_key.strip():
            # Si CredentialStore n'a pas de clé, migrer
            if not self.has_api_key():
                self.set_api_key(legacy_key)
                # Supprimer de SettingsManager après migration réussie
                settings_manager.set_api_key("")
                settings_manager.save()
                return True

        return False
