# Perfume Shop Telegram Bot

Готовий Telegram-бот для магазину духів з розділами:
- 📚 Каталог
- 💵 Активні ціни
- 📰 Новини
- 🛒 Замовити
- 📞 Контакти
- ✅ Оформлення замовлення

## 1) Швидкий старт

### Linux / macOS
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### Windows (cmd)
```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

### Windows (PowerShell)
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

У `.env` вставте токен:

```env
TELEGRAM_BOT_TOKEN=ВАШ_ТОКЕН
```

Запуск:

```bash
python bot.py
```

> Якщо забули створити `.env`, бот попросить вставити токен прямо в консолі під час запуску.
> Якщо токен вставлений некоректно, бот покаже підказку з прикладом формату токена.
> Якщо після введення токена бот закривається: перевірте текст помилки в консолі. Найчастіше це або `409 Conflict` (бот уже запущений в іншому місці), або проблеми з інтернетом/блокуванням доступу до Telegram API.

## 2) Де зберігаються дані

- `data/catalog.json` — товари, наявність, ціни.
- `data/news.json` — новини.
- `data/contacts.json` — контакти магазину.
- `data/orders.json` — автоматично створюється після першого замовлення.

## 3) Як підтримувати актуальний стан

### Оновити ціни/товари
Відкрийте `data/catalog.json` і змініть:
- `price_uah`
- `in_stock`
- `description`

### Оновити новини
Додайте/редагуйте записи в `data/news.json` (дата, заголовок, текст).

### Оновити контакти
Відредагуйте `data/contacts.json`.

Після кожної зміни перезапустіть бота:

```bash
python bot.py
```

## 4) Рекомендації для продакшену

- Не зберігайте токен у репозиторії (тільки у `.env`).
- Якщо токен випадково опубліковано — **негайно перевипустіть** його через @BotFather.
- Налаштуйте запуск через `systemd` або Docker, щоб бот перезапускався автоматично.
- Регулярно робіть backup файлу `data/orders.json`.

## 5) Що можна покращити далі

- Адмін-панель для керування каталогом з Telegram.
- Підключення бази даних (PostgreSQL/MySQL).
- Онлайн-оплата (LiqPay/WayForPay/Stripe).
- Інтеграція з CRM і Nova Poshta API.
