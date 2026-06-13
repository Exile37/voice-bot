import os
import tempfile
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from groq import Groq
import logging

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = Groq(api_key=GROQ_API_KEY)

SUPPORTED_LANGS = {
    "ru": "Russian",
    "en": "English",
    "uk": "Ukrainian",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "auto": "Auto-detect",
}

user_lang = {}


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🎙 <b>Voice to Text Bot</b>\n\n"
        "Отправь голосовое или аудио — получишь текст.\n\n"
        "Команды:\n"
        "/lang ru — язык (ru, en, uk, de, fr, es, auto)\n"
        "/lang — текущий язык\n"
        "/help — помощь"
    )


@dp.message(Command("help"))
async def help_cmd(message: Message):
    langs = ", ".join(f"<code>{k}</code>" for k in SUPPORTED_LANGS)
    await message.answer(
        "🎤 <b>Как использовать:</b>\n"
        "1. Запиши голосовое или пришли аудио/видео\n"
        "2. Бот пришлёт текст\n\n"
        f"🌍 Языки: {langs}\n\n"
        "⚡ Поддерживается: .ogg, .mp3, .wav, .m4a, .mp4 (аудио)"
    )


@dp.message(Command("lang"))
async def set_lang(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        current = user_lang.get(message.from_user.id, "auto")
        await message.answer(f"🌍 Текущий язык: <code>{current}</code>\n\nНапиши /lang ru чтобы сменить")
        return

    lang = args[1].strip().lower()
    if lang not in SUPPORTED_LANGS:
        await message.answer(f"❌ Неизвестный язык. Доступные: {', '.join(SUPPORTED_LANGS)}")
        return

    user_lang[message.from_user.id] = lang
    await message.answer(f"✅ Язык установлен: <b>{SUPPORTED_LANGS[lang]}</b>")


@dp.message(F.voice | F.audio | F.video)
async def handle_voice(message: Message):
    status = await message.answer("⏳ Расшифровываю...")

    file_info = None
    if message.voice:
        file_info = await bot.get_file(message.voice.file_id)
    elif message.audio:
        file_info = await bot.get_file(message.audio.file_id)
    elif message.video:
        file_info = await bot.get_file(message.video.file_id)

    if not file_info:
        await status.edit_text("❌ Не удалось получить файл")
        return

    ext = os.path.splitext(file_info.file_path)[1] or ".ogg"
    lang = user_lang.get(message.from_user.id, "auto")

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        await bot.download_file(file_info.file_path, tmp.name)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as audio_file:
            kwargs = {"model": "whisper-large-v3-turbo", "file": audio_file, "response_format": "verbose_json"}
            if lang != "auto":
                kwargs["language"] = lang

            transcript = client.audio.transcriptions.create(**kwargs)

        text = transcript.text.strip()
        detected = getattr(transcript, "language", "unknown")

        if not text:
            await status.edit_text("🤷 Не удалось распознать речь. Попробуй ещё раз.")
            return

        header = f"🌍 <i>{detected}</i>\n\n" if lang == "auto" else ""
        max_len = 4000
        if len(text) <= max_len:
            await status.edit_text(f"{header}📝 <b>{text}</b>", parse_mode="HTML")
        else:
            await status.delete()
            for i in range(0, len(text), max_len):
                await message.answer(f"{header}📝 <b>{text[i:i+max_len]}</b>", parse_mode="HTML")
                header = ""

    except Exception as e:
        logging.error(f"Transcription error: {e}")
        await status.edit_text(f"❌ Ошибка: {e}")
    finally:
        os.unlink(tmp_path)


@dp.message(F.text)
async def text_hint(message: Message):
    await message.answer("🎤 Отправь голосовое сообщение или аудио, и я расшифрую в текст.")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
