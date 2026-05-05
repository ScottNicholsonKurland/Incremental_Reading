"""Incremental Reading add-on for Anki.

A practical, native-Anki incremental reading workflow inspired by SuperMemo:
- Capture long articles as notes.
- Create child extracts from articles.
- Capture extracts directly from in-reviewer webview text selection.
- Optionally convert extract text to cloze format.
- Postpone cards safely with Anki scheduler day numbers.
"""

from __future__ import annotations

from dataclasses import dataclass

from aqt import gui_hooks, mw
from aqt.qt import (
    QAction,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)
from aqt.utils import showInfo, tooltip

MODEL_NAME = "IncrementalReading"
ARTICLE_CARD = "IR-Article"
EXTRACT_CARD = "IR-Extract"


@dataclass(frozen=True)
class IRFields:
    title: str = "Title"
    source: str = "Source"
    content: str = "Content"
    status: str = "Status"
    parent: str = "ParentID"


FIELDS = IRFields()


def _model():
    return mw.col.models.by_name(MODEL_NAME)


def ensure_notetype() -> None:
    mm = mw.col.models
    if _model():
        return

    model = mm.new(MODEL_NAME)
    for name in (FIELDS.title, FIELDS.source, FIELDS.content, FIELDS.status, FIELDS.parent):
        mm.add_field(model, mm.new_field(name))

    article = mm.new_template(ARTICLE_CARD)
    article["qfmt"] = "<h3>{{Title}}</h3><hr>{{Content}}"
    article["afmt"] = "{{FrontSide}}<hr><small>{{Source}}</small><br><small>Status: {{Status}}</small>"
    mm.add_template(model, article)

    extract = mm.new_template(EXTRACT_CARD)
    extract["qfmt"] = "{{Content}}"
    extract["afmt"] = "{{FrontSide}}<hr><b>{{Title}}</b><br><small>{{Source}}</small>"
    mm.add_template(model, extract)

    mm.add(model)


def _current_deck_id() -> int:
    return mw.col.decks.current()["id"]


def _new_ir_note():
    ensure_notetype()
    model = _model()
    if not model:
        raise RuntimeError("Could not create or load IncrementalReading model.")
    return mw.col.new_note(model)


def add_article_dialog() -> None:
    d = QDialog(mw)
    d.setWindowTitle("Add Incremental Reading Article")
    form = QFormLayout(d)

    title = QLineEdit(d)
    source = QLineEdit(d)
    content = QTextEdit(d)
    content.setPlaceholderText("Paste article text, web clipping, or your summary here...")

    form.addRow("Title", title)
    form.addRow("Source URL", source)

    save_btn = QPushButton("Save Article", d)

    layout = QVBoxLayout(d)
    layout.addLayout(form)
    layout.addWidget(content)
    layout.addWidget(save_btn)

    def save() -> None:
        if not content.toPlainText().strip():
            showInfo("Article content cannot be empty.")
            return

        note = _new_ir_note()
        note[FIELDS.title] = title.text().strip() or "Untitled Article"
        note[FIELDS.source] = source.text().strip()
        note[FIELDS.content] = content.toPlainText().strip()
        note[FIELDS.status] = "reading"
        note[FIELDS.parent] = ""

        mw.col.add_note(note, _current_deck_id())
        mw.reset()
        tooltip("Incremental reading article added")
        d.accept()

    save_btn.clicked.connect(save)
    d.exec()


def _get_reviewer_card():
    reviewer = getattr(mw, "reviewer", None)
    if not reviewer or not reviewer.card:
        return None
    return reviewer.card


def postpone_current_card(days: int = 3) -> None:
    card = _get_reviewer_card()
    if not card:
        showInfo("No active review card. Open the Reviewer first.")
        return
    if days < 1:
        showInfo("Postpone days must be >= 1.")
        return

    target_due = mw.col.sched.today + days
    card.due = target_due
    card.queue = 2
    card.type = 2
    card.flush()

    mw.reviewer.nextCard()
    tooltip(f"Postponed by {days} day(s)")


def _to_cloze(text: str) -> str:
    stripped = text.strip()
    if "{{c1::" in stripped:
        return stripped
    return f"{{{{c1::{stripped}}}}}"


def add_extract_from_text(text: str, cloze: bool) -> None:
    card = _get_reviewer_card()
    if not card:
        showInfo("Open Reviewer on an IR article card first.")
        return

    body = text.strip()
    if not body:
        showInfo("Extract text is empty.")
        return

    parent = card.note()
    note = _new_ir_note()
    note[FIELDS.title] = f"Extract: {parent[FIELDS.title]}"
    note[FIELDS.source] = parent[FIELDS.source]
    note[FIELDS.content] = _to_cloze(body) if cloze else body
    note[FIELDS.status] = "extract"
    note[FIELDS.parent] = str(parent.id)

    mw.col.add_note(note, _current_deck_id())
    mw.reset()
    tooltip("Extract created")


def create_extract_from_web_selection(cloze: bool = False) -> None:
    reviewer = getattr(mw, "reviewer", None)
    if not reviewer or not getattr(reviewer, "web", None):
        showInfo("Open Reviewer first to capture selected text.")
        return

    js = "(window.getSelection && window.getSelection().toString()) || ''"

    def on_selection(selected: str) -> None:
        if not selected or not selected.strip():
            showInfo("No selected text found in reviewer webview.")
            return
        add_extract_from_text(selected, cloze=cloze)

    reviewer.web.evalWithCallback(js, on_selection)


def prompt_extract() -> None:
    d = QDialog(mw)
    d.setWindowTitle("Create Incremental Reading Extract")

    text = QTextEdit(d)
    text.setPlaceholderText("Paste the passage you want to extract...")

    hint = QLabel("Tip: Type y for cloze auto-wrap.", d)
    cloze_input = QLineEdit(d)
    cloze_input.setPlaceholderText("y / n")

    create_btn = QPushButton("Create Extract", d)

    layout = QVBoxLayout(d)
    layout.addWidget(text)

    row = QHBoxLayout()
    row.addWidget(hint)
    row.addWidget(cloze_input)
    layout.addLayout(row)
    layout.addWidget(create_btn)

    def save() -> None:
        want_cloze = cloze_input.text().strip().lower() in {"y", "yes", "1", "true"}
        add_extract_from_text(text.toPlainText(), want_cloze)
        d.accept()

    create_btn.clicked.connect(save)
    d.exec()


def setup_menu() -> None:
    if hasattr(mw, "ir_menu") and mw.ir_menu:
        return

    menu = mw.form.menuTools.addMenu("Incremental Reading")
    mw.ir_menu = menu

    add_article = QAction("Add Article", mw)
    add_article.triggered.connect(add_article_dialog)
    menu.addAction(add_article)

    create_extract = QAction("Create Extract (manual)", mw)
    create_extract.triggered.connect(prompt_extract)
    menu.addAction(create_extract)

    capture_extract = QAction("Create Extract from Selection", mw)
    capture_extract.triggered.connect(lambda: create_extract_from_web_selection(False))
    menu.addAction(capture_extract)

    capture_extract_cloze = QAction("Create Cloze Extract from Selection", mw)
    capture_extract_cloze.triggered.connect(lambda: create_extract_from_web_selection(True))
    menu.addAction(capture_extract_cloze)

    postpone_3 = QAction("Postpone Current Card (3 days)", mw)
    postpone_3.triggered.connect(lambda: postpone_current_card(3))
    menu.addAction(postpone_3)

    postpone_7 = QAction("Postpone Current Card (7 days)", mw)
    postpone_7.triggered.connect(lambda: postpone_current_card(7))
    menu.addAction(postpone_7)


def on_profile_loaded() -> None:
    ensure_notetype()
    setup_menu()


gui_hooks.profile_did_open.append(on_profile_loaded)
