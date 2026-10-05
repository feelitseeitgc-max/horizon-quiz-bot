#!/usr/bin/env python3
"""Horizon quiz bot — delivers the express-test result + offer in Telegram.

Deep link from the test page: https://t.me/<bot>?start=quiz_B2
The bot reads the level from the /start payload and replies with the
matching level message + the Horizon offer.

Env vars:
  BOT_TOKEN    Telegram Bot API token from @BotFather (required)
  PRICE        Offer price label, e.g. "$49" (default "$55")
  PAYMENT_URL  Checkout link (default https://www.arghorizon.com)
  TEST_URL     Express test page (default https://www.arghorizon.com/expresstest.html)
"""
import logging
import os

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
PRICE = os.environ.get("PRICE", "$55")
PAYMENT_URL = os.environ.get("PAYMENT_URL", "https://www.arghorizon.com")
TEST_URL = os.environ.get(
    "TEST_URL", "https://www.arghorizon.com/expresstest.html"
)
# Invite link to the Horizon Telegram community group (optional).
COMMUNITY_URL = os.environ.get("COMMUNITY_URL", "")

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
        "🔥 HORIZON — заговори на американском английском\n\n"
        "• 3 прямых эфира в неделю с Аргом — сленг, лексика, твои вопросы\n"
        "• Speaking club каждую неделю — говоришь ты\n"
        "• Уроки в записи под твой уровень\n"
        "• Сообщество — практика каждый день\n\n"
        f"{PRICE}/мес — дешевле одного индивидуального урока."
    )


def offer_keyboard() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(f"Занять место — {PRICE}/мес", url=PAYMENT_URL)]]
    if COMMUNITY_URL:
        rows.append(
            [InlineKeyboardButton("Заглянуть в сообщество Horizon", url=COMMUNITY_URL)]
        )
    return InlineKeyboardMarkup(rows)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    payload = (context.args[0] if context.args else "").strip().upper()
    log.info("start payload=%r from user=%s", payload, update.effective_user.id)

    if payload.startswith("QUIZ_"):
        level = payload.split("QUIZ_", 1)[1]
        body = LEVELS.get(level)
        if body:
            await update.message.reply_text(body)
            await update.message.reply_text(
                offer_text(), reply_markup=offer_keyboard()
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
    log.info("Horizon quiz bot starting (polling)…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
