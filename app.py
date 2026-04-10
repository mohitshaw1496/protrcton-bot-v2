
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from flask import Flask, request, render_template, redirect
import sqlite3, hashlib, time

API_TOKEN = "8498039053:AAFF0bLEb08q10IX8A90F5DZQ_PH7kQNfdo"
BOT_USERNAME = "Vertex_protrctor_Robot"
FORCE_CHANNEL = "@Z_Vertex_01"
ADMIN_ID = 7947256130
BASE_URL = "https://protrcton-bot-v2.onrender.com"

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS links (key TEXT PRIMARY KEY, url TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
conn.commit()

def generate_key(url):
    return hashlib.md5((url + str(time.time())).encode()).hexdigest()[:10]

def is_joined(user_id):
    try:
        member = bot.get_chat_member(FORCE_CHANNEL, user_id)
        return member.status in ["member","administrator","creator"]
    except:
        return False

def save_user(uid):
    cursor.execute("INSERT OR IGNORE INTO users VALUES (?)",(uid,))
    conn.commit()

@bot.message_handler(commands=['start'])
def start(msg):
    save_user(msg.from_user.id)
    args = msg.text.split()

    if len(args)>1:
        key = args[1]
        cursor.execute("SELECT url FROM links WHERE key=?",(key,))
        data = cursor.fetchone()

        if not data:
            bot.send_message(msg.chat.id,"Invalid link")
            return

        if not is_joined(msg.from_user.id):
            m=InlineKeyboardMarkup()
            m.add(InlineKeyboardButton("Join",url=f"https://t.me/{FORCE_CHANNEL.strip('@')}"))
            m.add(InlineKeyboardButton("Verify",callback_data=f"v_{key}"))
            bot.send_message(msg.chat.id,"Join channel first",reply_markup=m)
        else:
            open_webapp(msg.chat.id,key)

@bot.callback_query_handler(func=lambda c:c.data.startswith("v_"))
def verify(c):
    key=c.data.split("_")[1]
    if is_joined(c.from_user.id):
        open_webapp(c.message.chat.id,key)
    else:
        bot.answer_callback_query(c.id,"Join first!",show_alert=True)

def open_webapp(cid,key):
    m=InlineKeyboardMarkup()
    m.add(InlineKeyboardButton("Continue",web_app=WebAppInfo(f"{BASE_URL}/app?key={key}")))
    bot.send_message(cid,"Verified!",reply_markup=m)

@bot.message_handler(commands=['protect'])
def protect(msg):
    if msg.from_user.id!=ADMIN_ID: return
    try:
        _,url=msg.text.split(maxsplit=1)
        key=generate_key(url)
        cursor.execute("INSERT INTO links VALUES (?,?)",(key,url))
        conn.commit()
        bot.send_message(msg.chat.id,f"https://t.me/{BOT_USERNAME}?start={key}")
    except:
        bot.send_message(msg.chat.id,"Usage: /protect link")

@bot.message_handler(commands=['remove'])
def remove(msg):
    if msg.from_user.id!=ADMIN_ID: return
    try:
        _,key=msg.text.split()
        cursor.execute("DELETE FROM links WHERE key=?",(key,))
        conn.commit()
        bot.send_message(msg.chat.id,"Removed")
    except:
        bot.send_message(msg.chat.id,"Usage: /remove key")

@bot.message_handler(commands=['broadcast'])
def bc(msg):
    if msg.from_user.id!=ADMIN_ID: return
    txt=msg.text.replace("/broadcast ","")
    cursor.execute("SELECT user_id FROM users")
    for u in cursor.fetchall():
        try: bot.send_message(u[0],txt)
        except: pass

@app.route("/app")
def webapp():
    key=request.args.get("key")
    return render_template("index.html",key=key)

@app.route("/redirect/<key>")
def red(key):
    cursor.execute("SELECT url FROM links WHERE key=?",(key,))
    d=cursor.fetchone()
    if not d: return "Invalid"
    return redirect(d[0])

@app.route(f"/{API_TOKEN}",methods=["POST"])
def webhook():
    upd=telebot.types.Update.de_json(request.get_data().decode())
    bot.process_new_updates([upd])
    return "OK"

@app.route("/")
def home():
    return "Running"

bot.remove_webhook()
bot.set_webhook(url=f"{BASE_URL}/{API_TOKEN}")

if __name__=="__main__":
    app.run(host="0.0.0.0",port=10000)
