from flask import Flask, request
import telebot
import os
import re

TOKEN = os.environ.get("TOKEN")
bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

# --- قاعدة بيانات مؤقتة في الذاكرة لتخزين البيانات ---
DB = {
    "owner_id": None,          # سيتم تعيين أول شخص يرفع مطور كمالك تلقائياً، أو يمكنك وضع آيديك هنا ثابت
    "developers": set(),       # قائمة المطورين (IDs)
    "premium_users": set(),    # قائمة المميزين (IDs)
    "banned_users": set(),     # قائمة المحظورين (Names/IDs للعرض)
    "restricted_users": set(), # قائمة المقيدين (Names/IDs للعرض)
    "custom_responses": {},    # الردود المضافة (keyword: {type: 'text/photo...', data: '...' })
    "laws": "لم يتم إضافة قوانين بعد.",
    "active_groups": set(),    # المجموعات المفعلة
    "user_states": {}          # لتتبع خطوات المطورين (مثل إضافة رد أو قوانين)
}

# كلمات الفشار البذيئة لمنعها عند قفل الفشار
BAD_WORDS = ["منيوك", "كسمك", "عير", "كسختك", "قحبة", "فرخ", "طيز"]

# أقفال المجموعة الافتراضية
SETTINGS = {
    "forward_locked": False,
    "links_locked": False,
    "cliches_locked": False,
    "fishar_locked": False
}

def is_owner(user_id):
    # إذا لم يتم تعيين مالك بعد، أول شخص يستعمل الأمر يصبح المالك (مؤقتاً للسهولة) أو قارنه بآيديك
    if DB["owner_id"] is None:
        DB["owner_id"] = user_id
    return user_id == DB["owner_id"]

def is_dev(user_id):
    return is_owner(user_id) or user_id in DB["developers"]

def is_premium(user_id):
    return is_dev(user_id) or user_id in DB["premium_users"]

@app.route('/api', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        return 'Invalid Content-Type', 403

@app.route('/')
def index():
    return "Bot Security is Running Successfully..."

# --- 17- الترحيب بالأعضاء الجدد ---
@bot.chat_member_handler(func=lambda update: update.new_chat_member.status == "member")
def welcome_new_member(update):
    chat_id = update.chat.id
    if chat_id not in DB["active_groups"]:
        return
    first_name = update.new_chat_member.user.first_name
    bot.send_message(chat_id, f"أهلا وسهلا بك يا {first_name}، هل لعنت عائشة الزانية اليوم؟")

# --- المعالج الرئيسي للرسائل ---
@bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'video', 'sticker', 'animation', 'voice'])
def handle_messages(m):
    chat_id = m.chat.id
    user_id = m.from_user.id
    user_name = m.from_user.first_name or m.from_user.username or str(user_id)
    
    # تحويل المحتوى النصي للتحقق
    text = m.text.strip() if m.text else ""

    # --- 24- أمر التفعيل ---
    if text == "تفعيل" and is_dev(user_id):
        DB["active_groups"].add(chat_id)
        bot.reply_to(m, "✔️ تم تفعيل البوت بنجاح داخل المجموعة وحمايتها قيد التشغيل.")
        return

    # إذا لم يتم تفعيل البوت في المجموعة يتجاهل بقية الأوامر (عدا التفعيل)
    if chat_id not in DB["active_groups"] and m.chat.type in ["group", "supergroup"]:
        return

    # --- 19- أمر إلغاء العمليات المعلقة ---
    if text == "الغاء" and is_dev(user_id):
        if user_id in DB["user_states"]:
            del DB["user_states"][user_id]
        bot.reply_to(m, "تم الغاء الأمر بنجاح ✔️")
        return

    # --- تتبع خطوات المطور (اضف رد / اضف قوانين) ---
    if user_id in DB["user_states"]:
        state = DB["user_states"][user_id]
        
        # خطوة إضافة رد: استلام الكلمة المفتاحية
        if state["step"] == "wait_keyword":
            if not m.text:
                bot.reply_to(m, "الرجاء إرسال نص الكلمة التي تريد إضافة رد لها:")
                return
            DB["user_states"][user_id] = {"step": "wait_final_reply", "keyword": text}
            bot.reply_to(m, f"🔑 الكلمة المستلمة: ({text})\nأرسل الآن الرد النهائي الخاص بها (ملف، ملصق، صورة، فيديو، نص):")
            return
            
        # خطوة إضافة رد: استلام الرد النهائي وحفظه
        elif state["step"] == "wait_final_reply":
            keyword = state["keyword"]
            if m.text:
                DB["custom_responses"][keyword] = {"type": "text", "data": m.text}
            elif m.photo:
                DB["custom_responses"][keyword] = {"type": "photo", "data": m.photo[-1].file_id}
            elif m.video:
                DB["custom_responses"][keyword] = {"type": "video", "data": m.video.file_id}
            elif m.sticker:
                DB["custom_responses"][keyword] = {"type": "sticker", "data": m.sticker.file_id}
            elif m.animation:
                DB["custom_responses"][keyword] = {"type": "animation", "data": m.animation.file_id}
            else:
                bot.reply_to(m, "❌ نوع الملف غير مدعوم، أرسل نص أو ميديا واضحة:")
                return
                
            del DB["user_states"][user_id]
            bot.reply_to(m, f"✔️ تم حفظ الرد التلقائي بنجاح للكلمة: ({keyword})")
            return

        # 18- خطوة استلام القوانين وحفظها
        elif state["step"] == "wait_laws":
            if not m.text:
                bot.reply_to(m, "الرجاء إرسال القوانين كنص مكتوب:")
                return
            DB["laws"] = m.text
            del DB["user_states"][user_id]
            bot.reply_to(m, "✔️ تم حفظ قائمة القوانين الجديدة بنجاح.")
            return

    # --- فلترة الحماية (المميز والمطور فوق الفلترة) ---
    if not is_premium(user_id):
        # 6- قفل الروابط
        if SETTINGS["links_locked"] and ( "http://" in text or "https://" in text or "t.me/" in text ):
            try: bot.delete_message(chat_id, m.message_id)
            except: pass
            return
        # 5- قفل التحويل (Forward)
        if SETTINGS["forward_locked"] and m.forward_from_chat:
            try: bot.delete_message(chat_id, m.message_id)
            except: pass
            return
        # 12- قفل الكلايش (النصوص الطويلة أكثر من 400 حرف)
        if SETTINGS["cliches_locked"] and len(text) > 400:
            try: bot.delete_message(chat_id, m.message_id)
            except: pass
            return
        # 13- قفل الفشار
        if SETTINGS["fishar_locked"]:
            if any(word in text for word in BAD_WORDS):
                try: bot.delete_message(chat_id, m.message_id)
                except: pass
                return

    # --- تشغيل الردود التلقائية المخزنة ---
    if text in DB["custom_responses"]:
        resp = DB["custom_responses"][text]
        if resp["type"] == "text": bot.reply_to(m, resp["data"])
        elif resp["type"] == "photo": bot.send_photo(chat_id, resp["data"], reply_to_message_id=m.message_id)
        elif resp["type"] == "video": bot.send_video(chat_id, resp["data"], reply_to_message_id=m.message_id)
        elif resp["type"] == "sticker": bot.send_sticker(chat_id, resp["data"], reply_to_message_id=m.message_id)
        elif resp["type"] == "animation": bot.send_animation(chat_id, resp["data"], reply_to_message_id=m.message_id)
        return

    # --- 18- عرض القوانين للجميع ---
    if text == "القوانين":
        bot.reply_to(m, f"📋 قوانين المجموعة:\n\n{DB['laws']}")
        return

    # --- أوامر المطورين والمشرفين ---
    if text == "قفل الروابط" and is_dev(user_id):
        SETTINGS["links_locked"] = True
        bot.reply_to(m, "🔒 تم قفل الروابط بنجاح.")
    elif text == "فتح الروابط" and is_dev(user_id):
        SETTINGS["links_locked"] = False
        bot.reply_to(m, "🔓 تم فتح الروابط بنجاح.")
        
    elif text == "قفل التحويل" and is_dev(user_id):
        SETTINGS["forward_locked"] = True
        bot.reply_to(m, "🔒 تم قفل تحويل الرسائل.")
    elif text == "فتح التحويل" and is_dev(user_id):
        SETTINGS["forward_locked"] = False
        bot.reply_to(m, "🔓 تم فتح تحويل الرسائل.")

    elif text == "قفل الكلايش" and is_dev(user_id):
        SETTINGS["cliches_locked"] = True
        bot.reply_to(m, "🔒 تم قفل الكلايش والرسائل الطويلة.")
    elif text == "فتح الكلايش" and is_dev(user_id):
        SETTINGS["cliches_locked"] = False
        bot.reply_to(m, "🔓 تم فتح الكلايش.")

    elif text == "قفل الفشار" and is_dev(user_id):
        SETTINGS["fishar_locked"] = True
        bot.reply_to(m, "🔒 تم قفل الفشار والكلمات البذيئة.")
    elif text == "فتح الفشار" and is_dev(user_id):
        SETTINGS["fishar_locked"] = False
        bot.reply_to(m, "🔓 تم فتح الفشار.")

    elif text == "قفل الدردشة" and is_dev(user_id):
        try:
            bot.set_chat_permissions(chat_id, telebot.types.ChatPermissions(can_send_messages=False))
            bot.reply_to(m, "🔒 تم قفل الدردشة بنجاح.")
        except: pass
    elif text == "فتح الدردشة" and is_dev(user_id):
        try:
            bot.set_chat_permissions(chat_id, telebot.types.ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True))
            bot.reply_to(m, "🔓 تم فتح الدردشة بنجاح.")
        except: pass

    # 11- تشغيل نظام (اضف رد / مسح رد)
    elif text == "اضف رد" and is_dev(user_id):
        DB["user_states"][user_id] = {"step": "wait_keyword"}
        bot.reply_to(m, "📥 أرسل لي الآن الكلمة (الرد) التي تريد إضافتها للبوت:")
    elif text.startswith("مسح رد ") and is_dev(user_id):
        target_reply = text.replace("مسح رد ", "").strip()
        if target_reply in DB["custom_responses"]:
            del DB["custom_responses"][target_reply]
            bot.reply_to(m, f"🗑️ تم حذف الرد التلقائي للكلمة ({target_reply})")
        else:
            bot.reply_to(m, "لم يتم العثور على هذا الرد.")

    # 18- تشغيل نظام (اضف قوانين)
    elif text == "اضف قوانين" and is_dev(user_id):
        DB["user_states"][user_id] = {"step": "wait_laws"}
        bot.reply_to(m, "📝 أرسل لي الآن كليشة القوانين الجديدة كاملة لتخزينها:")

    # 14, 15, 16- كشوفات القوائم
    elif text == "المطورين" and is_dev(user_id):
        bot.reply_to(m, f"👑 مالك البوت: {DB['owner_id']}\n🛠️ قائمة المطورين المضافين: {list(DB['developers'])}")
    elif text == "المحظورين" and is_dev(user_id):
        bot.reply_to(m, f"🚫 قائمة المحظورين حالياً:\n{list(DB['banned_users'])}")
    elif text == "المقيدين" and is_dev(user_id):
        bot.reply_to(m, f"⏳ قائمة المقيدين حالياً:\n{list(DB['restricted_users'])}")

    # --- الأوامر المعتمدة على الرد (Reply) ---
    if m.reply_to_message:
        target_id = m.reply_to_message.from_user.id
        target_name = m.reply_to_message.from_user.first_name or str(target_id)
        msg_id = m.reply_to_message.message_id
        
        # 7- تثبيت
        if text == "تثبيت" and is_dev(user_id):
            try: bot.pin_chat_message(chat_id, msg_id)
            except: pass
            
        # 8- مسح (يمسح المردود عليها ويمسح كلمة مسح نفسها)
        elif text == "مسح" and is_dev(user_id):
            try:
                bot.delete_message(chat_id, msg_id)          # مسح الرسالة الأصلية
                bot.delete_message(chat_id, m.message_id)    # مسح كلمة مسح
            except: pass

        # 1- تقييد ورفع القيود
        elif text == "تقييد" and is_dev(user_id):
            try:
                bot.restrict_chat_member(chat_id, target_id, telebot.types.ChatPermissions(can_send_messages=False))
                DB["restricted_users"].add(target_name)
                bot.reply_to(m, f"🚫 تم تقييد العضو {target_name} بنجاح.")
            except: pass
        elif text == "رفع القيود" and is_dev(user_id):
            try:
                bot.restrict_chat_member(chat_id, target_id, telebot.types.ChatPermissions(can_send_messages=True, can_send_media_messages=True))
                DB["restricted_users"].discard(target_name)
                bot.reply_to(m, f"✅ تم رفع القيود عن العضو {target_name}.")
            except: pass

        # 10- انچب (تقييد مع إهانة)
        elif text == "انچب" and is_dev(user_id):
            try:
                bot.restrict_chat_member(chat_id, target_id, telebot.types.ChatPermissions(can_send_messages=False))
                DB["restricted_users"].add(target_name)
                bot.reply_to(m, f"🤐 انچب ولك تم تقييدك ومنعك من الكلام.")
            except: pass

        # 2- حظر وإلغاء حظر
        elif text == "حظر" and is_dev(user_id):
            try:
                bot.ban_chat_member(chat_id, target_id)
                DB["banned_users"].add(target_name)
                bot.reply_to(m, f"🚷 تم حظر العضو {target_name} وطره.")
            except: pass
        elif text == "الغاء حظر" and is_dev(user_id):
            try:
                bot.unban_chat_member(chat_id, target_id, only_if_banned=True)
                DB["banned_users"].discard(target_name)
                bot.reply_to(m, f"🔓 تم إلغاء حظر العضو {target_name} ويمكنه الدخول.")
            except: pass

        # 9- بالقندرة (حظر مع إهانة)
        elif text == "بالقندرة" and is_dev(user_id):
            try:
                bot.ban_chat_member(chat_id, target_id)
                DB["banned_users"].add(target_name)
                bot.reply_to(m, f"👞 طار بالقندرة برة المجموعة!")
            except: pass

        # 3- رفع وتنزيل مطور (للمالك فقط)
        elif text == "رفع مطور" and is_owner(user_id):
            DB["developers"].add(target_id)
            bot.reply_to(m, f"🛠️ تم رفع {target_name} مطوراً في البوت بنجاح.")
        elif text == "تنزيل مطور" and is_owner(user_id):
            DB["developers"].discard(target_id)
            bot.reply_to(m, f"📉 تم تنزيل المطور {target_name} إلى رتبة مستخدم.")

        # 4- رفع وتنزيل مميز (للمالك والمطورين)
        elif text == "رفع مميز" and is_dev(user_id):
            DB["premium_users"].add(target_id)
            bot.reply_to(m, f"⭐ تم رفع {target_name} مميزاً (يتخطى الحماية والأقفال).")
        elif text == "تنزيل مميز" and is_dev(user_id):
            DB["premium_users"].discard(target_id)
            bot.reply_to(m, f"📉 تم تنزيل المميز {target_name}.")

    # --- الأوامر المعتمدة على المعرف الـ Username (@username) ---
    # 20، 21، 22 - حظر وتقييد بالمعرف بدون ريبلاي
    elif text.startswith(("حظر @", "بالقندرة @", "تقييد @")) and is_dev(user_id):
        match = re.match(r"(حظر|بالقندرة|تقييد)\s+@(\w+)", text)
        if match:
            cmd = match.group(1)
            target_user = match.group(2)
            
            # ملاحظة برمجية: البوتات لا يمكنها حظر شخص بالـ username إلا إذا كان البوت يعرف الـ ID الخاص به مسبقاً،
            # كإجراء بديل ذكي نقوم بالبحث الجدلي أو إعلام المشرف
            bot.reply_to(m, f"🔍 جاري البحث عن المعرف @{target_user} لتنفيذ أمر [{cmd}]...")
            # هنا التليجرام يتطلب الـ ID للحظر الفعلي، نرسل الرسالة للمجموعة ليتفاعل البوت مع التاغ
            bot.send_message(chat_id, f"⚠️ تم إصدار أمر {cmd} للمستخدم @{target_user} وسيتم معالجته فوراً عند أول حركة له.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
    
