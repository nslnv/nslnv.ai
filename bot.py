import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaDocument,
    InputMediaPhoto,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.helpers import escape_markdown

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
OWNER_CHAT_ID = os.environ.get("MY_CHAT_ID")

if not BOT_TOKEN or not OWNER_CHAT_ID:
    raise RuntimeError("Environment variables BOT_TOKEN and MY_CHAT_ID must be set")

ORDERS_FILE = Path("orders.json")

STEP_HELP = "help"
STEP_HELP_FILES = "help_files"
STEP_TOPIC = "topic"
STEP_DEADLINE = "deadline"
STEP_GUIDELINES = "guidelines"
STEP_GUIDELINES_COLLECT_FILES = "guidelines_collect_files"
STEP_UNIQUENESS = "uniqueness"
STEP_BUDGET = "budget"

user_data: Dict[int, Dict[str, Any]] = {}


def load_orders() -> List[Dict[str, Any]]:
    """Load orders from disk."""
    if ORDERS_FILE.exists():
        with ORDERS_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_orders(orders: List[Dict[str, Any]]) -> None:
    """Save orders to disk."""
    with ORDERS_FILE.open("w", encoding="utf-8") as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)


orders_history: List[Dict[str, Any]] = load_orders()

WELCOME_TEXT = (
    "\U0001F31FМеня зовут Никита, и я готов предложить квалифицированную помощь "
    "в написании студенческих работ любой сложности. \U0001F393\U0001F4A1\n\n"
    "Нажмите кнопку ниже, чтобы создать заказ, узнать больше обо мне "
    "или связаться со мной напрямую! \U0001F680"
)

REVIEW_TEXT = (
    "\U0001F4CC Это мой профиль на Studwork: [nslnv_help](https://studwork.ru/info/564376)\n\n"
    "\u2728 Там вы найдёте:\n"
    "\u2705 Отзывы от моих клиентов.\n"
    "\u2705 Список выполненных авторских работ.\n"
    "\u2705 Магазин с готовыми работами.\n\n"
    "\U0001F3AF Буду рад помочь вам достичь ваших целей!"
)

HELP_TEXT = (
    "Это бот для помощи со студенческими работами.\n\n"
    "Доступные команды:\n"
    "/start — Запустить или вернуться в главное меню\n"
    "/help — Показать эту справку\n"
    "/myorders — Посмотреть список моих заказов\n"
    "/cancel — Отменить текущее действие и вернуться в главное меню\n"
)

def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Return the main menu keyboard."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("\U0001F4C4 Создать заказ", callback_data="create_order")],
        [InlineKeyboardButton("\U0001F198 Срочная помощь", callback_data="help_online")],
        [InlineKeyboardButton("\U0001F31F Отзывы", callback_data="reviews")],
    ])


def order_continue_keyboard() -> InlineKeyboardMarkup:
    """Keyboard after collecting guidelines."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("\U0001F4C1 Добавить ещё файлы", callback_data="guidelines_more_files")],
        [InlineKeyboardButton("\u27A1\uFE0F Продолжить заполнение заказа", callback_data="continue_order")],
    ])


def order_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Keyboard to confirm or edit order."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("\u2705 Отправить заказ", callback_data="submit_order")],
        [InlineKeyboardButton("\u270F\uFE0F Редактировать", callback_data="edit_order")],
        [InlineKeyboardButton("\U0001F3E0 Вернуться в главное меню", callback_data="main_menu")],
    ])


def order_edit_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for editing order fields."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("\U0001F4CC Тему работы", callback_data="edit_topic")],
        [InlineKeyboardButton("\u23F3 Сроки выполнения", callback_data="edit_deadline")],
        [InlineKeyboardButton("\U0001F4DA Методические рекомендации", callback_data="edit_guidelines")],
        [InlineKeyboardButton("\U0001F58B Уникальность", callback_data="edit_uniqueness")],
        [InlineKeyboardButton("\U0001F4B0 Бюджет", callback_data="edit_budget")],
        [InlineKeyboardButton("\U0001F3E0 В меню", callback_data="main_menu")],
    ])


def back_to_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Button to return to main menu."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("\U0001F3E0 Вернуться в главное меню", callback_data="main_menu")]]
    )

def build_order_card(order: Dict[str, Any], username: Optional[str] = None, *, title_prefix: str = "Ваш заказ") -> str:
    """Build Markdown V2 text for the order."""
    guidelines_text = order.get("guidelines", "Не указаны")
    file_count = len(order.get("files", []))
    file_part = f" (прикреплено файлов: {file_count})" if file_count else ""

    def esc(text: str) -> str:
        return escape_markdown(text, version=2)

    result = (
        f"\U0001F4CB *{title_prefix}:*\n\n"
        f"\U0001F4CC *Тема работы:* {esc(order.get('topic', ''))}\n"
        f"\u23F3 *Сроки выполнения:* {esc(order.get('deadline', ''))}\n"
        f"\U0001F4DA *Методические рекомендации:* {esc(guidelines_text)}{file_part}\n"
        f"\U0001F58B *Уникальность:* {esc(order.get('uniqueness', ''))}\n"
        f"\U0001F4B0 *Бюджет:* {esc(order.get('budget', ''))}\n"
    )
    if username:
        result += f"\n\U0001F464 *Заказчик:* @{esc(username)}\n"
    return result


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    if update.message:
        await update.message.reply_text(WELCOME_TEXT, reply_markup=main_menu_keyboard())
    elif update.callback_query:
        await update.callback_query.message.reply_text(WELCOME_TEXT, reply_markup=main_menu_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show help."""
    await update.message.reply_text(HELP_TEXT)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cancel current step."""
    user_id = update.message.from_user.id
    user_data.pop(user_id, None)
    await update.message.reply_text(
        "Все действия отменены. Возвращаюсь в главное меню...",
        reply_markup=main_menu_keyboard(),
    )


async def myorders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display current user's orders."""
    user_id = update.message.from_user.id
    user_orders = [o for o in orders_history if o["user_id"] == user_id]
    if not user_orders:
        await update.message.reply_text("У вас пока нет заказов.")
        return

    lines = ["Ваши заказы:"]
    for i, o in enumerate(user_orders, start=1):
        lines.append(f"{i}. Тема: {o.get('topic', 'Без темы')} | Срок: {o.get('deadline', '—')}")

    await update.message.reply_text("\n".join(lines))

async def process_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process fast help messages."""
    user_id = update.message.from_user.id
    username = update.message.from_user.username or f"ID_{user_id}"

    if update.message.document:
        file_id = update.message.document.file_id
        user_data[user_id]["files"].append({"file_id": file_id, "type": "document"})
        await update.message.reply_text("Документ добавлен.")
        return
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        user_data[user_id]["files"].append({"file_id": file_id, "type": "photo"})
        await update.message.reply_text("Фото добавлено.")
        return

    text_msg = update.message.text or "(пустое сообщение)"
    files = user_data[user_id]["files"]
    await context.bot.send_message(
        chat_id=OWNER_CHAT_ID,
        text=f"\U0001F4E9 Срочное сообщение от @{username}:\n{text_msg}",
    )

    if files:
        media_group = []
        for f in files:
            if f["type"] == "document":
                media_group.append(InputMediaDocument(media=f["file_id"]))
            else:
                media_group.append(InputMediaPhoto(media=f["file_id"]))
        for i in range(0, len(media_group), 10):
            chunk = media_group[i:i+10]
            await context.bot.send_media_group(chat_id=OWNER_CHAT_ID, media=chunk)

    await update.message.reply_text(
        "\u2705 Ваше сообщение отправлено! Я свяжусь с вами в ближайшее время.",
        reply_markup=back_to_main_menu_keyboard(),
    )
    user_data.pop(user_id, None)


async def process_topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process topic input."""
    user_id = update.message.from_user.id
    user_data[user_id]["topic"] = update.message.text
    user_data[user_id]["step"] = STEP_DEADLINE
    await update.message.reply_text("\u23F3 Укажите сроки выполнения (например, 01.12.2025):")


async def process_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process deadline input."""
    user_id = update.message.from_user.id
    user_data[user_id]["deadline"] = update.message.text
    user_data[user_id]["step"] = STEP_GUIDELINES
    await update.message.reply_text(
        "\U0001F4DA Опишите методические рекомендации (текст). Затем можно прикрепить файлы. Когда закончите — отправьте любой текст."
    )


async def process_guidelines(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process guidelines text and switch to file collection."""
    user_id = update.message.from_user.id
    if user_data[user_id]["step"] == STEP_GUIDELINES and not (update.message.document or update.message.photo):
        user_data[user_id]["guidelines"] = update.message.text
    user_data[user_id]["step"] = STEP_GUIDELINES_COLLECT_FILES
    await process_guidelines_collect_files(update, context)


async def process_guidelines_collect_files(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Collect guideline files until user sends text."""
    user_id = update.message.from_user.id
    if update.message.document:
        file_id = update.message.document.file_id
        user_data[user_id]["files"].append({"file_id": file_id, "type": "document"})
        await update.message.reply_text("Документ сохранён.")
        return
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        user_data[user_id]["files"].append({"file_id": file_id, "type": "photo"})
        await update.message.reply_text("Изображение сохранено.")
        return

    user_data[user_id]["step"] = None
    await update.message.reply_text(
        "\u2705 Методические рекомендации сохранены. Что вы хотите сделать дальше?",
        reply_markup=order_continue_keyboard(),
    )


async def process_uniqueness(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process uniqueness input."""
    user_id = update.message.from_user.id
    user_data[user_id]["uniqueness"] = update.message.text
    user_data[user_id]["step"] = STEP_BUDGET
    await update.message.reply_text(
        "\U0001F4B0 Укажите бюджет для выполнения работы или напишите 'договоримся':"
    )


async def process_budget(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process budget and show confirmation."""
    user_id = update.message.from_user.id
    user_data[user_id]["budget"] = update.message.text
    user_data[user_id]["step"] = None
    order_card_text = build_order_card(user_data[user_id])
    await update.message.reply_text(
        order_card_text,
        reply_markup=order_confirmation_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2,
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Dispatch user messages based on stored step."""
    user_id = update.message.from_user.id

    if user_id not in user_data:
        await update.message.reply_text(
            "Привет! Для начала работы введите /start или используйте меню:",
            reply_markup=main_menu_keyboard(),
        )
        return

    step = user_data[user_id].get("step")

    try:
        if step == STEP_HELP:
            await process_help(update, context)
        elif step == STEP_TOPIC:
            await process_topic(update, context)
        elif step == STEP_DEADLINE:
            await process_deadline(update, context)
        elif step in (STEP_GUIDELINES, STEP_GUIDELINES_COLLECT_FILES):
            if step == STEP_GUIDELINES:
                await process_guidelines(update, context)
            else:
                await process_guidelines_collect_files(update, context)
        elif step == STEP_UNIQUENESS:
            await process_uniqueness(update, context)
        elif step == STEP_BUDGET:
            await process_budget(update, context)
        elif step == "edit_topic":
            user_data[user_id]["topic"] = update.message.text
            user_data[user_id]["step"] = None
            await update.message.reply_text("Тема обновлена!", reply_markup=order_confirmation_keyboard())
        elif step == "edit_deadline":
            user_data[user_id]["deadline"] = update.message.text
            user_data[user_id]["step"] = None
            await update.message.reply_text("Сроки обновлены!", reply_markup=order_confirmation_keyboard())
        elif step == "edit_guidelines":
            await process_guidelines(update, context)
        elif step == "edit_uniqueness":
            user_data[user_id]["uniqueness"] = update.message.text
            user_data[user_id]["step"] = None
            await update.message.reply_text("Уникальность обновлена!", reply_markup=order_confirmation_keyboard())
        elif step == "edit_budget":
            user_data[user_id]["budget"] = update.message.text
            user_data[user_id]["step"] = None
            await update.message.reply_text("Бюджет обновлён!", reply_markup=order_confirmation_keyboard())
        else:
            await update.message.reply_text(
                "Неизвестная команда. Нажмите /start или используйте меню:",
                reply_markup=main_menu_keyboard(),
            )
    except Exception:
        logger.exception("Ошибка в handle_message")
        await update.message.reply_text(
            "Произошла ошибка при обработке вашего сообщения. Попробуйте ещё раз."
        )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline keyboard buttons."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in user_data:
        user_data[user_id] = {"step": None, "files": []}

    try:
        if query.data == "create_order":
            user_data[user_id] = {"step": STEP_TOPIC, "files": []}
            await query.message.reply_text("\U0001F4CC Введите тему работы:")
        elif query.data == "help_online":
            user_data[user_id] = {"step": STEP_HELP, "files": []}
            await query.message.reply_text(
                "\U0001F198 Напишите своё сообщение. Можно прикрепить файлы/изображения. Когда закончите — отправьте любой текст."
            )
        elif query.data == "reviews":
            await query.message.reply_text(
                REVIEW_TEXT,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=back_to_main_menu_keyboard(),
            )
        elif query.data == "main_menu":
            await start(update, context)
        elif query.data == "guidelines_more_files":
            user_data[user_id]["step"] = STEP_GUIDELINES_COLLECT_FILES
            await query.message.reply_text(
                "Пришлите ещё файлы. Когда закончите — отправьте любой текст."
            )
        elif query.data == "continue_order":
            user_data[user_id]["step"] = STEP_UNIQUENESS
            await query.message.reply_text(
                "\U0001F58B Укажите желаемый уровень уникальности (например, 90%):"
            )
        elif query.data == "edit_order":
            await query.message.reply_text(
                "Что вы хотите отредактировать?", reply_markup=order_edit_keyboard()
            )
        elif query.data == "submit_order":
            order = user_data.pop(user_id, None)
            if order:
                username = query.from_user.username or f"ID_{user_id}"
                order_card_text = build_order_card(order, username, title_prefix="Новый заказ")
                orders_history.append({
                    "user_id": user_id,
                    "topic": order.get("topic", ""),
                    "deadline": order.get("deadline", ""),
                    "guidelines": order.get("guidelines", ""),
                    "files": order.get("files", []),
                    "uniqueness": order.get("uniqueness", ""),
                    "budget": order.get("budget", ""),
                })
                save_orders(orders_history)
                await context.bot.send_message(
                    chat_id=OWNER_CHAT_ID,
                    text=order_card_text,
                    parse_mode=ParseMode.MARKDOWN_V2,
                )
                files = order.get("files", [])
                if files:
                    media_group = []
                    for f in files:
                        if f["type"] == "document":
                            media_group.append(InputMediaDocument(media=f["file_id"]))
                        else:
                            media_group.append(InputMediaPhoto(media=f["file_id"]))
                    for i in range(0, len(media_group), 10):
                        chunk = media_group[i:i+10]
                        await context.bot.send_media_group(chat_id=OWNER_CHAT_ID, media=chunk)
                await query.message.reply_text(
                    "\u2705 Ваш заказ успешно отправлен! Я свяжусь с вами в ближайшее время.",
                    reply_markup=back_to_main_menu_keyboard(),
                )
        elif query.data == "edit_topic":
            user_data[user_id]["step"] = "edit_topic"
            await query.message.reply_text("Введите новую тему работы:")
        elif query.data == "edit_deadline":
            user_data[user_id]["step"] = "edit_deadline"
            await query.message.reply_text("Введите новые сроки выполнения:")
        elif query.data == "edit_guidelines":
            user_data[user_id]["step"] = "edit_guidelines"
            user_data[user_id]["files"] = user_data[user_id].get("files", [])
            await query.message.reply_text(
                "\U0001F4DA Введите новые методические рекомендации, затем прикрепите файлы. Когда закончите — отправьте любой текст."
            )
        elif query.data == "edit_uniqueness":
            user_data[user_id]["step"] = "edit_uniqueness"
            await query.message.reply_text("Введите новый уровень уникальности:")
        elif query.data == "edit_budget":
            user_data[user_id]["step"] = "edit_budget"
            await query.message.reply_text("Введите новый бюджет:")
    except Exception:
        logger.exception("Ошибка в button handler")
        await query.message.reply_text(
            "Произошла ошибка при обработке вашего запроса. Попробуйте ещё раз."
        )

async def main() -> None:
    """Run the bot application."""
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("myorders", myorders))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.ALL, handle_message))

    logger.info("Бот запущен. Нажмите Ctrl+C для остановки.")
    await application.run_polling()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
