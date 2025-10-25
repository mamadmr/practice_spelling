"""CLI tool to add, remove, search, list, and check words in words.csv."""
import csv
import os
import sys
import re
import sqlite3
from typing import List, Tuple


class WordManager:
    def __init__(self, words_file: str = "words.csv"):
        """Initialize word manager."""
        self.words_file = words_file
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Create words.csv if it doesn't exist."""
        if not os.path.exists(self.words_file):
            with open(self.words_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['word'])
    
    def load_words(self) -> List[str]:
        """Load all words from the CSV file."""
        words: List[str] = []
        with open(self.words_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
            # Support optional header; only skip if it's literally 'word'
            start_index = 1 if (rows and rows[0] and rows[0][0].strip().lower() == 'word') else 0
            for row in rows[start_index:]:
                if row and row[0].strip():
                    words.append(row[0].strip().lower())
        return words
    
    def save_words(self, words: List[str]):
        """Save words to the CSV file."""
        with open(self.words_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['word'])
            for word in sorted(set(words)):  # Remove duplicates and sort
                writer.writerow([word])

    # --- Validation helpers ---
    @staticmethod
    def _get_spelling_suggestions(word: str, max_suggestions: int = 3) -> List[str]:
        """Get spelling suggestions for a potentially misspelled word.
        
        Returns a list of up to max_suggestions suggestions, ordered by relevance.
        """
        try:
            from spellchecker import SpellChecker  # type: ignore
            spell = SpellChecker(language='en')
            best = spell.correction(word)
            cands = spell.candidates(word) or set()
            
            # Also try online suggestions if local ones are limited
            if len(cands) < 2:
                try:
                    import requests
                    url = f"https://api.datamuse.com/sug?s={word}&max={max_suggestions}"
                    response = requests.get(url, timeout=2)
                    if response.status_code == 200:
                        data = response.json()
                        online_suggestions = [item.get('word', '') for item in data if 'word' in item]
                        cands.update(online_suggestions[:max_suggestions])
                except Exception:
                    pass
            
            # Order candidates by relevance
            ordered: List[str] = []
            try:
                from wordfreq import zipf_frequency  # type: ignore
                ordered = sorted(
                    cands,
                    key=lambda x: (0 if x == best else 1, -zipf_frequency(x, 'en'), len(x))
                )
            except Exception:
                the_rest = sorted([c for c in cands if c != best])
                ordered = ([best] if best else []) + the_rest
            
            # Return top suggestions
            top = []
            for s in ordered:
                if s and s not in top:
                    top.append(s)
                if len(top) >= max_suggestions:
                    break
            return top
        except Exception:
            return []

    @staticmethod
    def _is_format_valid(word: str) -> bool:
        """Return True if the word format is valid (letters, hyphen, apostrophe)."""
        return re.fullmatch(r"[a-zA-Z][a-zA-Z\-']*", word) is not None

    @staticmethod
    def _is_dictionary_word(word: str) -> Tuple[bool, float]:
        """Return (is_known, score) using online API first, then wordfreq as fallback.
        Tries Merriam-Webster API, then wordfreq.zipf_frequency if installed.
        """
        # Try online dictionary API first
        try:
            import requests
            # Merriam-Webster Dictionary API (free tier, no key needed for basic lookup)
            url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                data = response.json()
                # If we get valid JSON with entries, word exists
                if isinstance(data, list) and len(data) > 0:
                    return (True, 5.0)  # Assign decent score for API-verified words
            # If 404 or other error, word might not exist - continue to local check
        except Exception:
            pass  # Network issues, continue to offline check
        
        # Fallback to wordfreq for local checking
        try:
            from wordfreq import zipf_frequency  # type: ignore
            score = zipf_frequency(word, 'en')
            # zipf_frequency returns 0 for unknown; common words ~3-7. Use > 0 as known.
            return (score > 0.0), score
        except Exception:
            return (True, 0.0)  # If unavailable, don't block validation

    def check_words(self, auto_fix: bool = True, sync_database: bool = True):
        """Validate the word list, report issues, dedupe, and optionally sync the DB.

        - Checks format (letters/hyphen/apostrophe)
        - Checks against online dictionary APIs and local wordfreq/pyspellchecker
        - Finds duplicates (case-insensitive)
        - Auto-deduplicates and rewrites words.csv when auto_fix=True
        - Syncs the database to match the CSV when sync_database=True
        """
        words = self.load_words()

        normalized = [w.strip().lower() for w in words if w and w.strip()]
        
        print(f"\nChecking {len(normalized)} word(s) for format and duplicates...")
        
        # Check words individually and filter problematic ones
        seen = set()
        duplicates = []
        invalid_format = []
        unknown_words: List[str] = []
        suggestions_map: dict[str, List[str]] = {}

        for idx, w in enumerate(normalized):
            # Show progress for format checking
            if len(normalized) > 0:
                percent = ((idx + 1) / len(normalized)) * 100
                bar_length = 30
                filled = int(bar_length * (idx + 1) / len(normalized))
                bar = '█' * filled + '░' * (bar_length - filled)
                print(f"\r  [{bar}] {percent:.1f}% - checking: {w:<20}", end='', flush=True)
            
            if w in seen:
                duplicates.append(w)
            else:
                seen.add(w)

            if not self._is_format_valid(w):
                invalid_format.append(w)
        
        # Clear progress bar line
        if len(normalized) > 0:
            print(f"\r  {'✓ Format check complete':<70}")

        # Auto-fix: rewrite CSV with unique, sorted words
        if auto_fix:
            unique_sorted = sorted(seen)
            self.save_words(unique_sorted)

        # Sync database if requested - only check spelling for words being added
        added = removed = 0
        added_words = []
        removed_words = []
        if sync_database:
            try:
                from database import WordDatabase
                with WordDatabase() as db:
                    # Get current words in database
                    current_db_words = set()
                    try:
                        stats = db.get_all_stats()
                        current_db_words = {stat['word'] for stat in stats}
                    except sqlite3.Error as db_err:
                        print(f"Database query error: {db_err}")
                        pass
                    
                    # Only spell-check words that would be added to database
                    words_to_add = set(seen) - current_db_words
                    words_to_remove = current_db_words - set(seen)
                    
                    clean_words_to_add = []
                    words_to_check = list(words_to_add)
                    total_to_check = len(words_to_check)
                    
                    # Show progress bar for spell checking
                    if total_to_check > 0:
                        print(f"\nChecking spelling for {total_to_check} new word(s)...")
                    
                    for idx, word in enumerate(words_to_check):
                        # Skip words with invalid format
                        if word in invalid_format:
                            continue
                        
                        # Show progress bar
                        if total_to_check > 0:
                            percent = ((idx + 1) / total_to_check) * 100
                            bar_length = 30
                            filled = int(bar_length * (idx + 1) / total_to_check)
                            bar = '█' * filled + '░' * (bar_length - filled)
                            print(f"\r  [{bar}] {percent:.1f}% - checking: {word:<20}", end='', flush=True)
                            
                        # Check spelling only for new words
                        known, score = self._is_dictionary_word(word)
                        if not known:
                            unknown_words.append(word)
                            # Try to generate suggestions
                            suggestions = self._get_spelling_suggestions(word, max_suggestions=3)
                            if suggestions:
                                suggestions_map[word] = suggestions
                                # Include words with suggestions in database
                                clean_words_to_add.append(word)
                            # Exclude words without suggestions (likely severely misspelled)
                        else:
                            # Word is known, include it
                            clean_words_to_add.append(word)
                    
                    # Clear progress bar line if we showed it
                    if total_to_check > 0:
                        print(f"\r  {'✓ Spell check complete':<70}")
                    
                    # Build final word list: existing + validated new words
                    final_words = sorted(current_db_words - words_to_remove) + sorted(clean_words_to_add)
                    
                    # Track what will be added/removed
                    added_words = sorted(clean_words_to_add)
                    removed_words = sorted(words_to_remove)
                    
                    # Sync with similarity calculation for new words
                    if added_words:
                        print(f"\nCalculating similarities for {len(added_words)} new word(s)...")
                        
                        def progress_callback(current, total, other_word):
                            percent = (current / total) * 100 if total > 0 else 0
                            bar_length = 30
                            filled = int(bar_length * current / total) if total > 0 else 0
                            bar = '█' * filled + '░' * (bar_length - filled)
                            print(f"\r  [{bar}] {percent:.1f}% - {other_word}     ", end='', flush=True)
                        
                        added, removed, sims = db.sync_with_word_list(
                            final_words, 
                            remove_missing=True,
                            update_similarities=True,
                            progress_callback=progress_callback
                        )
                        print(f"\n  ✓ Calculated {sims} similarity scores")
                    else:
                        added, removed, sims = db.sync_with_word_list(
                            final_words, 
                            remove_missing=True,
                            update_similarities=False
                        )
            except ImportError as e:
                print(f"Database sync skipped - missing dependency: {e}")
            except Exception as e:
                print(f"Database sync skipped - error: {e}")

        # Summary
        print("\n=== Word List Check ===")
        print(f"Total lines: {len(words)}")
        print(f"Unique words: {len(seen)}")

        dup_list = sorted(set(duplicates))
        if dup_list:
            print(f"Duplicates removed: {len(duplicates)}")
            print("Duplicate words:")
            for w in dup_list:
                print(f"  - {w}")
        else:
            print("Duplicates removed: 0")

        inv_list = sorted(set(invalid_format))
        if inv_list:
            print(f"Format warnings: {len(invalid_format)}")
            print("Invalid format (letters, - and ' allowed):")
            for w in inv_list:
                print(f"  - {w}")

        unk_list = sorted(set(unknown_words))
        if unk_list:
            print(f"Dictionary warnings: {len(unknown_words)}")
            print("Unrecognized words:")
            for w in unk_list:
                sugg = suggestions_map.get(w)
                if sugg:
                    print(f"  - {w}  -> suggestions: {', '.join(sugg)}")
                else:
                    print(f"  - {w}")

        if sync_database:
            print(f"Database synced: +{added} added, -{removed} removed")
            if added_words:
                print("Words added to database:")
                for w in added_words:
                    print(f"  + {w}")
            if removed_words:
                print("Words removed from database:")
                for w in removed_words:
                    print(f"  - {w}")
            if unknown_words:
                excluded_count = len([w for w in unknown_words if w not in suggestions_map])
                if excluded_count > 0:
                    print(f"Words excluded from database (likely misspelled): {excluded_count}")
        print("=======================\n")
        
        # Return details for potential callers/tests
        return {
            'total': len(words),
            'unique': len(seen),
            'duplicates': sorted(set(duplicates)),
            'invalid_format': sorted(set(invalid_format)),
            'unknown_words': sorted(set(unknown_words)),
            'suggestions': suggestions_map,
            'db_added': added,
            'db_removed': removed,
            'added_words': added_words,
            'removed_words': removed_words,
        }
    
    def add_word(self, word: str, sync_db: bool = True) -> bool:
        """Add a word to the list and optionally sync with database."""
        word = word.strip().lower()
        if not word:
            print("Error: Word cannot be empty")
            return False
        
        words = self.load_words()
        if word in words:
            print(f"'{word}' is already in the list")
            return False
        
        words.append(word)
        self.save_words(words)
        print(f"✓ Added '{word}' to the word list")
        
        # Sync with database and calculate similarities
        if sync_db:
            try:
                from database import WordDatabase
                with WordDatabase() as db:
                    all_words = self.load_words()
                    print(f"Calculating similarities for '{word}'...")
                    
                    def progress_callback(current, total, other_word):
                        percent = (current / total) * 100 if total > 0 else 0
                        bar_length = 30
                        filled = int(bar_length * current / total) if total > 0 else 0
                        bar = '█' * filled + '░' * (bar_length - filled)
                        print(f"\r  [{bar}] {percent:.1f}% - {other_word}     ", end='', flush=True)
                    
                    added, removed, sims = db.sync_with_word_list(
                        all_words,
                        remove_missing=True,
                        update_similarities=True,
                        progress_callback=progress_callback
                    )
                    if sims > 0:
                        print(f"\n  ✓ Calculated {sims} similarity scores")
            except Exception as e:
                print(f"Warning: Could not update database: {e}")
        
        return True
    
    def add_words_bulk(self, word_list: List[str], sync_db: bool = True):
        """Add multiple words at once."""
        words = self.load_words()
        added_count = 0
        new_words = []
        
        for word in word_list:
            word = word.strip().lower()
            if word and word not in words:
                words.append(word)
                new_words.append(word)
                added_count += 1
                print(f"✓ Added '{word}'")
            elif word in words:
                print(f"⊘ Skipped '{word}' (already exists)")
        
        if added_count > 0:
            self.save_words(words)
            print(f"\n✓ Added {added_count} new word(s)")
            
            # Sync with database and calculate similarities
            if sync_db:
                try:
                    from database import WordDatabase
                    with WordDatabase() as db:
                        all_words = self.load_words()
                        print(f"Calculating similarities for {len(new_words)} new word(s)...")
                        
                        def progress_callback(current, total, other_word):
                            percent = (current / total) * 100 if total > 0 else 0
                            bar_length = 30
                            filled = int(bar_length * current / total) if total > 0 else 0
                            bar = '█' * filled + '░' * (bar_length - filled)
                            print(f"\r  [{bar}] {percent:.1f}% - {other_word}     ", end='', flush=True)
                        
                        added, removed, sims = db.sync_with_word_list(
                            all_words,
                            remove_missing=True,
                            update_similarities=True,
                            progress_callback=progress_callback
                        )
                        if sims > 0:
                            print(f"\n  ✓ Calculated {sims} similarity scores")
                except Exception as e:
                    print(f"Warning: Could not update database: {e}")
        else:
            print("\nNo new words added")
    
    def remove_word(self, word: str, sync_db: bool = True) -> bool:
        """Remove a word from the list and optionally sync with database."""
        word = word.strip().lower()
        words = self.load_words()
        
        if word not in words:
            print(f"'{word}' is not in the list")
            return False
        
        words.remove(word)
        self.save_words(words)
        print(f"✓ Removed '{word}' from the word list")
        
        # Sync with database to remove word and its similarities
        if sync_db:
            try:
                from database import WordDatabase
                with WordDatabase() as db:
                    db.remove_word(word)
                    print(f"  ✓ Removed from database")
            except Exception as e:
                print(f"Warning: Could not update database: {e}")
        
        return True
    
    def list_words(self):
        """Display all words in the list."""
        words = self.load_words()
        
        if not words:
            print("No words in the list")
            return
        
        print(f"\n{'='*50}")
        print(f"Word List ({len(words)} words)")
        print(f"{'='*50}\n")
        
        for i, word in enumerate(sorted(words), 1):
            print(f"{i:3d}. {word}")
        
        print(f"\n{'='*50}\n")
    
    def search_words(self, pattern: str):
        """Search for words containing the pattern."""
        words = self.load_words()
        pattern = pattern.lower()
        
        matches = [w for w in words if pattern in w]
        
        if not matches:
            print(f"No words found containing '{pattern}'")
            return
        
        print(f"\nFound {len(matches)} word(s) containing '{pattern}':")
        for word in sorted(matches):
            print(f"  - {word}")
        print()
    
    def clear_all(self):
        """Remove all words from the list."""
        print("⚠️  WARNING: This will remove ALL words from the list!")
        print("Type 'yes' to confirm: ", end="")
        
        if input().strip().lower() == 'yes':
            self.save_words([])
            print("✓ Cleared all words")
        else:
            print("Cancelled")
    
    def import_from_file(self, filename: str):
        """Import words from a text file (one word per line)."""
        if not os.path.exists(filename):
            print(f"Error: File '{filename}' not found")
            return
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                new_words = [line.strip() for line in f if line.strip()]
            
            self.add_words_bulk(new_words)
        except Exception as e:
            print(f"Error reading file: {e}")


def print_help():
    """Print usage information."""
    print("""
Word Manager - Manage your spelling practice word list

Usage:
    python word_manager.py <command> [arguments]

Commands:
    add <word>              Add a single word
    add <word1> <word2>...  Add multiple words
    remove <word>           Remove a word
    list                    Show all words
    search <pattern>        Search for words containing pattern
    clear                   Remove all words (with confirmation)
    import <file>           Import words from text file (one per line)
    clear-cache             Clear audio cache (audio will be re-downloaded)
        check                   Validate and deduplicate words, then sync database
    help                    Show this help message

Examples:
    python word_manager.py add accommodate
    python word_manager.py add separate definitely receive
    python word_manager.py remove accommodate
    python word_manager.py list
    python word_manager.py search tion
    python word_manager.py import my_words.txt
    """)


def main():
    """Main entry point for word manager CLI."""
    if len(sys.argv) < 2:
        print_help()
        return
    
    manager = WordManager()
    command = sys.argv[1].lower()
    
    if command == 'add':
        if len(sys.argv) < 3:
            print("Error: Please provide at least one word to add")
            print("Usage: python word_manager.py add <word1> [word2] ...")
        else:
            manager.add_words_bulk(sys.argv[2:])
    
    elif command == 'remove':
        if len(sys.argv) < 3:
            print("Error: Please provide a word to remove")
            print("Usage: python word_manager.py remove <word>")
        else:
            manager.remove_word(sys.argv[2])
    
    elif command == 'list':
        manager.list_words()
    
    elif command == 'search':
        if len(sys.argv) < 3:
            print("Error: Please provide a search pattern")
            print("Usage: python word_manager.py search <pattern>")
        else:
            manager.search_words(sys.argv[2])
    
    elif command == 'clear':
        manager.clear_all()
    
    elif command == 'import':
        if len(sys.argv) < 3:
            print("Error: Please provide a file to import")
            print("Usage: python word_manager.py import <filename>")
        else:
            manager.import_from_file(sys.argv[2])
    
    elif command == 'clear-cache':
        # Clear audio cache
        import shutil
        cache_dir = "audio_cache"
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
            print(f"✓ Cleared audio cache")
        else:
            print("No audio cache to clear")
    
    elif command == 'check':
        manager.check_words(auto_fix=True, sync_database=True)

    elif command == 'help':
        print_help()
    
    else:
        print(f"Error: Unknown command '{command}'")
        print_help()


if __name__ == "__main__":
    main()
