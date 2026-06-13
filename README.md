# Voice to Text Telegram Bot

Голосовые → текст за секунду. Бесплатно.

## Получение ключей

### 1. Telegram Bot Token
1. Открой [@BotFather](https://t.me/BotFather) в Telegram
2. `/newbot` → задай имя → получишь токен

### 2. Groq API Key (бесплатно)
1. Зайди на [console.groq.com](https://console.groq.com)
2. Зарегистрируйся → API Keys → Create
3. Скопируй ключ

## Локальный запуск

```bash
pip install -r requirements.txt
export BOT_TOKEN="твой_токен"
export GROQ_API_KEY="твой_ключ"
python bot.py
```

## Деплой на Railway (бесплатно)

1. Залей код на GitHub
2. [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. В Variables добавь:
   - `BOT_TOKEN`
   - `GROQ_API_KEY`
4. Railway автоматически соберёт Docker и запустит

## Деплой на Render (бесплатно)

1. [render.com](https://render.com) → New → Background Worker
2. Подключи GitHub репозиторий
3. Build: `pip install -r requirements.txt`
4. Start: `python bot.py`
5. В Environment добавь переменные

## Возможности

- 🎤 Голосовые сообщения → текст
- 🎵 Аудио файлы (mp3, wav, m4a, ogg)
- 🌍 Автоопределение языка + ручная настройка
- ⚡ Скорость: 1-3 секунды на сообщение
- 🔒 Не хранит аудио — только конвертация

## Команды

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие |
| `/lang ru` | Установить язык (ru, en, uk, de, fr, es, auto) |
| `/lang` | Текущий язык |
| `/help` | Помощь |

## Технологии

- **aiogram 3** — Telegram bot framework
- **Groq Whisper** — распознавание речи (бесплатно, ~14k запросов/день)
- **Docker** — деплой

## Лимиты Groq Free

- ~14,400 запросов в день
- ~20 минут аудио в сумме
- Этого хватит на 100-200 активных пользователей
