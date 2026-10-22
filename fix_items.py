import sys
sys.path.insert(0, "src")
# Read the file
with open("src/IPTVPlayerPro/core/backends.py", "r", encoding="utf-8") as f:
    text = f.read()

# M3U live_items: simplify to direct index access, no fallback
old_m3u = """    def live_items(self, category_id, query=""):
        self._ensure_live_groups()
        if category_id == "fav":
            favorites = self.favorite_keys()
            items = [item for item in self.live if self.favorite_key(item) in favorites]
        elif category_id.startswith("g:"):
            items = self._live_groups.get(category_id[2:]) or []
            if not items and self.live:
                group = category_id[2:]
                items = [item for item in self.live if (item.get("group") or "Live TV") == group]
        else:
            items = self.live
        if query:
            items = [item for item in items if _match(item.get("name"), query)]
        return items"""

new_m3u = """    def live_items(self, category_id, query=""):
        self._ensure_live_groups()
        if category_id == "fav":
            favorites = self.favorite_keys()
            items = [item for item in self.live if self.favorite_key(item) in favorites]
        elif category_id.startswith("g:"):
            items = self._live_groups.get(category_id[2:]) or []
            # Direct index access - no fallback scan (causes lag).
            # If index empty, return empty list; caller will show empty category.
        else:
            items = list(self.live)
        if query:
            items = [item for item in items if _match(item.get("name"), query)]
        return items"""

if old_m3u in text:
    text = text.replace(old_m3u, new_m3u)
    print("M3U live_items replaced")
else:
    print("M3U pattern not found")

# MAG live_items: simplify
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
    print("MAG live_items replaced")
else:
    print("MAG pattern not found")

# Write back
with open("src/IPTVPlayerPro/core/backends.py", "w", encoding="utf-8") as f:
    f.write(text)
print("done")