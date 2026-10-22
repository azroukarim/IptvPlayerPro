#!/usr/bin/env python
import sys
import re

with open("src/IPTVPlayerPro/core/backends.py", "r", encoding="utf-8") as f:
    text = f.read()

# Find all live_items methods
positions = [m.start() for m in re.finditer('def live_items', text)]
print("Found", len(positions), "live_items methods")
for i, pos in enumerate(positions):
    print(f"\n--- Method {i+1} at position {pos} ---")
    # Print 500 chars
    snippet = text[pos:pos+500]
    # Print with line numbers
    for line in snippet.split('\n')[:15]:
        print(line)