# -*- coding: utf-8 -*-
"""IPTV Player Pro - M3U and MAG/Stalker player for Enigma2."""

from __future__ import absolute_import

from Plugins.Plugin import PluginDescriptor

from .core.i18n import _
from .core.store import VERSION
from .ui.menu import MainMenu


def main(session, **kwargs):
    session.open(MainMenu)


def autostart(reason, **kwargs):
    """Start/stop the local web interface together with Enigma2."""
    try:
        from .web.server import manager
        if reason == 0:
            from .core.store import Store
            store = Store()
            if store.settings.get("web_enabled", True):
                manager.ensure(store)
        elif reason == 1:
            manager.stop()
    except Exception:
        pass


def Plugins(**kwargs):
    descriptors = [
        PluginDescriptor(
            name="IPTV Player Pro",
            description=_("M3U & MAG/Stalker player") + u"  v" + VERSION,
            where=[PluginDescriptor.WHERE_PLUGINMENU, PluginDescriptor.WHERE_EXTENSIONSMENU],
            icon="plugin.png",
            fnc=main,
        )
    ]
    if hasattr(PluginDescriptor, "WHERE_AUTOSTART"):
        descriptors.append(PluginDescriptor(
            where=[PluginDescriptor.WHERE_AUTOSTART],
            fnc=autostart,
        ))
    return descriptors
