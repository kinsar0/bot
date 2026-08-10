import os
import logging
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Хранилище сообщений по чатам
chat_messages = {}

# Лимит сообщений для анализа
MAX_MESSAGES = 50

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start"""
    await update.message.reply_text(
        "👋 Привет! Я бот для анализа переписок.\n\n"
        "📋 Доступные команды:\n"
        "/summary — краткое содержание переписки\n"
        "/entities — извлечь задачи, сроки, ответственных\n"
        "/sentiment — анализ тональности\n"
        "/search тема=... — поиск по теме\n\n"
        "Просто добавьте меня в чат, и я начну работать!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /help"""
    await start(update, context)

async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /summary"""
    chat_id = update.effective_chat.id
    messages = chat_messages.get(chat_id, [])
    
    if not messages:
        await update.message.reply_text("❌ Пока нет сообщений для анализа.")
        return
    
    # Берём последние N сообщений
    recent = messages[-MAX_MESSAGES:]
    
    # Формируем текст для анализа
    text_for_analysis = "\n".join([
        f"{m.get('time', '')} — {m.get('author', 'Unknown')}: {m.get('text', '')}"
        for m in recent
    ])
    
    # Анализируем (встроенная логика)
    summary_text = analyze_summary(text_for_analysis, recent)
    
    await update.message.reply_text(summary_text, parse_mode='Markdown')

async def entities(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /entities"""
    chat_id = update.effective_chat.id
    messages = chat_messages.get(chat_id, [])
    
    if not messages:
        await update.message.reply_text("❌ Пока нет сообщений для анализа.")
        return
    
    recent = messages[-MAX_MESSAGES:]
    text_for_analysis = "\n".join([
        f"{m.get('time', '')} — {m.get('author', 'Unknown')}: {m.get('text', '')}"
        for m in recent
    ])
    
    entities_text = analyze_entities(text_for_analysis, recent)
    await update.message.reply_text(entities_text, parse_mode='Markdown')

async def sentiment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /sentiment"""
    chat_id = update.effective_chat.id
    messages = chat_messages.get(chat_id, [])
    
    if not messages:
        await update.message.reply_text("❌ Пока нет сообщений для анализа.")
        return
    
    recent = messages[-MAX_MESSAGES:]
    text_for_analysis = "\n".join([
        f"{m.get('time', '')} — {m.get('author', 'Unknown')}: {m.get('text', '')}"
        for m in recent
    ])
    
    sentiment_text = analyze_sentiment(text_for_analysis, recent)
    await update.message.reply_text(sentiment_text, parse_mode='Markdown')

async def search_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /search"""
    if not context.args:
        await update.message.reply_text("❌ Укажите тему для поиска. Пример: /search тема=дедлайн")
        return
    
    topic = " ".join(context.args).replace("тема=", "").strip()
    chat_id = update.effective_chat.id
    messages = chat_messages.get(chat_id, [])
    
    if not messages:
        await update.message.reply_text("❌ Пока нет сообщений для анализа.")
        return
    
    # Ищем сообщения по теме
    found = []
    for m in messages:
        text = m.get('text', '').lower()
        if topic.lower() in text:
            found.append(m)
    
    if not found:
        await update.message.reply_text(f"❌ Не найдено сообщений по теме \"{topic}\"")
        return
    
    result = f"🔍 **Найдено по теме \"{topic}\":**\n\n"
    for m in found[:20]:  # Максимум 20 сообщений
        result += f"📅 {m.get('time', '')}\n"
        result += f"👤 {m.get('author', 'Unknown')}\n"
        result += f"💬 {m.get('text', '')[:200]}\n\n"
    
    if len(found) > 20:
        result += f"... и ещё {len(found) - 20} сообщений\n"
    
    await update.message.reply_text(result, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка обычных сообщений"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    # Получаем текст сообщения
    text = update.message.text if update.message.text else ""
    
    # Если сообщение пустое (например, только фото) — пропускаем
    if not text.strip():
        return
    
    # Сохраняем сообщение в хранилище
    if chat_id not in chat_messages:
        chat_messages[chat_id] = []
    
    chat_messages[chat_id].append({
        'time': update.message.date.strftime('%H:%M'),
        'author': user.first_name or user.username or 'Unknown',
        'text': text
    })
    
    # Ограничиваем хранилище (последние 100 сообщений)
    if len(chat_messages[chat_id]) > 100:
        chat_messages[chat_id] = chat_messages[chat_id][-100:]

# === Функции анализа (встроенные) ===

def analyze_summary(text, messages):
    """Анализ: суммаризация"""
    # Простая эвристика для суммаризации
    unique_authors = set(m['author'] for m in messages)
    
    summary = "📋 **Краткое содержание переписки**\n\n"
    summary += f"👥 **Участников:** {len(unique_authors)}\n"
    summary += f"💬 **Сообщений:** {len(messages)}\n\n"
    
    # Ключевые темы (ищем частые слова)
    words = text.lower().split()
    word_freq = {}
    stop_words = {'и', 'в', 'на', 'не', 'что', 'это', 'как', 'то', 'но', 'или', 'же', 'ли', 'бы', 'для', 'от', 'до', 'по', 'с', 'к', 'из', 'за', 'под', 'над', 'при', 'через', 'после', 'перед', 'без', 'для', 'между', 'возле', 'около', 'у', 'о', 'об', 'во', 'а', 'но', 'да', 'или', 'либо', 'то', 'же', 'ли', 'бы', 'если', 'когда', 'где', 'куда', 'откуда', 'почему', 'зачем', 'как', 'какой', 'какая', 'какое', 'какие', 'кто', 'что', 'чей', 'который', 'каковой', 'такой', 'сам', 'самый', 'весь', 'всякий', 'иной', 'другой', 'чужой', 'каждый', 'любой', 'некоторый', 'иные', 'прочие', 'разные', 'всяческие', 'какие-то', 'кто-то', 'что-то', 'где-то', 'когда-то', 'как-то', 'сколько-то', 'кое-кто', 'кое-что', 'кое-где', 'кое-как', 'некто', 'нечто', 'нечий', 'никто', 'ничто', 'никакой', 'ничей', 'нигде', 'никогда', 'никак', 'нисколько', 'некого', 'нечего', 'негде', 'некогда', 'некуда', 'неоткуда', 'зачем', 'почему', 'отчего', 'поскольку', 'ибо', 'так', 'также', 'тоже', 'хотя', 'несмотря', 'вопреки', 'благодаря', 'согласно', 'навстречу', 'вслед', 'наперерез', 'наперекор', 'взамен', 'вместо', 'кроме', 'помимо', 'сверх', 'около', 'возле', 'у', 'перед', 'пред', 'над', 'под', 'за', 'из', 'с', 'от', 'до', 'по', 'о', 'об', 'во', 'на', 'в', 'к', 'ко', 'для', 'ради', 'из-за', 'из-под', 'сиз-за', 'сиз-под'}
    
    for word in words:
        word = word.strip('.,!?;:()[]{}"\'-')
        if len(word) > 3 and word not in stop_words:
            word_freq[word] = word_freq.get(word, 0) + 1
    
    top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
    
    summary += "🔑 **Ключевые темы:**\n"
    for word, count in top_words:
        summary += f"• {word} ({count} раз)\n"
    
    summary += "\n💡 **Для детального анализа** используйте:\n"
    summary += "/entities — задачи и сроки\n"
    summary += "/sentiment — тональность\n"
    summary += "/search тема=... — поиск по теме"
    
    return summary

def analyze_entities(text, messages):
    """Анализ: извлечение сущностей"""
    entities = "📊 **Извлечённые сущности**\n\n"
    
    # Участники
    authors = set(m['author'] for m in messages)
    entities += f"👥 **Участники ({len(authors)}):**\n"
    for author in authors:
        entities += f"• {author}\n"
    
    # Ищем даты (простой паттерн)
    dates = re.findall(r'\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}', text)
    if dates:
        entities += f"\n📅 **Даты:**\n"
        for date in set(dates):
            entities += f"• {date}\n"
    
    # Ищем упоминания задач (простые эвристики)
    task_keywords = ['нужно', 'надо', 'задача', 'сделать', 'сделай', 'возьми', 'проверь', 'посмотри', 'подготовь', 'отправь', 'напиши', 'позвони', 'встреча', 'совещание', 'дедлайн', 'срок']
    tasks = []
    for m in messages:
        for keyword in task_keywords:
            if keyword in m['text'].lower():
                tasks.append(f"{m['author']}: {m['text'][:100]}")
                break
    
    if tasks:
        entities += f"\n✅ **Возможные задачи:**\n"
        for task in tasks[:10]:
            entities += f"• {task}\n"
    
    return entities

def analyze_sentiment(text, messages):
    """Анализ: тональность"""
    sentiment = "😊 **Анализ тональности**\n\n"
    
    # Простая эвристика по эмодзи и словам
    positive_words = ['хорошо', 'отлично', 'супер', 'класс', 'ок', 'договорились', 'спасибо', 'благодарю', 'здорово', 'прекрасно']
    negative_words = ['плохо', 'ужасно', 'кошмар', 'проблема', 'ошибка', 'не работает', 'срочно', 'горит', 'провал', 'ужас']
    
    pos_count = sum(1 for word in positive_words if word in text.lower())
    neg_count = sum(1 for word in negative_words if word in text.lower())
    
    # Считаем эмодзи
    emoji_pattern = r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]'
    emojis = re.findall(emoji_pattern, text)
    
    total = len(messages)
    
    sentiment += f"💬 **Всего сообщений:** {total}\n\n"
    
    if pos_count > neg_count:
        sentiment += "🟢 **Общее настроение: Позитивное**\n"
    elif neg_count > pos_count:
        sentiment += "🔴 **Общее настроение: Напряжённое**\n"
    else:
        sentiment += "🟡 **Общее настроение: Нейтральное**\n"
    
    sentiment += f"\n📊 **Индикаторы:**\n"
    sentiment += f"• Позитивных слов: {pos_count}\n"
    sentiment += f"• Негативных слов: {neg_count}\n"
    sentiment += f"• Эмодзи: {len(emojis)}\n"
    
    return sentiment

def main():
    """Запуск бота"""
    # Получаем токен из переменных окружения
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN не найден в переменных окружения!")
        return
    
    logger.info(f"✅ Запуск бота...")
    
    # Создаём приложение
    application = Application.builder().token(token).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("summary", summary))
    application.add_handler(CommandHandler("entities", entities))
    application.add_handler(CommandHandler("sentiment", sentiment))
    application.add_handler(CommandHandler("search", search_topic))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запускаем polling
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()