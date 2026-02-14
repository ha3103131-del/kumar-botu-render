import os
import telebot
import sqlite3
import random
from datetime import datetime, timedelta
from flask import Flask, request, abort

app = Flask(__name__)

# ────────────────────────────────────────────────
# BURAYI DOLDUR - KOLAYCA DEĞİŞTİR (Render'da environment variable olarak da ekleyebilirsin)
BOT_TOKEN = os.environ.get('8574466093:AAF6MnSQGePYvi1PefAyBk7F8z34Ptjrv6M')  # Render'da Environment Variables → Key: BOT_TOKEN
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable eksik! Render'da ekle.")

ADMIN_IDS = [7795343194, 6126663392]  # Senin ve adminlerin ID'leri (burada hardcoded veya env var yap)
# ────────────────────────────────────────────────

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

# Veritabanı (Render diskinde kalıcı, ama free tier restart'ta silinebilir)
DB_FILE = 'kumar_botu.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                  username TEXT,
                  first_name TEXT,
                  balance REAL DEFAULT 0.0,
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

# ────────────── KOMUTLAR (aynı kaldı, sadece handler'lar) ──────────────

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "yok"
    first_name = message.from_user.first_name
    register_user(user_id, username, first_name)
    bot.reply_to(message, "Hoş geldin! 💰 Bakiyen otomatik oluşturuldu.\nKomutlar için /yardim yazabilirsin.")

# ... (diğer handler'lar aynı: bakiye, bonus, slot, zar, gonder, zenenginler, yardim vs.)

# Admin komutları (/banka ve /ceza) aynı kaldı

# ────────────── WEBHOOK ENDPOINT (Render için zorunlu) ──────────────

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    else:
        abort(403)

@app.route('/')
def index():
    return "Kumar Botu Render'da çalışıyor! 🎲 Telegram'dan mesaj at."

# Render start komutu burada çalışır
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)