# ui/block_widget.py
import functools


from PySide6.QtWidgets import (
    QMenu,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QTextBrowser,
    QTextEdit,
    QComboBox,
    QLabel,
    QInputDialog,
    QPushButton,
    QLineEdit,
    QSizePolicy,
)

from PySide6.QtGui import (
    QColor,
    QCursor,
    QTextCursor,
)
from PySide6.QtCore import (
    Qt,
    QSize,
    QEasingCurve,
    QVariantAnimation,
    Signal,
)

from services.icons import make_tinted_icon


def make_speaker_icon(
    color,
    size,
    device_pixel_ratio=2.0
):
    """Retourne l'icône user.svg teintée avec la couleur du speaker."""

    return make_tinted_icon(
        color,
        "icons/user.svg",
        size,
        device_pixel_ratio
    )


# Couleurs de surlignage : chaque constante
# accepte un tuple (r, g, b) ou une couleur
# hex "#rrggbb".
HIGHLIGHT_COLOR = "#FFE06E"

# Variante assombrie du jaune pour le theme
# sombre : meme teinte, assez foncee pour que
# le texte clair du theme reste lisible
# dessus. Le texte ne change jamais de
# couleur : la selection ne peint que le fond.
HIGHLIGHT_COLOR_DARK = "#007812"


def make_highlight_color(color_spec):
    """Construit une QColor depuis un tuple
    (r, g, b) ou une couleur hex "#rrggbb"."""

    if isinstance(color_spec, str):

        return QColor(color_spec)

    return QColor(
        color_spec[0],
        color_spec[1],
        color_spec[2]
    )

HIGHLIGHT_FADE_IN_MS = 10

HIGHLIGHT_FADE_OUT_MS = 1000

# Caracteres regroupes avec le mot suivant
# (guillemets ouvrants, parentheses ouvrantes).
HIGHLIGHT_OPENING_CHARS = "«([“"

# Caracteres regroupes avec le mot precedent
# (guillemets fermants, parentheses fermantes
# et ponctuation isolee : . , ; : ! ? ...).
HIGHLIGHT_CLOSING_CHARS = "»)]”\',.;:!?…"


def make_word_html(word_index, text):

    return (
        f'<a href="word_{word_index}">'
        f'{text}'
        '</a>'
    )

class BlockWidget(QWidget):

    word_clicked = Signal(int)

    speaker_changed = Signal(
        int,     # block_id
        str      # speaker_id
    )

    rename_speaker_requested = Signal(
        str,  # speaker_id
        str   # nouveau nom
    )
    split_before_requested = Signal(
        int,   # block_id
        int    # word_index
    )

    split_after_requested = Signal(
        int,
        int
    )

    edit_word_requested = Signal(int)
    word_double_clicked = Signal(int)
    new_speaker_requested = Signal(int)

    def __init__(
        self,
        project,
        block,
        speaker_names,
        current_speaker_name,
        text_font_size=15,
        parent=None
    ):
        super().__init__(parent)

        self.project = project
        self.block = block

        self.active_word = None
        self.last_clicked_word = None

        # Surlignage du mot actif : positions
        # des ancres dans le document, alphas
        # courants des fonds en cours de fondu
        # et animations de fondu sortant (une
        # par mot, pour laisser chaque mot
        # s'effacer sur toute sa durée).
        self.word_positions = {}
        self.highlight_alphas = {}
        self.fade_in_word = None
        self.fade_out_anims = {}

        self.text_font_size = (
            text_font_size
        )
        # Layout principal
        root_layout = QHBoxLayout(self)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Maximum
        )
        root_layout.setContentsMargins(4,2,4,2)

        # Colonne speaker
        self.speaker_widget = QWidget()

        speaker_layout = QHBoxLayout(
            self.speaker_widget
        )

        self.speaker_widget.setFixedWidth(
            180
        )

        # Speaker courant
        speaker = self.project.get_speaker_by_id(
            self.block.speaker_id
        )

        # Icône couleur
        self.color_button = QPushButton()

        self.color_button.setFixedSize(18, 18)

        self.color_button.setFlat(True)

        self.color_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.color_button.setIcon(
            make_speaker_icon(
                speaker.color,
                18,
                self.color_button.devicePixelRatioF()
            )
        )

        self.color_button.setIconSize(
            QSize(18, 18)
        )

        # Nom affiché
        self.speaker_name_edit = QLineEdit(
            current_speaker_name
        )

        self.speaker_name_edit.setStyleSheet("""
            font-weight:bold;
            font-size:13px;
            border:none;
            background:transparent;
        """)
        self.speaker_name_edit.setReadOnly(True)


        # Combo caché
        self.speaker_combo = QComboBox()

        self.speaker_combo.addItems(
            speaker_names
        )

        self.speaker_combo.setCurrentText(
            current_speaker_name
        )

        self.speaker_combo.hide()

        # Texte
        self.text_edit = QTextBrowser()

        self.text_edit.document().setDocumentMargin(0)

        self.text_edit.setOpenLinks(False)

        self.text_edit.setFrameShape(
            QTextBrowser.Shape.NoFrame
        )

        self.text_edit.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.text_edit.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.text_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )

        self.text_edit.setStyleSheet("""
            border:none;
            background:transparent;
            padding:0px;
            margin:0px;
        """)

        self.text_edit.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )

        self.text_edit.customContextMenuRequested.connect(
            self.show_context_menu
        )
        
        # Construction UI
        speaker_layout.addWidget(self.color_button)

        speaker_layout.addWidget(
            self.speaker_name_edit
        )

        # speaker_layout.addStretch()
        speaker_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        speaker_layout.setSpacing(4)
        root_layout.addWidget(
            self.speaker_widget,
            alignment=Qt.AlignmentFlag.AlignTop
        )

        root_layout.addWidget(
            self.text_edit,
            1
        )
        self.speaker_name_edit.mouseDoubleClickEvent = (
            self.start_rename_speaker
        )

        self.speaker_name_edit.editingFinished.connect(
            self.finish_rename_speaker
        )
        # Connexions
        self.text_edit.anchorClicked.connect(
            self.on_word_clicked
        )

        self.speaker_combo.currentTextChanged.connect(
            self.on_speaker_changed
        )

        # Interactions futures
        self.color_button.clicked.connect(
            self.color_clicked
        )

        # self.speaker_name_label.mouseDoubleClickEvent = (
        #     self.rename_speaker
        # )

        # Animation de fondu entrant du mot actif.
        # Les fondus sortants sont créés à la
        # demande, un par mot, dans start_fade_out.
        self.fade_in_anim = QVariantAnimation(self)
        self.fade_in_anim.setDuration(
            HIGHLIGHT_FADE_IN_MS
        )
        self.fade_in_anim.setEasingCurve(
            QEasingCurve.Type.OutQuad
        )
        self.fade_in_anim.valueChanged.connect(
            self.on_fade_in_value
        )

        # Rendu initial
        self.render_words()
       
    def set_active(self, active: bool):
        pass
        # if active:

        #     self.setStyleSheet("""
        #         QWidget {
        #             background-color: #FFF8D6;
        #             border: 2px solid #F5A623;
        #             border-radius: 8px;
        #         }
        #     """)

        # else:

        #     self.setStyleSheet("")

    def render_words(self):
        text_color = (
            self.text_edit
            .palette()
            .text()
            .color()
            .name()
        )
        items = self.project.get_block_items(
            self.block
        )

        html = ""

        for local_index, item in enumerate(items):
            if item.is_deleted:
                continue

            global_index = (
                self.block.start_word
                + local_index
            )

            if item.item_type == "spacing":

                html += item.text

            else:
                html += make_word_html(
                    global_index,
                    item.text
                )

        html = f"""
        <html>
        <head>
        <style>
        body {{
            margin: 0px;
            padding: 0px;
            width: 100%;
            font-size: {self.text_font_size}px;
        }}

        a {{
            color: {text_color};
            text-decoration: none;
        }}
        </style>
        </head>
        <body>
        {html}
        </body>
        </html>
        """

        self.text_edit.setHtml(html)

        self.map_word_positions()

        self.reset_highlights()

    def set_text_font_size(
        self,
        size
    ):
        self.text_font_size = (
            size
        )

        self.render_words()

        self.update_text_height()
    
    def on_word_clicked(self, url):
        
        word_index = int(url.toString().replace("word_",""))
        self.word_clicked.emit(word_index)
        self.last_clicked_word = word_index

    def set_active_word(
        self,
        global_word_index
    ):

        if self.active_word == global_word_index:
            return

        previous_word = self.active_word

        self.active_word = global_word_index

        if previous_word is not None:
            self.start_fade_out(previous_word)

        if global_word_index is None:
            return

        if global_word_index in self.word_positions:
            self.start_fade_in(global_word_index)

    def start_fade_in(
        self,
        word_index
    ):

        self.fade_in_word = word_index

        self.fade_in_anim.stop()

        current_alpha = (
            self.highlight_alphas.get(word_index, 0)
        )

        # Si le mot etait en cours de fondu
        # sortant, celui-ci est interrompu :
        # le fondu entrant reprend depuis
        # l'alpha courant.
        old_anim = (
            self.fade_out_anims.pop(
                word_index,
                None
            )
        )

        if old_anim is not None:

            old_anim.stop()

            old_anim.deleteLater()

        self.highlight_alphas[word_index] = current_alpha

        self.fade_in_anim.setStartValue(current_alpha)

        self.fade_in_anim.setEndValue(255)

        self.fade_in_anim.start()

        self.apply_highlights()

    def start_fade_out(
        self,
        word_index
    ):

        if self.fade_in_word == word_index:

            self.fade_in_anim.stop()

            self.fade_in_word = None

        # Rien a effacer si le mot n'a jamais ete
        # surligne (ponctuation isolee sans region,
        # mot d'un autre bloc) : sans ce retour,
        # un fondu fantome partirait de l'alpha
        # par defaut.
        if (

            word_index not in self.highlight_alphas

            or self.highlight_alphas[word_index] <= 0

        ):

            return

        # Un mot actif ne peut pas avoir de fondu
        # sortant en cours, mais par precaution,
        # toute animation restante pour ce mot
        # est remplacee.
        old_anim = (
            self.fade_out_anims.get(
                word_index
            )
        )

        if old_anim is not None:

            old_anim.stop()

            old_anim.deleteLater()

        current_alpha = (
            self.highlight_alphas.get(word_index, 255)
        )

        # Chaque mot quitte le surlignage avec sa
        # propre animation : en lecture rapide,
        # plusieurs mots s'effacent simultanement
        # plutôt que de disparaitre brutalement.
        anim = QVariantAnimation(self)

        anim.setDuration(
            HIGHLIGHT_FADE_OUT_MS
        )

        anim.setEasingCurve(
            QEasingCurve.Type.OutQuad
        )

        anim.setStartValue(current_alpha)

        anim.setEndValue(0)

        anim.valueChanged.connect(
            functools.partial(
                self.on_fade_out_value,
                word_index
            )
        )

        anim.finished.connect(
            functools.partial(
                self.on_fade_out_finished,
                word_index
            )
        )

        self.fade_out_anims[word_index] = anim

        anim.start()

        self.apply_highlights()

    def on_fade_in_value(self, value):

        if self.fade_in_word is None:
            return

        self.highlight_alphas[self.fade_in_word] = value

        self.apply_highlights()

    def on_fade_out_value(
        self,
        word_index,
        value
    ):

        self.highlight_alphas[word_index] = value

        self.apply_highlights()

    def on_fade_out_finished(
        self,
        word_index
    ):

        anim = self.fade_out_anims.pop(
            word_index,
            None
        )

        if anim is not None:

            anim.deleteLater()

        self.highlight_alphas.pop(
            word_index,
            None
        )

        self.apply_highlights()

    def map_word_positions(self):

        self.word_positions = {}

        document = self.text_edit.document()

        items = []

        block = document.firstBlock()

        while block.isValid():

            iterator = block.begin()

            while not iterator.atEnd():

                fragment = iterator.fragment()

                href = (
                    fragment
                    .charFormat()
                    .anchorHref()
                )

                if href.startswith("word_"):

                    items.append(
                        {
                            'index': int(href[5:]),
                            'start': fragment.position(),
                            'end': (
                                fragment.position()
                                + fragment.length()
                            ),
                            'text': fragment.text()
                        }
                    )

                iterator += 1

            block = block.next()

        # Classification de chaque item :
        # - caracteres fermants/ponctuation en
        #   tete -> regroupes avec le mot precedent ;
        # - caracteres ouvrants en fin -> regroupes
        #   avec le mot suivant ;
        # - un item sans coeur alphanumerique est
        #   un item "pur" (ponctuation isolee ou
        #   guillemet autonome), integre a un voisin.
        for item in items:

            text = item['text']

            length = len(text)

            lead = 0

            while (
                lead < length
                and text[lead] in HIGHLIGHT_CLOSING_CHARS
            ):
                lead += 1

            trail = 0

            while (
                trail < length - lead
                and text[length - 1 - trail] in HIGHLIGHT_OPENING_CHARS
            ):
                trail += 1

            item['lead'] = lead

            item['trail'] = trail

            item['has_core'] = (
                item['end'] - item['start']
                > lead + trail
            )

            item['pure_opening'] = (
                not item['has_core']
                and length > 0
                and text[length - 1] in HIGHLIGHT_OPENING_CHARS
            )

        real_positions = [
            position
            for position, item in enumerate(items)
            if item['has_core']
        ]

        # Fin du "groupe" d'un mot reel : son texte
        # (hors guillemets ouvrants finaux, donnes
        # au mot suivant) etendu sur la ponctuation
        # isolee fermante qui le suit. L'espace
        # qui suit le groupe appartient au mot
        # suivant.
        group_ends = {}

        for position in real_positions:

            item = items[position]

            group_end = (
                item['end'] - item['trail']
            )

            follower = position + 1

            while (
                follower < len(items)

                and not items[follower]['has_core']

                and not items[follower]['pure_opening']
            ):
                group_end = items[follower]['end']
                follower += 1

            group_ends[position] = group_end

        # Region d'un mot reel : de la fin du
        # groupe du mot reel precedent (espace
        # d'entree compris) jusqu'a sa propre fin
        # de groupe. Les regions sont contigues :
        # chaque espace d'inter-mots est colore
        # avec le mot qui le suit. Le premier mot
        # reel demarre aux guillemets ouvrants
        # places avant lui, s'il y en a.
        previous_region_end = None

        for order, position in enumerate(real_positions):

            item = items[position]

            if previous_region_end is not None:

                region_start = previous_region_end

            else:

                region_start = (
                    item['start'] + item['lead']
                )

                previous = position - 1

                while (
                    previous >= 0
                    and items[previous]['pure_opening']
                ):
                    region_start = items[previous]['start']
                    previous -= 1

            if order + 1 < len(real_positions):

                next_real = (
                    real_positions[order + 1]
                )

                next_item = items[next_real]

                # Une ponctuation fermante colle en
                # tete du mot suivant ("»Le") reste
                # groupee avec le mot precedent : la
                # region s'etend jusqu'au bout de
                # cette ponctuation.
                if next_item['lead'] > 0:

                    region_end = (
                        next_item['start']
                        + next_item['lead']
                    )

                else:

                    region_end = group_ends[position]

            else:

                region_end = group_ends[position]

            self.word_positions[item['index']] = (
                region_start,
                region_end
            )

            previous_region_end = region_end

    def reset_highlights(self):

        self.fade_in_anim.stop()

        self.fade_in_word = None

        for anim in self.fade_out_anims.values():

            anim.stop()

            anim.deleteLater()

        self.fade_out_anims.clear()

        self.highlight_alphas.clear()

        if self.active_word in self.word_positions:
            self.highlight_alphas[self.active_word] = 255

        self.apply_highlights()

    def apply_highlights(self):

        selections = []

        document = self.text_edit.document()

        # Detection du theme par la couleur de
        # texte : le theme sombre affiche un texte
        # clair. Le role Window du widget n'est pas
        # utilisable (ecrase par sa stylesheet).
        # En theme sombre, le jaune du theme clair
        # laisserait un fond trop clair : on
        # utilise la variante assombrie de la meme
        # teinte. Le texte garde en permanence la
        # couleur du theme.
        base_text_color = (
            self.text_edit
            .palette()
            .text()
            .color()
        )

        text_luminance = (
            0.299 * base_text_color.red()
            + 0.587 * base_text_color.green()
            + 0.114 * base_text_color.blue()
        )

        if text_luminance > 127:

            highlight = make_highlight_color(
                HIGHLIGHT_COLOR_DARK
            )

        else:

            highlight = make_highlight_color(
                HIGHLIGHT_COLOR
            )

        for word_index, alpha in self.highlight_alphas.items():

            if alpha <= 0:
                continue

            span = self.word_positions.get(word_index)

            if span is None:
                continue

            selection = QTextEdit.ExtraSelection()

            selection.cursor = QTextCursor(document)

            selection.cursor.setPosition(span[0])

            selection.cursor.setPosition(
                span[1],
                QTextCursor.MoveMode.KeepAnchor
            )

            background = QColor(highlight)

            background.setAlpha(int(alpha))

            selection.format.setBackground(
                background
            )

            # La couleur du texte n'est jamais
            # modifiee : la selection ne peint
            # que le fond, le texte garde la
            # couleur du theme.

            selections.append(selection)

        self.text_edit.setExtraSelections(selections)

    def on_speaker_changed(
        self,
        speaker_name
    ):

        self.speaker_changed.emit(
            self.block.id,
            speaker_name
        )

    def color_clicked(self):

        menu = QMenu(self)

        for speaker in self.project.speakers:

            action = menu.addAction(
                speaker.name
            )

            action.setData(
                speaker.id
            )

        menu.addSeparator()

        new_speaker_action = menu.addAction(
            "+ Nouvel intervenant..."
        )

        action = menu.exec(
            self.color_button.mapToGlobal(
                self.color_button.rect().bottomLeft()
            )
        )

        if not action:
            return

        if action == new_speaker_action:

            self.new_speaker_requested.emit(self.block.id)

            return

        speaker_id = action.data()

        self.speaker_changed.emit(
        self.block.id,
        speaker_id
    )

    def rename_speaker(self, event):

        self.rename_speaker_requested.emit(
            self.block.speaker_id
        )

    def show_word_menu(self, word_index):
        menu = QMenu(self)
        split_before_action = menu.addAction(
            "Split avant le mot"
        )

        split_after_action = menu.addAction(
            "Split après le mot"
        )

        action = menu.exec(
            QCursor.pos()
        )
        if action == split_before_action:

            self.split_before_requested.emit(
                self.block.id,
                word_index
            )

        elif action == split_after_action:

            self.split_after_requested.emit(
                self.block.id,
                word_index
            )    

    def show_context_menu(self, pos):
        if self.last_clicked_word is None:
            return

        menu = QMenu(self)

        edit_action = menu.addAction(
            "Modifier le mot"
        )

        menu.addSeparator()

        split_before_action = menu.addAction(
            "Split avant le mot"
        )

        split_after_action = menu.addAction(
            "Split après le mot"
        )

        action = menu.exec(
            QCursor.pos()
        )

        if action == edit_action:

            self.edit_word_requested.emit(
                self.last_clicked_word
            )

        elif action == split_before_action:

            self.split_before_requested.emit(
                self.block.id,
                self.last_clicked_word
            )

        elif action == split_after_action:

            self.split_after_requested.emit(
                self.block.id,
                self.last_clicked_word
            )

    def start_rename_speaker(
        self,
        event
    ):

        self.speaker_name_edit.setReadOnly(
            False
        )

        self.speaker_name_edit.selectAll()

        self.speaker_name_edit.setFocus()

    def finish_rename_speaker(self):

        self.speaker_name_edit.setReadOnly(
            True
        )

        self.rename_speaker_requested.emit(
            self.block.speaker_id,
            self.speaker_name_edit.text()
        )

    def update_text_height(self):

        document = self.text_edit.document()

        # document.setTextWidth(
        #     self.text_edit.viewport().width()
        # )

        # document.adjustSize()

        height = (
            document.size().height()
            + 10
        )

        self.text_edit.setFixedHeight(
            int(height)
        )

    def resizeEvent(self, event):

        super().resizeEvent(event)

        self.update_text_height()