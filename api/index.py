from http.server import BaseHTTPRequestHandler
import telebot
import os

# يتم جلب التوكن بأمان من إعدادات Vercel
TOKEN = os.environ.get("TOKEN")
bot = telebot.TeleBot(TOKEN)

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        update = telebot.types.Update.de_json(post_data.decode('utf-8'))
        bot.process_new_updates([update])
        self.send_response(200)
        self.end_headers()
        return

@bot.message_handler(func=lambda m: True)
def handle_all(m):
    text = m.text.strip() if m.text else ""
    chat_id = m.chat.id
    
    # 17- الترحيب
    if text == "ترحيب":
        bot.reply_to(m, "أهلا وسهلا بك في مجموعة نهج المنتقم عليه السلام، هل لعنت عائشة الزانية اليوم؟")
    
    # أوامر التحكم بالدردشة العامة
    elif text == "قفل الدردشة":
        bot.set_chat_permissions(chat_id, telebot.types.ChatPermissions(can_send_messages=False))
        bot.reply_to(m, "تم قفل الدردشة بنجاح.")
    elif text == "فتح الدردشة":
        bot.set_chat_permissions(chat_id, telebot.types.ChatPermissions(can_send_messages=True, can_send_media_messages=True))
        bot.reply_to(m, "تم فتح الدردشة بنجاح.")
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
            bot.pin_chat_message(chat_id, msg_id)
        elif text == "مسح":
            bot.delete_message(chat_id, msg_id)
        elif text == "حظر" or text == "بالقندرة":
            bot.ban_chat_member(chat_id, target_id)
            bot.reply_to(m, "تم الحظر بنجاح.")
        elif text == "تقييد" or text == "انچب":
            bot.restrict_chat_member(chat_id, target_id, telebot.types.ChatPermissions(can_send_messages=False))
            bot.reply_to(m, "تم التقييد.")
        elif text == "رفع مطور":
            bot.reply_to(m, "تم رفعه مطور بنجاح.")
          
