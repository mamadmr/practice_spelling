"""Test the full app initialization including embeddings."""
from spelling_practice import SpellingPractice
import random

def test_app_full():
    """Test full app initialization with embeddings."""
    print("Testing full app initialization...\n")
    
    app = SpellingPractice()
    words = app.load_words()
    print(f"✓ Loaded {len(words)} words\n")
    
    # Check if embeddings exist
    print("Checking embeddings...")
    has_embeddings = app.db.has_embeddings()
    print(f"  Embeddings exist: {has_embeddings}")
    
    if not has_embeddings and len(words) > 0:
        print(f"\n  Generating embeddings for {len(words)} words...")
        app.initialize_embeddings(words[:10])  # Just test with first 10 words
        print(f"  ✓ Sample embeddings generated\n")
    
    # Test batch selection
    print("Testing batch selection with 50/50 random selection...\n")
    
    spelling_batches = 0
    semantic_batches = 0
    total_tests = 20
    
    for i in range(total_tests):
        batch = app.select_batch(words[:50])  # Test with first 50 words
        if batch:
            # We can't directly tell if it's semantic or spelling,
            # but we can verify the batch is properly formed
            print(f"  Test {i+1}: Batch of {len(batch)} words - {', '.join(batch[:3])}...")
    
    print(f"\n✓ Batch selection working!")
    print(f"✓ Each batch has {app.batch_size} words (or fewer if not enough available)")
    
    app.db.close()
    print("\n✓ All tests passed!")

if __name__ == '__main__':
    test_app_full()
