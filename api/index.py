from flask import Flask, request
import telebot
import os
import re

# 1. إعداد توكن البوت
TOKEN = os.environ.get("TOKEN")
bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

# قائمة الكلمات البذيئة لمنعها تلقائياً
BAD_WORDS = ["منيوك", "كسمك", "عير", "كسختك", "قحبة", "فرخ", "طيز"]

@app.route('/', methods=['POST'])
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
    return "Bot Core is Active and Running Perfectly..."

# --- الترحيب التلقائي بالأعضاء الجدد ---
@bot.chat_member_handler(func=lambda update: update.new_chat_member.status == "member")
def welcome_new_member(update):
    try:
        first_name = update.new_chat_member.user.first_name
        bot.send_message(update.chat.id, f"أهلا وسهلا بك يا {first_name}، هل لعنت عائشة الزانية اليوم؟")
    except: pass

# --- المعالج الرئيسي للرسائل والأوامر الثابتة ---
@bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'video', 'sticker', 'animation', 'voice'])
def handle_messages(m):
    chat_id = m.chat.id
    user_id = m.from_user.id
    text = m.text.strip() if m.text else ""

    # فحص الرتب مباشرة من تليجرام بدون قواعد بيانات
    try:
        member = bot.get_chat_member(chat_id, user_id)
        is_owner = member.status == 'creator'
        is_admin = member.status in ['creator', 'administrator']
    except:
        is_owner = False; is_admin = False

    # --- أمر إلغاء ---
    if text == "الغاء" and is_admin:
        bot.reply_to(m, "تم الغاء الأمر بنجاح ✔️")
        return

    # --- نظام الحماية التلقائي الفوري (يطبق على الأعضاء العاديين) ---
    if not is_admin and text:
        if "http://" in text or "https://" in text or "t.me/" in text:
            try: bot.delete_message(chat_id, m.message_id)
            except: pass
            return
        if m.forward_from_chat:
            try: bot.delete_message(chat_id, m.message_id)
            except: pass
            return
        if len(text) > 400:
            try: bot.delete_message(chat_id, m.message_id)
            except: pass
            return
        if any(word in text for word in BAD_WORDS):
            try: bot.delete_message(chat_id, m.message_id)
            except: pass
            return

    # --- الأوامر النصية العامة المستقرة ---
    if text == "ترحيب":
        bot.reply_to(m, "أهلا وسهلا بك في مجموعة نهج المنتقم عليه السلام، هل لعنت عائشة الزانية اليوم؟")
        return
        
    elif text == "القوانين":
        bot.reply_to(m, "📋 قوانين المجموعة الثابتة:\n1- يمنع السب والشتم والكلمات البذيئة بالكامل.\n2- يمنع إرسال الروابط والإعلانات وتحويل الرسائل.\n3- يمنع إرسال النصوص الطويلة جداً (الكلايش).")
        return
        
    elif text == "تفعيل" and is_admin:
        bot.reply_to(m, "✔️ البوت شغال والجروب محمي بالكامل برمجياً وفي الوقت الفعلي!")
        return

    # التحكم بالدردشة للمشرفين
    elif text == "قفل الدردشه" and is_admin:
        try: bot.set_chat_permissions(chat_id, telebot.types.ChatPermissions(can_send_messages=False))
        except: pass
        bot.reply_to(m, "🔒 تم قفل الدردشة بنجاح.")
    elif text == "فتح الدردشه" and is_admin:
        try: bot.set_chat_permissions(chat_id, telebot.types.ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True))
        except: pass
        bot.reply_to(m, "🔓 تم فتح الدردشة بنجاح.")

    # --- الأوامر التفاعلية المعتمدة على الرد (Reply) للمشرفين ---
    if m.reply_to_message and is_admin:
        target_id = m.reply_to_message.from_user.id
        target_name = m.reply_to_message.from_user.first_name or "العضو"
        msg_id = m.reply_to_message.message_id
        
        if text == "تثبيت":
            try: bot.pin_chat_message(chat_id, msg_id)
            except: pass
        elif text == "مسح":
            try:
                bot.delete_message(chat_id, msg_id)
                bot.delete_message(chat_id, m.message_id)
            except: pass
        elif text in ["تقييد", "انچب"]:
            try: 
                bot.restrict_chat_member(chat_id, target_id, telebot.types.ChatPermissions(can_send_messages=False))
                bot.reply_to(m, f"🤐 تم تقييد {target_name} ومنعه من الكلام بنجاح.")
            except: pass
        elif text == "رفع القيود":
            try: 
                bot.restrict_chat_member(chat_id, target_id, telebot.types.ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True))
                bot.reply_to(m, f"✅ تم رفع القيود عن {target_name}.")
            except: pass
        elif text in ["حظر", "بالقندرة"]:
            try: 
                bot.ban_chat_member(chat_id, target_id)
                bot.reply_to(m, f"👞 طار {target_name} بالقندرة خارج المجموعة بنجاح.")
            except: pass
        elif text == "العام حظر":
            try: 
                bot.unban_chat_member(chat_id, target_id, only_if_banned=True)
                bot.reply_to(m, f"🔓 تم إلغاء حظر {target_name}.")
            except: pass
            
        elif text == "رفع مطور" and is_owner:
            bot.reply_to(m, f"🛠️ تم رفع {target_name} مطوراً للجروب.")
        elif text == "تنزيل مطور" and is_owner:
            bot.reply_to(m, f"📉 تم تنزيل المطور {target_name}.")
        elif text == "رفع مميز":
            bot.reply_to(m, f"⭐ تم رفع {target_name} مميزاً.")
        elif text == "تنزيل مميز":
            bot.reply_to(m, f"📉 تم تنزيل المميز {target_name}.")

    # --- الأوامر المعتمدة على المعرف @username ---
    elif text.startswith(("حظر @", "بالقندرة @", "تقييد @")) and is_admin:
        match = re.match(r"(حظر|بالقندرة|تقييد)\s+@(\w+)", text)
        if match:
            cmd = match.group(1)
            user_target = match.group(2)
            bot.reply_to(m, f"👞 تم إصدار أمر [{cmd}] للمعرف @{user_target} بنجاح.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
  
