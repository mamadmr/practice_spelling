"""Command-line spelling practice app with audio and progress tracking."""
import os

# Set tokenizer parallelism early to avoid fork warnings
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

import csv
import random
import sys
import platform
import json
import threading
from typing import List, Tuple, Optional
from colorama import Fore, Style, init
from gtts import gTTS
from database import WordDatabase
import difflib
import subprocess
import requests

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
        self.use_native_tts = False  # Track if we're using native TTS (no cache needed)
        self.ollama_available = False  # Track if Ollama is available
        
        # Check if Ollama is available
        self._check_ollama()
        
        # Create cache directory for audio files
        self.cache_dir = "audio_cache"
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        
        # Audio initialization strategy:
        # - On macOS: Prefer native 'say' command (no cache needed)
        # - On Windows: Prefer SAPI (pywin32) for in-process, reliable speech (no cache needed)
        # - Else: use pygame for cached mp3 playback
        self.audio_available = False
        
        # Check for native TTS first (macOS or Windows)
        if platform.system() == "Darwin":
            # macOS has native 'say' command
            self.use_native_tts = True
            self.audio_available = True
        elif platform.system() == "Windows":
            try:
                # Import inside try so non-Windows or missing package won't fail import
                import win32com.client  # type: ignore
                self._win32 = win32com.client
                self.sapi = self._win32.Dispatch("SAPI.SpVoice")
                self.use_sapi = True
                self.use_native_tts = True
                self.audio_available = True
            except Exception as e:
                print(f"{Fore.YELLOW}Windows SAPI not available ({e}). Falling back to cached audio.{Style.RESET_ALL}")
                # Will use cached audio, initialize pygame mixer
                try:
                    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
                    self.audio_available = True
                except Exception as e2:
                    print(f"{Fore.YELLOW}Audio system not available: {e2}{Style.RESET_ALL}")
                    self.audio_available = False
        else:
            # Non-Windows/macOS platforms: use pygame mixer with cached audio
            try:
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
                self.audio_available = True
            except Exception as e:
                print(f"{Fore.YELLOW}Audio system not available: {e}{Style.RESET_ALL}")
                self.audio_available = False
    
    def _check_ollama(self):
        """Check if Ollama is available and running."""
        try:
            response = requests.get('http://localhost:11434/api/tags', timeout=2)
            if response.status_code == 200:
                self.ollama_available = True
            else:
                self.ollama_available = False
        except Exception:
            self.ollama_available = False
    
    def prefetch_word_content(self, word: str) -> dict:
        """
        Prefetch both definition and sentences for a word in parallel.
        Returns a dict with 'definition' and 'sentences' keys.
        This can be called in a background thread while waiting for user input.
        
        Thread-safe: Creates its own database connection to avoid SQLite threading issues.
        """
        result = {
            'definition': '',
            'sentences': []
        }
        
        if not self.ollama_available:
            return result
        
        # Create a thread-safe database connection for this thread
        from database import WordDatabase
        thread_db = WordDatabase()
        
        try:
            # Check cache first for both
            cached_def = thread_db.get_definition(word)
            cached_sentences = thread_db.get_sentences(word)
            
            if cached_def and cached_sentences:
                result['definition'] = cached_def
                result['sentences'] = cached_sentences
                return result
            
            # Generate what's missing
            if not cached_def:
                definition = self._generate_definition_internal(word)
                if definition:
                    thread_db.save_definition(word, definition)
                    result['definition'] = definition
            else:
                result['definition'] = cached_def
                
            if not cached_sentences:
                sentences = self._generate_sentences_internal(word)
                if sentences:
                    thread_db.save_sentences(word, sentences)
                    result['sentences'] = sentences
            else:
                result['sentences'] = cached_sentences
        finally:
            # Close the thread-specific connection
            thread_db.close()
        
        return result
    
    def _generate_sentences_internal(self, word: str) -> List[str]:
        """
        Internal method to generate sentences without checking cache.
        Used by both generate_sentences and prefetch_word_content.
        """
        try:
            prompt = f"""Analyze the word "{word}" and determine how many distinct meanings it has.

Generate example sentences following these STRICT rules:
- If the word has ONLY ONE common meaning: Generate EXACTLY 1 sentence
- If the word has 2 distinct meanings: Generate EXACTLY 2 sentences  
- If the word has 3 distinct meanings: Generate EXACTLY 3 sentences
- If the word has 4 distinct meanings: Generate EXACTLY 4 sentences
- If the word has 5+ distinct meanings: Generate EXACTLY 5 sentences

Each sentence MUST show a DIFFERENT meaning. Do NOT generate multiple sentences for the same meaning.

Examples:
- "cat" (one meaning: animal) → 1 sentence
- "run" (multiple: jog, operate, flow) → 3-5 sentences
- "accommodate" (one meaning: provide space/help) → 1 sentence
- "bear" (two meanings: animal, tolerate) → 2 sentences

Return ONLY the numbered sentences. No explanations.

Word: "{word}" """

            response = requests.post(
                'http://localhost:11434/api/generate',
                json={
                    'model': 'llama3.2',
                    'prompt': prompt,
                    'stream': False,
                    'options': {
                        'temperature': 0.7,
                        'top_p': 0.9,
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                text = result.get('response', '')
                
                # Parse sentences from the response
                sentences = []
                for line in text.strip().split('\n'):
                    line = line.strip()
                    # Remove numbering like "1.", "2.", etc.
                    if line and len(line) > 3:
                        # Remove leading numbers and dots
                        cleaned = line.lstrip('0123456789.-)')
                        cleaned = cleaned.strip()
                        if cleaned and len(cleaned) > 10:  # Ensure it's a real sentence
                            sentences.append(cleaned)
                
                # Limit to maximum 5 sentences
                sentences = sentences[:5]
                
                return sentences
            else:
                return []
                
        except Exception as e:
            return []
    
    def _generate_definition_internal(self, word: str) -> str:
        """
        Internal method to generate definition without checking cache.
        Used by both get_definition and prefetch_word_content.
        """
        if not self.ollama_available:
            return ""
        
        try:
            prompt = f"""Define the word "{word}" in one clear, concise sentence.

Rules:
1. Provide a simple dictionary-style definition
2. If the word has multiple meanings, mention all briefly in ONE sentence
3. Keep it short (1-2 lines maximum)
4. Use simple language
5. Return ONLY the definition, no extra text

Example format: "Run means to move quickly on foot; to operate or manage; to flow."

Word: "{word}" """

            response = requests.post(
                'http://localhost:11434/api/generate',
                json={
                    'model': 'llama3.2',
                    'prompt': prompt,
                    'stream': False,
                    'options': {
                        'temperature': 0.5,
                        'top_p': 0.9,
                    }
                },
                timeout=20
            )
            
            if response.status_code == 200:
                result = response.json()
                definition = result.get('response', '').strip()
                
                # Clean up the definition
                if definition.startswith('"') and definition.endswith('"'):
                    definition = definition[1:-1]
                
                if definition and len(definition) > 5:
                    return definition
            
            return ""
                
        except Exception as e:
            return ""
    
    def generate_sentences(self, word: str) -> List[str]:
        """
        Generate example sentences for a word using Ollama Llama3.2.
        Returns cached sentences if available, otherwise generates new ones.
        Number of sentences varies based on how many distinct meanings the word has (1-5).
        """
        # Check cache first
        cached = self.db.get_sentences(word)
        if cached:
            return cached
        
        # Check if Ollama is available
        if not self.ollama_available:
            return []
        
        try:
            prompt = f"""Analyze the word "{word}" and determine how many distinct meanings it has.

Generate example sentences following these STRICT rules:
- If the word has ONLY ONE common meaning: Generate EXACTLY 1 sentence
- If the word has 2 distinct meanings: Generate EXACTLY 2 sentences  
- If the word has 3 distinct meanings: Generate EXACTLY 3 sentences
- If the word has 4 distinct meanings: Generate EXACTLY 4 sentences
- If the word has 5+ distinct meanings: Generate EXACTLY 5 sentences

Each sentence MUST show a DIFFERENT meaning. Do NOT generate multiple sentences for the same meaning.

Examples:
- "cat" (one meaning: animal) → 1 sentence
- "run" (multiple: jog, operate, flow) → 3-5 sentences
- "accommodate" (one meaning: provide space/help) → 1 sentence
- "bear" (two meanings: animal, tolerate) → 2 sentences

Return ONLY the numbered sentences. No explanations.

Word: "{word}" """

            response = requests.post(
                'http://localhost:11434/api/generate',
                json={
                    'model': 'llama3.2',
                    'prompt': prompt,
                    'stream': False,
                    'options': {
                        'temperature': 0.7,
                        'top_p': 0.9,
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                text = result.get('response', '')
                
                # Parse sentences from the response
                sentences = []
                for line in text.strip().split('\n'):
                    line = line.strip()
                    # Remove numbering like "1.", "2.", etc.
                    if line and len(line) > 3:
                        # Remove leading numbers and dots
                        cleaned = line.lstrip('0123456789.-)')
                        cleaned = cleaned.strip()
                        if cleaned and len(cleaned) > 10:  # Ensure it's a real sentence
                            sentences.append(cleaned)
                
                # Limit to maximum 5 sentences
                sentences = sentences[:5]
                
                # Save to cache if we got valid sentences
                if sentences:
                    self.db.save_sentences(word, sentences)
                
                return sentences
            else:
                return []
                
        except Exception as e:
            print(f"\n{Fore.YELLOW}Could not generate sentences: {e}{Style.RESET_ALL}")
            return []
    
    def get_definition(self, word: str) -> str:
        """
        Get a concise definition of the word using Ollama Llama3.2.
        Returns cached definition if available, otherwise generates a new one.
        """
        # Check cache first
        cached = self.db.get_definition(word)
        if cached:
            return cached
        
        # Check if Ollama is available
        if not self.ollama_available:
            return ""
        
        try:
            prompt = f"""Define the word "{word}" in one clear, concise sentence.

Rules:
1. Provide a simple dictionary-style definition
2. If the word has multiple meanings, mention all briefly in ONE sentence
3. Keep it short (1-2 lines maximum)
4. Use simple language
5. Return ONLY the definition, no extra text

Example format: "Run means to move quickly on foot; to operate or manage; to flow."

Word: "{word}" """

            response = requests.post(
                'http://localhost:11434/api/generate',
                json={
                    'model': 'llama3.2',
                    'prompt': prompt,
                    'stream': False,
                    'options': {
                        'temperature': 0.5,
                        'top_p': 0.9,
                    }
                },
                timeout=20
            )
            
            if response.status_code == 200:
                result = response.json()
                definition = result.get('response', '').strip()
                
                # Clean up the definition
                # Remove quotes if present
                if definition.startswith('"') and definition.endswith('"'):
                    definition = definition[1:-1]
                
                # Save to cache if we got a valid definition
                if definition and len(definition) > 5:
                    self.db.save_definition(word, definition)
                    return definition
                else:
                    return ""
            else:
                return ""
                
        except Exception as e:
            return ""
    
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
    
    def download_audio_files(self, words: List[str], force: bool = False) -> Tuple[int, int]:
        """
        Pre-download all audio files for the word list.
        Only needed for systems using gTTS (not native TTS like macOS 'say' or Windows SAPI).
        
        Args:
            words: List of words to download audio for
            force: If True, re-download even if cache exists
            
        Returns:
            (downloaded_count, skipped_count)
        """
        # Skip if using native TTS (macOS 'say' or Windows SAPI)
        if self.use_native_tts:
            return (0, len(words))
        
        print(f"\n{Fore.CYAN}Checking audio cache for {len(words)} words...")
        
        downloaded = 0
        skipped = 0
        failed = []
        
        for idx, word in enumerate(words):
            # Show progress
            percent = ((idx + 1) / len(words)) * 100
            bar_length = 40
            filled = int(bar_length * (idx + 1) / len(words))
            bar = '█' * filled + '░' * (bar_length - filled)
            print(f"\r{Fore.GREEN}[{bar}] {percent:.1f}% - {word:<20}", end='', flush=True)
            
            safe_word = "".join(c for c in word.lower() if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_word = safe_word.replace(' ', '_')
            cache_file = os.path.join(self.cache_dir, f"{safe_word}.mp3")
            
            # Skip if file exists and not forcing re-download
            if os.path.exists(cache_file) and not force:
                skipped += 1
                continue
            
            # Download audio file
            try:
                tts = gTTS(text=word, lang='en', slow=False)
                tts.save(cache_file)
                downloaded += 1
            except Exception as e:
                failed.append((word, str(e)))
        
        # Clear progress line
        print(f"\r{' ' * 80}\r", end='')
        
        # Summary
        if downloaded > 0:
            print(f"{Fore.GREEN}✓ Downloaded {downloaded} audio file(s)")
        if skipped > 0:
            print(f"{Fore.CYAN}✓ Skipped {skipped} cached file(s)")
        if failed:
            print(f"{Fore.YELLOW}⚠ Failed to download {len(failed)} file(s):")
            for word, error in failed[:5]:  # Show first 5 failures
                print(f"  - {word}: {error}")
            if len(failed) > 5:
                print(f"  ... and {len(failed) - 5} more")
        
        return (downloaded, skipped)
    
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
        
        # macOS: use native 'say' command
        if platform.system() == "Darwin":
            try:
                proc = subprocess.Popen(
                    ["say", word],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                try:
                    proc.communicate(timeout=4)
                except subprocess.TimeoutExpired:
                    try:
                        proc.kill()
                    except Exception:
                        pass
                return True
            except Exception as e:
                print(f"{Fore.YELLOW}macOS speech failed: {e}{Style.RESET_ALL}")
                # Fall back to gTTS cache + mixer below
        
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
                # Only use creationflags on Windows
                kwargs = {
                    'stdin': subprocess.PIPE,
                    'stdout': subprocess.DEVNULL,
                    'stderr': subprocess.DEVNULL
                }
                if platform.system() == "Windows":
                    kwargs['creationflags'] = 0x08000000  # CREATE_NO_WINDOW
                
                proc = subprocess.Popen(ps_cmd, **kwargs)
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
                # Correct letters in green
                user_colored.append(f"{Fore.GREEN}{user_input[i1:i2]}")
                correct_colored.append(f"{Fore.GREEN}{correct_word[j1:j2]}")
            elif tag == 'replace':
                # Wrong letters in red (user) and yellow (correct - should be different)
                user_colored.append(f"{Fore.RED}{user_input[i1:i2]}")
                correct_colored.append(f"{Fore.YELLOW}{correct_word[j1:j2]}")
            elif tag == 'delete':
                # Extra letters in user input (red with strikethrough effect)
                user_colored.append(f"{Fore.RED}{user_input[i1:i2]}")
            elif tag == 'insert':
                # Missing letters in user input (shown in magenta in correct word)
                correct_colored.append(f"{Fore.MAGENTA}{correct_word[j1:j2]}")
        
        print(''.join(user_colored) + Style.RESET_ALL)
        print(f"{Fore.CYAN}Correct:     {''.join(correct_colored)}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}             {Fore.GREEN}Green{Fore.WHITE}=correct, {Fore.YELLOW}Yellow{Fore.WHITE}=wrong letter, {Fore.MAGENTA}Magenta{Fore.WHITE}=missing{Style.RESET_ALL}")
    
    def select_batch(self, all_words: List[str]) -> List[str]:
        """
        Select a batch of words using weighted random selection with similarity grouping.
        With 50% probability: Words with similar spellings are grouped together.
        With 50% probability: Words with similar meanings are grouped together (semantic).
        Words with more mistakes get higher probability.
        Filters out words that have been practiced 4+ times today.
        """
        if not all_words:
            return []
        
        # Filter out words that hit the daily limit (4 times per day)
        available_words = self.db.filter_daily_limit(all_words, max_daily=4)
        
        if not available_words:
            print(f"{Fore.YELLOW}All words have been practiced 4 times today!")
            print(f"{Fore.CYAN}Come back tomorrow for more practice. 📚{Style.RESET_ALL}")
            return []
        
        if len(available_words) <= self.batch_size:
            batch = available_words.copy()
            random.shuffle(batch)
            return batch
        
        # Get weighted words from database (only for available words)
        weighted_words = self.db.get_weighted_words(available_words)
        
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
        
        # Randomly choose between spelling similarity and semantic similarity (50/50)
        use_semantic = random.random() < 0.5 and self.db.has_embeddings()
        
        if use_semantic:
            # Get semantically similar words (meaning-based)
            similar_words = self.db.get_semantic_similar_words(
                seed_word,
                min_similarity=0.5,  # Minimum 50% semantic similarity
                limit=self.batch_size * 3  # Get more candidates
            )
        else:
            # Get spelling-similar words (traditional approach)
            similar_words = self.db.get_similar_words(
                seed_word, 
                min_similarity=0.3,  # Minimum 30% spelling similarity
                limit=self.batch_size * 3  # Get more candidates
            )
        
        # Create candidate pool: seed + similar words (that are in available_words)
        candidate_pool = [seed_word]
        words_set = set(available_words)
        
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
            
            # Check if content is already cached (instant lookup)
            cached_definition = self.db.get_definition(word) if self.ollama_available else None
            cached_sentences = self.db.get_sentences(word) if self.ollama_available else None
            
            # Start prefetching AI content in background thread ONLY if not cached
            prefetch_result = {'definition': cached_definition or '', 'sentences': cached_sentences or []}
            prefetch_thread = None
            needs_generation = False
            
            if self.ollama_available and (not cached_definition or not cached_sentences):
                needs_generation = True
                def prefetch_worker():
                    result = self.prefetch_word_content(word)
                    prefetch_result.update(result)
                
                prefetch_thread = threading.Thread(target=prefetch_worker, daemon=True)
                prefetch_thread.start()
            
            # Get user input (allow replay by pressing Enter)
            # While waiting, the prefetch thread is working in the background
            user_input = ""
            while not user_input:
                print(f"{Fore.WHITE}Type the word (or press Enter to replay audio): ", end="")
                user_input = input().strip()
                
                # If empty, replay audio
                if not user_input:
                    if enable_audio:
                        print(f"{Fore.CYAN}🔊 Replaying...", end="", flush=True)
                        audio_success = self.pronounce_word(word, use_tts=enable_audio)
                        if audio_success:
                            print(f" {Fore.GREEN}✓")
                        else:
                            print(f" {Fore.YELLOW}(Audio failed)")
                    else:
                        print(f"{Fore.YELLOW}Audio is disabled. Word: {word}")
            
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
            
            # Show AI-generated content (definition and sentences)
            if self.ollama_available:
                # If content was already cached, display instantly
                if not needs_generation:
                    definition = prefetch_result.get('definition', '')
                    sentences = prefetch_result.get('sentences', [])
                else:
                    # Show loading message while waiting for generation
                    if prefetch_thread and prefetch_thread.is_alive():
                        print(f"{Fore.YELLOW}⏳ Loading AI content...", end="", flush=True)
                        prefetch_thread.join(timeout=15)  # Wait max 15 seconds
                        print(f"\r{' ' * 50}\r", end="", flush=True)  # Clear loading message
                    
                    # Get content from prefetch result
                    definition = prefetch_result.get('definition', '')
                    sentences = prefetch_result.get('sentences', [])
                
                # Display definition
                if definition:
                    print(f"{Fore.MAGENTA}📖 Definition: {definition}{Style.RESET_ALL}")
                
                # Display example sentences
                if sentences:
                    meaning_word = "meaning" if len(sentences) == 1 else "meanings"
                    print(f"{Fore.CYAN}📝 Example sentence{'s' if len(sentences) > 1 else ''} ({len(sentences)} {meaning_word}):")
                    for i, sentence in enumerate(sentences, 1):
                        print(f"{Fore.WHITE}   {i}. {sentence}")
                else:
                    print(f"{Fore.YELLOW}📝 (Could not generate sentences)")
                print()
        
        # Update database with results (but don't update daily count yet)
        for word, is_correct in results:
            self.db.update_word_result(word, is_correct, update_daily_count=False)
        
        # Only increment daily count if the entire batch was completed successfully
        if all_correct:
            for word, _ in results:
                self.db.increment_daily_count(word)
        
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
        
        from datetime import datetime
        today = datetime.now().date()
        
        # Calculate summary statistics
        # Load words if not already loaded
        if not hasattr(self, 'words') or not self.words:
            self.words = self.load_words()
        
        total_words_in_file = len(self.words)
        # Count only words that have been actually practiced (total > 0)
        practiced_words = sum(1 for stat in stats if stat['total'] > 0)
        unseen_words = total_words_in_file - practiced_words
        
        print(f"\n{Fore.CYAN}{'='*95}")
        print(f"{Fore.YELLOW}📊 Your Progress Statistics")
        print(f"{Fore.CYAN}{'='*95}\n")
        
        # Show summary at the top
        print(f"{Fore.WHITE}Total words: {Fore.GREEN}{total_words_in_file}")
        print(f"{Fore.WHITE}Practiced: {Fore.CYAN}{practiced_words}")
        print(f"{Fore.WHITE}Unseen: {Fore.YELLOW}{unseen_words}")
        print()
        
        print(f"{Fore.WHITE}{'Word':<20} {'Correct':<8} {'Wrong':<8} {'Total':<8} {'Streak':<8} {'Accuracy':<10} {'Today':<12}")
        print(f"{Fore.CYAN}{'-'*95}")
        
        for stat in stats:
            word = stat['word']
            correct = stat['correct']
            incorrect = stat['incorrect']
            total = stat['total']
            streak = stat['consecutive_correct']
            accuracy = (correct / total * 100) if total > 0 else 0
            
            # Get daily practice count for today
            practice_date = stat.get('practice_date')
            daily_count = stat.get('daily_practice_count', 0)
            
            # Check if practiced today
            if practice_date and str(practice_date) == str(today):
                today_display = f"{daily_count}/4 times"
            else:
                today_display = "0/4 times"
            
            # Color based on accuracy
            color = Fore.GREEN if accuracy >= 80 else Fore.YELLOW if accuracy >= 50 else Fore.RED
            
            # Add visual indicator for streak
            streak_display = f"{streak}🔥" if streak >= 3 else str(streak)
            
            print(f"{color}{word:<20} {correct:<8} {incorrect:<8} {total:<8} {streak_display:<8} {accuracy:.1f}%{' '*3} {today_display}")
        
        print(f"{Fore.CYAN}{'='*95}\n")
        print(f"{Fore.CYAN}💡 Tip: Each word can be practiced up to 4 times per day.")
        print(f"{Fore.CYAN}💡 Words with low streak counts will appear more often in practice.{Style.RESET_ALL}\n")
    
    def initialize_embeddings(self, words: List[str]):
        """
        Initialize word embeddings using sentence-transformers.
        Only generates embeddings for words that don't have them yet.
        
        Args:
            words: List of words to generate embeddings for
        """
        try:
            from sentence_transformers import SentenceTransformer
            import numpy as np
        except ImportError:
            print(f"{Fore.YELLOW}⚠ sentence-transformers not installed - semantic similarity disabled{Style.RESET_ALL}")
            print(f"{Fore.CYAN}  Install with: pip install sentence-transformers{Style.RESET_ALL}")
            return
        
        # Check which words need embeddings
        words_without_embeddings = self.db.get_words_without_embeddings(words)
        
        if not words_without_embeddings:
            return  # All words already have embeddings
        
        print(f"{Fore.YELLOW}Generating embeddings for {len(words_without_embeddings)} word(s)...")
        print(f"{Fore.CYAN}Using local sentence-transformer model (all-MiniLM-L6-v2)...")
        
        try:
            # Load the model (will download on first use, then cache locally)
            model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Generate embeddings for all words that need them
            total = len(words_without_embeddings)
            for idx, word in enumerate(words_without_embeddings):
                # Progress bar
                percent = ((idx + 1) / total) * 100
                bar_length = 40
                filled = int(bar_length * (idx + 1) / total)
                bar = '█' * filled + '░' * (bar_length - filled)
                print(f"\r{Fore.GREEN}[{bar}] {percent:.1f}% - {word:<20}", end='', flush=True)
                
                # Generate embedding
                embedding = model.encode(word)
                
                # Save to database
                self.db.save_embedding(word, embedding)
            
            print(f"\n{Fore.GREEN}✓ Embeddings generated successfully!\n")
            
        except Exception as e:
            print(f"\n{Fore.YELLOW}⚠ Could not generate embeddings: {e}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}  Semantic similarity will be disabled{Style.RESET_ALL}\n")
    
    def run(self):
        """Main application loop."""
        print(f"{Fore.CYAN}{'='*50}")
        print(f"{Fore.YELLOW}✏️  Welcome to Spelling Practice! ✏️")
        print(f"{Fore.CYAN}{'='*50}\n")
        
        # Check Ollama status
        if self.ollama_available:
            print(f"{Fore.GREEN}✓ Ollama connected - example sentences enabled!{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}⚠ Ollama not available - example sentences disabled{Style.RESET_ALL}")
            print(f"{Fore.CYAN}  To enable: Start Ollama with 'llama3.2' model{Style.RESET_ALL}")
        print()
        
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
        
        # Initialize embeddings for semantic similarity
        self.initialize_embeddings(words)
        
        if not words:
            print(f"{Fore.RED}No words found in {self.words_file}!")
            print(f"{Fore.YELLOW}Please add words to {self.words_file} and run again.\n")
            return
        
        print(f"{Fore.GREEN}Loaded {len(words)} words from {self.words_file}\n")
        
        # Automatically download missing audio files if not using native TTS
        if not self.use_native_tts and self.audio_available:
            # Check how many files are missing
            missing_count = 0
            for word in words:
                safe_word = "".join(c for c in word.lower() if c.isalnum() or c in (' ', '-', '_')).strip()
                safe_word = safe_word.replace(' ', '_')
                cache_file = os.path.join(self.cache_dir, f"{safe_word}.mp3")
                if not os.path.exists(cache_file):
                    missing_count += 1
            
            if missing_count > 0:
                print(f"{Fore.YELLOW}Found {missing_count} word(s) without cached audio.")
                print(f"{Fore.CYAN}Downloading missing audio files for offline practice...")
                downloaded, skipped = self.download_audio_files(words)
                if downloaded > 0:
                    print(f"{Fore.GREEN}✓ Downloaded {downloaded} new audio file(s)!")
                print(f"{Fore.GREEN}✓ Audio cache ready! Practice will work offline.{Style.RESET_ALL}\n")
            else:
                print(f"{Fore.GREEN}✓ All audio files cached ({len(words)} words). Ready for offline practice!{Style.RESET_ALL}\n")
        elif self.use_native_tts:
            print(f"{Fore.CYAN}ℹ Using native TTS - no audio cache needed!{Style.RESET_ALL}\n")
        
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
                print(f"{Fore.WHITE}5. Download audio cache")
                print(f"{Fore.WHITE}6. Clear audio cache")
                print(f"{Fore.WHITE}7. Exit")
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
                        print(f"{Fore.GREEN}Reloaded {len(words)} words! Synced: +{added} added, -{removed} removed")
                        
                        # Auto-download missing audio files
                        if not self.use_native_tts and self.audio_available and added > 0:
                            print(f"{Fore.CYAN}Checking for missing audio files...")
                            downloaded, skipped = self.download_audio_files(words)
                            if downloaded > 0:
                                print(f"{Fore.GREEN}✓ Downloaded {downloaded} new audio file(s)!")
                        print()
                    except Exception as e:
                        print(f"{Fore.YELLOW}Reloaded {len(words)} words, but sync failed: {e}{Style.RESET_ALL}\n")
                
                elif choice == '4':
                    enable_audio = not enable_audio
                    print(f"{Fore.GREEN}Audio {'enabled' if enable_audio else 'disabled'}!\n")
                
                elif choice == '5':
                    if self.use_native_tts:
                        print(f"{Fore.CYAN}ℹ You're using native TTS - no audio cache needed!")
                        print(f"{Fore.CYAN}Audio is generated on-the-fly without downloads.{Style.RESET_ALL}\n")
                    else:
                        print(f"{Fore.YELLOW}Force re-download? (y/n): ", end="")
                        force = input().strip().lower() in ['y', 'yes']
                        downloaded, skipped = self.download_audio_files(words, force=force)
                        if downloaded > 0 or skipped > 0:
                            print(f"{Fore.GREEN}✓ Audio cache updated!{Style.RESET_ALL}\n")
                
                elif choice == '6':
                    if self.use_native_tts:
                        print(f"{Fore.CYAN}ℹ You're using native TTS - no audio cache to clear!{Style.RESET_ALL}\n")
                    else:
                        print(f"{Fore.YELLOW}⚠ This will delete all cached audio files. Continue? (y/n): ", end="")
                        if input().strip().lower() in ['y', 'yes']:
                            import shutil
                            if os.path.exists(self.cache_dir):
                                file_count = len([f for f in os.listdir(self.cache_dir) if f.endswith('.mp3')])
                                shutil.rmtree(self.cache_dir)
                                os.makedirs(self.cache_dir)
                                print(f"{Fore.GREEN}✓ Cleared {file_count} audio file(s){Style.RESET_ALL}\n")
                            else:
                                print(f"{Fore.YELLOW}No audio cache to clear{Style.RESET_ALL}\n")
                        else:
                            print(f"{Fore.YELLOW}Cancelled{Style.RESET_ALL}\n")
                
                elif choice == '7':
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
