import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Set

from dotenv import load_dotenv
from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.error import Conflict, InvalidToken, NetworkError, TelegramError
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
MENU_ADMIN = "🛠 Адмін-панель"
MENU_CANCEL = "❌ Скасувати"

(
    ORDER_PRODUCT,
    ORDER_QTY,
    ORDER_NAME,
    ORDER_PHONE,
    ORDER_ADDRESS,
    ORDER_COMMENT,
) = range(6)

(
    ADMIN_MENU,
    ADMIN_ADD_NAME,
    ADMIN_ADD_VOLUME,
    ADMIN_ADD_PRICE,
    ADMIN_ADD_DESCRIPTION,
    ADMIN_ADD_STOCK,
    ADMIN_SET_PRICE,
    ADMIN_TOGGLE_STOCK,
    ADMIN_DELETE_ITEM,
) = range(100, 109)

ADMIN_LIST_ITEMS = "📋 Список товарів"
ADMIN_ADD_ITEM = "➕ Додати товар"
ADMIN_CHANGE_PRICE = "💰 Змінити ціну"
ADMIN_TOGGLE_AVAILABILITY = "📦 Перемкнути наявність"
ADMIN_REMOVE_ITEM = "🗑 Видалити товар"
ADMIN_EXIT = "↩️ Вийти"


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


def build_main_keyboard_for_user(is_admin: bool) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(MENU_CATALOG), KeyboardButton(MENU_PRICES)],
        [KeyboardButton(MENU_NEWS), KeyboardButton(MENU_ORDER)],
        [KeyboardButton(MENU_CONTACTS), KeyboardButton(MENU_CHECKOUT)],
    ]
    if is_admin:
        keyboard.append([KeyboardButton(MENU_ADMIN)])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def build_admin_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(ADMIN_LIST_ITEMS), KeyboardButton(ADMIN_ADD_ITEM)],
        [KeyboardButton(ADMIN_CHANGE_PRICE), KeyboardButton(ADMIN_TOGGLE_AVAILABILITY)],
        [KeyboardButton(ADMIN_REMOVE_ITEM), KeyboardButton(ADMIN_EXIT)],
        [KeyboardButton(MENU_CANCEL)],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def parse_admin_ids(raw_value: str | None) -> Set[int]:
    if not raw_value:
        return set()

    admin_ids = set()
    for chunk in raw_value.split(","):
        chunk = chunk.strip()
        if chunk.isdigit():
            admin_ids.add(int(chunk))
    return admin_ids


def is_admin(context: ContextTypes.DEFAULT_TYPE, user_id: int | None) -> bool:
    if user_id is None:
        return False
    admin_ids: Set[int] = context.application.bot_data.get("admin_ids", set())
    return user_id in admin_ids


def load_catalog() -> List[dict]:
    return load_json("catalog.json")


def save_catalog(catalog: List[dict]) -> None:
    with (DATA_DIR / "catalog.json").open("w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)


def catalog_lines(catalog: List[dict]) -> List[str]:
    lines: List[str] = []
    for idx, item in enumerate(catalog, start=1):
        availability = "✅" if item["in_stock"] else "⛔"
        lines.append(
            f"{idx}. {availability} {item['name']} ({item['volume_ml']} мл) — {item['price_uah']} грн"
        )
    return lines


def format_catalog_item(item: dict) -> str:
    stock_status = "✅ В наявності" if item["in_stock"] else "⛔ Немає в наявності"
    return (
        f"🔹 {item['name']} ({item['volume_ml']} мл)\n"
        f"{item['description']}\n"
        f"Ціна: {item['price_uah']} грн\n"
        f"Статус: {stock_status}"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    admin_user = is_admin(context, update.effective_user.id if update.effective_user else None)
    await update.message.reply_text(
        "Вітаємо у Perfume Shop Bot 🌸\n"
        "Оберіть розділ з меню нижче:",
        reply_markup=build_main_keyboard_for_user(admin_user),
    )


async def show_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    catalog = load_catalog()
    text = "\n\n".join(format_catalog_item(item) for item in catalog)
    await update.message.reply_text(text)


async def show_prices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    catalog = load_catalog()
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
    admin_user = is_admin(context, update.effective_user.id if update.effective_user else None)
    await update.message.reply_text(summary, reply_markup=build_main_keyboard_for_user(admin_user))
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
    admin_user = is_admin(context, update.effective_user.id if update.effective_user else None)
    await update.message.reply_text(
        "Оформлення скасовано.", reply_markup=build_main_keyboard_for_user(admin_user)
    )
    return ConversationHandler.END


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_admin(context, update.effective_user.id if update.effective_user else None):
        await update.message.reply_text("⛔ У вас немає доступу до адмін-панелі.")
        return ConversationHandler.END
    await update.message.reply_text(
        "🛠 Адмін-панель каталогу.\nОберіть дію:",
        reply_markup=build_admin_keyboard(),
    )
    return ADMIN_MENU


async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == ADMIN_LIST_ITEMS:
        catalog = load_catalog()
        if not catalog:
            await update.message.reply_text("Каталог порожній.")
        else:
            await update.message.reply_text("📋 Поточний каталог:\n" + "\n".join(catalog_lines(catalog)))
        return ADMIN_MENU

    if text == ADMIN_ADD_ITEM:
        context.user_data["admin_new_item"] = {}
        await update.message.reply_text("Введіть назву нового товару:")
        return ADMIN_ADD_NAME

    if text == ADMIN_CHANGE_PRICE:
        catalog = load_catalog()
        if not catalog:
            await update.message.reply_text("Каталог порожній.")
            return ADMIN_MENU
        await update.message.reply_text(
            "Введіть номер товару та нову ціну через пробіл.\n"
            "Приклад: 2 3499\n\n"
            + "\n".join(catalog_lines(catalog))
        )
        return ADMIN_SET_PRICE

    if text == ADMIN_TOGGLE_AVAILABILITY:
        catalog = load_catalog()
        if not catalog:
            await update.message.reply_text("Каталог порожній.")
            return ADMIN_MENU
        await update.message.reply_text(
            "Введіть номер товару, щоб перемкнути наявність:\n\n" + "\n".join(catalog_lines(catalog))
        )
        return ADMIN_TOGGLE_STOCK

    if text == ADMIN_REMOVE_ITEM:
        catalog = load_catalog()
        if not catalog:
            await update.message.reply_text("Каталог порожній.")
            return ADMIN_MENU
        await update.message.reply_text(
            "Введіть номер товару, який потрібно видалити:\n\n" + "\n".join(catalog_lines(catalog))
        )
        return ADMIN_DELETE_ITEM

    if text in (ADMIN_EXIT, MENU_CANCEL):
        await update.message.reply_text(
            "Вихід з адмін-панелі.",
            reply_markup=build_main_keyboard_for_user(True),
        )
        return ConversationHandler.END

    await update.message.reply_text("Оберіть дію кнопками адмін-панелі.")
    return ADMIN_MENU


async def admin_add_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["admin_new_item"]["name"] = update.message.text.strip()
    await update.message.reply_text("Введіть об'єм (мл), наприклад 50:")
    return ADMIN_ADD_VOLUME


async def admin_add_volume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = update.message.text.strip()
    if not value.isdigit() or int(value) <= 0:
        await update.message.reply_text("Введіть коректний об'єм у мл (ціле число > 0).")
        return ADMIN_ADD_VOLUME
    context.user_data["admin_new_item"]["volume_ml"] = int(value)
    await update.message.reply_text("Введіть ціну в грн, наприклад 2890:")
    return ADMIN_ADD_PRICE


async def admin_add_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = update.message.text.strip()
    if not value.isdigit() or int(value) <= 0:
        await update.message.reply_text("Введіть коректну ціну (ціле число > 0).")
        return ADMIN_ADD_PRICE
    context.user_data["admin_new_item"]["price_uah"] = int(value)
    await update.message.reply_text("Введіть короткий опис товару:")
    return ADMIN_ADD_DESCRIPTION


async def admin_add_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["admin_new_item"]["description"] = update.message.text.strip()
    await update.message.reply_text("Товар у наявності? Введіть: так / ні")
    return ADMIN_ADD_STOCK


async def admin_add_stock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = update.message.text.strip().lower()
    if value not in {"так", "ні", "yes", "no", "y", "n", "1", "0"}:
        await update.message.reply_text("Введіть 'так' або 'ні'.")
        return ADMIN_ADD_STOCK

    item = context.user_data["admin_new_item"]
    item["in_stock"] = value in {"так", "yes", "y", "1"}
    catalog = load_catalog()
    catalog.append(item)
    save_catalog(catalog)
    context.user_data.pop("admin_new_item", None)
    await update.message.reply_text("✅ Товар додано до каталогу.", reply_markup=build_admin_keyboard())
    return ADMIN_MENU


async def admin_set_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    parts = update.message.text.strip().split()
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        await update.message.reply_text("Формат: <номер> <нова_ціна>. Приклад: 2 3499")
        return ADMIN_SET_PRICE

    idx = int(parts[0]) - 1
    new_price = int(parts[1])
    catalog = load_catalog()
    if idx < 0 or idx >= len(catalog) or new_price <= 0:
        await update.message.reply_text("Некоректний номер товару або ціна.")
        return ADMIN_SET_PRICE

    catalog[idx]["price_uah"] = new_price
    save_catalog(catalog)
    await update.message.reply_text("✅ Ціну оновлено.", reply_markup=build_admin_keyboard())
    return ADMIN_MENU


async def admin_toggle_stock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = update.message.text.strip()
    if not value.isdigit():
        await update.message.reply_text("Введіть номер товару цифрою.")
        return ADMIN_TOGGLE_STOCK

    idx = int(value) - 1
    catalog = load_catalog()
    if idx < 0 or idx >= len(catalog):
        await update.message.reply_text("Некоректний номер товару.")
        return ADMIN_TOGGLE_STOCK

    catalog[idx]["in_stock"] = not catalog[idx]["in_stock"]
    save_catalog(catalog)
    status = "в наявності" if catalog[idx]["in_stock"] else "немає в наявності"
    await update.message.reply_text(
        f"✅ Статус товару змінено: {status}.", reply_markup=build_admin_keyboard()
    )
    return ADMIN_MENU


async def admin_delete_item(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = update.message.text.strip()
    if not value.isdigit():
        await update.message.reply_text("Введіть номер товару цифрою.")
        return ADMIN_DELETE_ITEM

    idx = int(value) - 1
    catalog = load_catalog()
    if idx < 0 or idx >= len(catalog):
        await update.message.reply_text("Некоректний номер товару.")
        return ADMIN_DELETE_ITEM

    removed = catalog.pop(idx)
    save_catalog(catalog)
    await update.message.reply_text(
        f"✅ Товар '{removed['name']}' видалено.", reply_markup=build_admin_keyboard()
    )
    return ADMIN_MENU


async def admin_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("admin_new_item", None)
    await update.message.reply_text("Дію скасовано.", reply_markup=build_admin_keyboard())
    return ADMIN_MENU


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
    if ":" not in token:
        raise RuntimeError(
            "Схоже, токен має неправильний формат.\n"
            "Приклад валідного токена: 123456789:AA...\n"
            "Перевірте токен у @BotFather і запустіть бот ще раз."
        )

    app = Application.builder().token(token).build()
    app.bot_data["admin_ids"] = parse_admin_ids(os.getenv("ADMIN_USER_IDS"))

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

    admin_handler = ConversationHandler(
        entry_points=[
            CommandHandler("admin", admin_panel),
            MessageHandler(filters.Regex(f"^{MENU_ADMIN}$"), admin_panel),
        ],
        states={
            ADMIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_menu)],
            ADMIN_ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_name)],
            ADMIN_ADD_VOLUME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_volume)],
            ADMIN_ADD_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_price)],
            ADMIN_ADD_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_description)
            ],
            ADMIN_ADD_STOCK: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_stock)],
            ADMIN_SET_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_set_price)],
            ADMIN_TOGGLE_STOCK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_toggle_stock)
            ],
            ADMIN_DELETE_ITEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_delete_item)],
        },
        fallbacks=[MessageHandler(filters.Regex(f"^{MENU_CANCEL}$"), admin_cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex(f"^{MENU_CATALOG}$"), show_catalog))
    app.add_handler(MessageHandler(filters.Regex(f"^{MENU_PRICES}$"), show_prices))
    app.add_handler(MessageHandler(filters.Regex(f"^{MENU_NEWS}$"), show_news))
    app.add_handler(MessageHandler(filters.Regex(f"^{MENU_ORDER}$"), order_info))
    app.add_handler(MessageHandler(filters.Regex(f"^{MENU_CONTACTS}$"), show_contacts))
    app.add_handler(checkout_handler)
    app.add_handler(admin_handler)

    return app


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
    )
    logger = logging.getLogger(__name__)

    try:
        try:
            asyncio.get_event_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())

        app = build_app()
        logger.info("Бот запускається. Для зупинки натисніть Ctrl+C.")
        app.run_polling()
    except InvalidToken:
        print(
            "❌ Telegram відхилив токен.\n"
            "Перевірте значення TELEGRAM_BOT_TOKEN у .env "
            "або перевипустіть токен у @BotFather."
        )
        if sys.stdin.isatty():
            input("Натисніть Enter, щоб закрити вікно...")
        raise
    except Conflict:
        print(
            "❌ Виявлено конфлікт сесій (409 Conflict).\n"
            "Ймовірно, бот уже запущений десь іще (інший ПК/сервер або інший скрипт).\n"
            "Зупиніть інший процес бота та запустіть цей скрипт знову."
        )
        if sys.stdin.isatty():
            input("Натисніть Enter, щоб закрити вікно...")
        raise
    except NetworkError as exc:
        print(
            "❌ Не вдалося підключитися до Telegram API.\n"
            "Перевірте інтернет, VPN/проксі або мережеві обмеження та спробуйте ще раз."
        )
        if sys.stdin.isatty():
            input("Натисніть Enter, щоб закрити вікно...")
        raise exc
    except TelegramError as exc:
        print(f"❌ Помилка Telegram API: {exc}")
        if sys.stdin.isatty():
            input("Натисніть Enter, щоб закрити вікно...")
        raise


if __name__ == "__main__":
    main()
