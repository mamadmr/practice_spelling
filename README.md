# Spelling Practice Application 📚✏️

An intelligent Python application to help you practice and master English word spelling through an adaptive learning system.

## Features

✨ **Smart Learning Algorithm**
- Words are selected based on your performance history
- More mistakes = higher probability of practice
- Diverse selection ensures all words get attention
- Tracks: correct/incorrect attempts, appearances, difficulty score

🔊 **Audio Pronunciation**
- Uses Google Text-to-Speech (gTTS) for correct pronunciation
- Optional audio mode for silent practice
- High-quality English voice

🎯 **Batch Learning System**
- Practice in batches (default: 4 words)
- Randomized order each time
- Must spell ALL words correctly to advance
- Automatic retry for incomplete batches

🎨 **Color-Coded Feedback**
- Green: correct letters
- Red: incorrect/extra letters
- Visual diff showing exactly what was wrong
- Clear comparison with correct spelling

📊 **Progress Tracking**
- SQLite database stores all statistics
- View accuracy per word
- Track improvement over time
- Persistent progress across sessions

## Installation

1. Clone this repository:
```bash
git clone https://github.com/mamadmr/practice_spelling.git
cd practice_spelling
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Quick Start

### 1. Add Words to Practice

Add words using the word manager:
```bash
# Add single word
python word_manager.py add accommodate

# Add multiple words
python word_manager.py add separate definitely receive occurrence

# Import from a text file (one word per line)
python word_manager.py import my_words.txt

# List all words
python word_manager.py list

# Search for words
python word_manager.py search tion
```

Or directly edit `words.csv` - just add one word per line.

### 2. Start Practicing

Run the main application:
```bash
python spelling_practice.py
```

The application will:
1. Ask if you want audio pronunciation (recommended!)
2. Show the main menu with options
3. Select "1" to start practice
4. Listen to each word and type what you hear
5. Get immediate feedback with color-coded corrections
6. Retry the batch if you make mistakes
7. Move to next batch when all words are correct

### 3. View Your Progress

Select option "2" from the main menu to see:
- Each word's statistics
- Correct/incorrect attempts
- Overall accuracy percentage
- Difficulty rankings

## File Structure

```
practice_spelling/
├── spelling_practice.py    # Main application
├── word_manager.py          # Word management utility
├── database.py              # Progress tracking database
├── words.csv                # Your word list (editable)
├── progress.db              # SQLite database (auto-created)
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Usage Examples

### Word Manager Commands

```bash
# Add words
python word_manager.py add beautiful necessary embarrass
python word_manager.py add rhythm

# Remove a word
python word_manager.py remove rhythm

# View all words
python word_manager.py list

# Search words containing "tion"
python word_manager.py search tion

# Clear all words (with confirmation)
python word_manager.py clear

# Import from file
python word_manager.py import common_misspellings.txt

# Get help
python word_manager.py help
```

### Main Application

The main menu offers:
1. **Start practice** - Begin a new practice session
2. **View statistics** - See your progress and accuracy
3. **Reload words** - Refresh word list after adding/removing words
4. **Toggle audio** - Enable/disable pronunciation
5. **Exit** - Close the application

## How the Algorithm Works

### Word Selection Algorithm

1. **Difficulty Scoring**: Each word has a difficulty score (0.1 to 10.0)
   - Starts at 1.0 for new words
   - Increases by 0.5 for each mistake
   - Decreases by 0.1 for each correct answer

2. **Time-Based Weighting**: Words not seen recently get bonus weight
   - +0.1 weight per day since last seen (max +2.0)

3. **Weighted Random Selection**: Higher weight = higher probability
   - Focuses on difficult words
   - Still shows all words occasionally
   - Ensures comprehensive coverage

### Batch Learning Process

1. Select batch of words (default: 4) using weighted algorithm
2. Randomize order within batch
3. Present each word with audio pronunciation
4. User types the word
5. Immediate feedback with color-coded corrections
6. If ALL words correct → move to next batch
7. If ANY word incorrect → retry entire batch
8. All results saved to database for future selection

## Tips for Effective Practice

1. **Enable Audio**: Hearing the pronunciation helps with spelling
2. **Don't Rush**: Take time to think about each word
3. **Learn from Mistakes**: Pay attention to the color-coded differences
4. **Regular Practice**: Short daily sessions are more effective than long ones
5. **Add Related Words**: Build thematic word groups for better learning
6. **Review Statistics**: Check which words need more practice

## Customization

### Change Batch Size

Edit `spelling_practice.py`, line at the bottom:
```python
app = SpellingPractice(batch_size=6)  # Change from 4 to your preference
```

### Add Your Own Words

Create a text file with one word per line:
```
accommodate
separate
definitely
receive
occurred
```

Import it:
```bash
python word_manager.py import mywords.txt
```

### Reset Progress

Delete `progress.db` to start fresh (your word list in `words.csv` will remain intact).

## Troubleshooting

**Audio not playing:**
- Check your system audio settings
- Try running without audio (answer 'n' when prompted)
- On some systems, you may need to install additional audio libraries

**Import errors:**
- Make sure all dependencies are installed: `pip install -r requirements.txt`
- Use Python 3.7 or higher

**Words not loading:**
- Check that `words.csv` exists and has words in it
- Make sure each word is on its own line
- Use UTF-8 encoding if adding words manually

## Requirements

- Python 3.7+
- Internet connection (for gTTS on first use of each word)
- Audio output device (optional, can be disabled)

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is open source and available for educational purposes.

## Acknowledgments

- Uses Google Text-to-Speech (gTTS) for pronunciation
- Built with Python's colorama for terminal colors
- SQLite for efficient progress tracking

---

Happy spelling practice! 📚✨
