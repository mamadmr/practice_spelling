"""
Database manager for tracking word progress and statistics.
"""
import sqlite3
from datetime import datetime
from typing import List, Tuple, Optional
import os


class WordDatabase:
    def __init__(self, db_path: str = "progress.db"):
        """Initialize database connection and create tables if needed."""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._create_tables()
    
    def _create_tables(self):
        """Create necessary tables for tracking word progress."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS word_stats (
                word TEXT PRIMARY KEY,
                correct_count INTEGER DEFAULT 0,
                incorrect_count INTEGER DEFAULT 0,
                total_appearances INTEGER DEFAULT 0,
                last_seen TIMESTAMP,
                difficulty_score REAL DEFAULT 1.0,
                consecutive_correct INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()
    
    def add_word(self, word: str):
        """Add a new word to track or do nothing if it exists."""
        try:
            self.cursor.execute("""
                INSERT OR IGNORE INTO word_stats (word, last_seen)
                VALUES (?, ?)
            """, (word.lower(), datetime.now()))
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Database error adding word '{word}': {e}")
    
    def update_word_result(self, word: str, correct: bool):
        """Update statistics after user attempts a word."""
        word = word.lower()
        
        # Ensure word exists in database
        self.add_word(word)
        
        # Update statistics
        if correct:
            self.cursor.execute("""
                UPDATE word_stats
                SET correct_count = correct_count + 1,
                    total_appearances = total_appearances + 1,
                    last_seen = ?,
                    difficulty_score = MAX(0.1, difficulty_score - 0.1),
                    consecutive_correct = consecutive_correct + 1
                WHERE word = ?
            """, (datetime.now(), word))
        else:
            self.cursor.execute("""
                UPDATE word_stats
                SET incorrect_count = incorrect_count + 1,
                    total_appearances = total_appearances + 1,
                    last_seen = ?,
                    difficulty_score = MIN(10.0, difficulty_score + 0.5),
                    consecutive_correct = 0
                WHERE word = ?
            """, (datetime.now(), word))
        
        self.conn.commit()
    
    def get_word_stats(self, word: str) -> Optional[dict]:
        """Get statistics for a specific word."""
        self.cursor.execute("""
            SELECT word, correct_count, incorrect_count, total_appearances,
                   difficulty_score, last_seen, consecutive_correct
            FROM word_stats
            WHERE word = ?
        """, (word.lower(),))
        
        row = self.cursor.fetchone()
        if row:
            return {
                'word': row[0],
                'correct': row[1],
                'incorrect': row[2],
                'total': row[3],
                'difficulty': row[4],
                'last_seen': row[5],
                'consecutive_correct': row[6]
            }
        return None
    
    def get_all_stats(self) -> List[dict]:
        """Get statistics for all words."""
        self.cursor.execute("""
            SELECT word, correct_count, incorrect_count, total_appearances,
                   difficulty_score, last_seen, consecutive_correct
            FROM word_stats
            ORDER BY difficulty_score DESC, total_appearances ASC
        """)
        
        return [{
            'word': row[0],
            'correct': row[1],
            'incorrect': row[2],
            'total': row[3],
            'difficulty': row[4],
            'last_seen': row[5],
            'consecutive_correct': row[6]
        } for row in self.cursor.fetchall()]
    
    def get_weighted_words(self, word_list: List[str]) -> List[Tuple[str, float]]:
        """
        Get words with their weights for selection algorithm.
        Higher difficulty = higher weight = more likely to be selected.
        Words with lower consecutive_correct count get higher weight.
        Also considers how long ago the word was seen.
        """
        weights = []
        current_time = datetime.now()
        
        for word in word_list:
            stats = self.get_word_stats(word)
            
            if stats is None:
                # New word gets medium-high weight
                weights.append((word, 2.0))
            else:
                # Base weight from difficulty score
                weight = stats['difficulty']
                
                # Boost weight for words with low consecutive correct count
                # Words with 0 consecutive correct get highest boost
                consecutive = stats['consecutive_correct']
                if consecutive == 0:
                    weight += 2.0  # High priority for words never correct in a row
                elif consecutive == 1:
                    weight += 1.0  # Medium priority
                elif consecutive == 2:
                    weight += 0.5  # Low priority
                # Words with 3+ consecutive correct get no boost (rely on difficulty only)
                
                # Boost weight for words not seen recently
                if stats['last_seen']:
                    try:
                        last_seen = datetime.fromisoformat(stats['last_seen'])
                        days_ago = (current_time - last_seen).days
                        # Add bonus weight based on days since last seen
                        weight += min(days_ago * 0.1, 2.0)
                    except:
                        pass
                
                weights.append((word, weight))
        
        return weights
    
    def remove_word(self, word: str):
        """Remove a word from the database."""
        self.cursor.execute("DELETE FROM word_stats WHERE word = ?", (word.lower(),))
        self.conn.commit()
    
    def sync_with_word_list(self, word_list: List[str], remove_missing: bool = True) -> Tuple[int, int]:
        """
        Sync the database with the provided word list.
        - Adds any words present in the list but missing in the DB
        - If remove_missing=True, removes any words in the DB not present in the list
        Returns: (added_count, removed_count)
        """
        normalized = sorted(set(w.strip().lower() for w in word_list if w and w.strip()))
        added_count = 0
        removed_count = 0
        
        # Fetch existing words
        self.cursor.execute("SELECT word FROM word_stats")
        existing = {row[0] for row in self.cursor.fetchall()}
        target = set(normalized)
        
        to_add = list(target - existing)
        to_remove = list(existing - target) if remove_missing else []
        
        # Use a transaction to ensure atomicity
        try:
            self.conn.execute('BEGIN')
            
            # Add missing words
            if to_add:
                now = datetime.now()
                self.cursor.executemany(
                    "INSERT OR IGNORE INTO word_stats (word, last_seen) VALUES (?, ?)",
                    [(w, now) for w in to_add]
                )
                added_count = len(to_add)
            
            # Remove words not in CSV
            if to_remove:
                self.cursor.executemany(
                    "DELETE FROM word_stats WHERE word = ?",
                    [(w,) for w in to_remove]
                )
                removed_count = len(to_remove)
            
            self.conn.commit()
        except sqlite3.Error as e:
            self.conn.rollback()
            raise sqlite3.Error(f"Failed to sync word list: {e}") from e
        
        return added_count, removed_count
    
    def close(self):
        """Close database connection."""
        self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
