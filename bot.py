import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv
from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

MENU_CATALOG = "📚 Каталог"
MENU_PRICES = "💵 Активні ціни"
MENU_NEWS = "📰 Новини"
MENU_ORDER = "🛒 Замовити"
MENU_CONTACTS = "📞 Контакти"
MENU_CHECKOUT = "✅ Оформлення замовлення"
MENU_CANCEL = "❌ Скасувати"

(
    ORDER_PRODUCT,
    ORDER_QTY,
    ORDER_NAME,
    ORDER_PHONE,
    ORDER_ADDRESS,
    ORDER_COMMENT,
) = range(6)


def load_json(filename: str):
    with (DATA_DIR / filename).open("r", encoding="utf-8") as f:
        return json.load(f)


def build_main_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(MENU_CATALOG), KeyboardButton(MENU_PRICES)],
        [KeyboardButton(MENU_NEWS), KeyboardButton(MENU_ORDER)],
        [KeyboardButton(MENU_CONTACTS), KeyboardButton(MENU_CHECKOUT)],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def format_catalog_item(item: dict) -> str:
    stock_status = "✅ В наявності" if item["in_stock"] else "⛔ Немає в наявності"
    return (
        f"🔹 {item['name']} ({item['volume_ml']} мл)\n"
        f"{item['description']}\n"
        f"Ціна: {item['price_uah']} грн\n"
        f"Статус: {stock_status}"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Вітаємо у Perfume Shop Bot 🌸\n"
        "Оберіть розділ з меню нижче:",
        reply_markup=build_main_keyboard(),
    )


async def show_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    catalog = load_json("catalog.json")
    text = "\n\n".join(format_catalog_item(item) for item in catalog)
    await update.message.reply_text(text)


async def show_prices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    catalog = load_json("catalog.json")
    lines = ["💵 Активні ціни:"]
    for item in catalog:
        availability = "✅" if item["in_stock"] else "⛔"
        lines.append(f"{availability} {item['name']} {item['volume_ml']} мл — {item['price_uah']} грн")
    await update.message.reply_text("\n".join(lines))


async def show_news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    news = load_json("news.json")
    lines = ["📰 Актуальні новини:"]
    for post in news:
        lines.append(f"\n📅 {post['date']}\n<b>{post['title']}</b>\n{post['body']}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def show_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    contacts = load_json("contacts.json")
    text = (
        "📞 Контакти:\n"
        f"Телефон: {contacts['phone']}\n"
        f"Email: {contacts['email']}\n"
        f"Instagram: {contacts['instagram']}\n"
        f"Адреса: {contacts['address']}\n"
        f"Графік: {contacts['working_hours']}"
    )
    await update.message.reply_text(text)


async def order_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🛒 Щоб замовити, натисніть кнопку '✅ Оформлення замовлення'.\n"
        "Перед оформленням перегляньте каталог та активні ціни."
    )


async def start_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Введіть назву товару, який хочете замовити:",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton(MENU_CANCEL)]], resize_keyboard=True),
    )
    return ORDER_PRODUCT


async def order_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == MENU_CANCEL:
        return await cancel_order(update, context)

    context.user_data["product"] = update.message.text
    await update.message.reply_text("Вкажіть кількість (шт):")
    return ORDER_QTY


async def order_qty(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == MENU_CANCEL:
        return await cancel_order(update, context)

    if not update.message.text.isdigit() or int(update.message.text) <= 0:
        await update.message.reply_text("Будь ласка, введіть коректну кількість цифрами.")
        return ORDER_QTY

    context.user_data["qty"] = int(update.message.text)
    await update.message.reply_text("Ваше ім'я:")
    return ORDER_NAME


async def order_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == MENU_CANCEL:
        return await cancel_order(update, context)

    context.user_data["name"] = update.message.text
    await update.message.reply_text("Ваш номер телефону:")
    return ORDER_PHONE


async def order_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == MENU_CANCEL:
        return await cancel_order(update, context)

    context.user_data["phone"] = update.message.text
    await update.message.reply_text("Адреса доставки:")
    return ORDER_ADDRESS


async def order_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == MENU_CANCEL:
        return await cancel_order(update, context)

    context.user_data["address"] = update.message.text
    await update.message.reply_text("Коментар до замовлення (або '-' якщо немає):")
    return ORDER_COMMENT


async def order_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == MENU_CANCEL:
        return await cancel_order(update, context)

    context.user_data["comment"] = update.message.text
    order = context.user_data

    summary = (
        "✅ Замовлення оформлено!\n\n"
        f"Товар: {order['product']}\n"
        f"Кількість: {order['qty']}\n"
        f"Ім'я: {order['name']}\n"
        f"Телефон: {order['phone']}\n"
        f"Адреса: {order['address']}\n"
        f"Коментар: {order['comment']}\n\n"
        "Менеджер зв'яжеться з вами найближчим часом."
    )

    save_order(order)
    context.user_data.clear()
    await update.message.reply_text(summary, reply_markup=build_main_keyboard())
    return ConversationHandler.END


def save_order(order: Dict) -> None:
    orders_file = DATA_DIR / "orders.json"
    existing = []

    if orders_file.exists():
        with orders_file.open("r", encoding="utf-8") as f:
            existing = json.load(f)

    existing.append(order)

    with orders_file.open("w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)


async def cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Оформлення скасовано.", reply_markup=build_main_keyboard())
    return ConversationHandler.END


def build_app() -> Application:
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        token = os.getenv("BOT_TOKEN")

    if not token and sys.stdin.isatty():
        print(
            "ℹ️ TELEGRAM_BOT_TOKEN не знайдено. "
            "Вставте токен бота (можна отримати у @BotFather):"
        )
        token = input("TELEGRAM_BOT_TOKEN: ").strip()

    if not token:
        raise RuntimeError(
            "Не знайдено TELEGRAM_BOT_TOKEN.\n"
            "Швидке виправлення:\n"
            "1) Створіть файл .env у папці з bot.py\n"
            "2) Додайте рядок: TELEGRAM_BOT_TOKEN=ВАШ_ТОКЕН\n"
            "3) Запустіть знову: python bot.py"
        )

    app = Application.builder().token(token).build()

    checkout_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(f"^{MENU_CHECKOUT}$"), start_checkout)],
        states={
            ORDER_PRODUCT: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_product)],
            ORDER_QTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_qty)],
            ORDER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_name)],
            ORDER_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_phone)],
            ORDER_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_address)],
            ORDER_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_comment)],
        },
        fallbacks=[MessageHandler(filters.Regex(f"^{MENU_CANCEL}$"), cancel_order)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex(f"^{MENU_CATALOG}$"), show_catalog))
    app.add_handler(MessageHandler(filters.Regex(f"^{MENU_PRICES}$"), show_prices))
    app.add_handler(MessageHandler(filters.Regex(f"^{MENU_NEWS}$"), show_news))
    app.add_handler(MessageHandler(filters.Regex(f"^{MENU_ORDER}$"), order_info))
    app.add_handler(MessageHandler(filters.Regex(f"^{MENU_CONTACTS}$"), show_contacts))
    app.add_handler(checkout_handler)

    return app


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
    )
    app = build_app()
    app.run_polling()


if __name__ == "__main__":
    main()
