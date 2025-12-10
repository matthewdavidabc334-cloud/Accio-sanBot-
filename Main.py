import telebot
from telebot import types
import json
import os
import atexit
import time

# --------(--------------------
# CONFIGURATION
# ----------------------------
TOKEN = "8593372167:AAFpD8IXk3rBmOZfxFgfSzN8tSWKRwwd5v0"  # Replace with your bot token
bot = telebot.TeleBot(TOKEN)

ADMIN_IDS = [7672175037, 5748613413]
CHANNEL_ID = -1002718865918
EXCLUDE_GROUP_ID = -1002923012283

# ----------------------------
# FILES FOR PERSISTENCE
# ----------------------------
USERS_FILE = "users.json"
CHAPTERS_FILE = "chapters.json"
POINTS_FILE = "points.json"
LIKES_FILE = "likes.json"
BANNED_FILE = "banned.json"
ADMINS_FILE = "admins.json"

# ----------------------------
# HELPER FUNCTIONS FOR JSON
# ----------------------------
def load_json(file, default):
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return default

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f)

def save_all():
    save_json(USERS_FILE, users)
    save_json(CHAPTERS_FILE, chapters)
    save_json(POINTS_FILE, users_points)
    save_json(LIKES_FILE, likes)
    save_json(BANNED_FILE, list(banned_users))
    save_json(ADMINS_FILE, list(admins))

# ----------------------------
# LOAD DATA
# ----------------------------
users = load_json(USERS_FILE, {})               
chapters = load_json(CHAPTERS_FILE, {})         
users_points = load_json(POINTS_FILE, {})       
likes = load_json(LIKES_FILE, {})               
banned_users = set(load_json(BANNED_FILE, []))  
admins = set(load_json(ADMINS_FILE, ADMIN_IDS)) 

# ----------------------------
# STATE TRACKING
# ----------------------------
admin_states = {}   
upload_states = {}  

# ----------------------------
# HELPER FUNCTIONS
# ----------------------------
def is_admin(user_id):
    return user_id in admins

def check_ban(user_id):
    return user_id in banned_users

def add_points(user_id, amount):
    users_points[str(user_id)] = users_points.get(str(user_id), 0) + amount
    save_all()

def send_loading_bar(chat_id):
    msg = bot.send_message(chat_id, "⏳ Processing your request...\n[░░░░░░░░░░░░░░░░░░░░░] 0%")
    for i in range(1, 11):
        time.sleep(0.05)
        bar = '▓' * i + '░' * (10 - i)
        percent = i * 10
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id,
                                  text=f"⏳ Processing your request...\n[{bar}] {percent}%")
        except:
            pass

def send_image_with_caption(chat_id, image_path, caption):
    if os.path.exists(image_path):
        bot.send_photo(chat_id, open(image_path, "rb"), caption=caption)
    else:
        bot.send_message(chat_id, caption)

# ----------------------------
# /START COMMAND
# ----------------------------
@bot.message_handler(commands=["start"])
def start(message):
    uid = str(message.from_user.id)
    users[uid] = {"username": message.from_user.username}
    save_all()
    if check_ban(message.from_user.id):
        return
    caption = ("👋 Welcome to **Accio-San's Story Hub!** 📚\n\n"
               "✨ Here you can read amazing stories, chapters, and get updates directly from Accio-San!\n\n"
               "💡 Commands you can use:\n"
               "📖 /search <chapter_number> - Read chapters and earn points\n"
               "⭐ /points - Check your points\n"
               "💬 /leavemssg <message> - Send a message to Accio-San\n"
               "🎉 Enjoy your journey and discover new adventures with every chapter! ✨")
    send_image_with_caption(message.chat.id, "start_image.jpg", caption)

# ----------------------------
# /POINTS COMMAND
# ----------------------------
@bot.message_handler(commands=["points"])
def points(message):
    send_loading_bar(message.chat.id)
    pts = users_points.get(str(message.from_user.id), 0)
    bot.send_message(message.chat.id, f"🌟 You currently have {pts} history points!")

# ----------------------------
# /SEARCH COMMAND
# ----------------------------
@bot.message_handler(commands=["search"])
def search(message):
    if check_ban(message.from_user.id):
        return
    send_loading_bar(message.chat.id)
    try:
        number = int(message.text.split()[1])
    except:
        bot.reply_to(message, "❌ Usage: /search <chapter number>")
        return
    if str(number) not in chapters:
        bot.reply_to(message, "❌ Chapter not found.")
        return
    chapter = chapters[str(number)]
    add_points(message.from_user.id, 10)
    caption = f"📖 Chapter {number}: {chapter['title']}\n\nRead here: {chapter['link']}\n\n(by Accio-San) ✨"
    send_image_with_caption(message.chat.id, "chapter_image.jpg", caption)

# ----------------------------
# /ADD COMMAND (interactive)
# ----------------------------
@bot.message_handler(commands=["add"])
def add_start(message):
    if not is_admin(message.from_user.id):
        return
    admin_states[message.from_user.id] = {"step": 1, "data": {}}
    bot.send_message(message.chat.id, "📝 Send the name of the chapter:")

@bot.message_handler(func=lambda m: m.from_user.id in admin_states)
def add_step_handler(message):
    state = admin_states[message.from_user.id]
    if state["step"] == 1:
        state["data"]["title"] = message.text
        state["step"] = 2
        bot.send_message(message.chat.id, "🔢 Send the chapter number:")
    elif state["step"] == 2:
        try:
            state["data"]["number"] = int(message.text)
        except:
            bot.send_message(message.chat.id, "❌ Invalid number. Send the chapter number again:")
            return
        state["step"] = 3
        bot.send_message(message.chat.id, "🔗 Send the Telegraph link:")
    elif state["step"] == 3:
        state["data"]["link"] = message.text
        number = str(state["data"]["number"])
        chapters[number] = {
            "title": state["data"]["title"],
            "link": state["data"]["link"],
            "cover": None
        }
        bot.send_message(message.chat.id, f"✅ Chapter {number} added successfully!")
        save_all()
        del admin_states[message.from_user.id]

# ----------------------------
# /UPLOAD COMMAND (interactive)
# ----------------------------
@bot.message_handler(commands=["upload"])
def upload_start(message):
    if not is_admin(message.from_user.id):
        return
    bot.send_message(message.chat.id, "📤 Send the content: photo, video, file, audio, text, or Telegraph link.")
    upload_states[message.from_user.id] = {"step": 1, "data": {}}

@bot.message_handler(func=lambda m: m.from_user.id in upload_states)
def handle_upload(message):
    state = upload_states[message.from_user.id]
    data = state["data"]
    if state["step"] == 1:
        data["caption"] = message.caption if message.caption else ""
        if message.text and "telegra.ph" in message.text:
            data["content_type"] = "telegraph"
            data["link"] = message.text.strip()
            data["title"] = "Unknown Chapter"
        elif message.photo:
            data["content_type"] = "photo"
            data["file_id"] = message.photo[-1].file_id
        elif message.video:
            data["content_type"] = "video"
            data["file_id"] = message.video.file_id
        elif message.audio or message.document:
            data["content_type"] = "file"
            data["file_id"] = message.audio.file_id if message.audio else message.document.file_id
        else:
            bot.send_message(message.chat.id, "❌ Unsupported content. Try again.")
            return
        state["step"] = 2
        bot.send_message(message.chat.id, "📝 Send the chapter title:")
    elif state["step"] == 2:
        data["title"] = message.text
        state["step"] = 3
        bot.send_message(message.chat.id, "🔢 Send the chapter number:")
    elif state["step"] == 3:
        try:
            data["number"] = int(message.text)
        except:
            bot.send_message(message.chat.id, "❌ Invalid number. Send the chapter number again:")
            return
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Yes", callback_data="cover_yes"))
        markup.add(types.InlineKeyboardButton("❌ No", callback_data="cover_no"))
        state["step"] = 4
        bot.send_message(message.chat.id, "🖼 Do you want to add a book cover?", reply_markup=markup)

# ----------------------------
# CALLBACK HANDLER
# ----------------------------
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    user_id = call.from_user.id
    if call.data.startswith("like|"):
        chapter_number = call.data.split("|")[1]
        likes.setdefault(chapter_number, [])
        if user_id not in likes[chapter_number]:
            likes[chapter_number].append(user_id)
            save_all()
            bot.answer_callback_query(call.id, "👍 You liked this chapter!")
        else:
            bot.answer_callback_query(call.id, "❌ Already liked!")
        return
    if user_id not in upload_states:
        return
    state = upload_states[user_id]
    data = state["data"]
    if call.data == "cover_yes":
        bot.send_message(call.message.chat.id, "🖼 Send the book cover now:")
        state["step"] = 5
    elif call.data == "cover_no":
        finalize_upload(data)
        del upload_states[user_id]

@bot.message_handler(func=lambda m: m.from_user.id in upload_states and upload_states[m.from_user.id]["step"]==5)
def handle_cover(message):
    state = upload_states[message.from_user.id]
    data = state["data"]
    if message.photo:
        data["cover"] = message.photo[-1].file_id
    finalize_upload(data)
    del upload_states[message.from_user.id]

def finalize_upload(data):
    number = str(data["number"])
    chapters[number] = {
        "title": data["title"],
        "link": data.get("link", "N/A"),
        "cover": data.get("cover")
    }
    caption = f"📖 Chapter {number}: {data['title']}\n\nRead here: {data.get('link','')}\n\n(by Accio-San) ✨"
    content_type = data.get("content_type","text")
    file_id = data.get("file_id")
    link = data.get("link")
    if content_type == "photo" and file_id:
        bot.send_photo(CHANNEL_ID, file_id, caption=caption)
    elif content_type == "video" and file_id:
        bot.send_video(CHANNEL_ID, file_id, caption=caption)
    elif content_type == "file" and file_id:
        bot.send_document(CHANNEL_ID, file_id, caption=caption)
    elif content_type == "telegraph":
        bot.send_message(CHANNEL_ID, caption)
    else:
        bot.send_message(CHANNEL_ID, caption)
    save_all()
    for uid in users:
        if check_ban(int(uid)):
            continue
        try:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📖 Read", url=link if link else "https://t.me/c/..."))
            markup.add(types.InlineKeyboardButton("👍 Like", callback_data=f"like|{number}"))
            send_image_with_caption(int(uid), "chapter_image.jpg",
                                    "✨ Accio-San has done it again! Tap below to read the latest chapter.")
        except:
            continue

# ----------------------------
# ADMIN COMMANDS
# ----------------------------

# /adminonly
@bot.message_handler(commands=["adminonly"])
def adminonly(message):
    if not is_admin(message.from_user.id):
        return
    msg = ("/upload\n/add\n/ban\n/unban\n/banlist\n/addadmin\n/remadmin\n/adminlist\n"
           "/broadcast\n/profile\n/leavemssg\n/points\n/search\n/give")
    bot.send_message(message.chat.id, "⚡ Admin-only commands:\n" + msg)

# /ban, /unban, /banlist
@bot.message_handler(commands=["ban"])
def ban(message):
    if not is_admin(message.from_user.id): return
    try:
        uid = int(message.text.split()[1])
        banned_users.add(uid)
        save_all()
        bot.send_message(message.chat.id, f"🚫 User {uid} banned!")
    except: bot.reply_to(message, "Usage: /ban <user_id>")

@bot.message_handler(commands=["unban"])
def unban(message):
    if not is_admin(message.from_user.id): return
    try:
        uid = int(message.text.split()[1])
        banned_users.discard(uid)
        save_all()
        bot.send_message(message.chat.id, f"✅ User {uid} unbanned!")
    except: bot.reply_to(message, "Usage: /unban <user_id>")

@bot.message_handler(commands=["banlist"])
def banlist(message):
    if not is_admin(message.from_user.id): return
    msg = "🚫 Banned Users:\n" + "\n".join([str(u) for u in banned_users])
    bot.send_message(message.chat.id, msg)

# /addadmin, /remadmin, /adminlist
@bot.message_handler(commands=["addadmin"])
def addadmin(message):
    if not is_admin(message.from_user.id): return
    try:
        uid = int(message.text.split()[1])
        admins.add(uid)
        save_all()
        bot.send_message(message.chat.id, f"✅ User {uid} added as admin!")
    except: bot.reply_to(message, "Usage: /addadmin <user_id>")

@bot.message_handler(commands=["remadmin"])
def remadmin(message):
    if not is_admin(message.from_user.id): return
    try:
        uid = int(message.text.split()[1])
        admins.discard(uid)
        save_all()
        bot.send_message(message.chat.id, f"✅ User {uid} removed from admin!")
    except: bot.reply_to(message, "Usage: /remadmin <user_id>")

@bot.message_handler(commands=["adminlist"])
def adminlist(message):
    if not is_admin(message.from_user.id): return
    msg = "⚡ Admins:\n" + "\n".join([str(a) for a in admins])
    bot.send_message(message.chat.id, msg)

# /broadcast
@bot.message_handler(commands=["broadcast"])
def broadcast(message):
    if not is_admin(message.from_user.id): return
    try:
        text = message.text.split(maxsplit=1)[1]
    except:
        bot.reply_to(message, "Usage: /broadcast <message>")
        return
    for uid in users:
        if check_ban(int(uid)): continue
        try: bot.send_message(int(uid), text)
        except: continue
    bot.send_message(message.chat.id, "📢 Broadcast sent successfully!")

# /profile
@bot.message_handler(commands=["profile"])
def profile(message):
    if not is_admin(message.from_user.id): return
    msg = "👥 Users of the bot:\n"
    for uid, info in users.items():
        msg += f"{uid} - @{info.get('username','N/A')}\n"
    bot.send_message(message.chat.id, msg)

# /leavemssg
@bot.message_handler(commands=["leavemssg"])
def leavemssg(message):
    try:
        text = message.text.split(maxsplit=1)[1]
        for admin_id in admins:
            bot.send_message(admin_id, f"💬 User {message.from_user.id} says: {text}")
        bot.send_message(message.chat.id, "✅ Your message has been sent to Accio-San!")
    except:
        bot.reply_to(message, "Usage: /leavemssg <message>")

# /giveme
@bot.message_handler(commands=["giveme"])
def giveme(message):
    if not is_admin(message.from_user.id): return
    try:
        amount = int(message.text.split()[1])
        add_points(message.from_user.id, amount)
        bot.send_message(message.chat.id, f"🌟 You received {amount} points!")
    except:
        bot.reply_to(message, "Usage: /giveme <amount>")

# /give
@bot.message_handler(commands=["give"])
def give(message):
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Reply to a user's message to give points.")
        return
    try:
        amount = int(message.text.split()[1])
        uid = message.reply_to_message.from_user.id
        add_points(uid, amount)
        bot.send_message(message.chat.id, f"🌟 {amount} points given to {message.reply_to_message.from_user.first_name}!")
        bot.send_message(uid, f"🌟 You received {amount} points!")
    except:
        bot.reply_to(message, "Usage: /give <amount> (reply to a user's message)")

# ----------------------------
# SAVE ON EXIT
# ----------------------------
atexit.register(save_all)

# ----------------------------
# RUN BOT
# ----------------------------
bot.infinity_polling()
