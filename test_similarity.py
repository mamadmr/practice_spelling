"""Test script to demonstrate word similarity features."""
from database import WordDatabase
from colorama import Fore, Style, init

init(autoreset=True)

def test_similarity():
    """Test the similarity calculation and display results."""
    
    print(f"{Fore.CYAN}{'='*60}")
    print(f"{Fore.YELLOW}Word Similarity Matrix Test")
    print(f"{Fore.CYAN}{'='*60}\n")
    
    # Create database connection
    db = WordDatabase()
    
    # Get all words from database
    db.cursor.execute("SELECT word FROM word_stats ORDER BY word")
    all_words = [row[0] for row in db.cursor.fetchall()]
    
    if not all_words:
        print(f"{Fore.RED}No words in database. Please run the spelling practice first.")
        return
    
    print(f"{Fore.GREEN}Found {len(all_words)} words in database\n")
    
    # Check if similarities exist
    db.cursor.execute("SELECT COUNT(*) FROM word_similarity")
    sim_count = db.cursor.fetchone()[0]
    
    if sim_count == 0:
        print(f"{Fore.YELLOW}No similarities calculated yet.")
        print(f"{Fore.YELLOW}They will be calculated when you run the spelling practice.\n")
        return
    
    print(f"{Fore.CYAN}Total similarity pairs: {sim_count}\n")
    
    # Show some example similarities
    print(f"{Fore.YELLOW}Example: Most similar word pairs\n")
    
    db.cursor.execute("""
        SELECT word1, word2, similarity_score 
        FROM word_similarity 
        WHERE word1 < word2
        ORDER BY similarity_score DESC 
        LIMIT 15
    """)
    
    print(f"{Fore.CYAN}{'Word 1':<20} {'Word 2':<20} {'Similarity':<10}")
    print(f"{Fore.CYAN}{'-'*50}")
    
    for word1, word2, sim in db.cursor.fetchall():
        # Color code by similarity
        if sim >= 0.7:
            color = Fore.GREEN
        elif sim >= 0.5:
            color = Fore.YELLOW
        else:
            color = Fore.WHITE
        
        print(f"{color}{word1:<20} {word2:<20} {sim:.4f}")
    
    # Test with a specific word
    print(f"\n{Fore.YELLOW}Enter a word to see its similar words (or press Enter to skip): ", end="")
    test_word = input().strip().lower()
    
    if test_word:
        similar = db.get_similar_words(test_word, min_similarity=0.3, limit=10)
        
        if not similar:
            print(f"{Fore.RED}No similar words found for '{test_word}'")
        else:
            print(f"\n{Fore.GREEN}Words similar to '{test_word}':\n")
            print(f"{Fore.CYAN}{'Word':<20} {'Similarity':<10}")
            print(f"{Fore.CYAN}{'-'*30}")
            
            for word, sim in similar:
                if sim >= 0.7:
                    color = Fore.GREEN
                elif sim >= 0.5:
                    color = Fore.YELLOW
                else:
                    color = Fore.WHITE
                
                print(f"{color}{word:<20} {sim:.4f}")
    
    db.close()
    print(f"\n{Fore.GREEN}Test complete!")

if __name__ == "__main__":
    test_similarity()
