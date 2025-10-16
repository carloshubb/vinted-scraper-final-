"""
Quick fix script to remove emojis from vinted_scraper_enhanced.py
Run this to make it Windows-compatible
"""
import re

# Read the file
with open('vinted_scraper.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Define emoji replacements
replacements = {
    '🌐': '[WEB]',
    '📋': '[CONFIG]',
    '🏠': '[INIT]',
    '✅': '[OK]',
    '❌': '[ERROR]',
    '📄': '[PAGE]',
    '🛑': '[STOP]',
    '⏳': '[WAIT]',
    '⏸️': '[PAUSE]',
    '🔄': '[CLEAN]',
    '📊': '[TOTAL]',
    '📁': '[FILE]',
    '📦': '[CATEGORIES]',
    '🏷️': '[TOP 15 BRANDS]',
    '👥': '[AUDIENCE]',
    '📅': '[DATE RANGE]',
    '💰': '[PRICES (EUR)]',
    '🌡️': '[SEASONS]',
    '⚠️': '[WARNING]',
    '🎯': '[NEXT STEP]',
    '🔧': '[RETRY]',
}

# Replace all emojis
for emoji, replacement in replacements.items():
    content = content.replace(emoji, replacement)

# Remove any remaining emojis (catch-all)
content = re.sub(r'[^\x00-\x7F]+', '', content)

# Write back
with open('vinted_scraper.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Fixed! Emojis removed from vinted_scraper.py")
print("Now run: python vinted_scraper_enhanced.py")