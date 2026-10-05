#!/usr/bin/env python3
"""Horizon quiz bot — delivers the express-test result + offer in Telegram.

Deep link from the test page: https://t.me/<bot>?start=quiz_B2
The bot reads the level from the /start payload and replies with the
matching level message + the Horizon offer.

Env vars:
  BOT_TOKEN    Telegram Bot API token from @BotFather (required)
  PRICE        Offer price label, e.g. "$49" (default "$49")
  PAYMENT_URL  Checkout link (default https://www.arghorizon.com)
  PAYMENT_URL_A1A2  Checkout link for A1/A2 students (default PAYMENT_URL)
  PAYMENT_URL_B1B2  Checkout link for B1/B2 students (default PAYMENT_URL)
  TRIAL_URL      Free-trial link for the day-7 message (optional)
  TEST_URL     Express test page (default https://www.arghorizon.com/expresstest)
"""
import logging
import os
import sqlite3
from datetime import datetime, timedelta, timezone

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO
)
log = logging.getLogger("horizon-quiz-bot")

BOT_TOKEN = os.environ["BOT_TOKEN"]
PRICE = os.environ.get("PRICE", "$49")
PAYMENT_URL = os.environ.get("PAYMENT_URL", "https://www.arghorizon.com")
# One Stripe link per GetCourse level band; the bot picks the right one
# from the quiz result. Falls back to PAYMENT_URL when unset.
PAYMENT_URL_A = os.environ.get("PAYMENT_URL_A1A2", PAYMENT_URL)  # A1, A2
PAYMENT_URL_B = os.environ.get("PAYMENT_URL_B1B2", PAYMENT_URL)  # B1, B2
TEST_URL = os.environ.get(
    "TEST_URL", "https://www.arghorizon.com/expresstest"
)
# Invite link to the Horizon Telegram community group (optional).
COMMUNITY_URL = os.environ.get("COMMUNITY_URL", "")
TRIAL_URL = os.environ.get("TRIAL_URL", "")
DB_PATH = os.environ.get("DB_PATH", "horizon_quiz.db")


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS users ("
        "user_id INTEGER PRIMARY KEY, level TEXT, started_at TEXT, "
        "r2_sent INTEGER DEFAULT 0, r7_sent INTEGER DEFAULT 0)"
    )
    return conn


def save_user(user_id: int, level: str) -> None:
    conn = db()
    try:
        conn.execute(
            "INSERT INTO users (user_id, level, started_at) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET level=excluded.level",
            (user_id, level, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def due_reminders(days: int, flag: str):
    """Users who started >= `days` ago and haven't got this reminder."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    conn = db()
    try:
        cur = conn.execute(
            f"SELECT user_id, level FROM users WHERE started_at <= ? AND {flag}=0",
            (cutoff,),
        )
        return cur.fetchall()
    finally:
        conn.close()


def mark_sent(user_id: int, flag: str) -> None:
    conn = db()
    try:
        conn.execute(f"UPDATE users SET {flag}=1 WHERE user_id=?", (user_id,))
        conn.commit()
    finally:
        conn.close()


LEVELS = {
    "A1": (
        "Твой уровень — A1 (Beginner) 🎯\n\n"
        "Ты в самом начале пути — и это отличная новость: именно здесь "
        "прогресс самый быстрый. Тебе нужна система: база грамматики + "
        "живые примеры + люди, с которыми не страшно говорить."
    ),
    "A2": (
        "Твой уровень — A2 (Elementary) 🎯\n\n"
        "База у тебя уже есть: понимаешь простые фразы и можешь объясниться. "
        "Следующий шаг — перестать переводить в голове и начать думать "
        "по-английски."
    ),
    "B1": (
        "Твой уровень — B1 (Intermediate) 🎯\n\n"
        "Ты уже говоришь, но звучишь «как учебник», а американцев понимаешь "
        "через раз. Тебе нужен живой американский английский: сленг, скорость, "
        "культура."
    ),
    "B2": (
        "Твой уровень — B2 (Upper-Intermediate) 🎯\n\n"
        "Сильный уровень! Осталось отполировать: сложные конструкции, нюансы "
        "и уверенность — в споре, на собеседовании, в жизни."
    ),
}


def offer_text() -> str:
    return (
        "🔥 HORIZON — заговори на американском английском\n"
        "• 3 эфира в неделю со мной: сленг, грамматика, твои вопросы — без зубрёжки\n"
        "• Speaking club: говоришь ты, не я\n"
        "• Уроки в записи под твой уровень + PDF, конспекты и тесты\n"
        "• Замер уровня до и после — увидишь прогресс\n"
        "• Сообщество, где тебя не засмеют за ошибки\n"
        "🕗 Эфиры пн–чт в 20:15 МСК, записи всегда доступны\n"
        f"{PRICE}/4 недели — дешевле одного индивидуального урока."
    )


def offer_keyboard(level: str = "") -> InlineKeyboardMarkup:
    if level in ("A1", "A2"):
        pay_url = PAYMENT_URL_A
    elif level in ("B1", "B2"):
        pay_url = PAYMENT_URL_B
    else:
        pay_url = PAYMENT_URL
    rows = [[InlineKeyboardButton(f"Занять место — {PRICE}/4 недели", url=pay_url)]]
    if COMMUNITY_URL:
        rows.append(
            [InlineKeyboardButton("Заглянуть в сообщество Horizon", url=COMMUNITY_URL)]
        )
    return InlineKeyboardMarkup(rows)


def reminder_text(level: str) -> str:
    return (
        f"2 дня назад ты узнал свой уровень — {level}.\n\n"
        "Честный вопрос: что изменится через год, если всё останется как сейчас? "
        "Duolingo не считается 🙂\n\n"
        f"Horizon — {PRICE}/4 недели. Меньше, чем один индивидуальный урок."
    )


def trial_text() -> str:
    return (
        "Неделя в Horizon — бесплатно. Без карты.\n\n"
        "Эфиры, speaking club, уроки под твой уровень, сообщество. "
        "Не зайдёт — уйдёшь, ничего не потеряешь.\n\n"
        "А если зайдёт — через месяц будешь звучать по-другому."
    )


def trial_keyboard() -> InlineKeyboardMarkup:
    rows = []
    if TRIAL_URL:
        rows.append([InlineKeyboardButton("Попробовать неделю бесплатно", url=TRIAL_URL)])
    rows.append([InlineKeyboardButton(f"Сразу занять место — {PRICE}/4 недели", url=PAYMENT_URL)])
    if COMMUNITY_URL:
        rows.append(
            [InlineKeyboardButton("Заглянуть в сообщество Horizon", url=COMMUNITY_URL)]
        )
    return InlineKeyboardMarkup(rows)


async def send_due(context: ContextTypes.DEFAULT_TYPE) -> None:
    for user_id, level in due_reminders(2, "r2_sent"):
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=reminder_text(level),
                reply_markup=offer_keyboard(level),
            )
        except Exception as e:
            log.warning("reminder r2 failed for %s: %s", user_id, e)
        mark_sent(user_id, "r2_sent")
    for user_id, level in due_reminders(7, "r7_sent"):
        try:
            await context.bot.send_message(
                chat_id=user_id, text=trial_text(), reply_markup=trial_keyboard()
            )
        except Exception as e:
            log.warning("reminder r7 failed for %s: %s", user_id, e)
        mark_sent(user_id, "r7_sent")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    payload = (context.args[0] if context.args else "").strip().upper()
    log.info("start payload=%r from user=%s", payload, update.effective_user.id)

    if payload.startswith("QUIZ_"):
        level = payload.split("QUIZ_", 1)[1]
        body = LEVELS.get(level)
        if body:
            save_user(update.effective_user.id, level)
            await update.message.reply_text(body)
            await update.message.reply_text(
                offer_text(), reply_markup=offer_keyboard(level)
            )
            return

    # No (valid) payload — generic welcome.
    await update.message.reply_text(
        "Привет! Это бот Horizon 🇺🇸\n\n"
        "Узнай свой реальный уровень английского за 3 минуты — "
        "10 коротких вопросов, результат придёт сюда.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Пройти тест", url=TEST_URL)]]
        ),
    )


async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Нажми /start — расскажу, что я умею 🙂"
    )


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, fallback)
    )
    if app.job_queue:
        app.job_queue.run_repeating(send_due, interval=86400, first=60)
        log.info("reminder job scheduled (daily)")
    log.info("Horizon quiz bot starting (polling)…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
