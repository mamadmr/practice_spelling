#!/usr/bin/env python3
"""Test macOS audio functionality."""
import platform
import subprocess
import sys

def test_macos_say():
    """Test native macOS 'say' command."""
    if platform.system() != "Darwin":
        print("This test is for macOS only")
        return False
    
    print("Testing macOS native 'say' command...")
    try:
        proc = subprocess.Popen(
            ["say", "hello"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        proc.wait(timeout=5)
        print("✓ macOS 'say' command works!")
        return True
    except Exception as e:
        print(f"✗ macOS 'say' command failed: {e}")
        return False

def test_pygame_audio():
    """Test pygame audio."""
    print("\nTesting pygame audio system...")
    try:
        import pygame
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        print("✓ pygame mixer initialized successfully!")
        pygame.mixer.quit()
        return True
    except Exception as e:
        print(f"✗ pygame mixer failed: {e}")
        return False

def test_gtts():
    """Test gTTS."""
    print("\nTesting gTTS (Google Text-to-Speech)...")
    try:
        from gtts import gTTS
        import tempfile
        import os
        
        # Create a test audio file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
            temp_file = f.name
        
        tts = gTTS(text="test", lang='en', slow=False)
        tts.save(temp_file)
        
        # Check if file was created
        if os.path.exists(temp_file):
            os.remove(temp_file)
            print("✓ gTTS works!")
            return True
        else:
            print("✗ gTTS failed to create audio file")
            return False
    except Exception as e:
        print(f"✗ gTTS failed: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("  Audio System Test for macOS")
    print("="*60)
    print()
    
    results = []
    results.append(("macOS 'say' command", test_macos_say()))
    results.append(("pygame mixer", test_pygame_audio()))
    results.append(("gTTS", test_gtts()))
    
    print("\n" + "="*60)
    print("  Test Results Summary")
    print("="*60)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{name:<25} {status}")
    
    all_passed = all(result for _, result in results)
    
    print("\n" + "="*60)
    if all_passed:
        print("✓ All audio systems working!")
        print("\nYour system is ready for spelling practice with audio.")
    else:
        print("⚠ Some audio systems failed")
        print("\nThe app will still work but may fall back to text-only mode")
        print("or use alternative audio methods.")
    print("="*60)
    print()
    
    sys.exit(0 if all_passed else 1)
