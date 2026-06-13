# Тексты для продвижения бота

## 1. Telegram-каталоги (отправить в каждый канал)

### @BotList
```
🎙 Voice to Text Bot — расшифровка голосовых за секунду

Отправь голосовое, аудио, видео или кружок — получишь текст мгновенно.

✨ Что умеет:
• Голосовые, аудио, видео, кружки → текст
• Автоопределение языка (6 языков)
• Скорость: 1-3 секунды
• Экспорт в .txt

🆓 Free: 10 расшифровок/день
⭐ Premium: безлимит

🔗 @voice2text_ru_bot
```

### @tabor
```
🎙 Voice to Text — расшифровка голосовых

Быстро, бесплатно, без регистрации. Просто отправь голосовое.

t.me/voice2text_ru_bot
```

### @BotMark
```
🎙 Voice to Text Bot

Голосовые → текст за 1-3 секунды. Автоязык, экспорт, безлимит в Premium.

t.me/voice2text_ru_bot
```

---

## 2. Reddit

### r/TelegramBots
```
Title: I built a free Voice-to-Text bot for Telegram — 1-3 sec transcription

Body:
Hey! I built a Telegram bot that converts voice messages to text in 1-3 seconds.

Features:
- Supports voice messages, audio files, video notes (circles)
- Auto language detection (RU, EN, UK, DE, FR, ES)
- Export transcription to .txt
- Free tier: 10 transcriptions/day
- Premium: unlimited via Telegram Stars

Built with:
- Python + aiogram 3
- Groq Whisper (free API, fast inference)
- SQLite for user management
- Telegram Stars for payments

Try it: @voice2text_ru_bot

GitHub: https://github.com/Exile37/voice-bot

Feedback welcome!
```

### r/selfhosted
```
Title: Free Voice-to-Text Telegram Bot — no VPS needed (Groq Whisper)

Body:
Built a Telegram bot that transcribes voice messages using Groq's free Whisper API.

- 1-3 second transcription
- Runs on Railway free tier
- No VPS required
- Supports voice, audio, video, circles
- Auto language detection

GitHub: https://github.com/Exile37/voice-bot

Setup takes 2 minutes: get Groq API key (free) + Telegram bot token, deploy to Railway.
```

### r/SideProject
```
Title: Voice-to-Text Telegram Bot — transcribes in 1-3 seconds

Body:
Made a bot that turns voice messages into text instantly.

Tech: Python, aiogram, Groq Whisper (free API), SQLite
Hosting: Railway free tier
Monetization: Telegram Stars (freemium model)

It's live: @voice2text_ru_bot
```

---

## 3. Хабр (пост)

```
# Как я сделал бота для расшифровки голосовых за вечер

Приложение: Telegram
Технологии: Python, aiogram, Groq Whisper
Ссылка: t.me/voice2text_ru_bot
GitHub: github.com/Exile37/voice-bot

## Зачем

У меня куча голосовых в Telegram. Листать их — боль. Хочется прочитать за секунду, не слушая.

Сделал бота: отправил голосовое → получил текст за 1-3 секунды.

## Как работает

1. Пользователь шлёт голосовое/аудио/кружок
2. Бот скачивает файл
3. Отправляет в Groq Whisper API (бесплатно)
4. Возвращает текст + язык + время обработки

## Стек

- **aiogram 3** — фреймворк для Telegram ботов
- **Groq Whisper** — распознавание речи (бесплатно, ~14k запросов/день)
- **SQLite** — пользователи, лимиты, подписки
- **Telegram Stars** — встроенная оплата
- **Railway** — хостинг (бесплатный тариф)

## Бизнес-модель

- Free: 10 расшифровок/день
- Premium: безлимит (неделя/месяц/год/навсегда)
- Реферальная система: +3 дня Premium за друга

## Деплой за 2 минуты

```bash
pip install -r requirements.txt
export BOT_TOKEN="токен"
export GROQ_API_KEY="ключ"
python bot.py
```

Или: залей на GitHub → Railway → Deploy from GitHub.

## Что дальше

- Добавить саммари длинных голосовых
- Перевод после расшифровки
- Канал-режим (бот в группе расшифровывает все голосовые)

---

GitHub: https://github.com/Exile37/voice-bot
```

---

## 4. TikTok/Reels (сценарий 15 сек)

```
[0-3с] Текст: "Отправил голосовое →"
[3-6с] Скрин: голосовое отправляется боту
[6-9с] Скрин: текст появляется за 2 секунды
[9-12с] Текст: "Бесплатно, без VPN"
[12-15с] Текст: "Ссылка в шапке"

Хештеги: #telegram #voice2text #ai #бот #расшифровка
```

---

## 5. Что сделать прямо сейчас

1. Скопируй текст для @BotList → отправь в @BotList
2. Скопируй текст для @tabor → отправь в @tabor
3. Скопируй Reddit пост → опубликуй в r/TelegramBots
4. Скопируй Хабр пост → опубликуй на habr.com

Итого: 4 действия × 2 минуты = 8 минут.
