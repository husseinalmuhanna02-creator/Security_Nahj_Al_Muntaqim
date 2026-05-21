from flask import Flask, request
import telebot
import os

# جلب التوكن بأمان من إعدادات Vercel
TOKEN = os.environ.get("TOKEN")
bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

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
    return "Bot is running..."

@bot.message_handler(func=lambda m: True)
def handle_all(m):
    text = m.text.strip() if m.text else ""
    chat_id = m.chat.id
    
    # 17- الترحيب
    if text == "ترحيب":
        bot.reply_to(m, "أهلا وسهلا بك في مجموعة نهج المنتقم عليه السلام، هل لعنت عائشة الزانية اليوم؟")
    
    # أوامر التحكم بالدردشة العامة
    elif text == "قفل الدردشة":
        try:
            bot.set_chat_permissions(chat_id, telebot.types.ChatPermissions(can_send_messages=False))
            bot.reply_to(m, "تم قفل الدردشة بنجاح.")
        except Exception as e:
            bot.reply_to(m, f"فشل القفل: تأكد أنني مشرف بصلاحيات كاملة.")
            
    elif text == "فتح الدردشة":
        try:
            bot.set_chat_permissions(chat_id, telebot.types.ChatPermissions(can_send_messages=True, can_send_media_messages=True))
            bot.reply_to(m, "تم فتح الدردشة بنجاح.")
        except Exception as e:
            pass
            
    elif text == "قفل الكلايش":
        bot.reply_to(m, "تم قفل الكلايش")
    elif text == "فتح الكلايش":
        bot.reply_to(m, "تم فتح الكلايش")
    elif text == "الغاء":
        bot.reply_to(m, "تم الغاء الأمر بنجاح ✔️")

    # الأوامر التي تتطلب الرد على عضو (Reply)
    elif m.reply_to_message:
        target_id = m.reply_to_message.from_user.id
        msg_id = m.reply_to_message.message_id
        
        if text == "تثبيت":
            try: bot.pin_chat_message(chat_id, msg_id)
            except: pass
        elif text == "مسح":
            try: bot.delete_message(chat_id, msg_id)
            except: pass
        elif text == "حظر" or text == "بالقندرة":
            try:
                bot.ban_chat_member(chat_id, target_id)
                bot.reply_to(m, "تم الحظر بنجاح.")
            except: pass
        elif text == "تقييد" or text == "انچب":
            try:
                bot.restrict_chat_member(chat_id, target_id, telebot.types.ChatPermissions(can_send_messages=False))
                bot.reply_to(m, "تم التقييد.")
            except: pass
        elif text == "رفع مطور":
            bot.reply_to(m, "تم رفعه مطور بنجاح.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
    
