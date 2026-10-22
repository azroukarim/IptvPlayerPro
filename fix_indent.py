#!/usr/bin/env python
with open("src/IPTVPlayerPro/core/backends.py", "r", encoding="utf-8") as f:
    text = f.read()

# Remove the fallback lines that cause indentation issue
old = """                group = category_id[2:]
                    items = [item for item in self.channels if to_text(item.get("group") or "") == group]"""

new = "# fallback removed - direct index access"

text = text.replace(old, new)
with open("src/IPTVPlayerPro/core/backends.py", "w", encoding="utf-8") as f:
    f.write(text)
print("Fixed")