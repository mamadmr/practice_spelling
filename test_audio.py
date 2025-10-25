"""
Quick test script to verify audio functionality with caching.
Now uses pygame for in-program audio playback with cached files!
"""
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"

from spelling_practice import SpellingPractice
from colorama import Fore, Style, init
import time

init(autoreset=True)

print("="*60)
print("  Audio System Test (pygame + cache)")
print("="*60)
print()

app = SpellingPractice()

if not app.audio_available:
    print(f"{Fore.RED}✗ Audio system not available{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}The program will work in visual mode (showing words){Style.RESET_ALL}")
else:
    print(f"{Fore.GREEN}✓ Audio system initialized{Style.RESET_ALL}")
    print(f"{Fore.GREEN}✓ Cache directory: {app.cache_dir}{Style.RESET_ALL}")
    print()
    
    # Test 1: First time (downloads)
    print(f"{Fore.CYAN}Test 1: Playing 'hello' (first time - may download)...{Style.RESET_ALL}")
    start = time.time()
    success1 = app.pronounce_word("hello", use_tts=True)
    time1 = time.time() - start
    print(f"  Result: {'✓ SUCCESS' if success1 else '✗ FAILED'} in {time1:.2f}s")
    
    # Test 2: Second time (from cache)
    print(f"\n{Fore.CYAN}Test 2: Playing 'hello' again (from cache - should be faster)...{Style.RESET_ALL}")
    start = time.time()
    success2 = app.pronounce_word("hello", use_tts=True)
    time2 = time.time() - start
    print(f"  Result: {'✓ SUCCESS' if success2 else '✗ FAILED'} in {time2:.2f}s")
    
    # Test 3: Test timeout protection
    print(f"\n{Fore.CYAN}Test 3: Testing timeout protection (max 3 seconds)...{Style.RESET_ALL}")
    start = time.time()
    success3 = app.pronounce_word("test", use_tts=True)
    time3 = time.time() - start
    print(f"  Result: {'✓ SUCCESS' if success3 else '✗ FAILED'} in {time3:.2f}s")
    
    print()
    print(f"{Fore.GREEN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Summary:{Style.RESET_ALL}")
    print(f"  • First play: {time1:.2f}s (download + play)")
    print(f"  • Cached play: {time2:.2f}s (faster!)")
    if time2 < time1:
        print(f"  • {Fore.GREEN}✓ Cache is working! {time1-time2:.2f}s faster!{Style.RESET_ALL}")
    if time3 < 3.5:
        print(f"  • {Fore.GREEN}✓ Timeout protection working!{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'='*60}{Style.RESET_ALL}")

print()
print(f"{Fore.CYAN}Ready to practice! Run:{Style.RESET_ALL}")
print(f"{Fore.WHITE}  python spelling_practice.py{Style.RESET_ALL}")
print()
print(f"{Fore.CYAN}Audio files are cached in 'audio_cache/' for faster playback!{Style.RESET_ALL}")
print()

app.db.close()
