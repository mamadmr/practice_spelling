"""CLI tool to add, remove, search, and list words in words.csv."""
import csv
import os
import sys
from typing import List


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
        words = []
        with open(self.words_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for row in reader:
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
    
    def add_word(self, word: str) -> bool:
        """Add a word to the list."""
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
        return True
    
    def add_words_bulk(self, word_list: List[str]):
        """Add multiple words at once."""
        words = self.load_words()
        added_count = 0
        
        for word in word_list:
            word = word.strip().lower()
            if word and word not in words:
                words.append(word)
                added_count += 1
                print(f"✓ Added '{word}'")
            elif word in words:
                print(f"⊘ Skipped '{word}' (already exists)")
        
        if added_count > 0:
            self.save_words(words)
            print(f"\n✓ Added {added_count} new word(s)")
        else:
            print("\nNo new words added")
    
    def remove_word(self, word: str) -> bool:
        """Remove a word from the list."""
        word = word.strip().lower()
        words = self.load_words()
        
        if word not in words:
            print(f"'{word}' is not in the list")
            return False
        
        words.remove(word)
        self.save_words(words)
        print(f"✓ Removed '{word}' from the word list")
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
    
    elif command == 'help':
        print_help()
    
    else:
        print(f"Error: Unknown command '{command}'")
        print_help()


if __name__ == "__main__":
    main()
