# Perfume Shop Telegram Bot — Cloudflare Workers + D1

Повністю перероблена версія бота під **Cloudflare Workers** та **Cloudflare D1**.

## Що вже реалізовано

- Telegram webhook-бот (без polling).
- Головне меню:
  - 📚 Каталог
  - 💵 Активні ціни
  - 📰 Новини
  - 🛒 Замовити
  - 📞 Контакти
  - ✅ Оформлення замовлення
- Адмін-панель:
  - 📋 Список товарів
  - ➕ Додати товар (покроково)
  - 💰 Змінити ціну (`/setprice ID ЦІНА`)
  - 📦 Перемкнути наявність (`/stock ID`)
  - 🗑 Видалити товар (`/delete ID`)
- Збереження в D1:
  - товари, новини, контакти, замовлення, user-state.

---

## 1) Підготовка Cloudflare

1. Створіть акаунт Cloudflare.
2. Встановіть Node.js 20+.
3. Встановіть залежності:
   ```bash
   npm install
   ```
4. Авторизуйтесь у Cloudflare:
   ```bash
   npx wrangler login
   ```

---

## 2) Створення D1 бази

```bash
npx wrangler d1 create dyhi-db
```

Скопіюйте `database_id` з output і вставте в `wrangler.toml` у `[[d1_databases]]`.

Потім застосуйте схему:

```bash
npx wrangler d1 execute dyhi-db --remote --file=schema.sql
npx wrangler d1 execute dyhi-db --remote --file=seed.sql
```

---

## 3) Secrets і змінні

Задайте секрети:

```bash
npx wrangler secret put TELEGRAM_BOT_TOKEN
npx wrangler secret put TELEGRAM_WEBHOOK_SECRET
```

Задайте адмінів у `wrangler.toml`:

```toml
[vars]
ADMIN_USER_IDS = "123456789,987654321"
```

---

## 4) Деплой

```bash
npm run deploy
```

Після деплою отримаєте URL, наприклад:

```text
https://dyhi-telegram-bot.<your-subdomain>.workers.dev
```

---

## 5) Прив’язка Telegram webhook

Викличте endpoint встановлення webhook:

```bash
curl -X POST "https://dyhi-telegram-bot.<your-subdomain>.workers.dev/telegram/set-webhook" \
  -H "content-type: application/json" \
  -d '{"url":"https://dyhi-telegram-bot.<your-subdomain>.workers.dev/telegram/webhook"}'
```

Тепер Telegram буде слати апдейти напряму у Worker.

---

## 6) Локальний запуск (опціонально)

1. Створіть `.dev.vars` на основі `.dev.vars.example`.
2. Запустіть:

```bash
npm run dev
```

---

## 7) Структура проєкту

- `src/index.ts` — весь бот (webhook + меню + state machine + D1 queries).
- `schema.sql` — створення таблиць.
- `seed.sql` — стартові дані.
- `wrangler.toml` — конфіг Worker + D1 binding.
- `.dev.vars.example` — приклад локальних секретів.

---

## 8) Важливо по безпеці

- Токен Telegram не зберігайте в git.
- Якщо токен колись злився — перевипустіть в @BotFather.
- Використовуйте `TELEGRAM_WEBHOOK_SECRET`, щоб відсікати сторонні POST-запити.

---

## 9) Що легко додати далі

- Реальну Nova Poshta API інтеграцію (з API ключем).
- LiqPay/WayForPay/Stripe checkout links.
- CRM webhook з retry-чергою через Cloudflare Queues.
