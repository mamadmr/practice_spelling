# Quick Start Guide 🚀

## Your Spelling Practice Application is Ready!

### What You Have

✅ **25 commonly misspelled words** loaded and ready to practice
✅ **All dependencies installed** (colorama, gTTS, playsound, requests)
✅ **Database system** ready to track your progress
✅ **Word management tools** to add/remove words easily

---

## How to Use

### 1. Start Practicing (Main Way)

```bash
python spelling_practice.py
```

or if using the virtual environment directly:

```bash
.venv\Scripts\python.exe spelling_practice.py
```

**What happens:**
- You'll be asked if you want audio pronunciation (recommended: yes!)
- Choose option "1" to start practice
- Listen to each word (or see it if audio is off)
- Type what you hear
- Get immediate color-coded feedback:
  - 🟢 Green = correct letters
  - 🔴 Red = wrong/extra letters
- Complete all 4 words correctly to move to next batch
- Make a mistake? The batch repeats until perfect!

---

### 2. Manage Your Words

**Add new words:**
```bash
python word_manager.py add beautiful restaurant
```

**Remove a word:**
```bash
python word_manager.py remove rhythm
```

**View all words:**
```bash
python word_manager.py list
```

**Search for words:**
```bash
python word_manager.py search tion
```

**Get help:**
```bash
python word_manager.py help
```

---

### 3. Track Your Progress

From the main menu, choose option "2" to see:
- How many times you spelled each word correctly/incorrectly
- Your accuracy percentage per word
- Which words need more practice

---

## Tips for Success 💡

1. **Use Audio**: Hearing the pronunciation helps tremendously
2. **Practice Daily**: 10-15 minutes daily beats one long session
3. **Don't Give Up**: The batch system ensures you master each word
4. **Review Stats**: Check which words you struggle with
5. **Add Your Words**: Customize with words you personally find difficult

---

## What Makes This Effective?

🎯 **Smart Algorithm**: Words you miss more often appear more frequently

🔄 **Batch Learning**: Must spell all words correctly - no skipping

📊 **Progress Tracking**: SQLite database remembers everything

🎨 **Visual Feedback**: See exactly which letters were wrong

🔊 **Audio Support**: Proper pronunciation using Google TTS

---

## File Structure

```
practice_spelling/
├── spelling_practice.py   ← Main program (run this!)
├── word_manager.py         ← Add/remove words
├── database.py             ← Handles progress tracking
├── words.csv               ← Your word list (25 words loaded)
├── progress.db             ← Auto-created when you start
├── requirements.txt        ← Dependencies (already installed)
└── README.md              ← Full documentation
```

---

## Troubleshooting

**Can't hear audio?**
- Check system volume
- Run without audio (answer 'n' when asked)

**Want more/fewer words per batch?**
- Edit `spelling_practice.py`, line 294
- Change `batch_size=4` to your preference

**Want to reset progress?**
- Delete `progress.db` file
- Your word list stays intact!

---

## Ready to Start?

Run this command now:

```bash
python spelling_practice.py
```

**Good luck with your spelling practice! 📚✨**

---

## Need More Words?

Here are some word categories you might want to add:

**Silent letters:** knight, psychology, pneumonia, column
**Double letters:** millennium, committee, scissors, accommodation
**ie vs ei:** believe, receive, weird, seize
**Common mistakes:** separate, definitely, necessary, occurred

Add them with:
```bash
python word_manager.py add knight psychology pneumonia column
```
