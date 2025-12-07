#!/usr/bin/env python3
"""Test offline audio downloading feature."""
import os
import sys
import platform

def test_audio_cache():
    """Test the audio cache download feature."""
    print("="*60)
    print("  Testing Offline Audio Download Feature")
    print("="*60)
    print()
    
    # Import the app
    try:
        from spelling_practice import SpellingPractice
    except ImportError as e:
        print(f"✗ Failed to import SpellingPractice: {e}")
        return False
    
    # Create app instance
    print("Creating app instance...")
    app = SpellingPractice()
    
    # Check if using native TTS
    if app.use_native_tts:
        print(f"✓ Platform: {platform.system()}")
        print(f"✓ Using native TTS - no cache needed!")
        print(f"  Your system generates audio on-the-fly without downloads.")
        return True
    
    # Test with a small word list
    test_words = ["test", "hello", "world", "practice", "spelling"]
    
    print(f"\n✓ Platform: {platform.system()}")
    print(f"✓ Using gTTS with cache")
    print(f"\nTesting audio download for {len(test_words)} test words...")
    
    # Download audio
    downloaded, skipped = app.download_audio_files(test_words, force=True)
    
    print(f"\nResults:")
    print(f"  Downloaded: {downloaded}")
    print(f"  Skipped: {skipped}")
    
    # Verify files exist
    cache_dir = "audio_cache"
    missing = []
    for word in test_words:
        safe_word = "".join(c for c in word.lower() if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_word = safe_word.replace(' ', '_')
        cache_file = os.path.join(cache_dir, f"{safe_word}.mp3")
        if not os.path.exists(cache_file):
            missing.append(word)
    
    if missing:
        print(f"\n✗ Missing cache files for: {', '.join(missing)}")
        return False
    else:
        print(f"\n✓ All test audio files cached successfully!")
        
        # Show cache info
        cache_files = [f for f in os.listdir(cache_dir) if f.endswith('.mp3')]
        total_size = sum(os.path.getsize(os.path.join(cache_dir, f)) for f in cache_files)
        print(f"\nCache statistics:")
        print(f"  Total files: {len(cache_files)}")
        print(f"  Total size: {total_size / 1024:.1f} KB")
        
        return True

if __name__ == "__main__":
    print()
    success = test_audio_cache()
    
    print("\n" + "="*60)
    if success:
        print("✓ Offline audio feature is working!")
    else:
        print("✗ Some issues detected")
    print("="*60)
    print()
    
    sys.exit(0 if success else 1)
