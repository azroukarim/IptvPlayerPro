# -*- coding: utf-8 -*-
"""IPTV Player Pro - M3U and MAG/Stalker player for Enigma2."""

from __future__ import absolute_import

from Plugins.Plugin import PluginDescriptor

from .core.i18n import _
from .core.store import VERSION
from .ui.menu import MainMenu


def main(session, **kwargs):
    session.open(MainMenu)


def Plugins(**kwargs):
    return [
        PluginDescriptor(
            name="IPTV Player Pro",
            description=_("M3U & MAG/Stalker player") + u"  v" + VERSION,
            where=[PluginDescriptor.WHERE_PLUGINMENU, PluginDescriptor.WHERE_EXTENSIONSMENU],
            icon="plugin.png",
            fnc=main,
        )
    ]
