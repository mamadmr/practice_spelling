# Spelling Practice

A simple command-line app to practice English spelling with audio pronunciation and progress tracking.

## Requirements

- Python 3.8+
- pip to install dependencies

## Install

```powershell
pip install -r requirements.txt
```

## Add words

- Add one or more words:
```powershell
python word_manager.py add accommodate separate definitely
```

- Import from a text file (one word per line):
```powershell
python word_manager.py import sample_words.txt
```

- See your list:
```powershell
python word_manager.py list
```

## Practice

Run the app and use the menu to start practicing, view stats, reload words, or toggle audio.

```powershell
python spelling_practice.py
```

On Windows you can also double‑click `start_practice.bat`.

## Files

- `spelling_practice.py` — main app
- `word_manager.py` — manage the word list
- `database.py` — progress storage (SQLite)
- `words.csv` — your words (one per line)
- `requirements.txt` — dependencies
