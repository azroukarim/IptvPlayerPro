# -*- coding: utf-8 -*-
"""Smoke test for the UI modules using small Enigma2 stand-ins.

This does not test rendering, only that every screen can be constructed with
the real widget tree.  It catches import errors, missing attributes and typo
level mistakes without an actual receiver.
"""

from __future__ import absolute_import, print_function

import os
import shutil
import sys
import tempfile
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))


class Signal(object):
    def __init__(self):
        self.callbacks = []

    def get(self):
        return self

    def append(self, callback):
        self.callbacks.append(callback)

    def remove(self, callback):
        if callback in self.callbacks:
            self.callbacks.remove(callback)


class Timer(object):
    def __init__(self):
        self.callback = Signal()
        self.running = False

    def start(self, interval=0, single=False):
        self.running = True

    def stop(self):
        self.running = False


class PicLoad(object):
    def __init__(self):
        self.PictureData = Signal()

    def setPara(self, *args):
        pass

    def startDecode(self, *args):
        pass

    def getData(self):
        return None


class ServiceReference(object):
    def __init__(self, reference, flags=0, path=None):
        if path is not None:
            self.reference = path
        else:
            self.reference = reference
        self.name = ""

    def setName(self, name):
        self.name = name

    def toString(self):
        return self.reference


class Font(object):
    def __init__(self, name, size):
        self.name = name
        self.size = size


class Rect(object):
    def __init__(self, left=0, top=0, width=0, height=0):
        self._left = left
        self._top = top
        self._width = width
        self._height = height

    def left(self):
        return self._left

    def top(self):
        return self._top

    def width(self):
        return self._width

    def height(self):
        return self._height


class Desktop(object):
    def size(self):
        return Rect(0, 0, 1280, 720)


def _build_enigma():
    module = types.ModuleType("enigma")
    module.RT_HALIGN_CENTER = 2
    module.RT_HALIGN_LEFT = 1
    module.RT_HALIGN_RIGHT = 4
    module.RT_VALIGN_CENTER = 8
    module.eListboxPythonMultiContent = object
    module.eTimer = Timer
    module.ePicLoad = PicLoad
    module.eRect = Rect
    module.eServiceReference = ServiceReference
    module.getDesktop = lambda index=0: Desktop()
    module.gFont = Font
    return {"enigma": module}


def _build_components():
    action_map = types.ModuleType("Components.ActionMap")

    class HelpableActionMap(object):
        def __init__(self, parent, context, actions, prio=0, description=None):
            self.parent = parent
            self.context = context
            self.actions = actions

    action_map.HelpableActionMap = HelpableActionMap

    label = types.ModuleType("Components.Label")

    class Label(object):
        def __init__(self):
            self.text = ""

        def setText(self, text):
            self.text = text

    label.Label = Label

    class ListWidget(object):
        def __init__(self):
            self.items = []
            self.index = 0

        def setItemHeight(self, height):
            pass

        def setFont(self, index, font):
            pass

        def setList(self, items):
            self.items = items

        def getSelectedIndex(self):
            return self.index

        def setCurrentIndex(self, index):
            self.index = index

        def enableAutoNavigation(self, enabled):
            pass

        def goLineUp(self):
            self.index = max(0, self.index - 1)

        def goLineDown(self):
            self.index = min(max(0, len(self.items) - 1), self.index + 1)

        def goPageUp(self):
            self.goLineUp()

        def goPageDown(self):
            self.goLineDown()

        def goTop(self):
            self.index = 0

        def goBottom(self):
            self.index = max(0, len(self.items) - 1)

    menu_list = types.ModuleType("Components.MenuList")

    class MenuList(object):
        def __init__(self, items, enableWrapAround=False, content=None):
            self.l = ListWidget()
            self.l.setList(items)

        def setList(self, items):
            self.l.setList(items)

        def getSelectedIndex(self):
            return self.l.getSelectedIndex()

        def setCurrentIndex(self, index):
            self.l.setCurrentIndex(index)

        def enableAutoNavigation(self, enabled):
            self.l.enableAutoNavigation(enabled)

        def goLineUp(self):
            self.l.goLineUp()

        def goLineDown(self):
            self.l.goLineDown()

        def goPageUp(self):
            self.l.goPageUp()

        def goPageDown(self):
            self.l.goPageDown()

        def goTop(self):
            self.l.goTop()

        def goBottom(self):
            self.l.goBottom()

    menu_list.MenuList = MenuList

    multi = types.ModuleType("Components.MultiContent")

    class Entry(object):
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    multi.MultiContentEntryPixmapAlphaTest = Entry
    multi.MultiContentEntryRectangle = Entry
    multi.MultiContentEntryText = Entry

    pixmap = types.ModuleType("Components.Pixmap")

    class PixmapInstance(object):
        def __init__(self):
            self.pixmap = None

        def setPixmap(self, pixmap):
            self.pixmap = pixmap

    class Pixmap(object):
        def __init__(self):
            self.instance = PixmapInstance()
            self.visible = True

        def show(self):
            self.visible = True

        def hide(self):
            self.visible = False

    pixmap.Pixmap = Pixmap

    video_window = types.ModuleType("Components.VideoWindow")

    class VideoWindowInstance(object):
        def __init__(self):
            self.position = None
            self.fullscreen_position = None
            self.restored = False
            self.visible = True

        def setPosition(self, index, left, top, width, height):
            self.position = (index, left, top, width, height)

        def setFullScreenPosition(self, rect):
            self.fullscreen_position = (rect.left(), rect.top(), rect.width(), rect.height())

        def restoreFullsize(self):
            self.restored = True

        def show(self):
            self.visible = True

        def hide(self):
            self.visible = False

    class VideoWindow(object):
        def __init__(self, decoder=1, fb_width=720, fb_height=576):
            self.decoder = decoder
            self.fb_width = fb_width
            self.fb_height = fb_height
            self.instance = VideoWindowInstance()
            self.visible = True

        def show(self):
            self.visible = True
            self.instance.show()

        def hide(self):
            self.visible = False
            self.instance.hide()

    video_window.VideoWindow = VideoWindow

    scroll = types.ModuleType("Components.ScrollLabel")

    class ScrollLabel(object):
        def __init__(self):
            self.text = ""
            self.offset = 0

        def setText(self, text):
            self.text = text

        def moveUp(self):
            self.offset += 1

        def moveDown(self):
            self.offset = max(0, self.offset - 1)

        def pageUp(self):
            self.offset += 5

        def pageDown(self):
            self.offset = max(0, self.offset - 5)

    scroll.ScrollLabel = ScrollLabel

    package = types.ModuleType("Components")
    package.__path__ = []
    modules = {
        "Components": package,
        "Components.ActionMap": action_map,
        "Components.Label": label,
        "Components.MenuList": menu_list,
        "Components.MultiContent": multi,
        "Components.Pixmap": pixmap,
        "Components.ScrollLabel": scroll,
        "Components.VideoWindow": video_window,
    }
    return modules


def _build_screens():
    screen_module = types.ModuleType("Screens.Screen")

    class Screen(dict):
        def __init__(self, session, parent=None, mandatoryWidgets=None, enableHelp=False):
            dict.__init__(self)
            self.session = session
            self.parent = parent
            self.instance = None
            self.skinName = self.__class__.__name__
            self.onLayoutFinish = []
            self.onShown = []
            self.onShow = []
            self.onHide = []
            self.onClose = []
            self.execing = True

        def close(self, *result):
            self.closed = result

        def doClose(self):
            # Mirror Screens.Screen.doClose(): it calls dict.items() after
            # the onClose callbacks.  A screen attribute named "items" hides
            # that method and crashes the real close path.
            for method in self.onClose:
                method()
            for name, value in list(self.items()):
                pass

    screen_module.Screen = Screen

    message = types.ModuleType("Screens.MessageBox")

    class MessageBox(object):
        TYPE_INFO = 1
        TYPE_ERROR = 2
        TYPE_YESNO = 3

        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    message.MessageBox = MessageBox

    keyboard = types.ModuleType("Screens.VirtualKeyBoard")

    class VirtualKeyBoard(object):
        def __init__(self, session, title="", text=""):
            self.session = session
            self.title = title
            self.text = text

    keyboard.VirtualKeyBoard = VirtualKeyBoard

    choice = types.ModuleType("Screens.ChoiceBox")

    class ChoiceBox(object):
        def __init__(self, session, title="", list=None, **kwargs):
            self.session = session
            self.title = title
            self.list = list or []

    choice.ChoiceBox = ChoiceBox

    load_pixmap = types.ModuleType("Tools.LoadPixmap")
    load_pixmap.LoadPixmap = lambda path, **kwargs: object()

    plugin = types.ModuleType("Plugins.Plugin")

    class PluginDescriptor(object):
        WHERE_PLUGINMENU = 1
        WHERE_EXTENSIONSMENU = 2

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    plugin.PluginDescriptor = PluginDescriptor

    screens = types.ModuleType("Screens")
    screens.__path__ = []
    tools = types.ModuleType("Tools")
    tools.__path__ = []
    plugins = types.ModuleType("Plugins")
    plugins.__path__ = []
    return {
        "Screens": screens,
        "Screens.Screen": screen_module,
        "Screens.MessageBox": message,
        "Screens.VirtualKeyBoard": keyboard,
        "Screens.ChoiceBox": choice,
        "Tools": tools,
        "Tools.LoadPixmap": load_pixmap,
        "Plugins": plugins,
        "Plugins.Plugin": plugin,
    }


class Session(object):
    def __init__(self):
        self.opened = []
        self.nav = self

    def open(self, screen, *args, **kwargs):
        self.opened.append((screen, args, kwargs))
        return screen

    def openWithCallback(self, callback, screen, *args, **kwargs):
        self.opened.append((screen, args, kwargs))
        self.callback = callback
        return screen

    def playService(self, service):
        self.played = service


def main():
    saved = {}
    for name, module in list(_build_enigma().items()):
        saved[name] = sys.modules.get(name)
        sys.modules[name] = module
    for name, module in _build_components().items():
        saved[name] = sys.modules.get(name)
        sys.modules[name] = module
    for name, module in _build_screens().items():
        saved[name] = sys.modules.get(name)
        sys.modules[name] = module

    work = tempfile.mkdtemp(prefix="iptvpro-ui-")
    try:
        from IPTVPlayerPro.core.store import Store
        from IPTVPlayerPro.ui import browse as browse_module
        from IPTVPlayerPro.ui import menu as menu_module
        from IPTVPlayerPro.ui.account import AccountScreen
        from IPTVPlayerPro.ui.browse import (EpisodesScreen, LiveBrowserScreen,
                                             LiveCategoriesScreen, LiveScreen,
                                             SeasonsScreen, SeriesCategoriesScreen,
                                             SeriesScreen, VodCategoriesScreen, VodScreen)
        from IPTVPlayerPro.ui.info import InfoScreen
        from IPTVPlayerPro.ui.settings import SettingsScreen
        from IPTVPlayerPro.ui.sources import SourcesScreen
        from IPTVPlayerPro import plugin as plugin_module

        store = Store(config_dir=work, cache_dir=work)
        store.set_setting("web_enabled", False)
        store.set_setting("m3u_file", os.path.join(work, "m3u.txt"))
        store.set_setting("mac_file", os.path.join(work, "mac.txt"))
        menu_module.Store = lambda: store
        session = Session()

        main_menu = menu_module.MainMenu(session)
        main_menu.layout_ready()
        assert main_menu["l0"].text
        assert main_menu["status1"].text

        sources = SourcesScreen(session, store)
        assert sources["list"].l.items
        sources.layout_ready()

        settings = SettingsScreen(session, store)
        assert settings["list"].l.items
        settings.layout_ready()

        account = AccountScreen(session, store, None)
        account.layout_ready()
        assert account["details"].text

        info = InfoScreen(session, store, None, {"name": "Test", "description": "Plot"})
        info.layout_ready()
        assert info["title"].text == "Test"

        category = {"id": "all", "name": "All"}

        class FakeBackend(object):
            kind = "m3u"
            channels = []

            def live_categories(self):
                return [
                    {"id": "all", "name": "All channels", "count": 2},
                    {"id": "g:News", "name": "News", "count": 1},
                ]

            def live_items(self, category_id, query=""):
                items = [
                    {"id": "1", "name": "News One", "group": "News", "number": 1,
                     "fav_key": "one", "url": "http://example.test/one"},
                    {"id": "2", "name": "Sports Two", "group": "Sports", "number": 2,
                     "fav_key": "two", "url": "http://example.test/two"},
                ]
                if category_id == "g:News":
                    items = [items[0]]
                if query:
                    items = [item for item in items if query.lower() in item["name"].lower()]
                return items

            def is_favorite(self, item):
                return False

        live = LiveBrowserScreen(session, store, FakeBackend())
        live._layout_ready()
        live.build()
        assert live["categories"].l.items
        assert live["channels"].l.items
        assert live["previewName"].text
        live.key_right()
        assert live.focus == "channels"

        class PagedBackend(FakeBackend):
            def live_categories(self):
                return [{"id": "all", "name": "All channels", "count": 125}]

            def live_items(self, category_id, query=""):
                items = [
                    {"id": str(index), "name": "Channel {0}".format(index),
                     "group": "News", "number": index + 1,
                     "fav_key": str(index), "url": "http://example.test/{0}".format(index)}
                    for index in range(125)
                ]
                if query:
                    items = [item for item in items if query.lower() in item["name"].lower()]
                return items

        store.set_setting("page_size", 50)
        paged = LiveBrowserScreen(session, store, PagedBackend())
        paged._layout_ready()
        paged.build()
        assert paged.total == 125
        assert len(paged.browser_items) == 50
        assert len(paged["channels"].l.items) == 51  # 50 channels + "Load more"
        paged.set_focus("channels")
        paged["channels"].setCurrentIndex(50)
        paged.key_ok()
        assert len(paged.browser_items) == 100
        assert paged.page == 2
        assert paged["channels"].getSelectedIndex() == 50
        assert any(getattr(entry, "text", None) == "51"
                   for entry in paged["channels"].l.items[50])
        paged["channels"].setCurrentIndex(100)
        paged.key_ok()
        assert len(paged.browser_items) == 125
        assert paged.page == 3
        assert len(paged["channels"].l.items) == 125
        assert not paged.selected_is_more()

        # Live TV playback must stay in the browser and move the main video
        # plane into the preview pane.  It must also ignore close_after_zap.
        live.set_focus("channels")
        live["channels"].setCurrentIndex(0)
        calls = []
        original_play_url = browse_module.play_url

        def fake_play_url(*args, **kwargs):
            calls.append((args, kwargs))

        browse_module.play_url = fake_play_url
        try:
            live._play("http://example.test/one", live.selected_channel())
        finally:
            browse_module.play_url = original_play_url
        assert calls
        assert live._preview_active is True
        assert live["preview"].visible is False
        assert live["previewVideo"].visible is True
        assert not hasattr(live, "closed")
        live.stop_preview()
        assert live._preview_active is False
        assert live["preview"].visible is True
        assert live["previewVideo"].visible is False
        assert live["previewVideo"].instance.fullscreen_position == (0, 0, 720, 576)

        from IPTVPlayerPro.core.net import NetError

        def failing_play_url(*args, **kwargs):
            raise NetError("mini TV failed")

        browse_module.play_url = failing_play_url
        try:
            live._play("http://example.test/two", live.selected_channel())
        finally:
            browse_module.play_url = original_play_url
        assert live._preview_active is False
        assert live["preview"].visible is True
        assert live["previewVideo"].visible is False
        assert not hasattr(live, "closed")
        assert session.opened
        live.doClose()
        assert live._preview_active is False

        import xml.etree.ElementTree as ET
        from IPTVPlayerPro.ui.skins import LIVE_SKIN
        skin_names = set(widget.get("name") for widget in ET.fromstring(LIVE_SKIN).findall("widget"))
        for name in ("bg", "header", "categories", "channels", "previewLogo",
                     "previewName", "previewVideo", "playBg", "favBg", "hint"):
            assert name in skin_names, name

        from IPTVPlayerPro.ui.base import play_url

        class FailingPlaySession(Session):
            def playService(self, service):
                self.played = service
                return 1

            def getCurrentlyPlayingServiceOrGroup(self):
                return None

        failed_play = FailingPlaySession()
        try:
            play_url(failed_play, "http://example.test/live.ts")
        except NetError:
            pass
        else:
            raise AssertionError("A failed playService() must not be treated as success")

        class NativeFailureSession(Session):
            def playService(self, service):
                return 0

            def getCurrentlyPlayingServiceOrGroup(self):
                return None

        try:
            play_url(NativeFailureSession(), "http://example.test/live.ts")
        except NetError:
            pass
        else:
            raise AssertionError("A cleared current service means playback did not start")

        class PlayingSession(Session):
            def __init__(self):
                Session.__init__(self)
                self.current = None

            def playService(self, service):
                self.current = service
                return 0

            def getCurrentlyPlayingServiceOrGroup(self):
                return self.current

        play_url(PlayingSession(), "http://example.test/live.ts")

        header_session = PlayingSession()
        play_url(header_session, "http://example.test/live.ts", item_ua="VLC/3.0",
                 item_opts="Referer=http://portal.example/c/")
        header_reference = header_session.current.toString()
        assert header_reference.startswith("http://example.test/live.ts#")
        assert "User-Agent=VLC/3.0" in header_reference
        assert "Referer=http://portal.example/c/" in header_reference

        backend = None
        screens = [
            LiveCategoriesScreen(session, store, backend),
            LiveScreen(session, store, backend, category),
            LiveBrowserScreen(session, store, backend),
            VodCategoriesScreen(session, store, backend),
            VodScreen(session, store, backend, category),
            SeriesCategoriesScreen(session, store, backend),
            SeriesScreen(session, store, backend, category),
            SeasonsScreen(session, store, backend, {"id": "s1", "name": "Show"}),
            EpisodesScreen(session, store, backend, {"id": "s1", "name": "Show"}, {"id": "1", "name": "Season 1"}),
        ]
        for screen in screens:
            if screen.get("title") is not None:
                assert screen["title"].text
            # Enigma2 screens are dict subclasses.  Never shadow dict.items()
            # (or any other dict method) with a screen attribute, otherwise
            # Screen.deleteGUIScreen() raises "'list' object is not callable".
            assert "items" not in screen.__dict__, type(screen).__name__
            screen.doClose()

        descriptors = plugin_module.Plugins()
        assert len(descriptors) >= 1
        assert descriptors[0].name == "IPTV Player Pro"
        print("UI smoke test passed: {0} screens constructed.".format(len(screens) + 4))
    finally:
        for name, value in saved.items():
            if value is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
