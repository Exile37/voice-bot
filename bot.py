import os
import time
import uuid
import tempfile
import sqlite3
from datetime import date, datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardButton, InlineKeyboardMarkup,
    LabeledPrice, PreCheckoutQuery, FSInputFile,
)
from groq import Groq
import logging

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
FREE_LIMIT = 10
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = Groq(api_key=GROQ_API_KEY)

db = sqlite3.connect("users.db")
db.execute("""CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    lang TEXT DEFAULT 'auto',
    today_count INTEGER DEFAULT 0,
    today_date TEXT,
    total_count INTEGER DEFAULT 0
)""")
db.commit()

for col, definition in [
    ("premium_until", "TEXT"),
    ("referral_code", "TEXT UNIQUE"),
    ("referred_by", "INTEGER"),
    ("referrals_count", "INTEGER DEFAULT 0"),
]:
    try:
        db.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")
        db.commit()
    except sqlite3.OperationalError:
        pass

SUPPORTED_LANGS = {
    "ru": "Русский",
    "en": "English",
    "uk": "Українська",
    "de": "Deutsch",
    "fr": "Français",
    "es": "Español",
    "auto": "Авто",
}

PLANS = {
    "week": {"days": 7, "price": 29, "label": "📅 Неделя — 29 ⭐"},
    "month": {"days": 30, "price": 79, "label": "📆 Месяц — 79 ⭐"},
    "year": {"days": 365, "price": 199, "label": "🏆 Год — 199 ⭐"},
    "lifetime": {"days": 99999, "price": 299, "label": "💎 Навсегда — 299 ⭐"},
}

HTML = "HTML"


def gen_code():
    return uuid.uuid4().hex[:8].upper()


def get_user(user_id, username=None):
    row = db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not row:
        code = gen_code()
        db.execute(
            "INSERT INTO users (user_id, username, referral_code) VALUES (?, ?, ?)",
            (user_id, username, code),
        )
        db.commit()
        return db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    if username and username != row[1]:
        db.execute("UPDATE users SET username=? WHERE user_id=?", (username, user_id))
        db.commit()
    today = date.today().isoformat()
    if row[5] != today:
        db.execute("UPDATE users SET today_count=0, today_date=? WHERE user_id=?", (today, user_id))
        db.commit()
        row = list(row)
        row[5] = today
        row[4] = 0
    return row


def is_premium(user_id):
    user = get_user(user_id)
    premium_until = user[6]
    if not premium_until:
        return False
    try:
        until = datetime.fromisoformat(premium_until)
        return datetime.now() < until
    except Exception:
        return False


def activate_premium(user_id, days):
    user = get_user(user_id)
    now = datetime.now()
    if user[6]:
        try:
            until = datetime.fromisoformat(user[6])
            if until > now:
                until += timedelta(days=days)
            else:
                until = now + timedelta(days=days)
        except Exception:
            until = now + timedelta(days=days)
    else:
        until = now + timedelta(days=days)
    db.execute("UPDATE users SET premium_until=? WHERE user_id=?", (until.isoformat(), user_id))
    db.commit()


def premium_remaining_days(user_id):
    user = get_user(user_id)
    if not user[6]:
        return 0
    try:
        until = datetime.fromisoformat(user[6])
        delta = until - datetime.now()
        return max(0, delta.days)
    except Exception:
        return 0


def can_use(user_id):
    user = get_user(user_id)
    if is_premium(user_id):
        return True, 999, 0
    used = user[3]
    remaining = FREE_LIMIT - used
    return remaining > 0, remaining, used


def increment_usage(user_id):
    db.execute("UPDATE users SET today_count=today_count+1, total_count=total_count+1 WHERE user_id=?", (user_id,))
    db.commit()


def set_lang(user_id, lang):
    db.execute("UPDATE users SET lang=? WHERE user_id=?", (lang, user_id))
    db.commit()


def get_lang(user_id):
    user = get_user(user_id)
    return user[2]


def apply_referral(user_id, ref_code):
    if not ref_code:
        return False
    referrer = db.execute("SELECT user_id FROM users WHERE referral_code=?", (ref_code,)).fetchone()
    if not referrer or referrer[0] == user_id:
        return False
    user = get_user(user_id)
    if user[8]:
        return False
    db.execute("UPDATE users SET referred_by=?, referrals_count=referrals_count+1 WHERE user_id=?",
               (referrer[0], user_id))
    db.execute("UPDATE users SET referrals_count=referrals_count+1 WHERE user_id=?", (referrer[0],))
    db.commit()
    activate_premium(referrer[0], 3)
    return True


def back_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Назад", callback_data="menu_back")]
    ])


def premium_keyboard():
    buttons = [[InlineKeyboardButton(text=v["label"], callback_data=f"buy:{k}")] for k, v in PLANS.items()]
    buttons.append([InlineKeyboardButton(text="🎁 Промокод", callback_data="promo")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def lang_keyboard(current_lang):
    buttons, row = [], []
    for code, name in SUPPORTED_LANGS.items():
        prefix = "✅ " if code == current_lang else ""
        row.append(InlineKeyboardButton(text=f"{prefix}{name}", callback_data=f"lang:{code}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌍 Язык", callback_data="menu_lang")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="menu_stats")],
        [InlineKeyboardButton(text="⭐ Premium", callback_data="menu_premium")],
        [InlineKeyboardButton(text="👥 Реферал", callback_data="menu_referral")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="menu_help")],
    ])


@dp.message(CommandStart())
async def start(message: Message):
    args = message.text.split()
    if len(args) > 1:
        ref_code = args[1]
        if apply_referral(message.from_user.id, ref_code):
            await message.answer("🎉 Ты зашёл по реферальной ссылке! +3 дня Premium для пригласившего.")

    user = get_user(message.from_user.id, message.from_user.username)
    name = message.from_user.first_name

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"👤 Новый пользователь: <b>{name}</b> (@{message.from_user.username or 'нет'})",
                parse_mode=HTML,
            )
        except Exception:
            pass

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎙 Отправить голосовое", callback_data="menu_help")],
        [InlineKeyboardButton(text="🌍 Язык", callback_data="menu_lang"),
         InlineKeyboardButton(text="📊 Статистика", callback_data="menu_stats")],
        [InlineKeyboardButton(text="⭐ Premium", callback_data="menu_premium"),
         InlineKeyboardButton(text="👥 Реферал", callback_data="menu_referral")],
    ])

    if is_premium(message.from_user.id):
        days = premium_remaining_days(message.from_user.id)
        status = f"⭐ Premium: {days} дн."
    else:
        status = f"🆓 Сегодня: {user[3]}/{FREE_LIMIT}"

    await message.answer(
        f"Привет, <b>{name}</b>! 👋\n\n"
        "Я расшифровываю голосовые в текст за секунду.\n\n"
        "📌 Просто отправь голосовое, аудио, видео или кружок.\n\n"
        f"{status}",
        reply_markup=kb,
        parse_mode=HTML,
    )


@dp.callback_query(F.data == "menu_help")
async def cb_help(callback: CallbackQuery):
    await callback.message.edit_text(
        "🎙 <b>Как пользоваться:</b>\n\n"
        "1. Запиши голосовое сообщение\n"
        "2. Отправь его мне\n"
        "3. Получи текст за 1-3 секунды\n\n"
        "<b>Поддерживается:</b>\n"
        "🎤 Голосовые · 🎵 Аудио · 🎬 Видео · ⭕ Кружки\n\n"
        "🌍 Выбери язык или оставь авто.",
        reply_markup=back_button(),
        parse_mode=HTML,
    )
    await callback.answer()


@dp.callback_query(F.data == "menu_back")
async def cb_back(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    if is_premium(callback.from_user.id):
        days = premium_remaining_days(callback.from_user.id)
        status = f"⭐ Premium: {days} дн."
    else:
        status = f"🆓 Сегодня: {user[3]}/{FREE_LIMIT}"
    await callback.message.edit_text(
        f"🎙 <b>Voice to Text</b>\n\n{status}",
        reply_markup=main_menu_keyboard(),
        parse_mode=HTML,
    )
    await callback.answer()


@dp.callback_query(F.data == "menu_lang")
async def cb_lang(callback: CallbackQuery):
    current = get_lang(callback.from_user.id)
    await callback.message.edit_text(
        "🌍 Выбери язык распознавания:",
        reply_markup=lang_keyboard(current),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("lang:"))
async def cb_set_lang(callback: CallbackQuery):
    lang = callback.data.split(":")[1]
    set_lang(callback.from_user.id, lang)
    await callback.message.edit_text(
        f"✅ Язык: <b>{SUPPORTED_LANGS[lang]}</b>",
        reply_markup=back_button(),
        parse_mode=HTML,
    )
    await callback.answer()


@dp.callback_query(F.data == "menu_stats")
async def cb_stats(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    if is_premium(callback.from_user.id):
        days = premium_remaining_days(callback.from_user.id)
        premium = f"⭐ Premium ({days} дн.)"
    else:
        premium = "🆓 Free"
    await callback.message.edit_text(
        f"📊 <b>Статистика</b>\n\n"
        f"👤 Тариф: {premium}\n"
        f"📈 Всего расшифровок: <b>{user[5]}</b>\n"
        f"📅 Сегодня: <b>{user[3]}/{FREE_LIMIT}</b>\n"
        f"👥 Рефералов: <b>{user[9]}</b>",
        reply_markup=back_button(),
        parse_mode=HTML,
    )
    await callback.answer()


@dp.callback_query(F.data == "menu_premium")
async def cb_premium(callback: CallbackQuery):
    if is_premium(callback.from_user.id):
        days = premium_remaining_days(callback.from_user.id)
        await callback.message.edit_text(
            f"⭐ <b>Premium активен!</b>\n\n"
            f"Осталось: <b>{days} дн.</b>\n"
            "Безлимитные расшифровки.\n"
            "Спасибо за поддержку! ❤️",
            reply_markup=back_button(),
            parse_mode=HTML,
        )
    else:
        await callback.message.edit_text(
            "⭐ <b>Выбери тариф:</b>\n\n"
            "🆓 Free: 10 расшифровок/день\n"
            "📅 Неделя: безлимит 7 дней\n"
            "📆 Месяц: безлимит 30 дней\n"
            "🏆 Год: безлимит 365 дней\n"
            "💎 Навсегда: безлимит навсегда\n\n"
            "🎁 Или введи промокод:",
            reply_markup=premium_keyboard(),
            parse_mode=HTML,
        )
    await callback.answer()


@dp.callback_query(F.data.startswith("buy:"))
async def cb_buy(callback: CallbackQuery):
    plan = callback.data.split(":")[1]
    if plan not in PLANS:
        await callback.answer("❌ Неизвестный тариф", show_alert=True)
        return
    p = PLANS[plan]
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"⭐ VoiceBot {p['label']}",
        description=f"Безлимитные расшифровки на {p['days']} дн.",
        payload=f"premium:{plan}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=p["label"], amount=p["price"])],
    )
    await callback.answer()


@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(query.id, ok=True)


@dp.message(F.successful_payment)
async def on_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    amount = message.successful_payment.total_amount
    username = message.from_user.username or "нет"
    user_id = message.from_user.id

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"💰 <b>Новая оплата!</b>\n\n"
                f"👤 Пользователь: @{username} (ID: {user_id})\n"
                f"💎 Сумма: {amount} Stars\n"
                f"📦 Тариф: {payload}\n\n"
                f"⏳ Stars зачислятся на баланс бота через ~48 часов.\n"
                f"Проверить: @BotFather → /mybots → Payments",
                parse_mode=HTML,
            )
        except Exception:
            pass

    if payload.startswith("premium:"):
        plan = payload.split(":")[1]
        if plan in PLANS:
            activate_premium(message.from_user.id, PLANS[plan]["days"])
            await message.answer(
                f"🎉 <b>Premium активирован!</b>\n\n"
                f"Тариф: {PLANS[plan]['label']}\n"
                f"Действует: {PLANS[plan]['days']} дн.\n\n"
                "Отправляй голосовые — безлимит! ❤️",
                parse_mode=HTML,
            )


@dp.callback_query(F.data == "menu_referral")
async def cb_referral(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    code = user[7]
    count = user[9]
    link = f"https://t.me/{(await bot.get_me()).username}?start={code}"
    await callback.message.edit_text(
        f"👥 <b>Реферальная программа</b>\n\n"
        f"Приглашай друзей — получай <b>+3 дня Premium</b> за каждого.\n\n"
        f"🔗 Твоя ссылка:\n<code>{link}</code>\n\n"
        f"👥 Приглашено: <b>{count}</b>\n"
        f"⭐ Получено дней: <b>{count * 3}</b>",
        reply_markup=back_button(),
        parse_mode=HTML,
    )
    await callback.answer()


@dp.callback_query(F.data == "promo")
async def cb_promo(callback: CallbackQuery):
    await callback.message.answer(
        "🎁 Введи промокод сообщением:",
    )
    await callback.answer()


@dp.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer(
        "🎙 <b>Как пользоваться:</b>\n\n"
        "Просто отправь голосовое, аудио или кружок.\n"
        "Бот вернёт текст.\n\n"
        "🌍 Язык: кнопка в меню.\n"
        "📊 Статистика: кнопка в меню.\n"
        "⭐ Premium: безлимит расшифровок.\n"
        "👥 Реферал: делись ссылкой.",
        parse_mode=HTML,
    )


@dp.message(Command("lang"))
async def set_lang_cmd(message: Message):
    current = get_lang(message.from_user.id)
    await message.answer("🌍 Выбери язык:", reply_markup=lang_keyboard(current))


@dp.message(F.voice | F.audio | F.video | F.video_note)
async def handle_voice(message: Message):
    user_id = message.from_user.id
    allowed, remaining, used = can_use(user_id)

    if not allowed:
        await message.answer(
            f"🚫 Лимит: <b>{used}/{FREE_LIMIT}</b> сегодня.\n\n"
            "⏳ С завтрашнего дня или:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⭐ Premium — безлимит", callback_data="menu_premium")],
            ]),
            parse_mode=HTML,
        )
        return

    start_time = time.time()
    status = await message.answer("🎙 Расшифровываю...")

    file_info = None
    if message.voice:
        file_info = await bot.get_file(message.voice.file_id)
    elif message.audio:
        file_info = await bot.get_file(message.audio.file_id)
    elif message.video:
        file_info = await bot.get_file(message.video.file_id)
    elif message.video_note:
        file_info = await bot.get_file(message.video_note.file_id)

    if not file_info:
        await status.edit_text("❌ Не удалось получить файл")
        return

    ext = os.path.splitext(file_info.file_path)[1].lower() or ".ogg"
    if ext in (".oga", ".opus"):
        ext = ".ogg"
    lang = get_lang(user_id)

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        await bot.download_file(file_info.file_path, tmp.name)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as audio_file:
            kwargs = {
                "model": "whisper-large-v3-turbo",
                "file": audio_file,
                "response_format": "verbose_json",
            }
            if lang != "auto":
                kwargs["language"] = lang
            transcript = client.audio.transcriptions.create(**kwargs)

        text = transcript.text.strip()
        detected = getattr(transcript, "language", "unknown")
        elapsed = round(time.time() - start_time, 1)

        if not text:
            await status.edit_text("🤷 Не удалось распознать речь.")
            return

        increment_usage(user_id)
        new_remaining = remaining - 1

        lang_label = f"🌍 {SUPPORTED_LANGS.get(detected, detected)}" if lang == "auto" else ""
        time_label = f"⚡ {elapsed}с"
        if is_premium(user_id):
            days = premium_remaining_days(user_id)
            limit_label = f"⭐ {days}дн."
        else:
            limit_label = f"🆓 {new_remaining}/{FREE_LIMIT}"
        header_parts = [p for p in [lang_label, time_label, limit_label] if p]
        header = " · ".join(header_parts)

        txt_path = os.path.join(tempfile.gettempdir(), f"transcript_{user_id}.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)

        export_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Скачать .txt", callback_data=f"export:{user_id}")],
        ])

        max_len = 4000
        full_msg = f"📝 {text}\n\n<i>{header}</i>"

        if len(full_msg) <= max_len:
            try:
                await status.edit_text(full_msg, reply_markup=export_kb, parse_mode=HTML)
            except Exception:
                await status.delete()
                await message.answer(full_msg, reply_markup=export_kb, parse_mode=HTML)
        else:
            await status.delete()
            await message.answer(f"📝 {text[:max_len]}\n\n<i>{header}</i>", reply_markup=export_kb, parse_mode=HTML)
            for i in range(max_len, len(text), max_len):
                await message.answer(f"📝 {text[i:i+max_len]}")

    except Exception as e:
        logging.error(f"Transcription error: {e}")
        try:
            await status.edit_text(f"❌ Ошибка: {e}")
        except Exception:
            await message.answer(f"❌ Ошибка: {e}")
    finally:
        os.unlink(tmp_path)


@dp.callback_query(F.data.startswith("export:"))
async def cb_export(callback: CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    txt_path = os.path.join(tempfile.gettempdir(), f"transcript_{user_id}.txt")
    if os.path.exists(txt_path):
        await bot.send_document(
            chat_id=callback.from_user.id,
            document=FSInputFile(txt_path),
            caption="📄 Транскрипция",
        )
    else:
        await callback.answer("❌ Файл уже удалён", show_alert=True)
    await callback.answer()


@dp.message(F.text)
async def text_hint(message: Message):
    user = get_user(message.from_user.id)
    if is_premium(message.from_user.id):
        days = premium_remaining_days(message.from_user.id)
        status = f"⭐ Premium: {days} дн."
    else:
        status = f"🆓 {user[3]}/{FREE_LIMIT}"
    await message.answer(
        f"🎙 Отправь голосовое, аудио или кружок.\n\n{status}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌍 Язык", callback_data="menu_lang"),
             InlineKeyboardButton(text="📊 Статистика", callback_data="menu_stats")],
        ]),
    )


@dp.message(Command("admin"))
async def admin_stats(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    total = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    premium_count = db.execute(
        "SELECT COUNT(*) FROM users WHERE premium_until > ?", (datetime.now().isoformat(),)
    ).fetchone()[0]
    today_total = db.execute(
        "SELECT SUM(today_count) FROM users WHERE today_date=?", (date.today().isoformat(),)
    ).fetchone()[0] or 0
    total_revenue = db.execute(
        "SELECT COUNT(*) FROM users WHERE premium_until IS NOT NULL AND premium_until > ?",
        (datetime.now().isoformat(),)
    ).fetchone()[0]
    await message.answer(
        f"🛡 <b>Админ-панель</b>\n\n"
        f"👥 Всего пользователей: <b>{total}</b>\n"
        f"⭐ Premium: <b>{premium_count}</b>\n"
        f"📊 Расшифровок сегодня: <b>{today_total}</b>\n"
        f"💰 Платящих: <b>{total_revenue}</b>\n\n"
        f"💡 Баланс Stars: @BotFather → /mybots → Payments",
        parse_mode=HTML,
    )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
