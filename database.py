"""
Database manager for tracking word progress and statistics.
"""
import sqlite3
from datetime import datetime
from typing import List, Tuple, Optional, Dict
import os

# Set tokenizer parallelism to avoid fork warnings
os.environ['TOKENIZERS_PARALLELISM'] = 'false'


class WordDatabase:
    def __init__(self, db_path: str = "progress.db"):
        """Initialize database connection and create tables if needed."""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._create_tables()
    
    def _create_tables(self):
        """Create necessary tables for tracking word progress and similarity matrix."""
        # Table for word statistics
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS word_stats (
                word TEXT PRIMARY KEY,
                correct_count INTEGER DEFAULT 0,
                incorrect_count INTEGER DEFAULT 0,
                total_appearances INTEGER DEFAULT 0,
                last_seen TIMESTAMP,
                last_correct_date DATE,
                daily_practice_count INTEGER DEFAULT 0,
                practice_date DATE,
                difficulty_score REAL DEFAULT 1.0,
                consecutive_correct INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Add new columns if they don't exist (for existing databases)
        try:
            self.cursor.execute("ALTER TABLE word_stats ADD COLUMN last_correct_date DATE")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            self.cursor.execute("ALTER TABLE word_stats ADD COLUMN daily_practice_count INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            self.cursor.execute("ALTER TABLE word_stats ADD COLUMN practice_date DATE")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Table for word-to-word similarity scores
        # Store similarity score between each pair of words
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS word_similarity (
                word1 TEXT NOT NULL,
                word2 TEXT NOT NULL,
                similarity_score REAL NOT NULL,
                PRIMARY KEY (word1, word2),
                FOREIGN KEY (word1) REFERENCES word_stats(word),
                FOREIGN KEY (word2) REFERENCES word_stats(word)
            )
        """)
        
        # Create index for faster lookups
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_similarity_word1 
            ON word_similarity(word1)
        """)
        
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_similarity_word2 
            ON word_similarity(word2)
        """)
        
        # Table for example sentences cache
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS word_sentences (
                word TEXT PRIMARY KEY,
                sentences TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (word) REFERENCES word_stats(word)
            )
        """)
        
        # Table for word definitions cache
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS word_definitions (
                word TEXT PRIMARY KEY,
                definition TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (word) REFERENCES word_stats(word)
            )
        """)
        
        # Table for word embeddings (vector representations)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS word_embeddings (
                word TEXT PRIMARY KEY,
                embedding BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (word) REFERENCES word_stats(word)
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
    
    @staticmethod
    def _levenshtein_distance(s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return WordDatabase._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                # Cost of insertions, deletions, or substitutions
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    @staticmethod
    def calculate_similarity(word1: str, word2: str) -> float:
        """
        Calculate similarity score between two words (0 to 1).
        Higher score = more similar.
        Based on normalized Levenshtein distance with additional features.
        """
        if word1 == word2:
            return 1.0
        word1, word2 = word1.lower(), word2.lower()
        
        # Levenshtein distance
        distance = WordDatabase._levenshtein_distance(word1, word2)
        max_len = max(len(word1), len(word2))
        
        # Normalize to 0-1 range (1 = identical, 0 = completely different)
        base_similarity = 1.0 - (distance / max_len) if max_len > 0 else 0.0
        
        # Bonus for common prefixes (important in spelling)
        common_prefix = 0
        for c1, c2 in zip(word1, word2):
            if c1 == c2:
                common_prefix += 1
            else:
                break
        prefix_bonus = (common_prefix / max_len) * 0.2 if max_len > 0 else 0.0
        
        # Bonus for common suffixes
        common_suffix = 0
        for c1, c2 in zip(reversed(word1), reversed(word2)):
            if c1 == c2:
                common_suffix += 1
            else:
                break
        suffix_bonus = (common_suffix / max_len) * 0.2 if max_len > 0 else 0.0
        
        # Bonus for similar length
        len_diff = abs(len(word1) - len(word2))
        length_similarity = 1.0 - (len_diff / max_len) if max_len > 0 else 0.0
        length_bonus = length_similarity * 0.1
        
        # Total similarity (capped at 1.0)
        total_similarity = min(1.0, base_similarity + prefix_bonus + suffix_bonus + length_bonus)
        
        return round(total_similarity, 4)
    
    def update_similarity_for_word(self, new_word: str, all_words: List[str], 
                                   progress_callback=None) -> int:
        """
        Calculate and store similarity scores for a new word against all existing words.
        Returns the number of similarity pairs added.
        
        Args:
            new_word: The new word to calculate similarities for
            all_words: List of all words in the database
            progress_callback: Optional callback function(current, total, word) for progress updates
        """
        new_word = new_word.lower()
        pairs_added = 0
        
        # Get list of words excluding the new word itself
        other_words = [w for w in all_words if w.lower() != new_word]
        total = len(other_words)
        
        for idx, other_word in enumerate(other_words):
            other_word = other_word.lower()
            
            # Calculate similarity
            similarity = self.calculate_similarity(new_word, other_word)
            
            # Store both directions for easier queries
            try:
                self.cursor.execute("""
                    INSERT OR REPLACE INTO word_similarity (word1, word2, similarity_score)
                    VALUES (?, ?, ?)
                """, (new_word, other_word, similarity))
                
                self.cursor.execute("""
                    INSERT OR REPLACE INTO word_similarity (word1, word2, similarity_score)
                    VALUES (?, ?, ?)
                """, (other_word, new_word, similarity))
                
                pairs_added += 2
                
                # Call progress callback if provided
                if progress_callback:
                    progress_callback(idx + 1, total, other_word)
                    
            except sqlite3.Error as e:
                print(f"Error storing similarity for {new_word} <-> {other_word}: {e}")
        
        self.conn.commit()
        return pairs_added
    
    def update_all_similarities(self, all_words: List[str], progress_callback=None) -> int:
        """
        Calculate and store similarity scores for all word pairs.
        This is used when building the matrix from scratch.
        
        Args:
            all_words: List of all words to calculate similarities for
            progress_callback: Optional callback function(current, total, word1, word2) for progress
        
        Returns:
            Number of similarity pairs added
        """
        all_words = [w.lower() for w in all_words]
        n = len(all_words)
        total_pairs = (n * (n - 1)) // 2  # Number of unique pairs
        pairs_added = 0
        current_pair = 0
        
        for i in range(n):
            for j in range(i + 1, n):
                word1, word2 = all_words[i], all_words[j]
                
                # Calculate similarity
                similarity = self.calculate_similarity(word1, word2)
                
                # Store both directions
                try:
                    self.cursor.execute("""
                        INSERT OR REPLACE INTO word_similarity (word1, word2, similarity_score)
                        VALUES (?, ?, ?)
                    """, (word1, word2, similarity))
                    
                    self.cursor.execute("""
                        INSERT OR REPLACE INTO word_similarity (word1, word2, similarity_score)
                        VALUES (?, ?, ?)
                    """, (word2, word1, similarity))
                    
                    pairs_added += 2
                    current_pair += 1
                    
                    # Call progress callback if provided
                    if progress_callback:
                        progress_callback(current_pair, total_pairs, word1, word2)
                        
                except sqlite3.Error as e:
                    print(f"Error storing similarity for {word1} <-> {word2}: {e}")
        
        self.conn.commit()
        return pairs_added
    
    def get_similar_words(self, word: str, min_similarity: float = 0.5, 
                          limit: int = 10) -> List[Tuple[str, float]]:
        """
        Get words similar to the given word.
        
        Args:
            word: The word to find similar words for
            min_similarity: Minimum similarity threshold (0 to 1)
            limit: Maximum number of results to return
        
        Returns:
            List of (word, similarity_score) tuples, sorted by similarity (highest first)
        """
        self.cursor.execute("""
            SELECT word2, similarity_score
            FROM word_similarity
            WHERE word1 = ? AND similarity_score >= ?
            ORDER BY similarity_score DESC
            LIMIT ?
        """, (word.lower(), min_similarity, limit))
        
        return [(row[0], row[1]) for row in self.cursor.fetchall()]
    
    def get_similarity(self, word1: str, word2: str) -> Optional[float]:
        """Get the similarity score between two specific words."""
        self.cursor.execute("""
            SELECT similarity_score
            FROM word_similarity
            WHERE word1 = ? AND word2 = ?
        """, (word1.lower(), word2.lower()))
        
        row = self.cursor.fetchone()
        return row[0] if row else None
    
    def remove_word_similarities(self, word: str):
        """Remove all similarity entries for a word."""
        word = word.lower()
        self.cursor.execute("""
            DELETE FROM word_similarity 
            WHERE word1 = ? OR word2 = ?
        """, (word, word))
        self.conn.commit()

    
    def update_word_result(self, word: str, correct: bool, update_daily_count: bool = True):
        """
        Update statistics after user attempts a word.
        
        Args:
            word: The word being practiced
            correct: Whether the user got it correct
            update_daily_count: If False, don't increment daily count (used during batch retries)
        """
        word = word.lower()
        today = datetime.now().date()
        
        # Ensure word exists in database
        self.add_word(word)
        
        # Update statistics
        if correct:
            self.cursor.execute("""
                UPDATE word_stats
                SET correct_count = correct_count + 1,
                    total_appearances = total_appearances + 1,
                    last_seen = ?,
                    last_correct_date = ?,
                    difficulty_score = MAX(0.1, difficulty_score - 0.1),
                    consecutive_correct = consecutive_correct + 1
                WHERE word = ?
            """, (datetime.now(), today, word))
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
    
    def increment_daily_count(self, word: str):
        """
        Increment the daily practice count for a word when a batch is successfully completed.
        This should only be called once per successful batch completion.
        """
        word = word.lower()
        today = datetime.now().date()
        
        # Ensure word exists in database
        self.add_word(word)
        
        # Get current practice date and count
        self.cursor.execute("""
            SELECT practice_date, daily_practice_count
            FROM word_stats
            WHERE word = ?
        """, (word,))
        row = self.cursor.fetchone()
        
        practice_date = row[0] if row and row[0] else None
        daily_count = row[1] if row else 0
        
        # Reset count if it's a new day
        if practice_date != str(today):
            daily_count = 0
        
        # Increment daily practice count
        daily_count += 1
        
        # Update only the daily count fields
        self.cursor.execute("""
            UPDATE word_stats
            SET daily_practice_count = ?,
                practice_date = ?
            WHERE word = ?
        """, (daily_count, today, word))
        
        self.conn.commit()
    
    def filter_daily_limit(self, word_list: List[str], max_daily: int = 4) -> List[str]:
        """
        Filter out words that have been practiced max_daily times or more today.
        Returns only words that can still be practiced today.
        """
        if not word_list:
            return []
        
        today = datetime.now().date()
        placeholders = ','.join('?' * len(word_list))
        
        self.cursor.execute(f"""
            SELECT word
            FROM word_stats
            WHERE word IN ({placeholders})
            AND (practice_date != ? OR daily_practice_count < ? OR practice_date IS NULL)
        """, word_list + [str(today), max_daily])
        
        available_words = [row[0] for row in self.cursor.fetchall()]
        
        # Also include words that are not in the database yet
        words_in_db = set(available_words)
        for word in word_list:
            if word.lower() not in [w.lower() for w in words_in_db]:
                # Check if word exists in database
                self.cursor.execute("SELECT word FROM word_stats WHERE word = ?", (word.lower(),))
                if not self.cursor.fetchone():
                    available_words.append(word)
        
        return available_words
    
    def get_word_stats(self, word: str) -> Optional[dict]:
        """Get statistics for a specific word."""
        self.cursor.execute("""
            SELECT word, correct_count, incorrect_count, total_appearances,
                   difficulty_score, last_seen, consecutive_correct, 
                   last_correct_date, daily_practice_count, practice_date
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
                'consecutive_correct': row[6],
                'last_correct_date': row[7],
                'daily_practice_count': row[8],
                'practice_date': row[9]
            }
        return None
    
    def get_all_stats(self) -> List[dict]:
        """Get statistics for all words."""
        self.cursor.execute("""
            SELECT word, correct_count, incorrect_count, total_appearances,
                   difficulty_score, last_seen, consecutive_correct,
                   last_correct_date, daily_practice_count, practice_date
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
            'consecutive_correct': row[6],
            'last_correct_date': row[7],
            'daily_practice_count': row[8],
            'practice_date': row[9]
        } for row in self.cursor.fetchall()]
    
    def get_weighted_words(self, word_list: List[str]) -> List[Tuple[str, float]]:
        """
        Get words with their weights for selection algorithm.
        Higher difficulty = higher weight = more likely to be selected.
        Words with lower consecutive_correct count get higher weight.
        Also considers how long ago the word was seen.
        NEW WORDS GET HIGHEST PRIORITY (5x boost).
        """
        weights = []
        current_time = datetime.now()
        
        for word in word_list:
            stats = self.get_word_stats(word)
            
            if stats is None:
                # NEW WORD - Give VERY HIGH priority (5x boost)
                # This ensures new words appear frequently until practiced
                weights.append((word, 10.0))  # Very high weight for unseen words
            else:
                # Base weight from difficulty score
                weight = stats['difficulty']
                
                # Boost weight for words with low consecutive correct count
                # Words with 0 consecutive correct get highest boost
                consecutive = stats['consecutive_correct']
                if consecutive == 0:
                    weight += 3.0  # High priority for words never correct in a row
                elif consecutive == 1:
                    weight += 1.5  # Medium-high priority
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
                
                # Ensure minimum weight of 0.1 for practiced words
                weight = max(weight, 0.1)
                
                weights.append((word, weight))
        
        return weights
    
    def remove_word(self, word: str):
        """Remove a word from the database and its similarity entries."""
        word_lower = word.lower()
        
        # Remove similarities first
        self.remove_word_similarities(word_lower)
        
        # Remove the word itself
        self.cursor.execute("DELETE FROM word_stats WHERE word = ?", (word_lower,))
        self.conn.commit()
    
    def get_sentences(self, word: str) -> Optional[List[str]]:
        """Get cached example sentences for a word."""
        self.cursor.execute(
            "SELECT sentences FROM word_sentences WHERE word = ?",
            (word.lower(),)
        )
        row = self.cursor.fetchone()
        if row:
            # Sentences are stored as newline-separated text
            return row[0].split('\n')
        return None
    
    def save_sentences(self, word: str, sentences: List[str]):
        """Save example sentences for a word."""
        sentences_text = '\n'.join(sentences)
        self.cursor.execute("""
            INSERT OR REPLACE INTO word_sentences (word, sentences, created_at)
            VALUES (?, ?, ?)
        """, (word.lower(), sentences_text, datetime.now()))
        self.conn.commit()
    
    def get_definition(self, word: str) -> Optional[str]:
        """Get cached definition for a word."""
        self.cursor.execute(
            "SELECT definition FROM word_definitions WHERE word = ?",
            (word.lower(),)
        )
        row = self.cursor.fetchone()
        if row:
            return row[0]
        return None
    
    def save_definition(self, word: str, definition: str):
        """Save definition for a word."""
        self.cursor.execute("""
            INSERT OR REPLACE INTO word_definitions (word, definition, created_at)
            VALUES (?, ?, ?)
        """, (word.lower(), definition, datetime.now()))
        self.conn.commit()
    
    def sync_with_word_list(self, word_list: List[str], remove_missing: bool = True, 
                           update_similarities: bool = False, progress_callback=None) -> Tuple[int, int, int]:
        """
        Sync the database with the provided word list.
        - Adds any words present in the list but missing in the DB
        - If remove_missing=True, removes any words in the DB not present in the list
        - If update_similarities=True, calculates similarities for new words
        
        Args:
            word_list: List of words to sync
            remove_missing: Whether to remove words not in the list
            update_similarities: Whether to calculate similarities for new words
            progress_callback: Optional callback for similarity calculation progress
            
        Returns: (added_count, removed_count, similarities_added)
        """
        normalized = sorted(set(w.strip().lower() for w in word_list if w and w.strip()))
        added_count = 0
        removed_count = 0
        similarities_added = 0
        
        # Fetch existing words
        self.cursor.execute("SELECT word FROM word_stats")
        existing = {row[0] for row in self.cursor.fetchall()}
        target = set(normalized)
        
        to_add = list(target - existing)
        to_remove = list(existing - target) if remove_missing else []
        
        # Use a transaction to ensure atomicity
        try:
            self.conn.execute('BEGIN')
            
            # Remove words not in CSV (including their similarities)
            if to_remove:
                for word in to_remove:
                    self.cursor.execute(
                        "DELETE FROM word_similarity WHERE word1 = ? OR word2 = ?",
                        (word, word)
                    )
                    self.cursor.execute(
                        "DELETE FROM word_sentences WHERE word = ?",
                        (word,)
                    )
                    self.cursor.execute(
                        "DELETE FROM word_definitions WHERE word = ?",
                        (word,)
                    )
                self.cursor.executemany(
                    "DELETE FROM word_stats WHERE word = ?",
                    [(w,) for w in to_remove]
                )
                removed_count = len(to_remove)
            
            # Add missing words
            if to_add:
                now = datetime.now()
                self.cursor.executemany(
                    "INSERT OR IGNORE INTO word_stats (word, last_seen) VALUES (?, ?)",
                    [(w, now) for w in to_add]
                )
                added_count = len(to_add)
            
            self.conn.commit()
            
            # Calculate similarities for new words if requested
            if update_similarities and to_add:
                all_words_in_db = list(target)  # All words that should now be in DB
                
                for new_word in to_add:
                    sims = self.update_similarity_for_word(
                        new_word, 
                        all_words_in_db, 
                        progress_callback
                    )
                    similarities_added += sims
                    
        except sqlite3.Error as e:
            self.conn.rollback()
            raise sqlite3.Error(f"Failed to sync word list: {e}") from e
        
        return added_count, removed_count, similarities_added
    
    def save_embedding(self, word: str, embedding: 'numpy.ndarray'):
        """
        Save word embedding vector to database.
        
        Args:
            word: The word
            embedding: Numpy array of embedding vector
        """
        import pickle
        
        word = word.lower()
        # Serialize numpy array to bytes
        embedding_bytes = pickle.dumps(embedding)
        
        self.cursor.execute("""
            INSERT OR REPLACE INTO word_embeddings (word, embedding, created_at)
            VALUES (?, ?, ?)
        """, (word, embedding_bytes, datetime.now()))
        self.conn.commit()
    
    def get_embedding(self, word: str) -> Optional['numpy.ndarray']:
        """
        Retrieve embedding for a word.
        
        Args:
            word: The word to get embedding for
            
        Returns:
            Numpy array of embedding vector, or None if not found
        """
        import pickle
        
        word = word.lower()
        self.cursor.execute("""
            SELECT embedding FROM word_embeddings WHERE word = ?
        """, (word,))
        
        row = self.cursor.fetchone()
        if row:
            return pickle.loads(row[0])
        return None
    
    def get_semantic_similar_words(
        self, 
        word: str, 
        min_similarity: float = 0.5, 
        limit: int = 20
    ) -> List[Tuple[str, float]]:
        """
        Get words semantically similar to the given word using cosine similarity
        of embeddings.
        
        Args:
            word: The word to find similar words for
            min_similarity: Minimum cosine similarity (0-1)
            limit: Maximum number of similar words to return
            
        Returns:
            List of (word, similarity_score) tuples, sorted by similarity descending
        """
        import numpy as np
        
        word = word.lower()
        
        # Get embedding for the query word
        query_embedding = self.get_embedding(word)
        if query_embedding is None:
            return []
        
        # Get all embeddings from database
        self.cursor.execute("""
            SELECT word, embedding FROM word_embeddings
            WHERE word != ?
        """, (word,))
        
        import pickle
        similarities = []
        
        for row in self.cursor.fetchall():
            other_word = row[0]
            other_embedding = pickle.loads(row[1])
            
            # Calculate cosine similarity
            dot_product = np.dot(query_embedding, other_embedding)
            norm_query = np.linalg.norm(query_embedding)
            norm_other = np.linalg.norm(other_embedding)
            
            if norm_query > 0 and norm_other > 0:
                similarity = dot_product / (norm_query * norm_other)
                
                if similarity >= min_similarity:
                    similarities.append((other_word, float(similarity)))
        
        # Sort by similarity (highest first) and return top results
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:limit]
    
    def has_embeddings(self) -> bool:
        """Check if any embeddings exist in database."""
        self.cursor.execute("SELECT COUNT(*) FROM word_embeddings")
        count = self.cursor.fetchone()[0]
        return count > 0
    
    def get_words_without_embeddings(self, word_list: List[str]) -> List[str]:
        """
        Get list of words that don't have embeddings yet.
        
        Args:
            word_list: List of words to check
            
        Returns:
            List of words missing embeddings
        """
        if not word_list:
            return []
        
        normalized = [w.lower() for w in word_list]
        placeholders = ','.join('?' * len(normalized))
        
        self.cursor.execute(f"""
            SELECT word FROM word_embeddings
            WHERE word IN ({placeholders})
        """, normalized)
        
        words_with_embeddings = {row[0] for row in self.cursor.fetchall()}
        return [w for w in normalized if w not in words_with_embeddings]
    
    def close(self):
        """Close database connection."""
        self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
