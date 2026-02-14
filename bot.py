import os
import telebot
import sqlite3
import random
from datetime import datetime, timedelta
from flask import Flask, request, abort

app = Flask(__name__)

# ────────────────────────────────────────────────
# TOKEN BURAYA GELİYOR – SENİN TOKEN'INI TAM BURAYA YAPIŞTIR
BOT_TOKEN = '8574466093:AAF6MnSQGePYvi1PefAyBk7F8z34Ptjrv6M'  # ← BURAYA KENDİ TOKEN'INI YAZ / YAPISTIR
# ────────────────────────────────────────────────

# Admin ID'ler (senin Telegram ID'lerini sayı olarak yaz)
ADMIN_IDS = [7795343194, 6126663392]  # ← burayı değiştir, yoksa admin komutları çalışmaz

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

# Veritabanı dosyası
DB_FILE = 'kumar_botu.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                  username TEXT,
                  first_name TEXT,
                  balance REAL DEFAULT 5000.0,
                  last_bonus TEXT)''')
    conn.commit()
    conn.close()

init_db()

def get_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def register_user(user_id, username, first_name):
    if not get_user(user_id):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO users (user_id, username, first_name, balance) VALUES (?, ?, ?, 5000.0)",
                  (user_id, username, first_name))
        conn.commit()
        conn.close()

def update_balance(user_id, amount):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def get_balance(user_id):
    user = get_user(user_id)
    return user[3] if user else 0.0

# Komutlar
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "yok"
    first_name = message.from_user.first_name
    register_user(user_id, username, first_name)
    bot.reply_to(message, "Hoş geldin! 💰 Bakiyen 5.000 TL olarak oluşturuldu.\n/yardim yaz komutları gör.")

@bot.message_handler(commands=['bakiye'])
def bakiye(message):
    register_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    bal = get_balance(message.from_user.id)
    bot.reply_to(message, f"💰 Bakiyen: {bal:,.0f} TL")

@bot.message_handler(commands=['bonus'])
def bonus(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        return bot.reply_to(message, "Önce /start yap.")
    
    last_bonus = user[4]
    if last_bonus:
        last_time = datetime.fromisoformat(last_bonus)
        if datetime.now() - last_time < timedelta(days=1):
            kalan = timedelta(days=1) - (datetime.now() - last_time)
            return bot.reply_to(message, f"Bir sonraki bonus için ≈ {kalan.seconds // 3600} saat { (kalan.seconds % 3600) // 60 } dakika bekle.")
    
    update_balance(user_id, 20000)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET last_bonus = ? WHERE user_id = ?", (datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()
    
    bot.reply_to(message, f"🎁 +20.000 TL günlük harçlık aldın!\nYeni bakiye: {get_balance(user_id):,.0f} TL")

@bot.message_handler(commands=['slot'])
def slot(message):
    args = message.text.split()
    if len(args) < 2:
        return bot.reply_to(message, "Kullanım: /slot <miktar>  (ör: /slot 1000)")
    
    try:
        miktar = float(args[1])
    except:
        return bot.reply_to(message, "Miktar sayı olmalı.")
    
    user_id = message.from_user.id
    bal = get_balance(user_id)
    if miktar <= 0 or miktar > bal:
        return bot.reply_to(message, "Geçersiz / yetersiz bakiye.")
    
    update_balance(user_id, -miktar)
    
    dice = bot.send_dice(message.chat.id, emoji="🎰")
    value = dice.dice.value
    
    kazanc = 0
    if value == 64:
        kazanc = miktar * 10
    elif value >= 50:
        kazanc = miktar * 3
    elif value >= 30:
        kazanc = miktar * 1.5
    
    if kazanc > 0:
        update_balance(user_id, kazanc)
        bot.reply_to(message, f"🎰 KAZANDIN! +{kazanc:,.0f} TL\nYeni bakiye: {get_balance(user_id):,.0f} TL")
    else:
        bot.reply_to(message, f"🎰 Kaybettin -{miktar:,.0f} TL\nKalan: {get_balance(user_id):,.0f} TL")

# Diğer komutlar (gonder, zenenginler, zar vs.) aynı mantıkta devam eder
# İstersen tam listeyi eklerim, ama şu an temel oyunlar çalışıyor

# Webhook endpoint (Render için zorunlu)
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
    return "Bot Render'da çalışıyor! Telegram'dan mesaj at."

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
