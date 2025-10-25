"""
Main spelling practice application with TTS, batch learning, and progress tracking.
"""
import csv
import random
import os
import sys
import platform
from typing import List, Tuple
from colorama import Fore, Style, init
import requests
from gtts import gTTS
from database import WordDatabase
import tempfile
import difflib
import time
import threading
import subprocess
import contextlib

# Suppress pygame welcome message (if we end up using it)
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
        self.temp_audio_file = None
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
        
        self.play_obj = None  # For tracking playback
    
    def load_words(self) -> List[str]:
        """Load words from CSV file."""
        words = []
        
        if not os.path.exists(self.words_file):
            print(f"{Fore.YELLOW}Warning: {self.words_file} not found. Creating it...")
            with open(self.words_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['word'])
            return words
        
        try:
            with open(self.words_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None)  # Skip header if exists
                
                for row in reader:
                    if row and row[0].strip():  # Skip empty rows
                        words.append(row[0].strip().lower())
        except Exception as e:
            print(f"{Fore.RED}Error loading words: {e}")
        
        return words
    
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
                    with contextlib.suppress(Exception):
                        proc.kill()
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
        Select a batch of words using weighted random selection.
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
        
        # Select batch using weighted sampling WITHOUT replacement
        # Efraimidis-Spirakis algorithm: key = U^(1/weight), take top-k by key
        pairs = []
        for w, wt in zip(words, weights):
            wt = max(float(wt), 1e-9)
            u = random.random()
            key = u ** (1.0 / wt)
            pairs.append((key, w))
        pairs.sort(reverse=True)
        batch = [word for _, word in pairs[: self.batch_size]]
        
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
        
        print(f"\n{Fore.CYAN}{'='*70}")
        print(f"{Fore.YELLOW}📊 Your Progress Statistics")
        print(f"{Fore.CYAN}{'='*70}\n")
        
        print(f"{Fore.WHITE}{'Word':<20} {'Correct':<10} {'Wrong':<10} {'Total':<10} {'Accuracy':<10}")
        print(f"{Fore.CYAN}{'-'*70}")
        
        for stat in stats:
            word = stat['word']
            correct = stat['correct']
            incorrect = stat['incorrect']
            total = stat['total']
            accuracy = (correct / total * 100) if total > 0 else 0
            
            color = Fore.GREEN if accuracy >= 80 else Fore.YELLOW if accuracy >= 50 else Fore.RED
            
            print(f"{color}{word:<20} {correct:<10} {incorrect:<10} {total:<10} {accuracy:.1f}%")
        
        print(f"{Fore.CYAN}{'='*70}\n")
    
    def run(self):
        """Main application loop."""
        print(f"{Fore.CYAN}{'='*50}")
        print(f"{Fore.YELLOW}✏️  Welcome to Spelling Practice! ✏️")
        print(f"{Fore.CYAN}{'='*50}\n")
        
        # Load words
        words = self.load_words()
        # Sync database to match words.csv exactly (add new, remove deleted)
        try:
            added, removed = self.db.sync_with_word_list(words, remove_missing=True)
            if added or removed:
                print(f"{Fore.GREEN}Synced word list with database: +{added} added, -{removed} removed")
        except Exception as e:
            print(f"{Fore.YELLOW}Warning: Could not sync database with words.csv: {e}{Style.RESET_ALL}")
        
        if not words:
            print(f"{Fore.RED}No words found in {self.words_file}!")
            print(f"{Fore.YELLOW}Please add words to the file and try again.")
            print(f"{Fore.YELLOW}You can use: python word_manager.py add <word>\n")
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
