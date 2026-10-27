# services/timecodes.py
"""
Lecture et écriture des timecodes du format étude v2.

Le contrat (CONTRAT_FORMAT_ETUDE_V2.md) exprime les positions au
format ``HH:MM:SS.mmm`` (ex. ``00:02:31.400``). Le journal des
opérations de prétraitement utilise le même format.

Les conversions travaillent en secondes (float).
"""

import re


_TIMECODE_RE = re.compile(
    r"^(?:(\d+):)?(\d{1,2}):(\d{1,2}(?:\.\d+)?)$"
)


def horodatage_iso() -> str:
    """
    Horodatage ISO local ``AAAA-MM-JJTHH:MM:SS``,
    convention du format étude et du journal des
    opérations.
    """

    from datetime import datetime

    return (
        datetime
        .now()
        .isoformat(timespec="seconds")
    )


def formater_timecode(seconds: float) -> str:
    """
    Formate une durée en secondes au format ``HH:MM:SS.mmm``.

    Les durées négatives lèvent ValueError : une position
    audio ne peut pas l'être.
    """

    if seconds < 0:
        raise ValueError(
            "Une position audio ne peut pas être négative "
            f"(reçu : {seconds})"
        )

    total_ms = int(round(seconds * 1000))

    hours, reste = divmod(total_ms, 3600_000)
    minutes, reste = divmod(reste, 60_000)
    secondes, millisecondes = divmod(reste, 1000)

    return (
        f"{hours:02d}:{minutes:02d}:"
        f"{secondes:02d}.{millisecondes:03d}"
    )


def lire_timecode(timecode: str) -> float:
    """
    Lit un timecode ``[HH:]MM:SS[.mmm]`` et retourne
    des secondes.

    Les valeurs manquantes (heures, fraction) valent zéro.
    """

    if not isinstance(timecode, str):
        raise ValueError(
            "Timecode attendu sous forme de texte, "
            f"reçu : {timecode!r}"
        )

    texte = timecode.strip()

    match = _TIMECODE_RE.match(texte)

    if not match:
        raise ValueError(
            f"Timecode invalide : {timecode!r}"
        )

    heures = match.group(1)
    minutes = match.group(2)
    secondes = match.group(3)

    total = float(secondes)

    total += int(minutes) * 60

    if heures is not None:
        total += int(heures) * 3600

    return total
