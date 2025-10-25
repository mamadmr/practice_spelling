"""
Quick setup script for first-time users.
Imports sample words and provides guidance.
"""
import os
import sys


def setup():
    """Run initial setup."""
    print("="*60)
    print("  Welcome to Spelling Practice Setup! 📚")
    print("="*60)
    print()
    
    # Check if words.csv exists and has content
    words_exist = False
    if os.path.exists("words.csv"):
        with open("words.csv", "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
            if len(lines) > 1:  # More than just header
                words_exist = True
                print(f"✓ Found {len(lines)-1} words in words.csv")
    
    if not words_exist:
        print("No words found. Would you like to import sample words? (y/n): ", end="")
        response = input().strip().lower()
        
        if response in ['y', 'yes', '']:
            if os.path.exists("sample_words.txt"):
                print("\nImporting sample words...")
                os.system(f"{sys.executable} word_manager.py import sample_words.txt")
                print("\n✓ Sample words imported successfully!")
            else:
                print("\nCreating words.csv with header...")
                with open("words.csv", "w", encoding="utf-8") as f:
                    f.write("word\n")
                print("✓ Created words.csv")
                print("\nAdd words using: python word_manager.py add <word>")
    
    print("\n" + "="*60)
    print("  Setup Complete!")
    print("="*60)
    print()
    print("Quick Start Commands:")
    print()
    print("  1. Add words:")
    print("     python word_manager.py add beautiful necessary")
    print()
    print("  2. View all words:")
    print("     python word_manager.py list")
    print()
    print("  3. Start practicing:")
    print("     python spelling_practice.py")
    print()
    print("="*60)
    print()
    
    print("Ready to start? (y/n): ", end="")
    response = input().strip().lower()
    
    if response in ['y', 'yes', '']:
        print("\nStarting Spelling Practice...\n")
        os.system(f"{sys.executable} spelling_practice.py")
    else:
        print("\nYou can start anytime with: python spelling_practice.py")
        print("Good luck! 📚✨\n")


if __name__ == "__main__":
    setup()
