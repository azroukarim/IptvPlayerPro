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

LIVE_SKIN = """
<screen name="IPTVProLive" position="0,0" size="1280,720" resolution="1280,720" title="IPTV Player Pro" flags="wfNoBorder" backgroundColor="#00000000">
    <widget name="bg" position="0,0" size="1280,720" alphatest="blend" scale="1" />
    <widget name="header" position="0,0" size="1280,80" alphatest="blend" scale="1" />
    <widget name="logo" position="20,12" size="120,44" alphatest="blend" scale="1" />
    <widget name="navLive" position="158,18" size="132,42" font="Regular;20" halign="center" valign="center" foregroundColor="#f5c84b" transparent="1" />
    <widget name="navMovies" position="298,18" size="102,42" font="Regular;18" halign="center" valign="center" foregroundColor="#aeb2d6" transparent="1" />
    <widget name="navSeries" position="408,18" size="102,42" font="Regular;18" halign="center" valign="center" foregroundColor="#aeb2d6" transparent="1" />
    <widget name="searchPill" position="528,18" size="424,44" alphatest="blend" scale="1" />
    <widget name="searchText" position="550,18" size="380,44" font="Regular;16" halign="left" valign="center" foregroundColor="#aeb2d6" transparent="1" />
    <widget name="status" position="966,14" size="294,28" font="Regular;16" halign="right" valign="center" foregroundColor="#e4e2ff" transparent="1" />
    <widget name="source" position="966,42" size="294,22" font="Regular;13" halign="right" valign="center" foregroundColor="#9fa6cc" transparent="1" />

    <widget name="leftPanel" position="0,80" size="300,640" alphatest="blend" scale="1" />
    <widget name="midPanel" position="300,80" size="420,640" alphatest="blend" scale="1" />
    <widget name="rightPanel" position="720,80" size="560,640" alphatest="blend" scale="1" />

    <widget name="catHeader" position="18,92" size="264,32" font="Regular;22" halign="left" valign="center" foregroundColor="#d7d5ff" transparent="1" />
    <widget name="categories" position="4,126" size="292,524" scrollbarMode="showOnDemand" />
    <widget name="chHeader" position="318,92" size="384,32" font="Regular;22" halign="left" valign="center" foregroundColor="#d7d5ff" transparent="1" />
    <widget name="channels" position="304,126" size="412,524" scrollbarMode="showOnDemand" />

    <widget name="preview" position="744,104" size="512,300" alphatest="blend" scale="1" />
    <widget name="previewVideo" position="744,104" size="512,300" backgroundColor="transparent" />
    <widget name="previewKind" position="762,112" size="250,24" font="Regular;14" halign="left" valign="center" foregroundColor="#8f93be" transparent="1" />
    <widget name="previewLogo" position="884,142" size="216,216" alphatest="blend" scale="1" />
    <widget name="previewName" position="744,418" size="512,44" font="Regular;26" halign="left" valign="center" foregroundColor="#ffffff" transparent="1" />
    <widget name="previewMeta" position="744,462" size="512,28" font="Regular;17" halign="left" valign="center" foregroundColor="#c7c4ef" transparent="1" />
    <widget name="previewEpgNow" position="744,490" size="512,30" font="Regular;18" halign="left" valign="center" foregroundColor="#f5c84b" transparent="1" />
    <widget name="previewEpgNext" position="744,520" size="512,24" font="Regular;15" halign="left" valign="center" foregroundColor="#aeb2d6" transparent="1" />
    <widget name="previewUrl" position="744,492" size="512,44" font="Regular;14" halign="left" valign="top" foregroundColor="#858bb8" transparent="1" />
    <widget name="previewFav" position="744,548" size="512,28" font="Regular;17" halign="left" valign="center" foregroundColor="#f5c84b" transparent="1" />

    <widget name="playBg" position="744,610" size="230,48" alphatest="blend" scale="1" />
    <widget name="playLabel" position="744,610" size="230,48" font="Regular;18" halign="center" valign="center" foregroundColor="#ffffff" transparent="1" />
    <widget name="favBg" position="992,610" size="264,48" alphatest="blend" scale="1" />
    <widget name="favLabel" position="992,610" size="264,48" font="Regular;17" halign="center" valign="center" foregroundColor="#e4e2ff" transparent="1" />
    <widget name="hint" position="20,676" size="1240,28" font="Regular;16" halign="center" valign="center" foregroundColor="#9a9fc7" transparent="1" />
</screen>
"""

# Enigma2 stores transparency in the alpha byte: #00000000 is opaque black,
# while "transparent" (or #ff000000) is fully transparent.  The player screen
# must leave the centre transparent so the running video stays visible.
PLAYER_SKIN = """
<screen name="IPTVProPlayer" position="0,0" size="1280,720" resolution="1280,720" title="IPTV Player Pro" flags="wfNoBorder" backgroundColor="transparent">
    <widget name="topBar" position="0,0" size="1280,70" alphatest="blend" scale="1" />
    <widget name="logo" position="22,12" size="120,44" alphatest="blend" scale="1" />
    <widget name="title" position="158,12" size="500,44" font="Regular;24" halign="left" valign="center" foregroundColor="#ffffff" transparent="1" />
    <widget name="clock" position="1000,12" size="256,44" font="Regular;24" halign="right" valign="center" foregroundColor="#ffffff" transparent="1" />

    <widget name="bottomBar" position="0,520" size="1280,200" alphatest="blend" scale="1" />
    <widget name="logoBg" position="32,540" size="104,104" alphatest="blend" scale="1" />
    <widget name="channelLogo" position="44,552" size="80,80" alphatest="blend" scale="1" />
    <widget name="channelName" position="156,528" size="780,42" font="Regular;28" halign="left" valign="center" foregroundColor="#ffffff" transparent="1" />
    <widget name="channelMeta" position="156,570" size="780,26" font="Regular;16" halign="left" valign="center" foregroundColor="#b9bdd8" transparent="1" />
    <widget name="liveBg" position="156,600" size="62,26" alphatest="blend" scale="1" />
    <widget name="liveLabel" position="156,600" size="62,26" font="Regular;14" halign="center" valign="center" foregroundColor="#ffffff" transparent="1" />
    <widget name="epgNow" position="226,598" size="710,30" font="Regular;19" halign="left" valign="center" foregroundColor="#f5c84b" transparent="1" />
    <widget name="epgNext" position="156,630" size="780,26" font="Regular;16" halign="left" valign="center" foregroundColor="#aeb2d6" transparent="1" />
    <widget name="volumeText" position="950,528" size="298,34" font="Regular;20" halign="right" valign="center" foregroundColor="#e8e8ff" transparent="1" />
    <widget name="hint" position="36,668" size="1208,32" font="Regular;17" halign="left" valign="center" foregroundColor="#9fa6cc" transparent="1" />
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
