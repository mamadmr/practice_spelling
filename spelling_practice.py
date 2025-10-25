"""Command-line spelling practice app with audio and progress tracking."""
import csv
import random
import os
import sys
import platform
from typing import List, Tuple
from colorama import Fore, Style, init
from gtts import gTTS
from database import WordDatabase
import difflib
import subprocess

# Suppress pygame welcome message
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"
import pygame


# Initialize colorama for colored terminal output
init(autoreset=True)


class SpellingPractice:
    def __init__(self, words_file: str = "words.csv", batch_size: int = 4):
        """Initialize the spelling practice application."""
        self.words_file = words_file
        self.batch_size = batch_size
        self.db = WordDatabase()
        self.use_sapi = False  # Prefer Windows SAPI when available
        
        # Create cache directory for audio files
        self.cache_dir = "audio_cache"
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        
        # Audio initialization strategy:
        # - On Windows: Prefer SAPI (pywin32) for in-process, reliable speech (no external apps)
        # - Else: use pygame for cached mp3 playback
        self.audio_available = False
        if platform.system() == "Windows":
            try:
                # Import inside try so non-Windows or missing package won't fail import
                import win32com.client  # type: ignore
                self._win32 = win32com.client
                self.sapi = self._win32.Dispatch("SAPI.SpVoice")
                self.use_sapi = True
                self.audio_available = True
            except Exception as e:
                print(f"{Fore.YELLOW}Windows SAPI not available ({e}). Falling back to mixer.{Style.RESET_ALL}")
                # Fall back to pygame mixer
                try:
                    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
                    self.audio_available = True
                except Exception as e2:
                    print(f"{Fore.YELLOW}Audio system not available: {e2}{Style.RESET_ALL}")
                    self.audio_available = False
        else:
            # Non-Windows platforms: use pygame mixer
            try:
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
                self.audio_available = True
            except Exception as e:
                print(f"{Fore.YELLOW}Audio system not available: {e}{Style.RESET_ALL}")
                self.audio_available = False
    
    def load_words(self) -> List[str]:
        """Load words from CSV file, remove duplicates, and save cleaned version."""
        words: List[str] = []
        
        if not os.path.exists(self.words_file):
            print(f"{Fore.YELLOW}Warning: {self.words_file} not found. Creating it...")
            with open(self.words_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['word'])
            return words
        
        try:
            with open(self.words_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                first = next(reader, None)
                # Only skip first row if it's the 'word' header
                if first is not None and (len(first) > 0) and first[0].strip().lower() != 'word':
                    if first[0].strip():
                        words.append(first[0].strip().lower())
                
                for row in reader:
                    if row and row[0].strip():  # Skip empty rows
                        words.append(row[0].strip().lower())
        except FileNotFoundError:
            print(f"{Fore.RED}Error: {self.words_file} not found!")
        except PermissionError:
            print(f"{Fore.RED}Error: Permission denied reading {self.words_file}")
        except csv.Error as e:
            print(f"{Fore.RED}Error reading CSV file: {e}")
        except Exception as e:
            print(f"{Fore.RED}Unexpected error loading words: {e}")
        
        # Check for duplicates and clean if found
        original_count = len(words)
        unique_words = sorted(set(words))  # Remove duplicates and sort
        duplicates_found = original_count - len(unique_words)
        
        if duplicates_found > 0:
            print(f"{Fore.YELLOW}Found {duplicates_found} duplicate word(s) - cleaning...{Style.RESET_ALL}")
            # Save cleaned version back to file
            try:
                with open(self.words_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['word'])
                    for word in unique_words:
                        writer.writerow([word])
                print(f"{Fore.GREEN}✓ Removed duplicates and saved cleaned list ({len(unique_words)} unique words){Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}Error saving cleaned words: {e}{Style.RESET_ALL}")
        
        return unique_words
    
    def pronounce_word(self, word: str, use_tts: bool = True) -> bool:
        """Pronounce the word using TTS. On Windows, prefer SAPI; otherwise use cached gTTS with pygame.
        Returns True if successful."""
        if not use_tts or not self.audio_available:
            return False
        
        # Windows SAPI via pywin32: no downloads, in-process speech
        if self.use_sapi:
            try:
                # 1 = SVSFlagsAsync (speak asynchronously)
                self.sapi.Speak(word, 1)
                # Wait up to 3 seconds for it to finish speaking (non-blocking beyond this)
                try:
                    self.sapi.WaitUntilDone(3000)
                except Exception:
                    pass
                return True
            except Exception as e:
                print(f"{Fore.YELLOW}SAPI speech failed: {e}{Style.RESET_ALL}")
                # Fall through to gTTS cache + mixer as a fallback
        
        # Windows without pywin32: use PowerShell System.Speech (no external media player UI)
        if platform.system() == "Windows":
            try:
                ps_cmd = [
                    "powershell.exe",
                    "-NoProfile",
                    "-Command",
                    (
                        "Add-Type -AssemblyName System.Speech; "
                        "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                        "$s.Rate=0; "
                        "$text=[Console]::In.ReadToEnd(); "
                        "$s.Speak($text)"
                    )
                ]
                proc = subprocess.Popen(
                    ps_cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=0x08000000 if hasattr(subprocess, 'STARTF_USESHOWWINDOW') else 0
                )
                try:
                    proc.communicate(input=word.encode('utf-8'), timeout=4)
                except subprocess.TimeoutExpired:
                    # If it takes too long, terminate gracefully
                    try:
                        proc.kill()
                    except Exception:
                        pass
                return True
            except Exception as e:
                print(f"{Fore.YELLOW}PowerShell speech failed: {e}{Style.RESET_ALL}")
                # Fall back to gTTS cache + mixer below
        
        # Fallback path (non-Windows or SAPI unavailable): gTTS with mp3 cache + pygame playback
        try:
            safe_word = "".join(c for c in word.lower() if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_word = safe_word.replace(' ', '_')
            cache_file = os.path.join(self.cache_dir, f"{safe_word}.mp3")
            
            if not os.path.exists(cache_file):
                tts = gTTS(text=word, lang='en', slow=False)
                tts.save(cache_file)
            
            return self._play_audio(cache_file)
        except Exception as e:
            print(f"\n{Fore.YELLOW}Could not play audio: {e}")
            print(f"{Fore.CYAN}Word: {word}{Style.RESET_ALL}")
            return False
    
    def _play_audio(self, audio_file: str) -> bool:
        """
        Start playback using pygame.mixer.music in a fire-and-forget (non-blocking) manner.
        We intentionally do NOT wait/poll; we let the OS/audio thread play while we continue.
        """
        try:
            # Stop any previous music to avoid overlap
            try:
                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.stop()
            except Exception:
                pass

            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            # Return immediately; playback continues in background
            return True

        except Exception as e:
            print(f"\n{Fore.YELLOW}Audio error: {e}{Style.RESET_ALL}")
            return False
    
    def show_difference(self, user_input: str, correct_word: str):
        """Show the difference between user input and correct word with colors."""
        print(f"\n{Fore.CYAN}Your answer: ", end="")
        
        # Use difflib to find differences
        matcher = difflib.SequenceMatcher(None, user_input.lower(), correct_word.lower())
        
        user_colored = []
        correct_colored = []
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                user_colored.append(f"{Fore.GREEN}{user_input[i1:i2]}")
                correct_colored.append(f"{Fore.GREEN}{correct_word[j1:j2]}")
            elif tag == 'replace':
                user_colored.append(f"{Fore.RED}{user_input[i1:i2]}")
                correct_colored.append(f"{Fore.GREEN}{correct_word[j1:j2]}")
            elif tag == 'delete':
                user_colored.append(f"{Fore.RED}{user_input[i1:i2]}")
            elif tag == 'insert':
                correct_colored.append(f"{Fore.GREEN}{correct_word[j1:j2]}")
        
        print(''.join(user_colored) + Style.RESET_ALL)
        print(f"{Fore.CYAN}Correct:     {''.join(correct_colored)}{Style.RESET_ALL}")
    
    def select_batch(self, all_words: List[str]) -> List[str]:
        """
        Select a batch of words using weighted random selection with similarity grouping.
        Words with similar spellings are grouped together in the same batch.
        Words with more mistakes get higher probability.
        """
        if not all_words:
            return []
        
        if len(all_words) <= self.batch_size:
            batch = all_words.copy()
            random.shuffle(batch)
            return batch
        
        # Get weighted words from database
        weighted_words = self.db.get_weighted_words(all_words)
        
        # Extract words and weights
        words = [w[0] for w in weighted_words]
        weights = [w[1] for w in weighted_words]
        
        # First, select a seed word using weighted selection
        total_weight = sum(weights)
        if total_weight <= 0:
            # Fallback to uniform if all weights are zero
            seed_word = random.choice(words)
        else:
            # Weighted random choice
            rand_val = random.uniform(0, total_weight)
            cumsum = 0
            seed_word = words[0]
            for w, wt in zip(words, weights):
                cumsum += wt
                if cumsum >= rand_val:
                    seed_word = w
                    break
        
        # Get similar words to the seed word
        similar_words = self.db.get_similar_words(
            seed_word, 
            min_similarity=0.3,  # Minimum 30% similarity
            limit=self.batch_size * 3  # Get more candidates
        )
        
        # Create candidate pool: seed + similar words (that are in all_words)
        candidate_pool = [seed_word]
        words_set = set(all_words)
        
        for similar_word, similarity in similar_words:
            if similar_word in words_set and similar_word != seed_word:
                candidate_pool.append(similar_word)
            if len(candidate_pool) >= self.batch_size * 2:
                break
        
        # If we don't have enough similar words, add some random words
        if len(candidate_pool) < self.batch_size:
            remaining_words = [w for w in words if w not in candidate_pool]
            random.shuffle(remaining_words)
            candidate_pool.extend(remaining_words[:self.batch_size * 2 - len(candidate_pool)])
        
        # Now select from candidate pool using weights
        # Get weights for candidates
        word_to_weight = {w: wt for w, wt in weighted_words}
        candidate_weights = [word_to_weight.get(w, 1.0) for w in candidate_pool]
        
        # Use weighted sampling for final batch selection
        if len(candidate_pool) <= self.batch_size:
            batch = candidate_pool
        else:
            # Efraimidis-Spirakis algorithm: key = U^(1/weight), take top-k by key
            pairs = []
            for w, wt in zip(candidate_pool, candidate_weights):
                wt = max(float(wt), 1e-9)
                u = random.random()
                key = u ** (1.0 / wt)
                pairs.append((key, w))
            pairs.sort(reverse=True)
            batch = [word for _, word in pairs[:self.batch_size]]
        
        # Shuffle the batch so order is random
        random.shuffle(batch)
        
        return batch
    
    def practice_batch(self, batch: List[str], enable_audio: bool = True) -> bool:
        """
        Practice a batch of words.
        Returns True if all words were spelled correctly, False otherwise.
        """
        print(f"\n{Fore.CYAN}{'='*50}")
        print(f"{Fore.YELLOW}New batch of {len(batch)} words!")
        print(f"{Fore.CYAN}{'='*50}\n")
        
        all_correct = True
        results = []
        
        for i, word in enumerate(batch, 1):
            print(f"{Fore.MAGENTA}Word {i}/{len(batch)}")
            
            # Pronounce the word
            if enable_audio:
                print(f"{Fore.CYAN}🔊 Playing pronunciation...", end="", flush=True)
                audio_success = self.pronounce_word(word, use_tts=enable_audio)
                if audio_success:
                    print(f" {Fore.GREEN}✓")
                else:
                    print(f" {Fore.YELLOW}(Audio failed, showing word: {word})")
            else:
                print(f"{Fore.YELLOW}Word: {word}")
            
            # Get user input
            print(f"{Fore.WHITE}Type the word: ", end="")
            user_input = input().strip()
            
            # Check answer
            is_correct = user_input.lower() == word.lower()
            results.append((word, is_correct))
            
            if is_correct:
                print(f"{Fore.GREEN}✓ Correct!\n")
            else:
                print(f"{Fore.RED}✗ Incorrect!")
                self.show_difference(user_input, word)
                print()
                all_correct = False
        
        # Update database with results
        for word, is_correct in results:
            self.db.update_word_result(word, is_correct)
        
        # Show batch summary
        correct_count = sum(1 for _, correct in results if correct)
        print(f"\n{Fore.CYAN}{'='*50}")
        print(f"{Fore.YELLOW}Batch Summary: {correct_count}/{len(batch)} correct")
        print(f"{Fore.CYAN}{'='*50}\n")
        
        if all_correct:
            print(f"{Fore.GREEN}🎉 Perfect! Moving to next batch!\n")
        else:
            print(f"{Fore.YELLOW}📚 Let's try this batch again!\n")
        
        return all_correct
    
    def show_statistics(self):
        """Display overall statistics."""
        stats = self.db.get_all_stats()
        
        if not stats:
            print(f"{Fore.YELLOW}No statistics yet. Start practicing!\n")
            return
        
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.YELLOW}📊 Your Progress Statistics")
        print(f"{Fore.CYAN}{'='*80}\n")
        
        print(f"{Fore.WHITE}{'Word':<20} {'Correct':<10} {'Wrong':<10} {'Total':<10} {'Streak':<10} {'Accuracy':<10}")
        print(f"{Fore.CYAN}{'-'*80}")
        
        for stat in stats:
            word = stat['word']
            correct = stat['correct']
            incorrect = stat['incorrect']
            total = stat['total']
            streak = stat['consecutive_correct']
            accuracy = (correct / total * 100) if total > 0 else 0
            
            color = Fore.GREEN if accuracy >= 80 else Fore.YELLOW if accuracy >= 50 else Fore.RED
            
            # Add visual indicator for streak
            streak_display = f"{streak}🔥" if streak >= 3 else str(streak)
            
            print(f"{color}{word:<20} {correct:<10} {incorrect:<10} {total:<10} {streak_display:<10} {accuracy:.1f}%")
        
        print(f"{Fore.CYAN}{'='*80}\n")
        print(f"{Fore.CYAN}💡 Tip: Words with low streak counts will appear more often in practice.{Style.RESET_ALL}\n")
    
    def run(self):
        """Main application loop."""
        print(f"{Fore.CYAN}{'='*50}")
        print(f"{Fore.YELLOW}✏️  Welcome to Spelling Practice! ✏️")
        print(f"{Fore.CYAN}{'='*50}\n")
        
        # Load words
        words = self.load_words()
        # Sync database to match words.csv exactly (add new, remove deleted)
        try:
            # First check if we need to initialize similarities
            self.db.cursor.execute("SELECT COUNT(*) FROM word_similarity")
            similarity_count = self.db.cursor.fetchone()[0]
            
            needs_full_init = similarity_count == 0 and len(words) > 0
            
            if needs_full_init:
                print(f"{Fore.YELLOW}Initializing word similarity matrix for the first time...")
                print(f"{Fore.YELLOW}This will calculate spelling similarity between all word pairs.")
                print(f"{Fore.CYAN}Total words: {len(words)}")
                
                # Progress bar for initial similarity calculation
                total_pairs = (len(words) * (len(words) - 1)) // 2
                print(f"{Fore.CYAN}Total pairs to calculate: {total_pairs}\n")
                
                def progress_callback(current, total, word1, word2):
                    # Simple progress bar
                    percent = (current / total) * 100 if total > 0 else 0
                    bar_length = 40
                    filled = int(bar_length * current / total) if total > 0 else 0
                    bar = '█' * filled + '░' * (bar_length - filled)
                    print(f"\r{Fore.GREEN}[{bar}] {percent:.1f}% ({current}/{total}) - {word1} ↔ {word2}     ", end='', flush=True)
                
                added, removed, sims_added = self.db.sync_with_word_list(
                    words, 
                    remove_missing=True,
                    update_similarities=False
                )
                
                # Now calculate all similarities with progress
                self.db.update_all_similarities(words, progress_callback=progress_callback)
                print(f"\n{Fore.GREEN}✓ Similarity matrix initialized successfully!\n")
                
            else:
                # Regular sync with similarity updates for new words only
                print(f"{Fore.CYAN}Syncing word list...")
                
                def new_word_progress(current, total, other_word):
                    percent = (current / total) * 100 if total > 0 else 0
                    bar_length = 30
                    filled = int(bar_length * current / total) if total > 0 else 0
                    bar = '█' * filled + '░' * (bar_length - filled)
                    print(f"\r{Fore.YELLOW}  [{bar}] {percent:.1f}% - comparing with: {other_word}     ", end='', flush=True)
                
                added, removed, sims_added = self.db.sync_with_word_list(
                    words, 
                    remove_missing=True,
                    update_similarities=True,
                    progress_callback=new_word_progress
                )
                
                if added or removed or sims_added:
                    if added:
                        print(f"\n{Fore.GREEN}  ✓ Added {added} new word(s)")
                    if removed:
                        print(f"{Fore.YELLOW}  ✓ Removed {removed} word(s)")
                    if sims_added:
                        print(f"{Fore.CYAN}  ✓ Calculated {sims_added} similarity scores")
                    print()
                    
        except Exception as e:
            print(f"{Fore.YELLOW}Warning: Could not sync database: {e}{Style.RESET_ALL}")
        
        if not words:
            print(f"{Fore.RED}No words found in {self.words_file}!")
            print(f"{Fore.YELLOW}Please add words to {self.words_file} and run again.\n")
            return
        
        print(f"{Fore.GREEN}Loaded {len(words)} words from {self.words_file}\n")
        
        # Ask about audio
        print(f"{Fore.YELLOW}Enable audio pronunciation? (y/n): ", end="")
        enable_audio = input().strip().lower() in ['y', 'yes', '']
        
        try:
            while True:
                # Show menu
                print(f"\n{Fore.CYAN}{'='*50}")
                print(f"{Fore.YELLOW}Main Menu:")
                print(f"{Fore.WHITE}1. Start practice")
                print(f"{Fore.WHITE}2. View statistics")
                print(f"{Fore.WHITE}3. Reload words")
                print(f"{Fore.WHITE}4. Toggle audio (currently: {'ON' if enable_audio else 'OFF'})")
                print(f"{Fore.WHITE}5. Exit")
                print(f"{Fore.CYAN}{'='*50}")
                print(f"{Fore.WHITE}Choose option: ", end="")
                
                choice = input().strip()
                
                if choice == '1':
                    # Select and practice batch
                    batch = self.select_batch(words)
                    batch_complete = False
                    
                    while not batch_complete:
                        batch_complete = self.practice_batch(batch, enable_audio)
                        
                        if not batch_complete:
                            print(f"{Fore.YELLOW}Press Enter to retry this batch (or 'q' to quit): ", end="")
                            if input().strip().lower() == 'q':
                                break
                
                elif choice == '2':
                    self.show_statistics()
                
                elif choice == '3':
                    words = self.load_words()
                    try:
                        added, removed = self.db.sync_with_word_list(words, remove_missing=True)
                        print(f"{Fore.GREEN}Reloaded {len(words)} words! Synced: +{added} added, -{removed} removed\n")
                    except Exception as e:
                        print(f"{Fore.YELLOW}Reloaded {len(words)} words, but sync failed: {e}{Style.RESET_ALL}\n")
                
                elif choice == '4':
                    enable_audio = not enable_audio
                    print(f"{Fore.GREEN}Audio {'enabled' if enable_audio else 'disabled'}!\n")
                
                elif choice == '5':
                    print(f"{Fore.GREEN}Goodbye! Keep practicing! 📚\n")
                    break
                
                else:
                    print(f"{Fore.RED}Invalid option. Please try again.\n")
        
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Practice interrupted. Goodbye!\n")
        
        finally:
            # Clean up pygame mixer
            if self.audio_available:
                try:
                    pygame.mixer.quit()
                except:
                    pass
            self.db.close()


if __name__ == "__main__":
    app = SpellingPractice(batch_size=4)
    app.run()
