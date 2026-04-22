# Perfume Shop Telegram Bot

Telegram-бот для магазину духів з такими можливостями:
- Каталог, активні ціни, новини, контакти.
- Оформлення замовлення.
- Адмін-панель в Telegram для керування каталогом.
- Підтримка бази даних (**PostgreSQL/MySQL**) через `DATABASE_URL`.
- Онлайн-оплата (**LiqPay/WayForPay**, за наявності ключів).
- Інтеграція з CRM через webhook.
- Інтеграція з Nova Poshta API (команда `/np`).

---

## 1) Швидкий запуск

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

В `.env` мінімально потрібно:
```env
TELEGRAM_BOT_TOKEN=ВАШ_ТОКЕН
ADMIN_USER_IDS=123456789
```

Запуск:
```bash
python bot.py
```

> Важливо: без ключів LiqPay/WayForPay/CRM/Nova Poshta бот **все одно працює**.  
> Ці інтеграції опціональні — без них буде лише базовий функціонал магазину.

---

## 2) Налаштування бази даних (PostgreSQL/MySQL)

Бот працює у двох режимах:
1. **Без `DATABASE_URL`**: використовує JSON (`data/catalog.json`, `data/orders.json`).
2. **З `DATABASE_URL`**: використовує SQLAlchemy + БД.

### PostgreSQL
1. Створіть БД (наприклад `dyhi`).
2. Додайте в `.env`:
```env
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/dyhi
```

### MySQL
1. Створіть БД (UTF-8, бажано `utf8mb4`).
2. Додайте в `.env`:
```env
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/dyhi?charset=utf8mb4
```

### Як працює міграція даних
- При першому старті бот створює таблиці автоматично.
- Якщо таблиця товарів порожня, вона заповнюється даними з `data/catalog.json`.

---

## 3) Адмін-панель каталогу в Telegram

### Доступ
- Додайте ваш Telegram `user_id` у `ADMIN_USER_IDS`.
- `user_id` можна отримати через @userinfobot.

### Як відкрити панель
- Кнопка **🛠 Адмін-панель** (видно тільки адмінам), або
- Команда `/admin`.

### Можливості
- **📋 Список товарів** — показує товари з номерами.
- **➕ Додати товар** — покроково: назва → об’єм → ціна → опис → наявність.
- **💰 Змінити ціну** — формат `номер ціна` (напр. `2 3499`).
- **📦 Перемкнути наявність** — введіть `номер`.
- **🗑 Видалити товар** — введіть `номер`.

---

## 4) Онлайн-оплата (LiqPay / WayForPay)

Після оформлення замовлення бот пробує згенерувати посилання на оплату.

### LiqPay
У `.env`:
```env
PAYMENT_PROVIDER=liqpay
LIQPAY_PUBLIC_KEY=...
LIQPAY_PRIVATE_KEY=...
LIQPAY_SERVER_URL=https://your-domain.com/payment/callback
```

### WayForPay
У `.env`:
```env
PAYMENT_PROVIDER=wayforpay
WAYFORPAY_MERCHANT_ACCOUNT=...
WAYFORPAY_SECRET_KEY=...
WAYFORPAY_RETURN_URL=https://your-domain.com/payment/callback
```

> Якщо ключі не задано, бот не падає — просто повідомить, що оплату не згенеровано.

---

## 5) Інтеграція з CRM

Після створення замовлення бот надсилає payload у CRM webhook (якщо налаштовано).

У `.env`:
```env
CRM_WEBHOOK_URL=https://your-crm.example.com/webhooks/orders
```

### Формат payload (приклад)
```json
{
  "id": 15,
  "product": "Dior Sauvage",
  "qty": 2,
  "total_uah": 9780,
  "name": "Іван",
  "phone": "+380...",
  "delivery": "📦 Nova Poshta",
  "address": "Київ, відділення 12",
  "comment": "Передзвоніть"
}
```

Якщо webhook не відповідає, бот покаже статус-помилку, але замовлення все одно збережеться.

---

## 6) Інтеграція з Nova Poshta API

Підтримується запит відділень командою:
```text
/np Київ
```

У `.env`:
```env
NOVA_POSHTA_API_KEY=...
```

Бот повертає до 10 відділень для вказаного міста.

---

## 7) Рекомендований production-процес (детально)

1. **Git-процес**
   - Один раз: `git clone`.
   - Далі: `git pull` для оновлень.

2. **Секрети**
   - Тримайте `.env` лише на сервері.
   - Не комітьте токени/ключі в Git.

3. **Стабільний запуск 24/7**
   - Linux VPS + `systemd` (`Restart=always`).
   - Або PaaS (Render/Railway/Fly.io) із змінними оточення.

4. **Бекапи**
   - Якщо без БД: копіюйте `data/orders.json`.
   - Якщо з БД: регулярний `pg_dump`/`mysqldump`.

5. **Моніторинг**
   - Логи помилок Telegram API.
   - Логи CRM/Nova Poshta інтеграцій.

6. **Безпека**
   - Якщо токен опубліковано — одразу revoke/new token через @BotFather.
   - Обмежуйте список `ADMIN_USER_IDS`.

---

## 8) Файли проєкту

- `bot.py` — основна логіка Telegram-бота.
- `storage.py` — шар зберігання (JSON або SQL БД).
- `integrations.py` — оплата, CRM webhook, Nova Poshta API.
- `data/catalog.json` — стартовий каталог.
- `data/news.json` — новини.
- `data/contacts.json` — контакти.
