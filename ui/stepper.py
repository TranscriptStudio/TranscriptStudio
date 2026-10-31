# ui/stepper.py
"""
Barre d'étapes du stepper de réunion (P18.6,
spec navigation §3.2) : Transcription ·
Reformulation · Résumé · Export.

P18.6-bis série 8 (retour David 31/10, points 3
et 5) : plus AUCUN numéro — chaque étape porte
une ICÔNE (micro vintage pour la transcription,
crayon pour la reformulation, document pour le
résumé, plateau fléché pour l'export), teintée à
la couleur de texte de son état ; en thème
CLAIR, l'étape « à faire » est un gris TRÈS
CLAIR (jamais une forme noire).

Couleurs affirmées (P18.6-bis série 5, spec 30f
§24, maquette hub v4 — sombre) : à faire = gris
discret ; en cours = pastille pleine bleue à
texte blanc, lueur discrète ; fait = émeraude
sur fond translucide. P18.6-bis (§18) : PLUS
AUCUN contour pointillé — l'optionnalité ne se
lit que dans l'info-bulle au survol.

P18.6-bis série 7 (SPEC_NAVIGATION_MODIFS_
2026-10-31d §30, invariant 16) : au survol d'une
pastille QUI EST UN LIEN INDIVIDUEL (page
Réunion uniquement), un reflet translucide la
traverse de gauche à droite en UNE SEULE PASSE
(~900 ms, léger skew, fondu) + léger contour
assorti — teinte fonction de l'état (fait →
émeraude, en cours → blanc translucide, à faire
→ voile clair discret). Jamais en boucle,
rejoué à chaque entrée de survol, retour ~120
ms, curseur main. Les pastilles SANS lien propre
(hub, page Étude) restent ENTÈREMENT STATIQUES —
ni balayage, ni contour, ni curseur main. Repli
sur le simple contour assorti si l'animation
n'est pas supportée.

Réutilisé par :
- la page Réunion (stepper fixe, cliquable) ;
- la page Étude (avancement sans Export,
  invariant §9.4) ;
- les mini-tuiles du hub et de la page Étude.
"""

from PySide6.QtCore import (
    QEasingCurve,
    QPointF,
    QRectF,
    QSize,
    Signal,
    QVariantAnimation,
    Qt,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QIcon,
    QLinearGradient,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from services.avancement import (
    A_FAIRE,
    EN_COURS,
    ETAPES_OPTIONNELLES,
    ETAPES_REUNION,
    LIBELLES_ETAPES,
    TERMINE,
)

from services.theme_manager import (
    couleurs_stepper,
    est_sombre,
)

from services.resources import resource_path


#
# Icônes des étapes (série 8 : les numéros
# disparaissent) — SVG recolorés à la couleur de
# texte de l'état à chaque rafraîchissement.
#

ICONES_ETAPES = {
    "transcription": (
        "icons/stepper-transcription.svg"
    ),
    "reformulation": (
        "icons/stepper-reformulation.svg"
    ),
    "resume": "icons/stepper-resume.svg",
    "export": "icons/stepper-export.svg",
}

#
# Série 7 (spec 31d §30) : teintes du reflet et
# du contour de survol, FONCTION DE L'ÉTAT —
# jamais un bleu unique imposé.
#

TEINTES_SURVOL = {
    True: {  # thème sombre
        TERMINE: (46, 201, 138),
        EN_COURS: (255, 255, 255),
        A_FAIRE: (255, 255, 255),
    },
    False: {  # thème clair : voile clair discret
        TERMINE: (46, 201, 138),
        EN_COURS: (255, 255, 255),
        A_FAIRE: (255, 255, 255),
    },
}


def _style_etat(
    etat: str,
    sombre: bool,
    couleur_bord: str = None
) -> str:
    """
    Feuille de style d'une pastille pour un état,
    dans le thème courant (série 5 §24 pour le
    sombre ; série 8 pour le clair — l'étape à
    faire y devient un gris très clair).
    ``couleur_bord`` surcharge le contour (survol
    de la série 7 §30) — l'état et ses couleurs
    ne sont JAMAIS modifiés par le survol.
    """

    couleurs = couleurs_stepper(sombre)

    if etat == EN_COURS:

        bord = (
            couleur_bord
            or couleurs["en_cours_lueur"]
        )

        return (
            "border: 1px solid "
            + bord
            + ";"
            "color: "
            + couleurs["en_cours_texte"]
            + ";"
            "background-color: "
            + couleurs["en_cours_fond"]
            + ";"
        )

    if etat == TERMINE:

        bord = (
            couleur_bord
            or couleurs["fait_contour"]
        )

        return (
            "border: 1px solid "
            + bord
            + ";"
            "color: "
            + couleurs["fait_texte"]
            + ";"
            "background-color: "
            + couleurs["fait_fond"]
            + ";"
        )

    bord = (
        couleur_bord
        or couleurs["a_faire_fond"]
    )

    return (
        "border: 1px solid "
        + bord
        + ";"
        "color: "
        + couleurs["a_faire_texte"]
        + ";"
        "background-color: "
        + couleurs["a_faire_fond"]
        + ";"
    )


def _teinte_survol(etat: str):
    """
    Teinte (r, g, b) du reflet et du contour au
    survol, selon l'état et le thème (§30).
    """

    return TEINTES_SURVOL[True].get(
        etat,
        (255, 255, 255)
    )


class RefletPastille(QWidget):
    """
    Reflet lumineux translucide qui traverse une
    pastille de gauche à droite en UNE SEULE
    PASSE (série 7 §30, effet « B — shine ») :
    bande légèrement inclinée (skew), fondu
    d'entrée et de sortie, ~900 ms, JAMAIS en
    boucle — rejouée à chaque entrée de survol.

    Peint par-dessus la pastille sans jamais
    l'occlure (translucide) ni la modifier :
    l'état et ses couleurs restent inchangés
    (invariant 16).
    """

    DUREE_MS = 900

    def __init__(self, parent):

        super().__init__(parent)

        self.setAttribute(
            Qt.WidgetAttribute
            .WA_TransparentForMouseEvents,
            True
        )

        self._phase = 0.0
        self._animation = None

        self.hide()

    def jouer(self, teinte):
        """
        Démarre UNE passe du reflet avec la teinte
        (r, g, b) de l'état.
        """

        self._teinte = teinte

        if self._animation is not None:
            self._animation.stop()

        self._animation = QVariantAnimation(self)

        self._animation.setDuration(self.DUREE_MS)

        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)

        self._animation.setEasingCurve(
            QEasingCurve.Type.InOutSine
        )

        self._animation.valueChanged.connect(
            self._sur_phase
        )

        self._animation.finished.connect(
            self.hide
        )

        self.setGeometry(
            self.parentWidget().rect()
        )

        self.show()
        self.raise_()

        self._animation.start()

    def _sur_phase(self, phase):

        self._phase = float(phase)

        self.update()

    def paintEvent(self, event):

        if self._phase <= 0.0:
            return

        parent = self.parentWidget()

        largeur = parent.width()
        hauteur = parent.height()

        #
        # Bande diagonale (léger skew par
        # rotation) : elle traverse de gauche à
        # droite ; fondu d'entrée et de sortie —
        # alpha nul aux deux extrémités de la
        # passe, maximal au milieu.
        #
        r, v, b = self._teinte

        alpha = int(
            90
            * (
                1.0
                - abs(2.0 * self._phase - 1.0)
            )
        )

        if alpha <= 0:
            return

        peintre = QPainter(self)

        peintre.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        peintre.setPen(
            QPen(Qt.PenStyle.NoPen)
        )

        centre = largeur * self._phase

        demi = largeur * 0.35

        degrade = QLinearGradient(
            QPointF(centre - demi, 0.0),
            QPointF(centre + demi, 0.0)
        )

        degrade.setColorAt(
            0.0,
            QColor(r, v, b, 0)
        )

        degrade.setColorAt(
            0.5,
            QColor(r, v, b, alpha)
        )

        degrade.setColorAt(
            1.0,
            QColor(r, v, b, 0)
        )

        peintre.setBrush(QBrush(degrade))

        peintre.save()

        peintre.translate(centre, hauteur / 2.0)

        peintre.rotate(-8.0)

        peintre.drawRect(
            QRectF(
                -demi,
                -hauteur,
                demi * 2.0,
                hauteur * 2.0
            )
        )

        peintre.restore()


class StepperBar(QWidget):
    """
    Stepper horizontal : une pastille par étape —
    ICÔNE de l'étape + libellé, couleur selon
    l'état (série 8 : plus de numéros).

    ``etape_cliquee`` est émis avec la clé de
    l'étape (navigation directe de la page
    Réunion ; le hub ignore le signal).

    Une pastille CLIQUABLE porte le reflet de
    survol de la série 7 (§30) ; une pastille
    sans lien individuel reste entièrement
    statique (invariant 16).
    """

    etape_cliquee = Signal(str)

    def __init__(
        self,
        etapes=ETAPES_REUNION,
        optionnelles=ETAPES_OPTIONNELLES,
        cliquable=True,
        compact=False,
        parent=None
    ):
        super().__init__(parent)

        self.etapes = tuple(etapes)
        self.optionnelles = tuple(optionnelles)
        self._compact = compact
        self._cliquable = cliquable

        self.setObjectName("stepper_reunion")

        self._etats = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.boutons = {}

        for etape in self.etapes:

            bouton = QPushButton(
                LIBELLES_ETAPES[etape]
            )

            police = QFont(self.font())

            if compact:
                police.setPixelSize(10)
            else:
                police.setPixelSize(12)

            bouton.setFont(police)

            bouton.setFlat(True)

            bouton.setStyleSheet(
                self._style(etape, A_FAIRE)
            )

            if etape in self.optionnelles:
                bouton.setToolTip(
                    "Étape optionnelle"
                )

            if cliquable:

                #
                # Série 7 (§30) : curseur main sur
                # toute pastille réellement
                # cliquable, reflet translucide au
                # survol — UNE passe, teinte de
                # l'état, contour assorti.
                #
                bouton.setCursor(
                    Qt.CursorShape
                    .PointingHandCursor
                )

                bouton._reflet = RefletPastille(
                    bouton
                )

                bouton.enterEvent = (
                    lambda evenement,
                    b=bouton,
                    e=etape: (
                        self._sur_entree(b, e)
                    )
                )

                bouton.leaveEvent = (
                    lambda evenement,
                    b=bouton,
                    e=etape: (
                        self._sur_sortie(b, e)
                    )
                )

                bouton.clicked.connect(
                    lambda checked=False,
                    cle=etape: (
                        self.etape_cliquee.emit(
                            cle
                        )
                    )
                )

            else:

                #
                # Sans lien individuel : ENTÈREMENT
                # statique (invariant 16) — ni
                # balayage, ni contour, ni curseur
                # main ; pas d'info-bulle en
                # compact (elle doublait le
                # libellé).
                #
                bouton.setDisabled(True)

                if compact:
                    bouton.setToolTip(None)

            self._poser_icone(
                bouton,
                etape,
                A_FAIRE
            )

            layout.addWidget(bouton)

            self.boutons[etape] = bouton

        layout.addStretch()

        #
        # La taille VERROUILLÉE (série 7-bis :
        # steppers alignés) : la barre ne dépasse
        # jamais ses pastilles.
        #
        self.setSizePolicy(
            QSizePolicy.Policy.Maximum,
            QSizePolicy.Policy.Fixed,
        )

    def _style(
        self,
        etape: str,
        etat: str,
        survol: bool = False
    ) -> str:
        """
        Feuille de style d'une pastille : couleur
        d'état du thème courant ; au survol d'une
        pastille CLIQUABLE, léger contour ASSORTI
        à l'état (§30) — l'état et ses couleurs ne
        sont JAMAIS modifiés par le survol.
        """

        bord = None

        if survol:

            r, v, b = _teinte_survol(etat)

            bord = f"rgba({r},{v},{b},120)"

        style = _style_etat(
            etat,
            est_sombre(self),
            couleur_bord=bord
        )

        return (
            style
            + "border-radius: 10px;"
            "padding: 1px 8px;"
            + (
                #
                # Hauteur pleine taille calée sur les
                # boutons d'icones voisins (ICON_
                # BUTTON_HEIGHT = 25 px dans services/
                # icons.py : 21 + 2x1 de padding + 2x1
                # de bordure) — le stepper partage la
                # ligne avec la barre d'outils (retour
                # David 31/10).
                #
                "min-height: 21px;"
                if not self._compact
                else ""
            )
            + "font-size: "
            + ("10px" if self._compact else "12px")
            + ";"
        )

    def _poser_icone(
        self,
        bouton,
        etape: str,
        etat: str
    ):
        """
        Icône de l'étape (série 8), recolorée à la
        couleur de TEXTE de l'état — l'icône suit
        toujours son pastille.
        """

        from services.icons import (
            make_tinted_icon
        )
        from services.theme_manager import (
            couleurs_stepper
        )

        chemin = ICONES_ETAPES.get(etape)

        if not chemin:
            bouton.setIcon(QIcon())
            return

        couleurs = couleurs_stepper(
            est_sombre(self)
        )

        texte = {
            A_FAIRE: couleurs[
                "a_faire_texte"
            ],
            EN_COURS: couleurs[
                "en_cours_texte"
            ],
            TERMINE: couleurs[
                "fait_texte"
            ],
        }.get(etat, couleurs["a_faire_texte"])

        bouton.setIcon(
            make_tinted_icon(
                texte,
                chemin,
                14,
                bouton.devicePixelRatioF()
            )
        )

        bouton.setIconSize(QSize(14, 14))

    def _sur_entree(self, bouton, etape):
        """
        Entrée de survol d'une pastille cliquable :
        contour assorti + LE reflet translucide en
        UNE passe (rejoué à chaque entrée).
        """

        etat = self._etats.get(etape, A_FAIRE)

        bouton.setStyleSheet(
            self._style(etape, etat, survol=True)
        )

        teinte = _teinte_survol(etat)

        try:
            bouton._reflet.jouer(teinte)
        except Exception:
            #
            # Repli (§30) : si l'animation n'est pas
            # supportée, le contour assorti seul
            # demeure — jamais de dégradation
            # bloquante.
            #
            pass

    def _sur_sortie(self, bouton, etape):
        """
        Sortie de survol : retour discret ~120 ms
        (le contour disparaît, l'état reprend).
        """

        etat = self._etats.get(etape, A_FAIRE)

        #
        # Retour discret ~120 ms (§30) : le
        # contour disparaît, l'état reprend.
        #
        retour = QVariantAnimation(bouton)

        retour.setDuration(120)

        retour.setStartValue(0.0)
        retour.setEndValue(1.0)

        retour.finished.connect(
            lambda: bouton.setStyleSheet(
                self._style(etape, etat)
            )
        )

        retour.start()

        try:
            bouton._reflet.hide()
        except Exception:
            pass

    def definir_etats(self, etats: dict):
        """
        Met à jour la couleur et l'icône de chaque
        pastille (états du service d'avancement ;
        une étape absente repasse à faire).
        """

        self._etats = dict(etats or {})

        for etape, bouton in (
            self.boutons.items()
        ):

            etat = etats.get(etape, A_FAIRE)

            bouton.setStyleSheet(
                self._style(etape, etat)
            )

            self._poser_icone(
                bouton,
                etape,
                etat
            )

    @property
    def isCompact(self) -> bool:
        return getattr(self, "_compact", False)

    def sur_changement_theme(self):
        """
        Broadcast de ThemeManager : rejoue les
        styles ET les icones dans le theme courant —
        sinon les pastilles gardaient les couleurs
        du theme precedent jusqu'au survol (retour
        David 31/10).
        """

        self.definir_etats(self._etats)
