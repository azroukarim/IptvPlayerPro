#!/usr/bin/env python

with open("src/IPTVPlayerPro/core/backends.py", "r", encoding="utf-8") as f:
    text = f.read()

# MAG live_items: replace fallback with direct index access
old_mag = """    def live_items(self, category_id, query=""):
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

new_mag = """    def live_items(self, category_id, query=""):
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

if old_mag in text:
    text = text.replace(old_mag, new_mag)
    print("MAG live_items replaced OK")
else:
    print("MAG pattern NOT found - showing snippet")
    idx = text.find('if self.channels:')
    print("Found at:", idx)
    print("Snippet:", text[idx:idx+200])

# Write back
with open("src/IPTVPlayerPro/core/backends.py", "w", encoding="utf-8") as f:
    f.write(text)
print("done")