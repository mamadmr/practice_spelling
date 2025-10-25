# Spelling Practice

A smart command-line spelling practice app with audio pronunciation, progress tracking, and intelligent word grouping based on spelling similarity.

## Features

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

```powershell
pip install -r requirements.txt
```

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

```powershell
python spelling_practice.py
```

**That's it!** The system automatically:
- ✅ Detects new words in `words.csv`
- ✅ Removes words deleted from `words.csv`
- ✅ Calculates spelling similarities
- ✅ Shows progress bars for all operations
- ✅ Groups similar words in practice batches

On Windows, you can also double-click `start_practice.bat`.

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
- **Difficulty score** - increases with mistakes
- **Consecutive correct** - prioritizes words you haven't mastered
- **Last seen** - words not practiced recently get priority

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
5. Exit
==================================================
```

### During Practice

1. **Listen** - Word is pronounced (or shown if audio is off)
2. **Type** - Enter your spelling
3. **Feedback** - See if correct, with color-coded differences
4. **Repeat** - Practice full batch

Wrong answers are shown with color-coded differences:
```
Your answer:  recieve
Correct:      receive
              ^^^   ^^^
```

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
- **`start_practice.bat`** - Windows shortcut (optional)

### Directories
- **`audio_cache/`** - Cached audio files (auto-created)
- **`__pycache__/`** - Python cache (auto-created)

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

### No audio on Windows
**Problem:** Audio not playing  
**Solution:** Install pywin32: `pip install pywin32`

### Progress bar not visible
**Problem:** Progress bar shows weird characters  
**Solution:** Use PowerShell or Windows Terminal (not CMD or IDLE)

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
- **pywin32** (Windows) - Native Windows speech API

Optional:
- **requests** - Online dictionary checking
- **pyspellchecker** - Spell checking
- **wordfreq** - Word frequency data

---

## Tips for Best Results

1. **Start small** - Begin with 20-30 words
2. **Practice daily** - Consistency improves retention
3. **Use audio** - Hearing words helps memory
4. **Review stats** - Focus on words with low accuracy
5. **Add similar words** - Learn spelling patterns together
6. **Be patient** - First run calculates similarities (one-time)

---

## Example Workflow

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
