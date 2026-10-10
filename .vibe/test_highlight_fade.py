# Test fonctionnel hors-ecran du surlignage ExtraSelections + fondu
import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, r"C:\Users\d_fre\Documents\Biblique\elevenlabs speech to text\TranscriptStudio_dev")

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QTextCursor

from models.project import Project
from models.speaker import Speaker
from models.word import Word
from models.block import Block
from ui.block_widget import BlockWidget, HIGHLIGHT_FADE_OUT_MS


def build_project():
    words = [
        Word(text="Bonjour", start=0.0, end=1.0, speaker_id="speaker_1", item_type="word"),
        Word(text=" ", start=1.0, end=1.0, speaker_id="speaker_1", item_type="spacing"),
        Word(text="tout", start=1.0, end=1.5, speaker_id="speaker_1", item_type="word"),
        Word(text=" ", start=1.5, end=1.5, speaker_id="speaker_1", item_type="spacing"),
        Word(text="le", start=1.5, end=1.8, speaker_id="speaker_1", item_type="word"),
        Word(text=" ", start=1.8, end=1.8, speaker_id="speaker_1", item_type="spacing"),
        Word(text="monde", start=1.8, end=2.5, speaker_id="speaker_1", item_type="word"),
    ]
    block = Block(
        id=1,
        speaker_id="speaker_1",
        start_word=0,
        end_word=len(words) - 1,
        created_by_user=False,
    )
    return Project(
        project_file="test.sttproj",
        modified=False,
        name="T",
        audio_file="a.wav",
        transcription_id="t",
        language_code="fr",
        duration_seconds=10.0,
        speakers=[Speaker(id="speaker_1", name="Alice", color="#FF0000")],
        words=words,
        blocks=[block],
        original_elevenlabs_response={},
        project_format_version=1,
    ), block, words


def pump(app, ms):
    t0 = time.monotonic()
    while (time.monotonic() - t0) * 1000 < ms:
        app.processEvents()
        time.sleep(0.004)


def selected_text(widget, word_index):
    span = widget.word_positions[word_index]
    cursor = QTextCursor(widget.text_edit.document())
    cursor.setPosition(span[0])
    cursor.setPosition(span[1], QTextCursor.MoveMode.KeepAnchor)
    return cursor.selectedText()


app = QApplication([])
project, block, words = build_project()
w = BlockWidget(project, block, ["Alice"], "Alice")
w.show()

# 1. Cartographie des ancres : chaque mot reel possede une region
# couvrant son texte et l'espace qui suit (sauf le dernier du bloc)
assert set(w.word_positions.keys()) == {0, 2, 4, 6}, w.word_positions.keys()
assert selected_text(w, 0) == "Bonjour", repr(selected_text(w, 0))
for idx in (2, 4, 6):
    assert selected_text(w, idx) == " " + words[idx].text, (idx, repr(selected_text(w, idx)))
print("MAP_OK")

# 2. Fondu entrant : mot 2 actif
w.set_active_word(2)
assert w.highlight_alphas.get(2, 0) == 0, "depart du fondu attendu a 0"
pump(app, 150)
assert w.highlight_alphas[2] == 255, w.highlight_alphas
sels = w.text_edit.extraSelections()
assert len(sels) == 1, len(sels)
cur = sels[0].cursor
assert cur.selectedText() == " tout"
print("FADE_IN_OK")

# 3. Changement de mot : fondu sortant sur 2, entrant sur 4
w.set_active_word(4)
# prelevement a mi-parcours du fondu sortant (le plus long) ;
# le fondu entrant, plus court, peut deja etre termine
pump(app, min(60, max(2, HIGHLIGHT_FADE_OUT_MS // 3)))
a2 = w.highlight_alphas.get(2, 255)
a4 = w.highlight_alphas.get(4, 0)
assert 0 < a2 < 255, ("fondu sortant en cours", a2)
assert 0 < a4 <= 255, ("fondu entrant demarre", a4)
pump(app, HIGHLIGHT_FADE_OUT_MS + 200)
assert w.highlight_alphas == {4: 255}, w.highlight_alphas
sels = w.text_edit.extraSelections()
assert len(sels) == 1 and sels[0].cursor.selectedText() == " le"
print("TRANSITION_OK")

# 4. Scrubbing arriere : mot 4 en fin de fondu sortant redevient actif
w.set_active_word(4)  # no-op attendu
w.set_active_word(2)
pump(app, 200)
w.set_active_word(4)  # interruption du fondu sortant de 4
pump(app, HIGHLIGHT_FADE_OUT_MS + 200)
assert w.highlight_alphas == {4: 255}, w.highlight_alphas
assert len(w.text_edit.extraSelections()) == 1
print("SCRUB_OK")

# 5. Desactivation : tout disparait apres le fondu sortant
w.set_active_word(None)
pump(app, HIGHLIGHT_FADE_OUT_MS + 200)
assert w.highlight_alphas == {}, w.highlight_alphas
assert w.text_edit.extraSelections() == []
print("FADE_OUT_OK")

# 5b. Transitions rapides (mots plus courts que le fondu sortant) :
# chaque mot garde son fondu complet, plusieurs mots peuvent
# s'effacer simultanement, et aucune remanence ne s'accumule
import random
random.seed(7)
indices = [i for i in w.word_positions.keys() if i % 2 == 0]
max_concurrent = 0
for idx in indices:
    w.set_active_word(None)
    w.set_active_word(idx)
    pump(app, random.choice([60, 90, 120, 150]))
    max_concurrent = max(max_concurrent, len(w.highlight_alphas))
pump(app, HIGHLIGHT_FADE_OUT_MS + 200)
assert w.highlight_alphas == {indices[-1]: 255}, w.highlight_alphas
assert len(w.text_edit.extraSelections()) == 1
assert w.fade_out_anims == {}, w.fade_out_anims
print("RAPID_OK (max simultane:", max_concurrent, ")")
assert max_concurrent >= 2, ("fondus simultanes attendus", max_concurrent)

# 5c. Verifications internes apres drain : plus d'animation
# sortante residuelle ni d'entree d'alpha orpheline
assert w.fade_in_word == indices[-1]

# 6. Re-render (changement de taille) : le mot actif est reaplique sans animation
w.set_active_word(2)
pump(app, 150)
w.set_text_font_size(20)
assert w.highlight_alphas == {2: 255}, w.highlight_alphas
assert len(w.text_edit.extraSelections()) == 1
assert selected_text(w, 2) == " tout"
print("RERENDER_OK")

# 7. Ancres intactes (clic souris)
doc = w.text_edit.document()
found = []
b = doc.firstBlock()
while b.isValid():
    it = b.begin()
    while not it.atEnd():
        href = it.fragment().charFormat().anchorHref()
        if href.startswith("word_"):
            found.append(int(href[5:]))
        it += 1
    b = b.next()
assert found == [0, 2, 4, 6], found
print("ANCHORS_OK")

# 8. Regions avec ponctuation et guillemets
# items : Rome. | : | « | nous | », | dit
punct_words = [
    Word(text="Rome.", start=0.0, end=0.5, speaker_id="speaker_1", item_type="word"),
    Word(text=" ", start=0.5, end=0.6, speaker_id="speaker_1", item_type="spacing"),
    Word(text=":", start=0.6, end=0.7, speaker_id="speaker_1", item_type="word"),
    Word(text=" ", start=0.7, end=0.8, speaker_id="speaker_1", item_type="spacing"),
    Word(text="«", start=0.8, end=0.9, speaker_id="speaker_1", item_type="word"),
    Word(text=" ", start=0.9, end=1.0, speaker_id="speaker_1", item_type="spacing"),
    Word(text="nous", start=1.0, end=1.4, speaker_id="speaker_1", item_type="word"),
    Word(text=" ", start=1.4, end=1.5, speaker_id="speaker_1", item_type="spacing"),
    Word(text="»,", start=1.5, end=1.7, speaker_id="speaker_1", item_type="word"),
    Word(text=" ", start=1.7, end=1.8, speaker_id="speaker_1", item_type="spacing"),
    Word(text="dit", start=1.8, end=2.0, speaker_id="speaker_1", item_type="word"),
]
punct_block = Block(
    id=2, speaker_id="speaker_1", start_word=0,
    end_word=len(punct_words) - 1, created_by_user=False,
)
punct_project = Project(
    project_file="p.sttproj", modified=False, name="P", audio_file="a.wav",
    transcription_id="t", language_code="fr", duration_seconds=10.0,
    speakers=[Speaker(id="speaker_1", name="Alice", color="#FF0000")],
    words=punct_words, blocks=[punct_block],
    original_elevenlabs_response={}, project_format_version=1,
)
w2 = BlockWidget(punct_project, punct_block, ["Alice"], "Alice")
w2.show()

# seuls les mots reels ont une region
assert set(w2.word_positions.keys()) == {0, 6, 10}, w2.word_positions.keys()

def region_text(widget, idx):
    span = widget.word_positions[idx]
    c = QTextCursor(widget.text_edit.document())
    c.setPosition(span[0])
    c.setPosition(span[1], QTextCursor.MoveMode.KeepAnchor)
    return c.selectedText()

# "Rome." possede sa ponctuation attachee et le deux-points isole,
# mais l'espace qui suit appartient au mot suivant
assert region_text(w2, 0) == "Rome. :", repr(region_text(w2, 0))
# "nous" demarre par l'espace apres le deux-points, couvre le guillemet
# ouvrant, le mot, le fermant », et sa ponctuation
assert region_text(w2, 6) == " « nous »,", repr(region_text(w2, 6))
# dernier mot : espace d'entree + texte
assert region_text(w2, 10) == " dit", repr(region_text(w2, 10))

# un item pur (guillemet) comme mot actif : rien a surligner,
# pas d'entree dans le dictionnaire des regions
w2.set_active_word(4)
assert w2.highlight_alphas == {}, w2.highlight_alphas
w2.set_active_word(6)
pump(app, 150)
assert w2.highlight_alphas == {6: 255}, w2.highlight_alphas
assert len(w2.text_edit.extraSelections()) == 1
print("PUNCT_OK")

print("ALL_OK")
