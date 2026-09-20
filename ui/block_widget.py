# ui/block_widget.py

from PySide6.QtWidgets import (
    QMenu,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QTextBrowser,
    QComboBox,
    QLabel,
    QInputDialog,
    QPushButton,
    QLineEdit,
    QSizePolicy,
)

from PySide6.QtGui import QCursor
from PySide6.QtCore import Qt, Signal

def make_word_html(word_index, text, active=False):

    link_start = (
        f'<a href="word_{word_index}">'
    )

    link_end = '</a>'

    span_start = (
        '<span style="'
        'background-color:#FFD54F;'
        'font-weight:bold;'
        'color:black;'
        'border-radius:3px;'
        'padding:1px;'
        '">'
    )

    span_end = '</span>'

    if active:

        return (
            link_start
            + span_start
            + text
            + span_end
            + link_end
        )

    return (
        link_start
        + text
        + link_end
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
        parent=None
    ):
        super().__init__(parent)

        self.project = project
        self.block = block

        self.active_word = None
        self.last_clicked_word = None
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

        self.color_button.setStyleSheet(
            f"""
            QPushButton {{
                background-color:{speaker.color};
                border-radius:9px;
                border:none;
            }}
            """
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
                    item.text,
                    global_index == self.active_word)

        html = f"""
        <html>
        <head>
        <style>
        body {{
            margin: 0px;
            padding: 0px;
            width: 100%;
        }}

        a {{
            color: black;
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

        self.active_word = global_word_index
        

        self.render_words()

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