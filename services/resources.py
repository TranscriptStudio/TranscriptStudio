from pathlib import Path


def get_application_root() -> Path:
    """
    Retourne le répertoire racine contenant
    les ressources de Transcript Studio.

    Fonctionne lorsque l'application est :
    - exécutée depuis les sources ;
    - déplacée avec son arborescence ;
    - compilée en mode standalone avec Nuitka,
      à condition que les ressources soient
      incluses dans le build.
    """

    return (
        Path(__file__)
        .resolve()
        .parent
        .parent
    )


def resource_path(
    relative_path
) -> Path:
    """
    Retourne le chemin absolu d'une ressource
    à partir de la racine de l'application.
    """

    return (
        get_application_root()
        / Path(relative_path)
    )