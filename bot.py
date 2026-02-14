import os
import telebot
import sqlite3
import random
from datetime import datetime, timedelta
from flask import Flask, request, abort

app = Flask(__name__)

# ────────────────────────────────────────────────
# BOT TOKEN BURAYA GELİYOR
BOT_TOKEN = '8574466093:AAF6MnSQGePYvi1PefAyBk7F8z34Ptjrv6M'  # ← Token'ı tam buraya yapıştır

# Admin ID'ler (senin ID'ni mutlaka yaz, yoksa admin komutları çalışmaz)
ADMIN_IDS = [7795343194]  # ← buraya kendi ID'ni yaz (sayı olarak)
# ────────────────────────────────────────────────

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

DB_FILE = 'kumar_botu.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        balance REAL DEFAULT 5000.0,
        last_bonus TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

def get_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def register_user(user):
    user_id = user.id
    username = user.username or "yok"
    first_name = user.first_name

    if not get_user(user_id):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO users (user_id, username, first_name, balance) VALUES (?, ?, ?, 5000.0)",
                  (user_id, username, first_name))
        conn.commit()
        conn.close()

def get_balance(user_id):
    user = get_user(user_id)
    return user[3] if user else 0.0

def update_balance(user_id, amount):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def set_last_bonus(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET last_bonus = ? WHERE user_id = ?", (datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()

# ────────────────────────────── KOMUTLAR ──────────────────────────────

@bot.message_handler(commands=['start'])
def start(message):
    register_user(message.from_user)
    bot.reply_to(message, "Hoş geldin kanka! 💰 Bakiyen otomatik 5.000 TL olarak açıldı.\n\nKomutları görmek için /yardim yaz.")

@bot.message_handler(commands=['yardim', 'help'])
def yardim(message):
    text = """𝐊𝐔𝐌𝐀𝐑 𝐁𝐎𝐓𝐔 𝐊𝐎𝐌𝐔𝐓𝐋𝐀𝐑𝐈

Hesap & Para:
 /bakiye           → Cüzdanım ne kadar?
 /bonus            → Günlük 20.000 TL harçlık
 /gonder <ID> <miktar> → Başkasına para at
 /zenenginler      → En zenginler listesi

Oyunlar:
 /slot <miktar>    → Slot makinesi (🎰 animasyon)
 /zar <miktar>     → Zar atma (🎲 animasyon)
 /blackjack <miktar> → Yakında...
 /rulet <miktar>   → Yakında...
 /mayin <miktar>   → Yakında...
 /risk <miktar>    → Yakında...
 /cark <miktar>    → Yakında...

PvP & Diğer:
 /duello @kullanıcı <miktar> → Meydan oku (yakında)

Admin (sadece belirli kişiler):
 /banka <miktar>       → Kendine para ekle
 /ceza <miktar>        → Yanıtladığın kişiden para kes

Başlangıç bakiyesi: 5.000 TL
Günlük bonus: 20.000 TL (24 saatte bir)"""
    bot.reply_to(message, text)

@bot.message_handler(commands=['bakiye'])
def bakiye(message):
    register_user(message.from_user)
    bal = get_balance(message.from_user.id)
    bot.reply_to(message, f"💰 Bakiyen: {bal:,.0f} TL")

@bot.message_handler(commands=['bonus'])
def bonus(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        return bot.reply_to(message, "Önce /start yaz.")

    last_bonus_str = user[4]
    if last_bonus_str:
        last_time = datetime.fromisoformat(last_bonus_str)
        if datetime.now() - last_time < timedelta(days=1):
            kalan = timedelta(days=1) - (datetime.now() - last_time)
            h = kalan.seconds // 3600
            m = (kalan.seconds % 3600) // 60
            return bot.reply_to(message, f"Bir sonraki bonus için {h} saat {m} dakika bekle.")

    update_balance(user_id, 20000)
    set_last_bonus(user_id)
    yeni_bakiye = get_balance(user_id)
    bot.reply_to(message, f"🎁 Günlük 20.000 TL harçlık eklendi!\nYeni bakiye: {yeni_bakiye:,.0f} TL")

@bot.message_handler(commands=['slot'])
def slot(message):
    args = message.text.split()
    if len(args) < 2:
        return bot.reply_to(message, "Kullanım: /slot <miktar>   örn: /slot 5000")

    try:
        miktar = float(args[1])
    except:
        return bot.reply_to(message, "Miktar sayı olmalı.")

    user_id = message.from_user.id
    bakiye = get_balance(user_id)

    if miktar <= 0 or miktar > bakiye:
        return bot.reply_to(message, "Geçersiz miktar veya bakiye yetersiz.")

    update_balance(user_id, -miktar)

    msg = bot.send_dice(message.chat.id, emoji="🎰")
    value = msg.dice.value

    kazanc = 0
    if value == 64:
        kazanc = miktar * 10
    elif value >= 50:
        kazanc = miktar * 3
    elif value >= 30:
        kazanc = miktar * 1.5

    if kazanc > 0:
        update_balance(user_id, kazanc)
        bot.reply_to(message, f"🎰 **KAZANDIN!** +{kazanc:,.0f} TL\nYeni bakiye: {get_balance(user_id):,.0f} TL")
    else:
        bot.reply_to(message, f"🎰 Kaybettin... -{miktar:,.0f} TL\nKalan bakiye: {get_balance(user_id):,.0f} TL")

@bot.message_handler(commands=['zar'])
def zar(message):
    args = message.text.split()
    if len(args) < 2:
        return bot.reply_to(message, "Kullanım: /zar <miktar>   örn: /zar 1000")

    try:
        miktar = float(args[1])
    except:
        return bot.reply_to(message, "Miktar sayı olmalı.")

    user_id = message.from_user.id
    bakiye = get_balance(user_id)

    if miktar <= 0 or miktar > bakiye:
        return bot.reply_to(message, "Geçersiz miktar veya bakiye yetersiz.")

    update_balance(user_id, -miktar)

    msg = bot.send_dice(message.chat.id, emoji="🎲")
    value = msg.dice.value

    if value >= 4:  # 4,5,6 kazanır
        kazanc = miktar * 2
        update_balance(user_id, kazanc)
        bot.reply_to(message, f"🎲 **Kazandın!** +{kazanc:,.0f} TL (atış: {value})\nYeni bakiye: {get_balance(user_id):,.0f} TL")
    else:
        bot.reply_to(message, f"🎲 Kaybettin... (atış: {value})\nKalan bakiye: {get_balance(user_id):,.0f} TL")

@bot.message_handler(commands=['gonder'])
def gonder(message):
    args = message.text.split()
    if len(args) < 3:
        return bot.reply_to(message, "Kullanım: /gonder <ID> <miktar>")

    try:
        target_id = int(args[1])
        miktar = float(args[2])
    except:
        return bot.reply_to(message, "ID sayı, miktar ondalık olmalı.")

    user_id = message.from_user.id
    bakiye = get_balance(user_id)

    if miktar <= 0 or miktar > bakiye:
        return bot.reply_to(message, "Geçersiz miktar veya bakiye yetersiz.")

    update_balance(user_id, -miktar)
    update_balance(target_id, miktar)

    bot.reply_to(message, f"✅ {miktar:,.0f} TL → ID {target_id}'e gönderildi.")

@bot.message_handler(commands=['zenenginler'])
def zenenginler(message):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT first_name, username, balance FROM users ORDER BY balance DESC LIMIT 10")
    top = c.fetchall()
    conn.close()

    if not top:
        return bot.reply_to(message, "Henüz kimse yok.")

    msg = "🏆 **En Zenginler Listesi**\n\n"
    for i, (fname, uname, bal) in enumerate(top, 1):
        name = f"@{uname}" if uname != "yok" else fname
        msg += f"{i}. {name} → {bal:,.0f} TL\n"
    bot.reply_to(message, msg)

# ────────────────────────────── ADMIN KOMUTLARI ──────────────────────────────

@bot.message_handler(commands=['banka'])
def banka(message):
    if message.from_user.id not in ADMIN_IDS:
        return

    args = message.text.split()
    if len(args) < 2:
        return bot.reply_to(message, "Kullanım: /banka <miktar>")

    try:
        miktar = float(args[1])
    except:
        return bot.reply_to(message, "Miktar sayı olmalı.")

    update_balance(message.from_user.id, miktar)
    bot.reply_to(message, f"Admin: +{miktar:,.0f} TL eklendi\nYeni bakiye: {get_balance(message.from_user.id):,.0f} TL")

@bot.message_handler(commands=['ceza'])
def ceza(message):
    if message.from_user.id not in ADMIN_IDS:
        return

    if not message.reply_to_message:
        return bot.reply_to(message, "Ceza keseceğin kişinin mesajını yanıtla + /ceza <miktar>")

    target = message.reply_to_message.from_user
    target_id = target.id

    args = message.text.split()
    if len(args) < 2:
        return bot.reply_to(message, "Miktar gir: /ceza <miktar>")

    try:
        miktar = float(args[1])
    except:
        return bot.reply_to(message, "Miktar sayı olmalı.")

    bakiye = get_balance(target_id)
    if miktar > bakiye:
        miktar = bakiye

    update_balance(target_id, -miktar)

    name = target.username or target.first_name
    bot.reply_to(message, f"Ceza kesildi → @{name} -{miktar:,.0f} TL")

# ────────────────────────────── WEBHOOK ──────────────────────────────

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    abort(403)

@app.route('/')
def index():
    return "Bot çalışıyor! 🎲"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
