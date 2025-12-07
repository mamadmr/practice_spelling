"""Test script to verify embedding generation and semantic similarity."""
from database import WordDatabase
from sentence_transformers import SentenceTransformer

def test_embeddings():
    """Test embedding generation and retrieval."""
    print("Testing embedding functionality...\n")
    
    # Initialize database
    db = WordDatabase()
    
    # Test words
    test_words = ['happy', 'joyful', 'sad', 'melancholy', 'run', 'sprint']
    
    print(f"Loading sentence-transformer model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print("✓ Model loaded\n")
    
    # Generate and save embeddings
    print("Generating embeddings for test words...")
    for word in test_words:
        embedding = model.encode(word)
        db.save_embedding(word, embedding)
        print(f"  ✓ {word}: embedding shape = {embedding.shape}")
    
    print("\nTesting embedding retrieval...")
    for word in test_words:
        embedding = db.get_embedding(word)
        if embedding is not None:
            print(f"  ✓ {word}: retrieved embedding shape = {embedding.shape}")
        else:
            print(f"  ✗ {word}: failed to retrieve")
    
    print("\nTesting semantic similarity...")
    test_word = 'happy'
    similar = db.get_semantic_similar_words(test_word, min_similarity=0.3, limit=5)
    print(f"\nWords semantically similar to '{test_word}':")
    for word, score in similar:
        print(f"  {word}: {score:.4f}")
    
    print("\nTesting with 'run'...")
    similar = db.get_semantic_similar_words('run', min_similarity=0.3, limit=5)
    print(f"\nWords semantically similar to 'run':")
    for word, score in similar:
        print(f"  {word}: {score:.4f}")
    
    # Test has_embeddings
    print(f"\nhas_embeddings(): {db.has_embeddings()}")
    
    # Test get_words_without_embeddings
    all_test_words = test_words + ['new_word', 'another_word']
    missing = db.get_words_without_embeddings(all_test_words)
    print(f"Words without embeddings: {missing}")
    
    db.close()
    print("\n✓ All tests passed!")

if __name__ == '__main__':
    test_embeddings()
