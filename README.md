# Incremental Reading Add-on for Anki

A practical incremental-reading workflow for Anki inspired by SuperMemo.

## What this add-on does
- Adds an `IncrementalReading` note type (Title, Source, Content, Status, ParentID).
- Lets you save long article notes from `Tools -> Incremental Reading -> Add Article`.
- Lets you create child extracts while reviewing an article card.
- Supports direct capture from in-reviewer text selection.
- Supports optional one-step cloze wrapping of extract text.
- Lets you postpone the current review card by 3 or 7 days.

## Install
1. Copy `addons/incremental_reading` into your Anki add-ons directory.
2. Restart Anki.
3. Open **Tools -> Incremental Reading**.

## Workflow
1. Add an article.
2. Review it and highlight/select text on the card.
3. Use **Create Extract from Selection** (or the cloze variant).
4. Postpone and revisit later.

## Limitations
- This is intentionally lightweight and not a full clone of SuperMemo IR priority algorithms.
- Selection capture depends on reviewer webview selection availability in your Anki version.



