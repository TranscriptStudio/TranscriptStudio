# Repro remanence : transitions rapides + interruption de fondus sortants
import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, r"C:\Users\d_fre\Documents\Biblique\elevenlabs speech to text\TranscriptStudio_dev")

from PySide6.QtWidgets import QApplication

from models.project import Project
from models.speaker import Speaker
from models.word import Word
from models.block import Block
from ui.block_widget import BlockWidget


def build_project(n_words):
    words = []
    for i in range(n_words):
        words.append(Word(text=f"w{i}", start=float(i), end=i + 0.9, speaker_id="speaker_1", item_type="word"))
        words.append(Word(text=" ", start=0, end=0, speaker_id="speaker_1", item_type="spacing"))
    block = Block(id=1, speaker_id="speaker_1", start_word=0, end_word=len(words) - 1, created_by_user=False)
    return Project(
        project_file="test.sttproj", modified=False, name="T", audio_file="a.wav",
        transcription_id="t", language_code="fr", duration_seconds=600.0,
        speakers=[Speaker(id="speaker_1", name="Alice", color="#FF0000")],
        words=words, blocks=[block],
        original_elevenlabs_response={}, project_format_version=1,
    )


def pump(app, ms):
    t0 = time.monotonic()
    while (time.monotonic() - t0) * 1000 < ms:
        app.processEvents()
        time.sleep(0.002)


app = QApplication([])
project = build_project(60)
block = project.blocks[0]
w = BlockWidget(project, block, ["Alice"], "Alice")
w.show()

word_indices = [i for i in w.word_positions.keys()]
print("mapped:", len(word_indices), "words")

# Simulation lecture : un mot toutes les 120 ms (parfois 300 ms)
import random
random.seed(42)
seq = []
t = 0
for k, idx in enumerate(word_indices):
    dur = random.choice([90, 120, 150, 250, 300])
    seq.append((idx, dur))

max_alpha_seen = {}
stale_report = []

pos = 0
for idx, dur in seq:
    # comportement main_window : None sur tous, puis set sur le bloc cible
    w.set_active_word(None)
    w.set_active_word(idx)
    pump(app, dur)

for k, a in w.highlight_alphas.items():
    stale_report.append((k, a))
print("APRES LECTURE dict:", stale_report)
print("active_word:", w.active_word)

pump(app, 1000)
print("APRES DRAIN dict:", dict(w.highlight_alphas))
print("active_word:", w.active_word)
sels = w.text_edit.extraSelections()
print("extraSelections:", [(s.cursor.selectedText()) for s in sels])
print("fade_out_anims:", len(w.fade_out_anims), "fade_in_word:", w.fade_in_word)
