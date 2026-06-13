import os
import time
import tempfile
import sqlite3
from datetime import date

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardButton, InlineKeyboardMarkup,
)
from groq import Groq
import logging

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
FREE_LIMIT = 10

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = Groq(api_key=GROQ_API_KEY)

db = sqlite3.connect("users.db")
db.execute("""CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    lang TEXT DEFAULT 'auto',
    is_premium INTEGER DEFAULT 0,
    today_count INTEGER DEFAULT 0,
    today_date TEXT,
    total_count INTEGER DEFAULT 0
)""")
db.commit()

SUPPORTED_LANGS = {
    "ru": "Русский",
    "en": "English",
    "uk": "Українська",
    "de": "Deutsch",
    "fr": "Français",
    "es": "Español",
    "auto": "Авто",
}


def get_user(user_id, username=None):
    row = db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not row:
        db.execute("INSERT INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
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


def can_use(user_id):
    user = get_user(user_id)
    if user[3]:
        return True, 999, 0
    used = user[4]
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


def is_premium(user_id):
    user = get_user(user_id)
    return bool(user[3])


def premium_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Купить Premium — 100 Stars", callback_data="buy_premium")],
        [InlineKeyboardButton(text="🎁 Активировать промокод", callback_data="promo")],
    ])


def lang_keyboard(current_lang):
    buttons = []
    row = []
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
        [InlineKeyboardButton(text="❓ Помощь", callback_data="menu_help")],
    ])


def back_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Назад", callback_data="menu_back")]
    ])


HTML = "HTML"


@dp.message(CommandStart())
async def start(message: Message):
    user = get_user(message.from_user.id, message.from_user.username)
    name = message.from_user.first_name

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎙 Отправить голосовое", callback_data="menu_help")],
        [InlineKeyboardButton(text="🌍 Язык", callback_data="menu_lang"),
         InlineKeyboardButton(text="📊 Статистика", callback_data="menu_stats")],
        [InlineKeyboardButton(text="⭐ Premium", callback_data="menu_premium")],
    ])

    if user[3]:
        status = "⭐ Premium: безлимит расшифровок"
    else:
        status = f"🆓 Сегодня: {user[4]}/{FREE_LIMIT} расшифровок"

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
        "🌍 Выбери язык для точности или оставь авто.",
        reply_markup=back_button(),
        parse_mode=HTML,
    )
    await callback.answer()


@dp.callback_query(F.data == "menu_back")
async def cb_back(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    if user[3]:
        status = "⭐ Premium: безлимит"
    else:
        status = f"🆓 Сегодня: {user[4]}/{FREE_LIMIT}"
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
    if user[3]:
        premium = "⭐ Premium"
        remaining = "∞"
        used_display = "∞"
    else:
        premium = "🆓 Free"
        remaining = str(max(0, FREE_LIMIT - user[4]))
        used_display = f"{user[4]}/{FREE_LIMIT}"
    await callback.message.edit_text(
        f"📊 <b>Статистика</b>\n\n"
        f"👤 Тариф: {premium}\n"
        f"📈 Всего расшифровок: <b>{user[6]}</b>\n"
        f"📅 Сегодня: <b>{used_display}</b>\n"
        f"⏳ Осталось: <b>{remaining}</b>",
        reply_markup=back_button(),
        parse_mode=HTML,
    )
    await callback.answer()


@dp.callback_query(F.data == "menu_premium")
async def cb_premium(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    if user[3]:
        await callback.message.edit_text(
            "⭐ <b>Premium активен!</b>\n\n"
            "У тебя безлимитные расшифровки.\n"
            "Спасибо за поддержку! ❤️",
            reply_markup=back_button(),
            parse_mode=HTML,
        )
    else:
        await callback.message.edit_text(
            "⭐ <b>Premium</b>\n\n"
            "<b>Free:</b> 10 расшифровок/день\n"
            "<b>Premium:</b> безлимит + приоритет\n\n"
            "💳 Оплата: Telegram Stars (100 ⭐)\n"
            "Или введи промокод:",
            reply_markup=premium_keyboard(),
            parse_mode=HTML,
        )
    await callback.answer()


@dp.callback_query(F.data == "buy_premium")
async def cb_buy(callback: CallbackQuery):
    await callback.message.answer(
        "💳 Для оплаты:\n\n"
        "1. Напиши @QuarkBillsBot\n"
        "2. Купи 100 Stars\n"
        "3. Пришли сюда код чека\n\n"
        "Или напиши: @voice2text_support",
        parse_mode=HTML,
    )
    await callback.answer()


@dp.callback_query(F.data == "promo")
async def cb_promo(callback: CallbackQuery):
    await callback.message.answer(
        "🎁 Введи промокод:\n\n"
        "Просто напиши код сообщением.",
    )
    await callback.answer()


@dp.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer(
        "🎙 <b>Как пользоваться:</b>\n\n"
        "Просто отправь голосовое, аудио или кружок.\n"
        "Бот вернёт текст.\n\n"
        "🌍 Смена языка: кнопка в меню.\n"
        "📊 Статистика: кнопка в меню.\n"
        "⭐ Premium: безлимит расшифровок.",
        parse_mode=HTML,
    )


@dp.message(Command("lang"))
async def set_lang_cmd(message: Message):
    current = get_lang(message.from_user.id)
    await message.answer(
        "🌍 Выбери язык:",
        reply_markup=lang_keyboard(current),
    )


@dp.message(F.voice | F.audio | F.video | F.video_note)
async def handle_voice(message: Message):
    user_id = message.from_user.id
    allowed, remaining, used = can_use(user_id)

    if not allowed:
        await message.answer(
            f"🚫 Лимит исчерпан: <b>{used}/{FREE_LIMIT}</b> сегодня.\n\n"
            "⏳ Сброс завтра или:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⭐ Купить Premium — безлимит", callback_data="menu_premium")],
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
            await status.edit_text("🤷 Не удалось распознать речь. Попробуй ещё раз.")
            return

        increment_usage(user_id)
        new_remaining = remaining - 1

        if lang == "auto":
            lang_label = f"🌍 {SUPPORTED_LANGS.get(detected, detected)}"
        else:
            lang_label = ""
        time_label = f"⚡ {elapsed}с"
        if is_premium(user_id):
            limit_label = "⭐"
        else:
            limit_label = f"🆓 {new_remaining}/{FREE_LIMIT}"

        header_parts = [p for p in [lang_label, time_label, limit_label] if p]
        header = " · ".join(header_parts)

        max_len = 4000
        full_msg = f"📝 {text}\n\n<i>{header}</i>"

        if len(full_msg) <= max_len:
            try:
                await status.edit_text(full_msg, parse_mode=HTML)
            except Exception:
                await status.delete()
                await message.answer(full_msg, parse_mode=HTML)
        else:
            await status.delete()
            await message.answer(f"📝 {text[:max_len]}\n\n<i>{header}</i>", parse_mode=HTML)
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


@dp.message(F.text)
async def text_hint(message: Message):
    user = get_user(message.from_user.id)
    if user[3]:
        status = "⭐ Premium: безлимит"
    else:
        status = f"🆓 {user[4]}/{FREE_LIMIT}"

    await message.answer(
        f"🎙 Отправь голосовое, аудио или кружок.\n\n{status}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌍 Язык", callback_data="menu_lang"),
             InlineKeyboardButton(text="📊 Статистика", callback_data="menu_stats")],
        ]),
    )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
