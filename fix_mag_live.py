#!/usr/bin/env python
import sys

with open("src/IPTVPlayerPro/core/backends.py", "r", encoding="utf-8") as f:
    text = f.read()

# The exact old MAG live_items method - found at position ~30270
old = """    def live_items(self, category_id, query=""):
        self._ensure_live_groups()
        if self.channels:
            if category_id == "fav":
                favorites = self.favorite_keys()
                items = [item for item in self.channels
                         if self.favorite_key(item) in favorites]
            elif category_id.startswith("g:"):
                items = self._live_groups.get(category_id[2:]) or []
                if not items and self.channels:
                    group = category_id[2:]
                    items = [item for item in self.channels if to_text(item.get("group") or "") == group]
            else:
                items = list(self.channels)
            if query:
                items = [item for item in items if _match(item.get("name"), query)]
            return items
        items = []
        if category_id not in ("all", "fav"):
            genre = category_id[2:] if category_id.startswith("g:") else category_id
            page = 1
            while page <= 8:
                raws, total = self._make_client().ordered_list("itv", genre, page)
                for raw in raws:
                    item = self._channel(raw, genre, "live")
                    if query and not _match(item.get("name"), query):
                        continue
                    items.append(item)
                if page * _page_size(self.settings) >= total:
                    break
                page += 1
        return items"""

new = """    def live_items(self, category_id, query=""):
        self._ensure_live_groups()
        if self.channels:
            if category_id == "fav":
                favorites = self.favorite_keys()
                items = [item for item in self.channels
                         if self.favorite_key(item) in favorites]
            elif category_id.startswith("g:"):
                items = self._live_groups.get(category_id[2:]) or []
                # Direct index access - no fallback scan (causes lag).
                # If index empty, return empty list; caller will show empty category.
            else:
                items = list(self.channels)
            if query:
                items = [item for item in items if _match(item.get("name"), query)]
            return items
        items = []
        if category_id not in ("all", "fav"):
            genre = category_id[2:] if category_id.startswith("g:") else category_id
            page = 1
            while page <= 8:
                raws, total = self._make_client().ordered_list("itv", genre, page)
                for raw in raws:
                    item = self._channel(raw, genre, "live")
                    if query and not _match(item.get("name"), query):
                        continue
                    items.append(item)
                if page * _page_size(self.settings) >= total:
                    break
                page += 1
        return items"""

if old in text:
    text = text.replace(old, new)
    print("MAG live_items replaced OK")
    with open("src/IPTVPlayerPro/core/backends.py", "w", encoding="utf-8") as f:
        f.write(text)
else:
    print("MAG pattern NOT found")
    # Debug
    idx = text.find('if self.channels:')
    print("Found if self.channels at:", idx)
    # Show context
    pos = text.find('def live_items', 30000)
    print("live_items at:", pos)
    print("Snippet:", text[pos:pos+300])