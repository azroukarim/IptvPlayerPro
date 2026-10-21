# -*- coding: utf-8 -*-
"""Inline skins for the plugin (no dependency on the active image skin)."""

MAIN_SKIN = """
<screen name="IPTVProMain" position="0,0" size="1280,720" resolution="1280,720" title="IPTV Player Pro" flags="wfNoBorder">
    <widget name="bg" position="0,0" size="1280,720" scale="1" />
    <widget name="logo" position="480,10" size="320,118" alphatest="blend" scale="1" />
    <widget name="status1" position="800,46" size="438,28" font="Regular;19" halign="right" valign="center" foregroundColor="#d2d2d2" transparent="1" />
    <widget name="status2" position="800,74" size="438,26" font="Regular;16" halign="right" valign="center" foregroundColor="#a37c7c" transparent="1" />

    <widget name="t0" position="60,250" size="300,300" alphatest="blend" scale="1" />
    <widget name="i0" position="140,286" size="140,140" alphatest="blend" scale="1" />
    <widget name="l0" position="60,448" size="300,58" font="Regular;30" halign="center" valign="center" foregroundColor="#ffffff" transparent="1" />

    <widget name="t1" position="390,230" size="200,140" alphatest="blend" scale="1" />
    <widget name="i1" position="462,246" size="56,56" alphatest="blend" scale="1" />
    <widget name="l1" position="390,320" size="200,36" font="Regular;22" halign="center" valign="center" foregroundColor="#ffffff" transparent="1" />

    <widget name="t2" position="610,230" size="200,140" alphatest="blend" scale="1" />
    <widget name="i2" position="682,246" size="56,56" alphatest="blend" scale="1" />
    <widget name="l2" position="610,320" size="200,36" font="Regular;22" halign="center" valign="center" foregroundColor="#ffffff" transparent="1" />

    <widget name="t3" position="390,390" size="200,140" alphatest="blend" scale="1" />
    <widget name="i3" position="462,406" size="56,56" alphatest="blend" scale="1" />
    <widget name="l3" position="390,480" size="200,36" font="Regular;22" halign="center" valign="center" foregroundColor="#ffffff" transparent="1" />

    <widget name="t4" position="610,390" size="200,140" alphatest="blend" scale="1" />
    <widget name="i4" position="682,406" size="56,56" alphatest="blend" scale="1" />
    <widget name="l4" position="610,480" size="200,36" font="Regular;22" halign="center" valign="center" foregroundColor="#ffffff" transparent="1" />

    <widget name="t5" position="850,230" size="370,70" alphatest="blend" scale="1" />
    <widget name="i5" position="868,246" size="38,38" alphatest="blend" scale="1" />
    <widget name="l5" position="920,230" size="280,70" font="Regular;24" halign="left" valign="center" foregroundColor="#ffffff" transparent="1" />

    <widget name="t6" position="850,330" size="370,70" alphatest="blend" scale="1" />
    <widget name="i6" position="868,346" size="38,38" alphatest="blend" scale="1" />
    <widget name="l6" position="920,330" size="280,70" font="Regular;24" halign="left" valign="center" foregroundColor="#ffffff" transparent="1" />

    <widget name="t7" position="850,430" size="370,70" alphatest="blend" scale="1" />
    <widget name="i7" position="868,446" size="38,38" alphatest="blend" scale="1" />
    <widget name="l7" position="920,430" size="280,70" font="Regular;24" halign="left" valign="center" foregroundColor="#ffffff" transparent="1" />

    <widget name="hint" position="60,650" size="1160,30" font="Regular;18" halign="center" valign="center" foregroundColor="#8f8f8f" transparent="1" />
</screen>
"""

INFO_SKIN = """
<screen name="IPTVProInfo" position="0,0" size="1280,720" resolution="1280,720" title="IPTV Player Pro" flags="wfNoBorder">
    <widget name="bg" position="0,0" size="1280,720" scale="1" />
    <widget name="logo" position="40,16" size="160,59" alphatest="blend" scale="1" />
    <widget name="title" position="40,88" size="1180,44" font="Regular;30" halign="left" valign="center" foregroundColor="#ffffff" transparent="1" />
    <widget name="meta" position="40,132" size="1180,28" font="Regular;18" halign="left" valign="center" foregroundColor="#d0a8a8" transparent="1" />
    <widget name="poster" position="40,178" size="280,400" alphatest="blend" scale="1" />
    <widget name="description" position="350,178" size="890,400" font="Regular;20" halign="left" valign="top" foregroundColor="#d6d6d6" transparent="1" />
    <widget name="hint" position="40,632" size="1200,32" font="Regular;18" halign="center" valign="center" foregroundColor="#9a9a9a" transparent="1" />
</screen>
"""

ACCOUNT_SKIN = """
<screen name="IPTVProAccount" position="0,0" size="1280,720" resolution="1280,720" title="IPTV Player Pro" flags="wfNoBorder">
    <widget name="bg" position="0,0" size="1280,720" scale="1" />
    <widget name="logo" position="40,16" size="160,59" alphatest="blend" scale="1" />
    <widget name="title" position="40,86" size="800,40" font="Regular;30" halign="left" valign="center" foregroundColor="#ffffff" transparent="1" />
    <widget name="subtitle" position="40,126" size="900,26" font="Regular;18" halign="left" valign="center" foregroundColor="#bdbdbd" transparent="1" />
    <widget name="status" position="860,90" size="380,26" font="Regular;18" halign="right" valign="center" foregroundColor="#d8a8a8" transparent="1" />
    <widget name="details" position="40,166" size="1200,214" font="Regular;21" halign="left" valign="top" foregroundColor="#e2e2e2" transparent="1" />
    <widget name="list" position="40,398" size="1200,214" scrollbarMode="showOnDemand" />
    <widget name="hint" position="40,632" size="1200,32" font="Regular;18" halign="center" valign="center" foregroundColor="#9a9a9a" transparent="1" />
</screen>
"""
