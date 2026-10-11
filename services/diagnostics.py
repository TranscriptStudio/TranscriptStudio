# services/diagnostics.py

import datetime
import sys
import traceback

from services.app_paths import (
    APP_DATA_DIR,
)


# Journal des exceptions non gerees. Dans le binaire
# standalone (console desactivee), une exception levee
# dans un slot Qt est perdue sans trace : on l'ecrit
# dans un fichier pour pouvoir diagnostiquer.
LOG_FILE = (
    APP_DATA_DIR
    / "diagnostic.log"
)


def _format_exception(
    exc_type,
    exc_value,
    exc_tb
):
    lines = (
        traceback
        .format_exception(
            exc_type,
            exc_value,
            exc_tb
        )
    )

    stamp = (
        datetime
        .datetime
        .now()
        .isoformat(
            timespec="seconds"
        )
    )

    return (
        f"\n===== {stamp} =====\n"
        + "".join(lines)
    )


def _log_and_show(
    exc_type,
    exc_value,
    exc_tb
):
    text = (
        _format_exception(
            exc_type,
            exc_value,
            exc_tb
        )
    )

    try:
        with open(
            LOG_FILE,
            "a",
            encoding="utf-8"
        ) as f:
            f.write(text)
    except OSError:
        pass

    #
    # Afficher aussi la trace a l'ecran :
    # sans console, elle serait sinon invisible.
    # Les dernieres lignes suffisent (message
    # + appel fautif), la version complete est
    # dans le fichier.
    #
    try:
        from PySide6.QtWidgets import (
            QApplication,
            QMessageBox,
        )

        if (
            QApplication.instance()
            is not None
        ):
            QMessageBox.critical(
                None,
                "Erreur interne Transcript Studio",
                (
                    "Une erreur inattendue est survenue :\n\n"
                    + "".join(
                        traceback
                        .format_exception(
                            exc_type,
                            exc_value,
                            exc_tb
                        )[-8:]
                    )
                    + f"\n\nTrace complete : {LOG_FILE}"
                )
            )
    except Exception:
        pass


def checkpoint(tag):
    """Point de controle de diagnostic : journalise le passage."""
    log_message(
        "CHECKPOINT "
        + tag
    )


def log_message(message):
    """Journalise un message dans le fichier de diagnostic."""
    try:
        stamp = (
            datetime
            .datetime
            .now()
            .isoformat(
                timespec="seconds"
            )
        )
        with open(
            LOG_FILE,
            "a",
            encoding="utf-8"
        ) as f:
            f.write(
                "["
                + stamp
                + "] "
                + message
                + "\n"
            )
    except OSError:
        pass


def _qt_message_handler(
    mode,
    context,
    message
):
    """Capte les messages Qt (warnings et fatals)
    et les journalise : dans le binaire sans console,
    le texte d'un qFatal est sinon perdu avant l'abort.
    """
    import traceback

    # Ordre de l'enum QtMsgType (Qt5/Qt6) :
    # Debug=0, Warning=1, Critical=2, Fatal=3,
    # Info=4.
    levels = {
        0: "QtDebug",
        1: "QtWarning",
        2: "QtCritical",
        3: "QtFatal",
        4: "QtInfo",
    }

    level = (
        levels.get(
            mode,
            f"QtMsgType({mode})"
        )
    )

    origin = (
        f"{context.file}:{context.line}"
        if context.file
        else "(origine inconnue)"
    )

    log_message(
        f"{level} {origin} : {message}"
    )

    #
    # Une trace Python accompagne le message :
    # le contexte d'appel est precieux pour un
    # diagnostic.
    #
    lines = (
        traceback
        .format_stack()
    )
    try:
        with open(
            LOG_FILE,
            "a",
            encoding="utf-8"
        ) as f:
            f.write(
                "  pile Python au moment du message :"
                + "\n"
                + "".join(lines)
            )
    except OSError:
        pass

    if mode == 3:
        # QtFatal : laisser Qt aborter ensuite.
        # Ne rien faire d'autre pour ne pas masquer
        # le comportement reel.
        pass


def install_qt_message_handler():
    try:
        from PySide6.QtCore import (
            qInstallMessageHandler,
        )
        qInstallMessageHandler(
            _qt_message_handler
        )
    except Exception:
        pass


def install_excepthook():
    sys.excepthook = (
        _log_and_show
    )
