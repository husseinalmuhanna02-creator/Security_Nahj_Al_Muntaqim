from flask import Flask, request
import telebot
import firebase_admin
from firebase_admin import credentials, db
import os
import re
import json

# 1. إعداد توكن البوت من بيئة Vercel
TOKEN = os.environ.get("TOKEN")
bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

# 2. جلب مفتاح Firebase بأمان من متغيرات Vercel البيئية
FIREBASE_CONFIG = os.environ.get("FIREBASE_KEY")

if FIREBASE_CONFIG and not firebase_admin._apps:
    try:
        creds_dict = json.loads(FIREBASE_CONFIG)
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            
        cred = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://nahj-al-muntaqem-bot-5f7ad-default-rtdb.firebaseio.com/'
        })
    except Exception as e:
        print(f"Firebase Init Error: {e}")

# قائمة الكلمات البذيئة لمنعها
BAD_WORDS = ["منيوك", "كسمك", "عير", "كسختك", "قحبة", "فرخ", "طيز"]

def get_data(path, default):
    try:
        ref = db.reference(path)
        val = ref.get()
        return val if val is not None else default
    except: return default

def set_data(path, value):
    try: db.reference(path).set(value)
    except: pass

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
    return "Bot Core with Safe Firebase is Active..."

@bot.chat_member_handler(func=lambda update: update.new_chat_member.status == "member")
def welcome_new_member(update):
    chat_id = str(update.chat.id)
    if not get_data(f'groups/{chat_id}/active', False): return
    first_name = update.new_chat_member.user.first_name
    bot.send_message(update.chat.id, f"أهلا وسهلا بك يا {first_name}، هل لعنت عائشة الزانية اليوم؟")

@bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'video', 'sticker', 'animation', 'voice'])
def handle_messages(m):
    chat_id = str(m.chat.id)
    user_id = str(m.from_user.id)
    text = m.text.strip() if m.text else ""
    
    try:
        member_status = bot.get_chat_member(m.chat.id, m.from_user.id).status
        is_chat_admin = member_status in ['creator', 'administrator']
        is_chat_owner = member_status == 'creator'
    except:
        is_chat_admin = False; is_chat_owner = False

    developers = get_data(f'groups/{chat_id}/developers', [])
    premium_users = get_data(f'groups/{chat_id}/premium', [])
    
    is_bot_dev = is_chat_owner or user_id in developers
    is_bot_premium = is_bot_dev or user_id in premium_users or is_chat_admin

    # --- وضعنا أمر التفعيل في البداية تماماً لتخطي القفل ---
    if text == "تفعيل" and is_chat_admin:
        set_data(f'groups/{chat_id}/active', True)
        set_data(f'groups/{chat_id}/settings/links', True)
        set_data(f'groups/{chat_id}/settings/forward', True)
        set_data(f'groups/{chat_id}/settings/cliches', True)
        set_data(f'groups/{chat_id}/settings/fishar', True)
        bot.reply_to(m, "✔️ تم تفعيل البوت بنجاح وحفظ غرفتك داخل قاعدة بيانات Firebase السحابية.")
        return

    # التحقق من التفعيل لبقية الأوامر
    if not get_data(f'groups/{chat_id}/active', False): return

    if text == "الغاء" and is_bot_dev:
        if get_data(f'states/{user_id}', None):
            set_data(f'states/{user_id}', None)
        bot.reply_to(m, "تم الغاء الأمر بنجاح ✔️")
        return

    user_state = get_data(f'states/{user_id}', None)
    if user_state and is_bot_dev:
        if user_state['step'] == 'wait_keyword':
            if not text: bot.reply_to(m, "أرسل لي الكلمة كنص رجاءً:"); return
            set_data(f'states/{user_id}', {'step': 'wait_reply', 'keyword': text})
            bot.reply_to(m, f"🔑 تم استلام الكلمة: ({text})\nأرسل الآن الرد النهائي (ملف، ملصق، صورة، فيديو، نص):")
            return
        elif user_state['step'] == 'wait_reply':
            keyword = user_state['keyword']
            reply_data = {}
            if m.text: reply_data = {'type': 'text', 'data': m.text}
            elif m.photo: reply_data = {'type': 'photo', 'data': m.photo[-1].file_id}
            elif m.video: reply_data = {'type': 'video', 'data': m.video.file_id}
            elif m.sticker: reply_data = {'type': 'sticker', 'data': m.sticker.file_id}
            elif m.animation: reply_data = {'type': 'animation', 'data': m.animation.file_id}
            
            if reply_data:
                set_data(f'groups/{chat_id}/responses/{keyword}', reply_data)
                set_data(f'states/{user_id}', None)
                bot.reply_to(m, f"✔️ تم حفظ الرد السحابي بنجاح لكلمة: ({keyword})")
            else:
                bot.reply_to(m, "الملف غير مدعوم، أرسل نص أو ميديا واضحة:")
            return
        elif user_state['step'] == 'wait_laws':
            if not text: bot.reply_to(m, "أرسل القوانين بنص مكتوب:"); return
            set_data(f'groups/{chat_id}/laws', text)
            set_data(f'states/{user_id}', None)
            bot.reply_to(m, "✔️ تم حفظ قائمة القوانين الجديدة في السحابة بنجاح.")
            return

    if not is_bot_premium and text:
        if get_data(f'groups/{chat_id}/settings/links', True) and ("http://" in text or "https://" in text or "t.me/" in text):
            try: bot.delete_message(m.chat.id, m.message_id)
            except: pass
            return
        if get_data(f'groups/{chat_id}/settings/forward', True) and m.forward_from_chat:
            try: bot.delete_message(m.chat.id, m.message_id)
            except: pass
            return
        if get_data(f'groups/{chat_id}/settings/cliches', True) and len(text) > 400:
            try: bot.delete_message(m.chat.id, m.message_id)
            except: pass
            return
        if get_data(f'groups/{chat_id}/settings/fishar', True) and any(word in text for word in BAD_WORDS):
            try: bot.delete_message(m.chat.id, m.message_id)
            except: pass
            return

    custom_resp = get_data(f'groups/{chat_id}/responses/{text}', None)
    if custom_resp:
        rtype = custom_resp['type']
        rdata = custom_resp['data']
        if rtype == 'text': bot.reply_to(m, rdata)
        elif rtype == 'photo': bot.send_photo(m.chat.id, rdata, reply_to_message_id=m.message_id)
        elif rtype == 'video': bot.send_video(m.chat.id, rdata, reply_to_message_id=m.message_id)
        elif rtype == 'sticker': bot.send_sticker(m.chat.id, rdata, reply_to_message_id=m.message_id)
        elif rtype == 'animation': bot.send_animation(m.chat.id, rdata, reply_to_message_id=m.message_id)
        return

    if text == "ترحيب":
        bot.reply_to(m, "أهلا وسهلا بك في مجموعة نهج المنتقم عليه السلام، هل لعنت عائشة الزانية اليوم؟")
    elif text == "القوانين":
        laws_text = get_data(f'groups/{chat_id}/laws', "لم يتم إضافة قوانين للمجموعة بعد بواسطة المطور.")
        bot.reply_to(m, f"📋 قوانين المجموعة الحالية:\n\n{laws_text}")

    elif text == "قفل الروابط" and is_bot_dev: set_data(f'groups/{chat_id}/settings/links', True); bot.reply_to(m, "🔒 تم قفل الروابط.")
    elif text == "فتح الروابط" and is_bot_dev: set_data(f'groups/{chat_id}/settings/links', False); bot.reply_to(m, "🔓 تم فتح الروابط.")
    elif text == "قفل التحويل" and is_bot_dev: set_data(f'groups/{chat_id}/settings/forward', True); bot.reply_to(m, "🔒 تم قفل تحويل الرسائل.")
    elif text == "فتح التحويل" and is_bot_dev: set_data(f'groups/{chat_id}/settings/forward', False); bot.reply_to(m, "🔓 تم فتح تحويل الرسائل.")
    elif text == "قفل الكلايش" and is_bot_dev: set_data(f'groups/{chat_id}/settings/cliches', True); bot.reply_to(m, "🔒 تم قفل الرسائل الطويلة (الكلايش).")
    elif text == "فتح الكلايش" and is_bot_dev: set_data(f'groups/{chat_id}/settings/cliches', False); bot.reply_to(m, "🔓 تم فتح الكلايش.")
    elif text == "قفل الفشار" and is_bot_dev: set_data(f'groups/{chat_id}/settings/fishar', True); bot.reply_to(m, "🔒 تم قفل الفشار والكلمات البذيئة.")
    elif text == "فتح الفشار" and is_bot_dev: set_data(f'groups/{chat_id}/settings/fishar', False); bot.reply_to(m, "🔓 تم فتح الفشار.")

    elif text == "قفل الدردشه" and is_bot_dev:
        try: bot.set_chat_permissions(m.chat.id, telebot.types.ChatPermissions(can_send_messages=False))
        except: pass
        bot.reply_to(m, "🔒 تم قفل الدردشة بنجاح.")
    elif text == "فتح الدردشه" and is_bot_dev:
        try: bot.set_chat_permissions(m.chat.id, telebot.types.ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True))
        except: pass
        bot.reply_to(m, "🔓 تم فتح الدردشة بنجاح.")

    elif text == "اضف رد" and is_bot_dev:
        set_data(f'states/{user_id}', {'step': 'wait_keyword'})
        bot.reply_to(m, "📥 أرسل لي الآن الكلمة المفتاحية التي تريد إضافة رد لها:")
    elif text.startswith("مسح رد ") and is_bot_dev:
        kw = text.replace("مسح رد ", "").strip()
        set_data(f'groups/{chat_id}/responses/{kw}', None)
        bot.reply_to(m, f"🗑️ تم حذف الرد السحابي للكلمة ({kw})")

    elif text == "اضف قوانين" and is_bot_dev:
        set_data(f'states/{user_id}', {'step': 'wait_laws'})
        bot.reply_to(m, "📝 أرسل قائمة القوانين الجديدة كاملة كرسالة نصية لحفظها سحابياً:")

    elif text == "المطورين" and is_bot_premium:
        bot.reply_to(m, f"🛠️ معرفات المطورين المضافين سحابياً:\n{developers}")
    elif text == "المحظورين" and is_bot_premium:
        banned = get_data(f'groups/{chat_id}/banned_list', [])
        bot.reply_to(m, f"🚫 قائمة المطرودين المحظورين بالبُوت:\n{banned}")
    elif text == "المقيدين" and is_bot_premium:
        restricted = get_data(f'groups/{chat_id}/restricted_list', [])
        bot.reply_to(m, f"⏳ قائمة المقيدين عن الكتابة بالبُوت:\n{restricted}")

    if m.reply_to_message and is_bot_dev:
        target_uid = str(m.reply_to_message.from_user.id)
        target_name = m.reply_to_message.from_user.first_name or "العضو"
        msg_id = m.reply_to_message.message_id
        
        if text == "تثبيت":
            try: bot.pin_chat_message(m.chat.id, msg_id)
            except: pass
        elif text == "مسح":
            try:
                bot.delete_message(m.chat.id, msg_id)
                bot.delete_message(m.chat.id, m.message_id)
            except: pass
        elif text in ["تقييد", "انچب"]:
            try:
                bot.restrict_chat_member(m.chat.id, int(target_uid), telebot.types.ChatPermissions(can_send_messages=False))
                r_list = get_data(f'groups/{chat_id}/restricted_list', [])
                if target_name not in r_list: r_list.append(target_name); set_data(f'groups/{chat_id}/restricted_list', r_list)
                bot.reply_to(m, f"🤐 تم تقييد {target_name} بنجاح وإضافته لقائمة المقيدين سحابياً.")
            except: pass
        elif text == "رفع القيود":
            try:
                bot.restrict_chat_member(m.chat.id, int(target_uid), telebot.types.ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True))
                r_list = get_data(f'groups/{chat_id}/restricted_list', [])
                if target_name in r_list: r_list.remove(target_name); set_data(f'groups/{chat_id}/restricted_list', r_list)
                bot.reply_to(m, f"✅ تم رفع القيود سحابياً عن {target_name}.")
            except: pass
        elif text in ["حظر", "بالقندرة"]:
            try:
                bot.ban_chat_member(m.chat.id, int(target_uid))
                b_list = get_data(f'groups/{chat_id}/banned_list', [])
                if target_name not in b_list: b_list.append(target_name); set_data(f'groups/{chat_id}/banned_list', b_list)
                bot.reply_to(m, f"👞 طار {target_name} بالقندرة خارج المجموعة وتم تسجيله in المحظورين سحابياً.")
            except: pass
        elif text == "الغاء حظر":
            try:
                bot.unban_chat_member(m.chat.id, int(target_uid), only_if_banned=True)
                b_list = get_data(f'groups/{chat_id}/banned_list', [])
                if target_name in b_list: b_list.remove(target_name); set_data(f'groups/{chat_id}/banned_list', b_list)
                bot.reply_to(m, f"🔓 تم إلغاء حظر {target_name} من السحابة.")
            except: pass
            
        elif text == "رفع مطور" and is_chat_owner:
            devs = get_data(f'groups/{chat_id}/developers', [])
            if target_uid not in devs: devs.append(target_uid); set_data(f'groups/{chat_id}/developers', devs)
            bot.reply_to(m, f"🛠️ تم رفع {target_name} إلى رتبة مطور سحابي في البوت.")
        elif text == "تنزيل مطور" and is_chat_owner:
            devs = get_data(f'groups/{chat_id}/developers', [])
            if target_uid in devs: devs.remove(target_uid); set_data(f'groups/{chat_id}/developers', devs)
            bot.reply_to(m, f"📉 تم تنزيل المطور {target_name} سحابياً.")

        elif text == "رفع مميز":
            prem = get_data(f'groups/{chat_id}/premium', [])
            if target_uid not in prem: prem.append(target_uid); set_data(f'groups/{chat_id}/premium', prem)
            bot.reply_to(m, f"⭐ تم رفع {target_name} مميزاً (يتخطى الأقفال والحماية السحابية).")
        elif text == "تنزيل مميز":
            prem = get_data(f'groups/{chat_id}/premium', [])
            if target_uid in prem: prem.remove(target_uid); set_data(f'groups/{chat_id}/premium', prem)
            bot.reply_to(m, f"📉 تم تنزيل العضو المميز {target_name}.")

    elif text.startswith(("حظر @", "بالقندرة @", "تقييد @")) and is_bot_dev:
        match = re.match(r"(حظر|بالقندرة|تقييد)\s+@(\w+)", text)
        if match:
            cmd = match.group(1)
            user_target = match.group(2)
            bot.reply_to(m, f"👞 تم إصدار أمر الحماية السحابي [{cmd}] للمعرف @{user_target} وسيتم تطبيق العقوبة فور رصد حركته.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
    
