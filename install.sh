#!/bin/bash
#----------------------------
# IPTV Player Pro - Installer Script
#----------------------------

# الألوان للرسائل
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # Color Reset

PROJECT_DIR="D:\IPTVPlayerPro"
IPK_NAME="enigma2-plugin-extensions-iptvplayerpro_1.4.0_all.ipk"

echo -e "${GREEN}=== IPTV Player Pro Installer Script ===${NC}"
echo ""

# التحقق من وجود المجلد
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}❌ خطأ: المجلد $PROJECT_DIR غير موجود${NC}"
    exit 1
fi

cd "$PROJECT_DIR" || exit 1

echo -e "${YELLOW}📁 التحقق من الملفات...${NC}"

# التحقق من الملفات الأساسية
if [ ! -f "src/IPTVPlayerPro/core/backends.py" ]; then
    echo -e "${RED}❌ ملف backends.py غير موجود${NC}"
    exit 1
fi

if [ ! -f "src/IPTVPlayerPro/ui/skins.py" ]; then
    echo -e "${RED}❌ ملف skins.py غير موجود${NC}"
    exit 1
fi

echo -e "${GREEN}✅ جميع الملفات الأساسية موجودة${NC}"
echo ""

# بناء الإيبك
echo -e "${YELLOW}🔨 بناء ملف الإيبك...${NC}"

# طريقة 1: باستخدام install.sh إذا existed
if [ -f "install.sh" ]; then
    echo "جاري تنفيذ install.sh..."
    bash install.sh 2>&1 | tail -20
    IPK_RESULT=$?
else
    # طريقة 2: استخدام python build
    if [ -f "build.py" ]; then
        echo "جاري التشغيل بواسطة build.py..."
        python build.py 2>&1 | tail -20
        IPK_RESULT=$?
    else
        # طريقة 3: cpkg أو manual build
        echo -e "${RED}⚠️ لا توجد طريقة بناء تلقائية محددة${NC}"
        echo "الملفات موجودة وجاهزة للManual Build"
        IPK_RESULT=0
    fi
fi

# التحقق من إنشاء الإيبك
if [ -f "dist/$IPK_NAME" ]; then
    echo -e "${GREEN}✅ تم إنشاء ملف الإيبك successfully:${NC}"
    ls -la dist/$IPK_NAME
    IPK_SIZE=$(stat -c%s dist/$IPK_NAME)
    echo -e "   الحجم: ${IPK_SIZE} bytes"
else
    echo -e "${RED}❌ لم يتم إنشاء ملف الإيبك${NC}"
    echo -e "   يرجى التحقق من سجلات البناء أعلاه"
    exit 1
fi

echo ""
echo -e "${GREEN}=== خيارات التثبيت ===${NC}"
echo ""
echo -e "${GREEN}1. تثبيت على جهاز (via scp/ssh)${NC}"
echo -e "${GREEN}2. تثبيت يدوي (Copy ipk to device)${NC}"
echo -e "${GREEN}3. فقط البناء (Build only)${NC}"
echo -e "${GREEN}4. عرض تعليمات التثبيت${NC}"
echo ""

read -p "اختر خياراً (1-4): " install_choice

case $install_choice in
    1)
        echo -e "${YELLOW}📡 أدخل عنوان IP للجهاز:${NC}"
        read device_ip
        
        if [ -z "$device_ip" ]; then
            echo -e "${RED}❌ لم يدخل عنوان IP${NC}"
            exit 1
        fi
        
        echo -e "${YELLOW}📡 نسخ الملف للجهاز...${NC}"
        scp "dist/$IPK_NAME" "root@$device_ip:/tmp/"
        
        echo -e "${YELLOW}🔧 بدء التثبيت على الجهاز...${NC}"
        echo -e "   ssh root@$device_ip 'opkg install /tmp/$IPK_NAME'"
        echo ""
        echo -e "OR manually on device:${NC}"
        echo "   opkg install /tmp/$IPK_NAME"
        echo "   أو عبر واجهة الويب: http://<ip>/cgi-bin/ipkg.cgi"
        ;;
        
    2)
        echo -e "${YELLOW}📋 تعليمات التثبيت اليدوي:${NC}"
        echo "   1. نسخ الملف: dist/$IPK_NAME"
        echo "   2. نقله للجهاز: scp dist/$IPK_NAME root@<IP-device>:/tmp/"
        echo "   3. التثبيت على الجهاز: opkg install /tmp/$IPK_NAME"
        echo "   4. إعادة تشغيل enigma2: service enigma2 restart"
        ;;
        
    3)
        echo -e "${GREEN}✅ تم البناء فقط - الملف في: dist/$IPK_NAME${NC}"
        ;;
        
    4)
        echo -e "${GREEN}📋 تعليمات التثبيت:${NC}"
        echo "1. Build the ipk: bash install.sh (choice 1 or 2)"
        echo "2. Copy to device: scp dist/enigma2-plugin-extensions-iptvplayerpro_1.4.0_all.ipk root@<IP>/tmp/"
        echo "2. Install on device: opkg install /tmp/enigma2-plugin-extensions-iptvplayerpro_1.4.0_all.ipk"
        echo "3. Restart enigma2: service enigma2 restart"
        echo "4. Test: Live TV -> should show loading bar first, then list"
        ;;
    
    *)
        echo -e "${RED}❌ خيار غير صحيح${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}=== انتهى السكريبت ===${NC}"
echo -e "لمزيد من المعلومات، راجع:${NC}"
echo "   - GitHub: https://github.com/azroukarim/IptvPlayerPro"
echo "   - README: اقرأ ملف README.md في المجلد"
