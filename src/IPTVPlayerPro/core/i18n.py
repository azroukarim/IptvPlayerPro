# -*- coding: utf-8 -*-
"""Tiny translation layer (English source strings, Arabic translations)."""

from __future__ import absolute_import

LANGUAGES = [
    ("ar", u"العربية"),
    ("en", u"English"),
]

_AR = {
    # main menu
    "Live TV": u"البث المباشر",
    "Movies": u"أفلام",
    "Series": u"مسلسلات",
    "Account": u"الحساب",
    "Change Server": u"تغيير السيرفر",
    "Settings": u"الإعدادات",
    "Reload Portal": u"تحديث البورتال",
    "Exit": u"خروج",
    "Current playlist": u"القائمة الحالية",
    "No playlist selected": u"لم يتم اختيار قائمة",
    "Press MENU for the server list": u"اضغط MENU لقائمة السيرفرات",
    "IPTV Player Pro": u"IPTV Player Pro",
    "M3U & MAG/Stalker player": u"مشغّل M3U و MAG/Stalker",
    "OK select  •  BACK exit": u"OK اختيار  •  BACK خروج",
    "OK select  •  MENU servers  •  BACK exit": u"OK اختيار  •  MENU السيرفرات  •  BACK خروج",
    "Refreshing ...": u"جارٍ التحديث ...",
    "Refresh finished": u"تم التحديث",
    "Refresh failed": u"فشل التحديث",
    "Preparing ...": u"جارٍ تجهيز القنوات والأفلام ...",
    "Preparing movies ...": u"جارٍ تجهيز الأفلام ...",
    "Preparing series ...": u"جارٍ تجهيز المسلسلات ...",
    "Preparation failed": u"فشل تجهيز المصدر",
    "Refresh started in the background": u"بدأ التحديث في الخلفية",
    "The source is already being prepared.": u"المصدر قيد التجهيز بالفعل.",
    "Saving playlist ...": u"جارٍ حفظ القائمة ...",
    "Saving portal data ...": u"جارٍ حفظ بيانات البورتال ...",
    "No active playlist": u"لا توجد قائمة نشطة",
    "Open the server list and add an M3U playlist or a MAG portal first.":
        u"افتح قائمة السيرفرات وأضف قائمة M3U أو بورتال MAG أولًا.",
    "No channels": u"لا توجد قنوات",
    "No movies": u"لا توجد أفلام",
    "No series": u"لا توجد مسلسلات",
    "No episodes": u"لا توجد حلقات",
    # generic
    "Back": u"رجوع",
    "Close": u"إغلاق",
    "Cancel": u"إلغاء",
    "Save": u"حفظ",
    "Delete": u"حذف",
    "Edit": u"تعديل",
    "Add": u"إضافة",
    "Yes": u"نعم",
    "No": u"لا",
    "All": u"الكل",
    "All channels": u"كل القنوات",
    "All episodes": u"كل الحلقات",
    "Favorites": u"المفضلة",
    "Favorite": u"مفضلة",
    "Add favorite": u"إضافة للمفضلة",
    "Remove favorite": u"إزالة من المفضلة",
    "Categories": u"الأقسام",
    "Channels": u"القنوات",
    "Search channels": u"بحث القنوات",
    "CHANNEL PREVIEW": u"معاينة القناة",
    "LIVE TV": u"البث المباشر",
    "Not checked": u"لم يتم الفحص",
    "Not loaded yet": u"لم يتم التحميل بعد",
    "Search": u"بحث",
    "Search ...": u"بحث ...",
    "Loading ...": u"جارٍ التحميل ...",
    "Loading took too long. Check the connection and try again.":
        u"استغرق التحميل وقتًا طويلًا. تحقق من الاتصال وحاول مجددًا.",
    "Downloading playlist ...": u"جارٍ تحميل القائمة ...",
    "Downloading EPG ...": u"جارٍ تحميل دليل البرامج ...",
    "Reading playlist ...": u"جارٍ قراءة القائمة ...",
    "Connecting to the portal ...": u"جارٍ الاتصال بالبورتال ...",
    "Reading portal categories ...": u"جارٍ قراءة أقسام البورتال ...",
    "Reading channels ...": u"جارٍ قراءة القنوات ...",
    "Please wait ...": u"يرجى الانتظار ...",
    "Working ...": u"جارٍ العمل ...",
    "Error": u"خطأ",
    "Information": u"معلومات",
    "Unknown": u"غير معروف",
    "Active": u"نشط",
    "Expired": u"منتهي",
    "None": u"لا شيء",
    "OK": u"موافق",
    "OK play  •  GREEN search  •  YELLOW favorite  •  BLUE reload  •  RED back":
        u"OK تشغيل  •  أخضر بحث  •  أصفر مفضلة  •  أزرق تحديث  •  أحمر رجوع",
    "OK mini TV  •  GREEN search  •  YELLOW favorite  •  BLUE reload  •  RED back":
        u"OK شاشة مصغرة  •  أخضر بحث  •  أصفر مفضلة  •  أزرق تحديث  •  أحمر رجوع",
    "OK mini TV  •  OK again full screen  •  GREEN search  •  YELLOW favorite  •  BLUE reload  •  RED back":
        u"OK شاشة مصغرة  •  OK مرة أخرى شاشة كاملة  •  أخضر بحث  •  أصفر مفضلة  •  أزرق تحديث  •  أحمر رجوع",
    "OK info  •  LEFT/RIGHT volume  •  YELLOW mute  •  UP/BACK back":
        u"OK معلومات  •  يسار/يمين الصوت  •  أصفر كتم  •  أعلى/BACK رجوع",
    "OK play  •  GREEN search  •  BLUE reload  •  RED back":
        u"OK تشغيل  •  أخضر بحث  •  أزرق تحديث  •  أحمر رجوع",
    "OK open  •  GREEN search  •  BLUE reload  •  RED back":
        u"OK فتح  •  أخضر بحث  •  أزرق تحديث  •  أحمر رجوع",
    "OK open  •  BLUE reload  •  RED back": u"OK فتح  •  أزرق تحديث  •  أحمر رجوع",
    "OK open  •  RED back": u"OK فتح  •  أحمر رجوع",
    "OK select  •  RED back": u"OK اختيار  •  أحمر رجوع",
    "OK change  •  RED close": u"OK تغيير  •  أحمر إغلاق",
    "OK select  •  MENU edit  •  GREEN add M3U  •  BLUE add MAG  •  RED delete":
        u"OK اختيار  •  MENU تعديل  •  أخضر إضافة M3U  •  أزرق إضافة MAG  •  أحمر حذف",
    "OK play  •  RED back": u"OK تشغيل  •  أحمر رجوع",
    # lists
    "channels": u"قناة",
    "channel": u"قناة",
    "movies": u"فيلم",
    "series": u"مسلسل",
    "episodes": u"حلقة",
    "categories": u"قسم",
    "Season": u"الموسم",
    "Season {0}": u"الموسم {0}",
    "Seasons": u"المواسم",
    "Episode": u"الحلقة",
    "Load more ...": u"تحميل المزيد ...",
    "Toggle favorite": u"إضافة/إزالة من المفضلة",
    "Added to favorites": u"أضيفت إلى المفضلة",
    "Removed from favorites": u"أزيلت من المفضلة",
    "Playing ...": u"جارٍ التشغيل ...",
    "Playing in mini TV": u"يعمل في الشاشة المصغرة",
    "Volume": u"الصوت",
    "Muted": u"صامت",
    "Next": u"التالي",
    "EPG": u"دليل البرامج",
    "The EPG file is not valid XML.": u"ملف EPG ليس XML صالحًا.",
    "The EPG file is empty.": u"ملف EPG فارغ.",
    "No EPG URL configured.": u"لم يتم إعداد رابط EPG.",
    "No channels to match the EPG with.": u"لا توجد قنوات لمطابقة EPG معها.",
    "No matching channels found.": u"لم يتم العثور على قنوات مطابقة في EPG.",
    "Resolving stream ...": u"جارٍ تجهيز البث ...",
    "Could not open the stream": u"تعذر فتح البث",
    "This stream is not playable": u"هذا البث غير قابل للتشغيل",
    # sources
    "Servers / Playlists": u"السيرفرات / القوائم",
    "Your playlists and portals": u"قوائمك وبورتالاتك",
    "M3U playlist": u"قائمة M3U",
    "MAG portal": u"بورتال MAG",
    "MAC based Stalker portal": u"بورتال Stalker يعتمد على MAC",
    "Add M3U playlist": u"إضافة قائمة M3U",
    "Add MAG portal": u"إضافة بورتال MAG",
    "Edit source": u"تعديل المصدر",
    "Delete source": u"حذف المصدر",
    "Refresh now": u"تحديث الآن",
    "Delete this source?": u"حذف هذا المصدر؟",
    "Playlist name": u"اسم القائمة",
    "Playlist URL (m3u / m3u8)": u"رابط القائمة (m3u / m3u8)",
    "Portal name": u"اسم البورتال",
    "Portal URL": u"رابط البورتال",
    "MAC address": u"عنوان MAC",
    "User-Agent (optional)": u"User-Agent (اختياري)",
    "Name": u"الاسم",
    "URL": u"الرابط",
    "Change name": u"تغيير الاسم",
    "Change URL": u"تغيير الرابط",
    "Change EPG URL": u"تغيير رابط EPG",
    "EPG URL (optional)": u"رابط EPG (اختياري)",
    "Change MAC": u"تغيير MAC",
    "Change user-agent": u"تغيير User-Agent",
    "Invalid MAC address": u"عنوان MAC غير صحيح",
    "Invalid URL": u"الرابط غير صحيح",
    "Enter a valid address like 00:1A:79:12:34:56": u"أدخل عنوانًا صحيحًا مثل 00:1A:79:12:34:56",
    "The address must start with http:// or https://": u"يجب أن يبدأ الرابط بـ http:// أو https://",
    "Saved": u"تم الحفظ",
    "Source activated": u"تم تنشيط المصدر",
    "No sources yet": u"لا توجد مصادر بعد",
    "Add your first M3U playlist or MAG portal.": u"أضف أول قائمة M3U أو بورتال MAG.",
    "Last update": u"آخر تحديث",
    "just now": u"الآن",
    "min ago": u"دقيقة مضت",
    "h ago": u"ساعة مضت",
    "d ago": u"يوم مضى",
    "Updated": u"تم التحديث",
    "Cache cleared": u"تم حذف الكاش",
    "Moving to the new source ...": u"جارٍ الانتقال إلى المصدر الجديد ...",
    # account
    "Account information": u"معلومات الحساب",
    "Source": u"المصدر",
    "Type": u"النوع",
    "Status": u"الحالة",
    "Expires": u"ينتهي",
    "MAC": u"MAC",
    "Portal": u"البورتال",
    "Playlist": u"القائمة",
    "Check account": u"فحص الحساب",
    "Checking account ...": u"جارٍ فحص الحساب ...",
    "Account is active": u"الحساب نشط",
    "Account has expired": u"الحساب منتهي",
    "Account status unknown": u"حالة الحساب غير معروفة",
    "This source is an M3U playlist and has no portal account.":
        u"هذا المصدر قائمة M3U وليس له حساب بورتال.",
    "Reload portal": u"تحديث البورتال",
    "Reloading portal ...": u"جارٍ تحديث البورتال ...",
    # settings
    "Player settings": u"إعدادات المشغل",
    "Save settings": u"حفظ الإعدادات",
    "Settings saved": u"تم حفظ الإعدادات",
    "You have unsaved changes. Save them now?":
        u"لديك تغييرات غير محفوظة. هل تريد حفظها الآن؟",
    "LEFT/RIGHT change  •  OK action  •  GREEN save  •  RED close":
        u"يسار/يمين تغيير  •  OK تنفيذ  •  أخضر حفظ  •  أحمر إغلاق",
    "Language": u"اللغة",
    "Stream engine": u"محرك البث",
    "HTTP timeout (seconds)": u"مهلة الاتصال (ثواني)",
    "Page size": u"حجم الصفحة",
    "Hide adult categories": u"إخفاء الأقسام للبالغين",
    "Load logos": u"تحميل الشعارات",
    "Close lists after zap": u"إغلاق القوائم بعد التشغيل",
    "Cache validity (hours)": u"صلاحية الكاش (ساعات)",
    "M3U servers file": u"ملف سيرفرات M3U",
    "MAG servers file": u"ملف سيرفرات MAC",
    "Import from server files": u"استيراد من ملفات السيرفرات",
    "Sync server files now": u"مزامنة ملفات السيرفرات الآن",
    "Import servers from the selected text files?":
        u"استيراد السيرفرات من ملفات النص المحددة؟",
    "Server files updated": u"تم تحديث ملفات السيرفرات",
    "Import completed": u"تم الاستيراد",
    "Added: {0}": u"تمت الإضافة: {0}",
    "Updated: {0}": u"تم التحديث: {0}",
    "Errors: {0}": u"الأخطاء: {0}",
    "Enable web interface": u"تفعيل واجهة الويب",
    "Web interface port": u"منفذ واجهة الويب",
    "Web interface address": u"عنوان واجهة الويب",
    "Web interface is disabled": u"واجهة الويب معطّلة",
    "Web server could not start": u"تعذر تشغيل خادم الويب",
    "Open this address from a browser on the same network:":
        u"افتح هذا العنوان من متصفح على نفس الشبكة:",
    "A PIN is required to access the web interface.":
        u"يتطلب الوصول إلى واجهة الويب رمز PIN.",
    "Clear cache": u"حذف الكاش",
    "About": u"حول",
    "About IPTV Player Pro": u"حول IPTV Player Pro",
    "Version": u"الإصدار",
    "A fast M3U and MAG/Stalker player for Enigma2.":
        u"مشغّل سريع لقوائم M3U وبورتالات MAG/Stalker على Enigma2.",
    "Reset": u"تصفير",
    "Close and reopen the plugin to apply the new language.":
        u"أغلق البلوجين وأعد فتحه لتطبيق اللغة الجديدة.",
    "Clear the cached playlists, EPG and logos?": u"حذف القوائم ودليل البرامج والشعارات المخزنة مؤقتًا؟",
    # info
    "Overview": u"نظرة عامة",
    "Year": u"السنة",
    "Rating": u"التقييم",
    "Genre": u"النوع",
    "Director": u"الإخراج",
    "Cast": u"الممثلون",
    "Duration": u"المدة",
    "Description": u"الوصف",
    "No description available.": u"لا يوجد وصف.",
    "Play": u"تشغيل",
    "OK play  •  BACK close": u"OK تشغيل  •  BACK إغلاق",
    # errors
    "Network error": u"خطأ في الشبكة",
    "Portal error": u"خطأ في البورتال",
    "Playlist error": u"خطأ في القائمة",
    "The portal did not accept the MAC address.": u"البورتال لم يقبل عنوان MAC.",
    "The portal did not return a token. Check the URL and the MAC.":
        u"لم يُرجع البورتال أي توكن. تحقق من الرابط و MAC.",
    "Invalid portal URL": u"رابط البورتال غير صحيح",
    "The portal returned an invalid response": u"أعاد البورتال استجابة غير صالحة",
    "This item has no stream command.": u"هذا العنصر لا يحتوي على أمر بث.",
    "The portal did not return a playable link.": u"لم يُرجع البورتال رابطًا قابلًا للتشغيل.",
    "The playlist is empty.": u"القائمة فارغة.",
    "The portal did not return any items.": u"لم يُرجع البورتال أي عناصر.",
    "The server returned an error": u"أعاد السيرفر خطأ",
    "Timeout": u"انتهت المهلة",
    "Connection failed": u"فشل الاتصال",
    "Details": u"التفاصيل",
    "All done": u"تم",
    "Copied from the playlist": u"من القائمة",
}

_TABLES = {"ar": _AR}
_LANGUAGE = ["ar"]


def set_language(language):
    if language not in [code for code, label in LANGUAGES]:
        language = "ar"
    _LANGUAGE[0] = language
    return language


def get_language():
    return _LANGUAGE[0]


def language_label(code):
    for item in LANGUAGES:
        if item[0] == code:
            return item[1]
    return LANGUAGES[0][1]


def _(text, *args, **kwargs):
    table = _TABLES.get(_LANGUAGE[0], {})
    value = table.get(text, text)
    if args or kwargs:
        try:
            value = value.format(*args, **kwargs)
        except Exception:
            pass
    return value
