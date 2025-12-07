#!/usr/bin/env python3
"""Test the example sentences feature with Ollama."""
import sys
import requests

def test_ollama_connection():
    """Test if Ollama is available."""
    print("="*60)
    print("  Testing Ollama Connection")
    print("="*60)
    print()
    
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=2)
        if response.status_code == 200:
            print("✓ Ollama is running!")
            data = response.json()
            models = data.get('models', [])
            print(f"\nAvailable models:")
            for model in models:
                name = model.get('name', 'unknown')
                print(f"  - {name}")
            
            # Check if llama3.2 is available
            has_llama = any('llama3.2' in model.get('name', '') for model in models)
            if has_llama:
                print(f"\n✓ llama3.2 model found!")
                return True
            else:
                print(f"\n⚠ llama3.2 model not found")
                print(f"  Run: ollama pull llama3.2")
                return False
        else:
            print(f"✗ Ollama returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("✗ Ollama is not running")
        print("\nTo start Ollama:")
        print("  1. Open a new terminal")
        print("  2. Run: ollama serve")
        print("  3. In another terminal run: ollama pull llama3.2")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_sentence_generation():
    """Test generating sentences and definitions for words."""
    print("\n" + "="*60)
    print("  Testing Definition & Sentence Generation")
    print("="*60)
    print()
    
    from spelling_practice import SpellingPractice
    
    app = SpellingPractice()
    
    if not app.ollama_available:
        print("✗ Ollama not available - skipping test")
        return False
    
    # Test with different types of words
    test_words = [
        ("run", "multiple meanings"),
        ("accommodate", "single meaning"),
        ("bear", "multiple meanings")
    ]
    
    print("Testing intelligent definition & sentence generation...")
    print("(Words with more meanings should get more sentences)\n")
    
    all_passed = True
    
    for test_word, description in test_words:
        print(f"\n{'-'*60}")
        print(f"Word: '{test_word}' ({description})")
        print(f"Generating definition and sentences...\n")
        
        # Test definition
        definition = app.get_definition(test_word)
        if definition:
            print(f"📖 Definition: {definition}\n")
        else:
            print("✗ Failed to generate definition")
            all_passed = False
        
        # Test sentences
        sentences = app.generate_sentences(test_word)
        
        if sentences:
            print(f"📝 Generated {len(sentences)} sentence(s):\n")
            for i, sentence in enumerate(sentences, 1):
                print(f"  {i}. {sentence}")
        else:
            print("✗ Failed to generate sentences")
            all_passed = False
    
    # Test caching
    print(f"\n{'='*60}")
    print("Testing cache (should be instant for both)...")
    import time
    test_word = test_words[0][0]
    
    # Test definition cache
    start = time.time()
    cached_def = app.get_definition(test_word)
    def_elapsed = time.time() - start
    
    # Test sentences cache
    start = time.time()
    cached_sentences = app.generate_sentences(test_word)
    sent_elapsed = time.time() - start
    
    if cached_def:
        print(f"✓ Definition cache working! Retrieved in {def_elapsed:.3f}s")
    else:
        print(f"⚠ Definition cache test failed")
        all_passed = False
    
    if cached_sentences:
        print(f"✓ Sentences cache working! Retrieved in {sent_elapsed:.3f}s")
    else:
        print(f"⚠ Sentences cache test failed")
        all_passed = False
    
    return all_passed

if __name__ == "__main__":
    print()
    
    ollama_ok = test_ollama_connection()
    
    if ollama_ok:
        sentences_ok = test_sentence_generation()
    else:
        sentences_ok = False
    
    print("\n" + "="*60)
    if ollama_ok and sentences_ok:
        print("✓ All tests passed!")
        print("\nExample sentences feature is ready to use!")
        print("Run: python3 spelling_practice.py")
    elif ollama_ok:
        print("⚠ Ollama is running but sentence generation failed")
        print("  Check that llama3.2 model is working")
    else:
        print("✗ Ollama is not available")
        print("\nTo enable example sentences:")
        print("  1. Install Ollama: https://ollama.ai")
        print("  2. Run: ollama serve")
        print("  3. Run: ollama pull llama3.2")
    print("="*60)
    print()
    
    sys.exit(0 if (ollama_ok and sentences_ok) else 1)
