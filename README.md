# Spelling Practice

A smart command-line spelling practice app with audio pronunciation, progress tracking, and intelligent word grouping based on spelling similarity and semantic meaning.

## Features

✅ **Cross-Platform** - Works seamlessly on macOS, Windows, and Linux  
✅ **Native Audio** - Uses platform-specific TTS (macOS `say`, Windows SAPI, or gTTS)  
✅ **Zero-Wait AI** - Definitions & sentences generate while you type (background prefetch)  
✅ **AI Definitions** - Shows concise word definitions in color (Ollama Llama3.2)  
✅ **Smart AI Examples** - Shows 1-5 sentences based on word meanings (Ollama Llama3.2)  
✅ **Semantic Grouping** - 50% chance to group words by meaning, 50% by spelling (NEW!)  
✅ **Replay Audio** - Press Enter to hear the word again before spelling  
✅ **Offline Mode** - Pre-download all audio files for internet-free practice  
✅ **Audio Pronunciation** - Hear each word before spelling it  
✅ **Progress Tracking** - Tracks correct/incorrect answers and difficulty  
✅ **Smart Batching** - Groups similar words together (e.g., "cat", "bat", "hat")  
✅ **Automatic Sync** - Just edit `words.csv` and the system handles everything  
✅ **Duplicate Removal** - Automatically detects and removes duplicate words  
✅ **Similarity Matrix** - Calculates spelling similarity between all words  
✅ **Weighted Selection** - Prioritizes words you struggle with  
✅ **Statistics** - View detailed performance metrics  

---

## Quick Start

### 1. Install Dependencies

**macOS/Linux:**
```bash
pip3 install -r requirements.txt
```

**Windows:**
```powershell
pip install -r requirements.txt
```

> **Note:** On macOS, audio uses the native `say` command (no extra setup needed!). On Windows, it will try to use pywin32 or PowerShell TTS. All platforms fall back to gTTS + pygame if needed.

### 1b. Install Ollama (Optional but Recommended)

For AI-powered example sentences:

1. **Install Ollama**: Visit [https://ollama.ai](https://ollama.ai) and download for your platform
2. **Start Ollama**: 
   ```bash
   ollama serve
   ```
3. **Pull Llama3.2 model**:
   ```bash
   ollama pull llama3.2
   ```

The app will automatically detect if Ollama is available and enable example sentences!

### 2. Add Your Words

Simply edit `words.csv` and add your words (one per line):

```csv
word
accommodate
separate
definitely
beautiful
receive
```

### 3. Start Practicing

**macOS/Linux:**
```bash
python3 spelling_practice.py
# Or use the launcher script:
./start_practice.sh
```

**Windows:**
```powershell
python spelling_practice.py
# Or double-click: start_practice.bat
```

**That's it!** The system automatically:
- ✅ Detects new words in `words.csv`
- ✅ Removes words deleted from `words.csv`
- ✅ Calculates spelling similarities
- ✅ Shows progress bars for all operations
- ✅ Groups similar words in practice batches
- ✅ Offers to pre-download audio for offline practice (if not using native TTS)

---

## Offline Audio Mode

### How It Works

The app intelligently handles audio based on your platform:

**🍎 macOS** - Uses native `say` command
- ✅ No internet required (built-in)
- ✅ No pre-downloading needed
- ✅ Works offline automatically

**🪟 Windows** - Uses SAPI or PowerShell TTS
- ✅ No internet required (built-in)
- ✅ No pre-downloading needed
- ✅ Works offline automatically

**🐧 Linux or fallback systems** - Uses gTTS with cache
- 📥 First time: Downloads audio files
- 💾 Stores in `audio_cache/` folder
- ✅ Subsequent practice works offline

### Pre-downloading Audio

When you first run the app (on systems using gTTS), you'll be asked:

```
Do you want to pre-download audio for all words? (y/n):
```

**Choose Yes** to:
- Download all audio files at once
- Practice completely offline afterward
- Avoid slow downloads during practice

**Choose No** to:
- Download audio on-demand during practice
- Save disk space
- Still works, but needs internet

### Managing Audio Cache

From the main menu, you can:

**Option 5: Download audio cache**
- Pre-download or update all audio files
- Force re-download if files are corrupted
- Only shown for gTTS systems (not macOS/Windows native TTS)

**Option 6: Clear audio cache**
- Delete all cached audio files
- Free up disk space
- Files will be re-downloaded on-demand

### Storage Size

For reference:
- **382 words** (your current list) ≈ **15-20 MB** of audio files
- **100 words** ≈ **4-5 MB**
- **1000 words** ≈ **40-50 MB**

---

## How It Works

### Automatic Synchronization

Every time you run `spelling_practice.py`, it automatically:

1. **Loads words** from `words.csv`
2. **Removes duplicates** - cleans and saves the file
3. **Syncs database** - adds new words, removes deleted words
4. **Calculates similarities** - only for new words (fast!)
5. **Ready to practice** - with smart word grouping

**No manual commands needed!** Just edit `words.csv` and run.

### Smart Word Grouping

The system calculates **similarity scores** between all words based on:
- **Levenshtein distance** (spelling edits needed)
- **Common prefixes** (words starting the same)
- **Common suffixes** (words ending the same)
- **Length similarity** (similar length words)

**Example:** If you're practicing "cat", the batch might include "bat", "hat", "mat" - helping you learn similar spelling patterns together!

### Weighted Selection

Words are selected based on:
- **New words** - 5x boost! Unseen words get highest priority to ensure quick learning
- **Difficulty score** - increases with mistakes
- **Consecutive correct** - prioritizes words you haven't mastered
  - 0 correct in a row: +3.0 boost
  - 1 correct in a row: +1.5 boost
  - 2 correct in a row: +0.5 boost
  - 3+ correct: standard difficulty only
- **Last seen** - words not practiced recently get priority

**New words appear ~5 times more often** than mastered words, helping you learn new vocabulary quickly!

### Progress Bars

All long operations show progress bars:

```
Initializing word similarity matrix...
[████████████████████████████████] 100.0% (1225/1225) - zebra ↔ zone
✓ Similarity matrix initialized successfully!
```

```
Syncing word list...
  [████████████████████████████████] 100.0% - comparing with: tiger
  ✓ Added 3 new word(s)
  ✓ Calculated 147 similarity scores
```

---

## Usage

### Main Menu

When you run `python spelling_practice.py`, you'll see:

```
==================================================
Main Menu:
1. Start practice
2. View statistics
3. Reload words
4. Toggle audio (currently: ON)
5. Download audio cache
6. Clear audio cache
7. Exit
==================================================
```

**Note:** Options 5-6 are only shown/relevant for systems using cached audio (gTTS). On macOS and Windows with native TTS, these options will inform you that caching isn't needed.

### During Practice

1. **Listen** - Word is pronounced (or shown if audio is off)
2. **Type** - Enter your spelling
   - 💡 **Tip**: Press Enter without typing to replay the audio!
3. **Feedback** - See if correct, with color-coded differences
4. **Learn** - View AI-generated definition (magenta) and sentences (1-5 based on meanings)
5. **Repeat** - Practice full batch until mastered

Wrong answers are shown with color-coded differences:
```
Your answer:  recieve
Correct:      receive
              ^^^   ^^^
```

**Replay Feature**: If you press Enter without typing anything, the audio will replay. This lets you hear the word as many times as you need before attempting to spell it!

**Definition & Examples** (with Ollama): After each word, you'll see:

1. **Definition** (in magenta):
```
📖 Definition: Run means to move quickly on foot; to be in operation; a sequence of events.
```

2. **Example Sentences** (1-5 based on meanings):

**Single meaning word:**
```
📝 Example sentence (1 meaning):
   1. The hotel staff will accommodate your request for a room.
```

**Multiple meaning word:**
```
📝 Example sentences (3 meanings):
   1. The kids love to run around in the park.
   2. She will run for office next year.
   3. The marathon runners were training to run 26 miles.
```

Both definitions and sentences are generated once and cached forever - no repeated API calls!
The number of sentences automatically matches the word's complexity.

### Statistics View

See detailed stats for all words:
- Correct/incorrect counts
- Total attempts
- Accuracy percentage
- Consecutive correct streak
- Difficulty score

---

## Files

### Core Files
- **`spelling_practice.py`** - Main application (run this!)
- **`database.py`** - Database management and similarity calculations
- **`words.csv`** - Your word list (edit this to add/remove words)
- **`progress.db`** - SQLite database (auto-created)

### Optional Files
- **`word_manager.py`** - Advanced word management (optional)
- **`test_similarity.py`** - Test similarity features (optional)
- **`test_macos_audio.py`** - Test macOS audio systems (optional)
- **`test_sentences.py`** - Test Ollama sentence generation (optional)
- **`start_practice.bat`** - Windows launcher (optional, double-click to run)
- **`start_practice.sh`** - macOS/Linux launcher (optional, double-click or `./start_practice.sh`)

### Directories
- **`audio_cache/`** - Cached audio files (auto-created, gTTS systems only)
- **`__pycache__/`** - Python cache (auto-created)

### Database Tables
- **`word_stats`** - Progress tracking for each word
- **`word_similarity`** - Spelling similarity matrix
- **`word_definitions`** - Cached word definitions from Ollama
- **`word_sentences`** - Cached example sentences from Ollama

---

## Database Schema

### Tables

#### `word_stats`
Tracks progress for each word:
- `word` - The word (primary key)
- `correct_count` - Times spelled correctly
- `incorrect_count` - Times spelled incorrectly
- `total_appearances` - Total practice attempts
- `difficulty_score` - Dynamic difficulty (0.1 to 10.0)
- `consecutive_correct` - Current streak of correct answers
- `last_seen` - Last practice timestamp

#### `word_similarity`
Stores spelling similarity between word pairs:
- `word1` - First word
- `word2` - Second word
- `similarity_score` - Similarity (0.0 to 1.0)

Indexed for fast lookups. Stores both directions (word1→word2 and word2→word1).

#### `word_definitions`
Caches AI-generated definitions:
- `word` - The word (primary key)
- `definition` - Concise definition in one sentence
- `created_at` - When definition was generated

Definitions are cached to avoid repeated Ollama API calls.

#### `word_sentences`
Caches AI-generated example sentences:
- `word` - The word (primary key)
- `sentences` - 1-5 example sentences based on meanings (newline-separated)
- `created_at` - When sentences were generated

Sentences are intelligently generated (more meanings = more sentences) and cached forever to avoid repeated Ollama API calls.

---

## Performance

### Time Complexity
- **Initial setup** (first run): O(n²) - calculates all pairs
- **Adding words**: O(n) - only calculates for new words
- **Practice session**: O(n log n) - fast batch selection

### Measured Performance

| Words | Word Pairs | First Run | Adding 1 Word | Database Size |
|-------|------------|-----------|---------------|---------------|
| 25    | 300        | < 1 sec   | < 1 sec       | ~100 KB       |
| 50    | 1,225      | 2-3 sec   | < 1 sec       | ~500 KB       |
| 100   | 4,950      | 8-10 sec  | 1-2 sec       | ~2 MB         |
| 200   | 19,900     | 30-40 sec | 2-3 sec       | ~8 MB         |

**Note:** First run is one-time. Subsequent runs are instant!

---

## Examples

### Example 1: Fresh Start

```powershell
# Create words.csv with your words
echo word > words.csv
echo accommodate >> words.csv
echo separate >> words.csv
echo definitely >> words.csv

# Run practice (auto-initializes everything)
python spelling_practice.py
```

Output:
```
Initializing word similarity matrix for the first time...
Total words: 3
[████████████████████████████████] 100.0% - separate ↔ definitely
✓ Similarity matrix initialized successfully!

Loaded 3 words from words.csv
```

### Example 2: Adding Words

```powershell
# Just add words to words.csv
echo beautiful >> words.csv
echo receive >> words.csv

# Run practice (auto-detects and adds new words)
python spelling_practice.py
```

Output:
```
Syncing word list...
  [████████████████████████████████] 100.0% - comparing with: definitely
  ✓ Added 2 new word(s)
  ✓ Calculated 6 similarity scores

Loaded 5 words from words.csv
```

### Example 3: Removing Words

```powershell
# Edit words.csv and remove some words

# Run practice (auto-removes from database)
python spelling_practice.py
```

Output:
```
Syncing word list...
  ✓ Removed 2 word(s)

Loaded 3 words from words.csv
```

---

## Advanced Features

### Testing Similarities

```powershell
python test_similarity.py
```

Shows:
- Most similar word pairs in your database
- Similarity scores
- Search for words similar to a specific word

### Manual Word Management (Optional)

While editing `words.csv` is recommended, you can use:

```powershell
# Add words programmatically
python word_manager.py add "word1" "word2"

# Remove a word
python word_manager.py remove "word1"

# Check word list
python word_manager.py check

# View all words
python word_manager.py list
```

### Database Queries

Explore your data with SQLite:

```powershell
sqlite3 progress.db
```

Example queries:
```sql
-- Most similar word pairs
SELECT word1, word2, similarity_score 
FROM word_similarity 
WHERE word1 < word2 
ORDER BY similarity_score DESC 
LIMIT 10;

-- Words similar to "cat"
SELECT word2, similarity_score 
FROM word_similarity 
WHERE word1 = 'cat' 
ORDER BY similarity_score DESC;

-- Hardest words
SELECT word, difficulty_score, incorrect_count 
FROM word_stats 
ORDER BY difficulty_score DESC 
LIMIT 10;
```

---

## Troubleshooting

### Testing Ollama sentences
Run the sentence test script:
```bash
python3 test_sentences.py
```

This will check:
- If Ollama is running
- If llama3.2 model is available
- Generate test sentences
- Verify caching works

### Ollama not available
**Problem:** Example sentences not showing  
**Solution:**
1. Install Ollama from https://ollama.ai
2. Start the service: `ollama serve`
3. Pull the model: `ollama pull llama3.2`
4. Restart the spelling practice app

The app works fine without Ollama - you just won't see example sentences.

### Testing audio on macOS
Run the audio test script to verify all systems work:
```bash
python3 test_macos_audio.py
```

This will test:
- Native macOS `say` command
- pygame mixer
- gTTS (Google Text-to-Speech)

### No audio on macOS
**Problem:** Audio not playing  
**Solution:** 
1. The native `say` command should work by default (try `say hello` in Terminal)
2. If not working, ensure pygame is installed: `pip3 install pygame`
3. Run the test script to diagnose: `python3 test_macos_audio.py`

### No audio on Windows
**Problem:** Audio not playing  
**Solution:** Install pywin32: `pip install pywin32`

### No audio on Linux
**Problem:** Audio not playing  
**Solution:** Install pygame and audio dependencies:
```bash
sudo apt-get install python3-pygame libsdl2-mixer-2.0-0
pip3 install pygame
```

### Progress bar not visible
**Problem:** Progress bar shows weird characters  
**Solution:** 
- **macOS/Linux:** Use a modern terminal (Terminal.app, iTerm2, or similar)
- **Windows:** Use PowerShell or Windows Terminal (not CMD or IDLE)

### Database locked error
**Problem:** "database is locked"  
**Solution:** Close other programs accessing `progress.db`

### Slow initial setup
**Problem:** First run takes long  
**Solution:** This is normal! It's a one-time calculation. Subsequent runs are fast.

### Words not syncing
**Problem:** Changes to words.csv not reflected  
**Solution:** Ensure proper CSV format (one word per line, optional "word" header)

---

## Dependencies

- **colorama** - Colored terminal output
- **gtts** - Google Text-to-Speech
- **pygame** - Audio playback
- **pywin32** (Windows only) - Native Windows speech API

Optional:
- **requests** - Online dictionary checking
- **pyspellchecker** - Spell checking
- **wordfreq** - Word frequency data

### Platform-Specific Audio

The app intelligently selects the best audio system for your platform:

- **macOS** 🍎 - Uses native `say` command (built-in, zero configuration!)
  - Fast, high-quality speech synthesis
  - No downloads or external dependencies needed
  - Falls back to gTTS + pygame if needed

- **Windows** 🪟 - Uses pywin32 SAPI or PowerShell System.Speech
  - Tries Windows SAPI first (requires pywin32)
  - Falls back to PowerShell TTS (built-in)
  - Finally falls back to gTTS + pygame

- **Linux** 🐧 - Uses gTTS with pygame mixer
  - Downloads and caches audio files
  - Works with any audio-capable Linux system

- **All platforms** - Graceful fallback chain ensures audio always works

---

## Tips for Best Results

1. **Start small** - Begin with 20-30 words
2. **Practice daily** - Consistency improves retention
3. **Use audio** - Hearing words helps memory
4. **Pre-download audio** - For uninterrupted offline practice (gTTS systems)
5. **Review stats** - Focus on words with low accuracy
6. **Add similar words** - Learn spelling patterns together
7. **Be patient** - First run calculates similarities (one-time)
8. **New words prioritized** - The system automatically focuses on unseen words until you master them

---

## Example Workflow

**macOS/Linux:**
```bash
# Day 1: Setup
pip3 install -r requirements.txt
# Edit words.csv with 25 words
python3 spelling_practice.py

# Day 2-7: Practice
python3 spelling_practice.py
# Practice, view stats, repeat

# Week 2: Add more words
# Edit words.csv, add 10 more words
python3 spelling_practice.py
# System auto-adds and calculates similarities

# Month 1: Review
python3 test_similarity.py
# See which words are similar
# View statistics to track improvement
```

**Windows:**
```powershell
# Day 1: Setup
pip install -r requirements.txt
# Edit words.csv with 25 words
python spelling_practice.py

# Day 2-7: Practice
python spelling_practice.py
# Practice, view stats, repeat

# Week 2: Add more words
# Edit words.csv, add 10 more words
python spelling_practice.py
# System auto-adds and calculates similarities

# Month 1: Review
python test_similarity.py
# See which words are similar
# View statistics to track improvement
```

---

## How Similarity Works

### Similarity Algorithm

```
similarity = base_similarity + prefix_bonus + suffix_bonus + length_bonus
```

**Components:**
1. **Base similarity** - Normalized Levenshtein distance
2. **Prefix bonus** - Up to +0.2 for common starting letters
3. **Suffix bonus** - Up to +0.2 for common ending letters  
4. **Length bonus** - Up to +0.1 for similar length

### Example Scores

| Word 1    | Word 2    | Score | Why                          |
|-----------|-----------|-------|------------------------------|
| cat       | bat       | 0.83  | One letter different         |
| house     | mouse     | 0.70  | Same ending, one diff        |
| receive   | believe   | 0.65  | Similar pattern              |
| beautiful | wonderful | 0.40  | Both end in 'ful'            |
| apple     | orange    | 0.20  | Very different               |

### Benefits of Grouping

**Traditional approach:** Random words  
- "elephant", "cat", "beautiful", "the"
- No pattern recognition
- Harder to remember

**Similarity-based approach:** Grouped words  
- "cat", "bat", "hat", "mat"
- Clear spelling pattern
- Easier to learn and remember

---

## License

MIT License - Feel free to use and modify!

---

## Contributing

Found a bug? Have a feature idea? Open an issue or submit a pull request!

---

**Happy Spelling! 📚✨**
