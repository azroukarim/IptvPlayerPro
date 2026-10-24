# -*- coding: utf-8 -*-
"""Full-screen Live TV player with an Ibo-style information bar."""

from __future__ import absolute_import

import time

from enigma import eTimer

from Components.ActionMap import HelpableActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Screens.Screen import Screen

from ..core.epg import clock_text, now_next
from ..core.i18n import _
from ..core.util import safe_int, to_text
import os
from ..core.store import Store
from .base import download_logo, pixmap
from .skins import PLAYER_SKIN


INFO_BAR_TIMEOUT = 5000


class LivePlayerScreen(Screen):
    """Show the running Live TV service full-screen.

    The service is already playing on decoder 0 when this screen opens; the
    screen only draws the information bar.  Hiding the browser screen makes
    Enigma2 restore the video plane to full screen, and this screen keeps the
    picture untouched until it is closed.
    """

    skin = PLAYER_SKIN

    def __init__(self, session, item, logo=None, programmes=None):
        Screen.__init__(self, session)
        self.skinName = "IPTVProPlayer"
        self.item = item or {}
        self._logo = logo
        self._programmes = programmes or []
        self._epg_signature = None
        self._info_visible = True
        self._clock_timer = None
        self._info_timer = None

        self["topBar"] = Pixmap()
        self["logo"] = Pixmap()
        self["title"] = Label()
        self["clock"] = Label()
        self["bottomBar"] = Pixmap()
        self["logoBg"] = Pixmap()
        self["channelLogo"] = Pixmap()
        self["channelName"] = Label()
        self["channelMeta"] = Label()
        self["liveBg"] = Pixmap()
        self["liveLabel"] = Label()
        self["epgNow"] = Label()
        self["epgNext"] = Label()
        self["volumeText"] = Label()
        self["hint"] = Label()

        self["actions"] = HelpableActionMap(self, [
            "NavigationActions", "OkCancelActions", "ColorActions",
        ], {
            "ok": self.toggle_info,
            "cancel": self.key_back,
            "up": self.key_up,
            "red": self.key_back,
            "yellow": self.toggle_mute,
            "left": self.volume_down,
            "right": self.volume_up,
        }, prio=0, description=_("IPTV Player Pro"))

        self.onLayoutFinish.append(self._layout_ready)
        self.onShow.append(self._start_clock)
        self.onClose.append(self._stop_timers)

    # -------------------------------------------------------------- layout
    def _layout_ready(self):
        self["topBar"].instance.setPixmap(pixmap("player_top.png"))
        self["logo"].instance.setPixmap(pixmap("logo_small.png"))
        self["bottomBar"].instance.setPixmap(pixmap("player_bottom.png"))
        self["logoBg"].instance.setPixmap(pixmap("player_logo_bg.png"))
        self["liveBg"].instance.setPixmap(pixmap("player_live.png"))
        if self._logo is not None:
            self["channelLogo"].instance.setPixmap(self._logo)
        else:
            self["channelLogo"].instance.setPixmap(pixmap("channel.png"))
            self._load_channel_logo()

        self["title"].setText(u"IPTV Player Pro")
        name = to_text(self.item.get("name") or _("Live TV"))
        self["channelName"].setText(name)
        group = to_text(self.item.get("group") or u"")
        number = safe_int(self.item.get("number"))
        meta = []
        if group:
            meta.append(group)
        if number:
            meta.append(u"#{0}".format(number))
        self["channelMeta"].setText(
            u"  \u2022  ".join(meta) if meta else _("Live TV"))
        self["liveLabel"].setText(u"LIVE")
        self["hint"].setText(
            _("OK info  \u2022  LEFT/RIGHT volume  \u2022  YELLOW mute  \u2022  UP/BACK back"))
        self.update_clock()
        self.update_volume()
        self.update_epg()
        self._start_info_timer()

    def _load_channel_logo(self):
        logo = to_text(self.item.get("logo"))
        if not logo:
            return
        store = Store()
        local = store.logo_file(logo)
        if os.path.exists(local) and os.path.getsize(local) > 64:
            try:
                from Tools.LoadPixmap import LoadPixmap
                ptr = LoadPixmap(local, cached=False)
                if ptr is not None:
                    self["channelLogo"].instance.setPixmap(ptr)
                    return
            except Exception:
                pass
        import threading
        def _bg():
            download_logo(logo, store)
            if os.path.exists(local) and os.path.getsize(local) > 64:
                try:
                    from Tools.LoadPixmap import LoadPixmap
                    ptr = LoadPixmap(local, cached=False)
                    if ptr is not None:
                        self["channelLogo"].instance.setPixmap(ptr)
                except Exception:
                    pass
        t = threading.Thread(target=_bg)
        t.daemon = True
        t.start()

    def _set_visible(self, name, visible):
        widget = self.get(name)
        if widget is None:
            return
        try:
            if visible:
                widget.show()
            else:
                widget.hide()
        except Exception:
            pass

    def _set_info_visible(self, visible):
        self._info_visible = visible
        for name in ("topBar", "logo", "title", "clock", "bottomBar",
                     "logoBg", "channelLogo", "channelName", "channelMeta",
                     "liveBg", "liveLabel", "epgNow", "epgNext", "volumeText",
                     "hint"):
            self._set_visible(name, visible)
        if visible:
            self.update_clock()
            self.update_volume()
            self.update_epg()
            self._start_info_timer()
        else:
            self._stop_info_timer()

    def _start_info_timer(self):
        if self._info_timer is None:
            try:
                self._info_timer = eTimer()
                self._info_timer.callback.append(self._hide_info)
            except Exception:
                self._info_timer = None
        if self._info_timer is None:
            return
        try:
            self._info_timer.stop()
            # Single-shot: the bar is shown again by OK or by the volume keys.
            self._info_timer.start(INFO_BAR_TIMEOUT, True)
        except Exception:
            pass

    def _stop_info_timer(self):
        if self._info_timer is not None:
            try:
                self._info_timer.stop()
            except Exception:
                pass
            self._info_timer = None

    def _hide_info(self):
        self._set_info_visible(False)

    def key_up(self):
        self.close()

    def key_back(self):
        self.close()

    def toggle_info(self):
        self._set_info_visible(not self._info_visible)

    # -------------------------------------------------------------- clock
    def _start_clock(self):
        if self._clock_timer is None:
            try:
                self._clock_timer = eTimer()
                self._clock_timer.callback.append(self._tick)
            except Exception:
                self._clock_timer = None
        if self._clock_timer is not None:
            try:
                self._clock_timer.start(1000, False)
            except Exception:
                pass
        self.update_clock()
        self.update_volume()

    def _stop_clock(self):
        if self._clock_timer is not None:
            try:
                self._clock_timer.stop()
            except Exception:
                pass
            self._clock_timer = None

    def _stop_timers(self):
        self._stop_clock()
        self._stop_info_timer()

    def _tick(self):
        self.update_clock()
        self.update_volume()
        self.update_epg()

    def update_clock(self):
        try:
            self["clock"].setText(to_text(time.strftime("%I:%M %p")))
        except Exception:
            pass

    # ----------------------------------------------------------------- epg
    def set_programmes(self, programmes):
        self._programmes = programmes or []
        self._epg_signature = None
        self.update_epg()

    def update_epg(self):
        current, upcoming = now_next(self._programmes)
        now_text = u""
        next_text = u""
        if current is not None:
            now_text = u"{0} - {1}  {2}".format(
                clock_text(current[0]), clock_text(current[1]),
                to_text(current[2]).replace(u"\n", u" "))
        if upcoming is not None:
            next_text = u"{0}  {1}  {2}".format(
                _("Next"), clock_text(upcoming[0]),
                to_text(upcoming[2]).replace(u"\n", u" "))
        signature = (now_text, next_text)
        if signature == self._epg_signature:
            return
        self._epg_signature = signature
        try:
            self["epgNow"].setText(now_text)
        except Exception:
            pass
        try:
            self["epgNext"].setText(next_text)
        except Exception:
            pass

    # ------------------------------------------------------------- volume
    def _volume_control(self):
        try:
            from enigma import eDVBVolumecontrol
            return eDVBVolumecontrol.getInstance()
        except Exception:
            return None

    def update_volume(self):
        control = self._volume_control()
        text = u""
        if control is not None:
            try:
                if control.isMuted():
                    text = _("Muted")
                else:
                    text = u"{0} {1}%".format(_("Volume"), control.getVolume())
            except Exception:
                text = u""
        try:
            self["volumeText"].setText(text)
        except Exception:
            pass

    def volume_up(self):
        control = self._volume_control()
        if control is not None:
            try:
                control.volumeUp()
            except Exception:
                pass
        self._set_info_visible(True)
        self.update_volume()

    def volume_down(self):
        control = self._volume_control()
        if control is not None:
            try:
                control.volumeDown()
            except Exception:
                pass
        self._set_info_visible(True)
        self.update_volume()

    def toggle_mute(self):
        control = self._volume_control()
        if control is not None:
            try:
                control.volumeToggleMute()
            except Exception:
                pass
        self._set_info_visible(True)
        self.update_volume()
