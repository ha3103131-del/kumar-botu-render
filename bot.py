import os
import telebot
import sqlite3
import random
from datetime import datetime, timedelta
from flask import Flask, request, abort

app = Flask(__name__)

# TOKEN VE ADMIN ID'LER
BOT_TOKEN = '8574466093:AAF6MnSQGePYvi1PefAyBk7F8z34Ptjrv6M'  # ← Token'ını buraya tam yapıştır
ADMIN_IDS = [7795343194, 6126663392]  # ← Kendi Telegram ID'ni sayı olarak buraya yaz (userinfobot ile öğren)

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
    bot.reply_to(message, "Hoş geldin! 💰 Bakiyen otomatik 5.000 TL olarak açıldı.\n\n/yardim yaz komutları gör.")

@bot.message_handler(commands=['yardim', 'help'])
def yardim(message):
    text = """𝐊𝐔𝐌𝐀𝐑 𝐁𝐎𝐓𝐔 𝐊𝐎𝐌𝐔𝐓𝐋𝐀𝐑𝐈

Hesap & Para:
 /bakiye           → Cüzdanım ne kadar?
 /bonus            → Günlük 20.000 TL harçlık
 /gonder <ID> <miktar> → Başkasına para at
 /zenenginler      → En zenginler listesi

Oyunlar:
 /slot <miktar>    → Slot makinesi (🎰)
 /zar <miktar>     → Zar atma (🎲)
 /rulet <miktar>   → Rulet (kırmızı/siyah/yeşil)
 /blackjack <miktar> → 21'e yakın ol
 /mayin <miktar>   → Mayın tarlası (5x5)
 /risk <miktar>    → Ya hep ya hiç (%50 şans)
 /cark <miktar>    → Şans çarkı

PvP:
 /duello @kullanıcı <miktar> → Meydan oku (yakında)

Admin:
 /banka <miktar>   → Kendine para ekle
 /ceza <miktar>    → Yanıtladığın kişiden kes

Başlangıç: 5.000 TL
Günlük bonus: 20.000 TL"""
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
    bot.reply_to(message, f"🎁 +20.000 TL eklendi!\nYeni bakiye: {get_balance(user_id):,.0f} TL")

# ────────────────────────────── OYUNLAR (GERÇEKÇİ ORANLAR) ──────────────────────────────

@bot.message_handler(commands=['slot'])
def slot(message):
    args = message.text.split()
    if len(args) < 2:
        return bot.reply_to(message, "Kullanım: /slot <miktar>")
    try:
        miktar = float(args[1])
    except:
        return bot.reply_to(message, "Miktar sayı olmalı.")
    
    user_id = message.from_user.id
    bakiye = get_balance(user_id)
    if miktar <= 0 or miktar > bakiye:
        return bot.reply_to(message, "Geçersiz / yetersiz bakiye.")
    
    update_balance(user_id, -miktar)
    dice = bot.send_dice(message.chat.id, emoji="🎰")
    value = dice.dice.value
    
    kazanc = 0
    if value == 64:  # Jackpot ~%1.5
        kazanc = miktar * 10
    elif value >= 48:  # İyi sonuç ~%25
        kazanc = miktar * 3
    elif value >= 32:  # Küçük kazanç ~%20
        kazanc = miktar * 1.5
    
    if kazanc > 0:
        update_balance(user_id, kazanc)
        bot.reply_to(message, f"🎰 KAZANDIN! +{kazanc:,.0f} TL\nYeni bakiye: {get_balance(user_id):,.0f} TL")
    else:
        bot.reply_to(message, f"🎰 Kaybettin -{miktar:,.0f} TL\nKalan: {get_balance(user_id):,.0f} TL")

@bot.message_handler(commands=['zar'])
def zar(message):
    args = message.text.split()
    if len(args) < 2:
        return bot.reply_to(message, "Kullanım: /zar <miktar>")
    try:
        miktar = float(args[1])
    except:
        return bot.reply_to(message, "Miktar sayı olmalı.")
    
    user_id = message.from_user.id
    bakiye = get_balance(user_id)
    if miktar <= 0 or miktar > bakiye:
        return bot.reply_to(message, "Geçersiz / yetersiz bakiye.")
    
    update_balance(user_id, -miktar)
    dice = bot.send_dice(message.chat.id, emoji="🎲")
    value = dice.dice.value
    
    if value >= 4:  # %50 kazanma (4,5,6)
        kazanc = miktar * 2
        update_balance(user_id, kazanc)
        bot.reply_to(message, f"🎲 Kazandın! +{kazanc:,.0f} TL (atış: {value})\nYeni bakiye: {get_balance(user_id):,.0f} TL")
    else:
        bot.reply_to(message, f"🎲 Kaybettin (atış: {value})\nKalan: {get_balance(user_id):,.0f} TL")

@bot.message_handler(commands=['rulet'])
def rulet(message):
    args = message.text.split()
    if len(args) < 2:
        return bot.reply_to(message, "Kullanım: /rulet <miktar>")
    try:
        miktar = float(args[1])
    except:
        return bot.reply_to(message, "Miktar sayı olmalı.")
    
    user_id = message.from_user.id
    bakiye = get_balance(user_id)
    if miktar <= 0 or miktar > bakiye:
        return bot.reply_to(message, "Geçersiz / yetersiz bakiye.")
    
    update_balance(user_id, -miktar)
    dice = bot.send_dice(message.chat.id, emoji="🎰")
    value = dice.dice.value
    
    if value == 0:  # Yeşil (0) ~%1.5
        kazanc = miktar * 35
        update_balance(user_id, kazanc)
        bot.reply_to(message, f"🎰 RULET: YEŞİL! +{kazanc:,.0f} TL\nYeni bakiye: {get_balance(user_id):,.0f} TL")
    elif value <= 32:  # Kırmızı ~%48
        kazanc = miktar * 2
        update_balance(user_id, kazanc)
        bot.reply_to(message, f"🎰 RULET: KIRMIZI! +{kazanc:,.0f} TL\nYeni bakiye: {get_balance(user_id):,.0f} TL")
    else:  # Siyah ~%48
        bot.reply_to(message, f"🎰 RULET: SİYAH - Kaybettin -{miktar:,.0f} TL\nKalan: {get_balance(user_id):,.0f} TL")

@bot.message_handler(commands=['blackjack'])
def blackjack(message):
    args = message.text.split()
    if len(args) < 2:
        return bot.reply_to(message, "Kullanım: /blackjack <miktar>")
    try:
        miktar = float(args[1])
    except:
        return bot.reply_to(message, "Miktar sayı olmalı.")
    
    user_id = message.from_user.id
    bakiye = get_balance(user_id)
    if miktar <= 0 or miktar > bakiye:
        return bot.reply_to(message, "Geçersiz / yetersiz bakiye.")
    
    update_balance(user_id, -miktar)
    
    # Basit blackjack (oyuncu avantajı var)
    oyuncu_kartlar = [random.randint(1, 11) for _ in range(2)]
    oyuncu_toplam = sum(oyuncu_kartlar)
    if oyuncu_toplam > 21 and 11 in oyuncu_kartlar:
        oyuncu_toplam -= 10  # As'ı 1 yap
    
    bot_kartlar = [random.randint(1, 11) for _ in range(2)]
    bot_toplam = sum(bot_kartlar)
    if bot_toplam > 21 and 11 in bot_kartlar:
        bot_toplam -= 10
    
    msg = f"Sen: {oyuncu_kartlar} = {oyuncu_toplam}\nBot: {bot_kartlar} = {bot_toplam}\n\n"
    
    if oyuncu_toplam > 21:
        msg += "Patladın, kaybettin."
    elif bot_toplam > 21 or oyuncu_toplam > bot_toplam:
        kazanc = miktar * 2
        update_balance(user_id, kazanc)
        msg += f"Kazandın! +{kazanc:,.0f} TL"
    elif oyuncu_toplam == bot_toplam:
        update_balance(user_id, miktar)
        msg += "Berabere, paran iade."
    else:
        msg += "Bot kazandı, kaybettin."
    
    bot.reply_to(message, msg + f"\nBakiye: {get_balance(user_id):,.0f} TL")

@bot.message_handler(commands=['mayin'])
def mayin(message):
    args = message.text.split()
    if len(args) < 2:
        return bot.reply_to(message, "Kullanım: /mayin <miktar>")
    try:
        miktar = float(args[1])
    except:
        return bot.reply_to(message, "Miktar sayı olmalı.")
    
    user_id = message.from_user.id
    bakiye = get_balance(user_id)
    if miktar <= 0 or miktar > bakiye:
        return bot.reply_to(message, "Geçersiz / yetersiz bakiye.")
    
    update_balance(user_id, -miktar)
    
    # 5x5 grid, 4 mayın (%60 kurtulma şansı)
    mayin_sayisi = 4
    kurtulma_sansi = 0.6
    
    msg = "Mayın Tarlası (5x5):\n"
    if random.random() < kurtulma_sansi:
        kazanc = miktar * 2.5
        update_balance(user_id, kazanc)
        msg += "Mayından kurtuldun! +{kazanc:,.0f} TL kazandın"
    else:
        msg += "💥 Mayına bastın! Kaybettin -{}".format(miktar)
    
    bot.reply_to(message, msg + f"\nBakiye: {get_balance(user_id):,.0f} TL")

@bot.message_handler(commands=['risk'])
def risk(message):
    args = message.text.split()
    if len(args) < 2:
        return bot.reply_to(message, "Kullanım: /risk <miktar>")
    try:
        miktar = float(args[1])
    except:
        return bot.reply_to(message, "Miktar sayı olmalı.")
    
    user_id = message.from_user.id
    bakiye = get_balance(user_id)
    if miktar <= 0 or miktar > bakiye:
        return bot.reply_to(message, "Geçersiz / yetersiz bakiye.")
    
    update_balance(user_id, -miktar)
    
    # %50 kazanma şansı
    if random.random() < 0.5:
        kazanc = miktar * 2.5  # %50'de 2.5 kat
        update_balance(user_id, kazanc)
        bot.reply_to(message, f"🎲 RISK: Kazandın +{kazanc:,.0f} TL\nYeni bakiye: {get_balance(user_id):,.0f} TL")
    else:
        bot.reply_to(message, f"🎲 RISK: Kaybettin -{miktar:,.0f} TL\nKalan: {get_balance(user_id):,.0f} TL")

@bot.message_handler(commands=['cark'])
def cark(message):
    args = message.text.split()
    if len(args) < 2:
        return bot.reply_to(message, "Kullanım: /cark <miktar>")
    try:
        miktar = float(args[1])
    except:
        return bot.reply_to(message, "Miktar sayı olmalı.")
    
    user_id = message.from_user.id
    bakiye = get_balance(user_id)
    if miktar <= 0 or miktar > bakiye:
        return bot.reply_to(message, "Geçersiz / yetersiz bakiye.")
    
    update_balance(user_id, -miktar)
    
    # %55 ödül, %25 sıfırlama, %20 kayıp
    sonuc = random.choices(['odul', 'sifir', 'kayip'], weights=[55, 25, 20])[0]
    
    if sonuc == 'odul':
        katsayi = random.choice([1.5, 2, 3, 5])
        kazanc = miktar * katsayi
        update_balance(user_id, kazanc)
        bot.reply_to(message, f"🎡 Çark: x{katsayi} kazandın! +{kazanc:,.0f} TL\nYeni bakiye: {get_balance(user_id):,.0f} TL")
    elif sonuc == 'sifir':
        bot.reply_to(message, f"🎡 Çark: SIFIRLANDI! Bahis gitti -{miktar:,.0f} TL")
    else:
        bot.reply_to(message, f"🎡 Çark: Kaybettin -{miktar:,.0f} TL\nKalan: {get_balance(user_id):,.0f} TL")

# Diğer komutlar (gonder, zenenginler, banka, ceza) aynı kalıyor, önceki mesajlardan kopyalayabilirsin veya istersen eklerim

# Webhook
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
    return "Bot çalışıyor! 🎲 Telegram'dan mesaj at."

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
