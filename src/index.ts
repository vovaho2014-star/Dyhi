export interface Env {
  DB: D1Database;
  TELEGRAM_BOT_TOKEN: string;
  TELEGRAM_WEBHOOK_SECRET?: string;
  ADMIN_USER_IDS?: string;
}

type TelegramUpdate = {
  message?: {
    message_id: number;
    chat: { id: number; type: string };
    from?: { id: number; first_name?: string; username?: string };
    text?: string;
  };
};

type UserState =
  | "idle"
  | "checkout_product"
  | "checkout_qty"
  | "checkout_name"
  | "checkout_phone"
  | "checkout_address"
  | "checkout_comment"
  | "admin_add_name"
  | "admin_add_volume"
  | "admin_add_price"
  | "admin_add_description"
  | "admin_add_stock";

const MENU = {
  catalog: "📚 Каталог",
  prices: "💵 Активні ціни",
  news: "📰 Новини",
  order: "🛒 Замовити",
  contacts: "📞 Контакти",
  checkout: "✅ Оформлення замовлення",
  admin: "🛠 Адмін-панель",
  cancel: "❌ Скасувати",
};

const ADMIN_MENU = {
  list: "📋 Список товарів",
  add: "➕ Додати товар",
  setPrice: "💰 Змінити ціну",
  toggleStock: "📦 Перемкнути наявність",
  del: "🗑 Видалити товар",
  exit: "↩️ Вийти",
};

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (request.method === "GET" && url.pathname === "/health") {
      return Response.json({ ok: true, service: "telegram-bot-worker" });
    }

    if (request.method === "POST" && url.pathname === "/telegram/webhook") {
      const secretHeader = request.headers.get("x-telegram-bot-api-secret-token") || "";
      if (env.TELEGRAM_WEBHOOK_SECRET && env.TELEGRAM_WEBHOOK_SECRET !== secretHeader) {
        return new Response("Unauthorized", { status: 401 });
      }

      const update = (await request.json()) as TelegramUpdate;
      await handleUpdate(update, env);
      return new Response("ok");
    }

    if (request.method === "POST" && url.pathname === "/telegram/set-webhook") {
      const body = await request.json().catch(() => ({}));
      const webhookUrl = String(body?.url || "");
      if (!webhookUrl) {
        return Response.json({ ok: false, error: "Missing webhook URL in body: {\"url\":\"https://.../telegram/webhook\"}" }, { status: 400 });
      }
      const result = await setWebhook(env, webhookUrl);
      return Response.json(result);
    }

    return new Response("Not found", { status: 404 });
  },
};

async function handleUpdate(update: TelegramUpdate, env: Env): Promise<void> {
  const message = update.message;
  if (!message || !message.text) return;

  const userId = message.from?.id;
  const chatId = message.chat.id;
  const text = message.text.trim();

  if (!userId) return;

  if (text === "/start") {
    await setState(env, userId, "idle", {});
    await sendMessage(env, chatId, "Вітаємо у Perfume Shop Bot (Cloudflare + D1) 🌸\nОберіть розділ:", mainKeyboard(isAdmin(env, userId)));
    return;
  }

  if (text === "/admin" || text === MENU.admin) {
    if (!isAdmin(env, userId)) {
      await sendMessage(env, chatId, "⛔ У вас немає доступу до адмін-панелі.");
      return;
    }
    await setState(env, userId, "idle", { mode: "admin" });
    await sendMessage(env, chatId, "🛠 Адмін-панель. Оберіть дію:", adminKeyboard());
    return;
  }

  if (text === "/np" || text.startsWith("/np ")) {
    const city = text.replace(/^\/np\s?/, "").trim();
    if (!city) {
      await sendMessage(env, chatId, "Використання: /np Київ");
      return;
    }
    const branches = await findWarehouses(env, city);
    await sendMessage(env, chatId, branches);
    return;
  }

  const stateRow = await getState(env, userId);
  const state = (stateRow?.state as UserState) || "idle";
  const data = stateRow?.data || {};

  if (text === MENU.cancel) {
    await setState(env, userId, "idle", {});
    await sendMessage(env, chatId, "Скасовано.", mainKeyboard(isAdmin(env, userId)));
    return;
  }

  if (state !== "idle") {
    await handleStateFlow(env, chatId, userId, state, data, text);
    return;
  }

  if (text === MENU.catalog) {
    await sendMessage(env, chatId, await formatCatalog(env));
    return;
  }

  if (text === MENU.prices) {
    await sendMessage(env, chatId, await formatPrices(env));
    return;
  }

  if (text === MENU.news) {
    await sendMessage(env, chatId, await formatNews(env), undefined, "HTML");
    return;
  }

  if (text === MENU.contacts) {
    await sendMessage(env, chatId, await formatContacts(env));
    return;
  }

  if (text === MENU.order) {
    await sendMessage(env, chatId, "Щоб замовити, натисніть '✅ Оформлення замовлення'.");
    return;
  }

  if (text === MENU.checkout) {
    await setState(env, userId, "checkout_product", {});
    await sendMessage(env, chatId, "Введіть назву товару:", cancelKeyboard());
    return;
  }

  if (isAdmin(env, userId)) {
    await handleAdminEntry(env, chatId, userId, text);
    return;
  }

  await sendMessage(env, chatId, "Не зрозумів команду. Натисніть /start.");
}

async function handleStateFlow(
  env: Env,
  chatId: number,
  userId: number,
  state: UserState,
  data: Record<string, unknown>,
  text: string,
): Promise<void> {
  if (state === "checkout_product") {
    await setState(env, userId, "checkout_qty", { ...data, product: text });
    await sendMessage(env, chatId, "Кількість (шт):", cancelKeyboard());
    return;
  }

  if (state === "checkout_qty") {
    const qty = Number(text);
    if (!Number.isInteger(qty) || qty <= 0) {
      await sendMessage(env, chatId, "Введіть коректну кількість цифрою.");
      return;
    }
    await setState(env, userId, "checkout_name", { ...data, qty });
    await sendMessage(env, chatId, "Ваше ім'я:");
    return;
  }

  if (state === "checkout_name") {
    await setState(env, userId, "checkout_phone", { ...data, name: text });
    await sendMessage(env, chatId, "Ваш телефон:");
    return;
  }

  if (state === "checkout_phone") {
    await setState(env, userId, "checkout_address", { ...data, phone: text });
    await sendMessage(env, chatId, "Адреса доставки:");
    return;
  }

  if (state === "checkout_address") {
    await setState(env, userId, "checkout_comment", { ...data, address: text });
    await sendMessage(env, chatId, "Коментар (або -):");
    return;
  }

  if (state === "checkout_comment") {
    const payload = { ...data, comment: text } as {
      product: string;
      qty: number;
      name: string;
      phone: string;
      address: string;
      comment: string;
    };

    const unitPrice = await findProductPriceByName(env, payload.product);
    const total = unitPrice * payload.qty;

    const result = await env.DB.prepare(
      `INSERT INTO orders (product_name, qty, unit_price_uah, total_uah, customer_name, phone, address, comment)
       VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8) RETURNING id`
    )
      .bind(payload.product, payload.qty, unitPrice, total, payload.name, payload.phone, payload.address, payload.comment)
      .first<{ id: number }>();

    await setState(env, userId, "idle", {});

    await sendMessage(
      env,
      chatId,
      `✅ Замовлення оформлено!\n\nНомер: #${result?.id ?? "-"}\nТовар: ${payload.product}\nКількість: ${payload.qty}\nСума: ${total} грн\nІм'я: ${payload.name}\nТелефон: ${payload.phone}\nАдреса: ${payload.address}\nКоментар: ${payload.comment}`,
      mainKeyboard(isAdmin(env, userId)),
    );
    return;
  }

  if (state === "admin_add_name") {
    await setState(env, userId, "admin_add_volume", { ...data, name: text });
    await sendMessage(env, chatId, "Об'єм (мл):", cancelKeyboard());
    return;
  }

  if (state === "admin_add_volume") {
    const volume = Number(text);
    if (!Number.isInteger(volume) || volume <= 0) {
      await sendMessage(env, chatId, "Введіть коректний об'єм.");
      return;
    }
    await setState(env, userId, "admin_add_price", { ...data, volume_ml: volume });
    await sendMessage(env, chatId, "Ціна в грн:");
    return;
  }

  if (state === "admin_add_price") {
    const price = Number(text);
    if (!Number.isInteger(price) || price <= 0) {
      await sendMessage(env, chatId, "Введіть коректну ціну.");
      return;
    }
    await setState(env, userId, "admin_add_description", { ...data, price_uah: price });
    await sendMessage(env, chatId, "Опис:");
    return;
  }

  if (state === "admin_add_description") {
    await setState(env, userId, "admin_add_stock", { ...data, description: text });
    await sendMessage(env, chatId, "В наявності? (так/ні)");
    return;
  }

  if (state === "admin_add_stock") {
    const inStock = ["так", "yes", "y", "1"].includes(text.toLowerCase());
    const product = { ...data, in_stock: inStock } as {
      name: string;
      volume_ml: number;
      price_uah: number;
      description: string;
      in_stock: boolean;
    };

    await env.DB.prepare(
      `INSERT INTO products (name, volume_ml, price_uah, in_stock, description)
       VALUES (?1, ?2, ?3, ?4, ?5)`
    )
      .bind(product.name, product.volume_ml, product.price_uah, product.in_stock ? 1 : 0, product.description)
      .run();

    await setState(env, userId, "idle", { mode: "admin" });
    await sendMessage(env, chatId, "✅ Товар додано.", adminKeyboard());
  }
}

async function handleAdminEntry(env: Env, chatId: number, userId: number, text: string): Promise<void> {
  if (text === ADMIN_MENU.list) {
    const items = await env.DB.prepare("SELECT id, name, volume_ml, price_uah, in_stock FROM products ORDER BY id").all<{
      id: number;
      name: string;
      volume_ml: number;
      price_uah: number;
      in_stock: number;
    }>();

    if (!items.results.length) {
      await sendMessage(env, chatId, "Каталог порожній.", adminKeyboard());
      return;
    }

    const lines = items.results.map((p) => `${p.id}. ${p.in_stock ? "✅" : "⛔"} ${p.name} (${p.volume_ml} мл) — ${p.price_uah} грн`);
    await sendMessage(env, chatId, "📋 Каталог:\n" + lines.join("\n"), adminKeyboard());
    return;
  }

  if (text === ADMIN_MENU.add) {
    await setState(env, userId, "admin_add_name", {});
    await sendMessage(env, chatId, "Назва товару:", cancelKeyboard());
    return;
  }

  if (text === ADMIN_MENU.setPrice) {
    await sendMessage(env, chatId, "Формат: /setprice ID НОВА_ЦІНА\nПриклад: /setprice 3 4990", adminKeyboard());
    return;
  }

  if (text === ADMIN_MENU.toggleStock) {
    await sendMessage(env, chatId, "Формат: /stock ID\nПриклад: /stock 3", adminKeyboard());
    return;
  }

  if (text === ADMIN_MENU.del) {
    await sendMessage(env, chatId, "Формат: /delete ID\nПриклад: /delete 3", adminKeyboard());
    return;
  }

  if (text === ADMIN_MENU.exit) {
    await setState(env, userId, "idle", {});
    await sendMessage(env, chatId, "Вихід з адмін-панелі.", mainKeyboard(true));
    return;
  }

  if (text.startsWith("/setprice ")) {
    const parts = text.split(/\s+/);
    const id = Number(parts[1]);
    const price = Number(parts[2]);
    if (!id || !price || price <= 0) {
      await sendMessage(env, chatId, "Некоректний формат. /setprice ID ЦІНА", adminKeyboard());
      return;
    }
    await env.DB.prepare("UPDATE products SET price_uah = ?1 WHERE id = ?2").bind(price, id).run();
    await sendMessage(env, chatId, "✅ Ціну оновлено.", adminKeyboard());
    return;
  }

  if (text.startsWith("/stock ")) {
    const id = Number(text.split(/\s+/)[1]);
    if (!id) {
      await sendMessage(env, chatId, "Некоректний формат. /stock ID", adminKeyboard());
      return;
    }
    await env.DB.prepare("UPDATE products SET in_stock = CASE WHEN in_stock = 1 THEN 0 ELSE 1 END WHERE id = ?1").bind(id).run();
    await sendMessage(env, chatId, "✅ Статус наявності змінено.", adminKeyboard());
    return;
  }

  if (text.startsWith("/delete ")) {
    const id = Number(text.split(/\s+/)[1]);
    if (!id) {
      await sendMessage(env, chatId, "Некоректний формат. /delete ID", adminKeyboard());
      return;
    }
    await env.DB.prepare("DELETE FROM products WHERE id = ?1").bind(id).run();
    await sendMessage(env, chatId, "✅ Товар видалено.", adminKeyboard());
  }
}

function isAdmin(env: Env, userId: number): boolean {
  const ids = (env.ADMIN_USER_IDS || "")
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean)
    .map((x) => Number(x));
  return ids.includes(userId);
}

function mainKeyboard(admin: boolean): ReplyMarkup {
  const keyboard = [
    [MENU.catalog, MENU.prices],
    [MENU.news, MENU.order],
    [MENU.contacts, MENU.checkout],
  ];
  if (admin) keyboard.push([MENU.admin]);
  return {
    keyboard,
    resize_keyboard: true,
  };
}

function adminKeyboard(): ReplyMarkup {
  return {
    keyboard: [
      [ADMIN_MENU.list, ADMIN_MENU.add],
      [ADMIN_MENU.setPrice, ADMIN_MENU.toggleStock],
      [ADMIN_MENU.del, ADMIN_MENU.exit],
      [MENU.cancel],
    ],
    resize_keyboard: true,
  };
}

function cancelKeyboard(): ReplyMarkup {
  return { keyboard: [[MENU.cancel]], resize_keyboard: true };
}

type ReplyMarkup = { keyboard: string[][]; resize_keyboard: boolean };

async function sendMessage(
  env: Env,
  chatId: number,
  text: string,
  replyMarkup?: ReplyMarkup,
  parseMode?: "HTML" | "MarkdownV2",
): Promise<void> {
  const body: Record<string, unknown> = { chat_id: chatId, text };
  if (replyMarkup) body.reply_markup = replyMarkup;
  if (parseMode) body.parse_mode = parseMode;

  await telegramApi(env, "sendMessage", body);
}

async function setWebhook(env: Env, webhookUrl: string): Promise<unknown> {
  const body: Record<string, unknown> = {
    url: webhookUrl,
  };
  if (env.TELEGRAM_WEBHOOK_SECRET) {
    body.secret_token = env.TELEGRAM_WEBHOOK_SECRET;
  }
  return telegramApi(env, "setWebhook", body);
}

async function telegramApi(env: Env, method: string, payload: Record<string, unknown>): Promise<unknown> {
  const res = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/${method}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error(`Telegram API ${method} failed: ${res.status} ${await res.text()}`);
  }

  return res.json();
}

async function getState(env: Env, userId: number): Promise<{ state: string; data: Record<string, unknown> } | null> {
  const row = await env.DB.prepare("SELECT state, data_json FROM user_state WHERE user_id = ?1")
    .bind(userId)
    .first<{ state: string; data_json: string }>();

  if (!row) return null;
  return { state: row.state, data: safeJson(row.data_json) };
}

async function setState(env: Env, userId: number, state: UserState, data: Record<string, unknown>): Promise<void> {
  await env.DB.prepare(
    `INSERT INTO user_state (user_id, state, data_json, updated_at)
     VALUES (?1, ?2, ?3, CURRENT_TIMESTAMP)
     ON CONFLICT(user_id) DO UPDATE SET state = excluded.state, data_json = excluded.data_json, updated_at = CURRENT_TIMESTAMP`
  )
    .bind(userId, state, JSON.stringify(data))
    .run();
}

async function formatCatalog(env: Env): Promise<string> {
  const rows = await env.DB.prepare("SELECT name, volume_ml, price_uah, in_stock, description FROM products ORDER BY id").all<{
    name: string;
    volume_ml: number;
    price_uah: number;
    in_stock: number;
    description: string;
  }>();

  if (!rows.results.length) return "Каталог порожній.";

  return rows.results
    .map((x) => `🔹 ${x.name} (${x.volume_ml} мл)\n${x.description}\nЦіна: ${x.price_uah} грн\nСтатус: ${x.in_stock ? "✅ В наявності" : "⛔ Немає в наявності"}`)
    .join("\n\n");
}

async function formatPrices(env: Env): Promise<string> {
  const rows = await env.DB.prepare("SELECT name, volume_ml, price_uah, in_stock FROM products ORDER BY id").all<{
    name: string;
    volume_ml: number;
    price_uah: number;
    in_stock: number;
  }>();

  if (!rows.results.length) return "Каталог порожній.";
  return [
    "💵 Активні ціни:",
    ...rows.results.map((x) => `${x.in_stock ? "✅" : "⛔"} ${x.name} ${x.volume_ml} мл — ${x.price_uah} грн`),
  ].join("\n");
}

async function formatNews(env: Env): Promise<string> {
  const rows = await env.DB.prepare("SELECT date, title, body FROM news ORDER BY id DESC").all<{
    date: string;
    title: string;
    body: string;
  }>();

  if (!rows.results.length) return "Новин поки немає.";
  return [
    "📰 Актуальні новини:",
    ...rows.results.map((x) => `\n📅 ${x.date}\n<b>${escapeHtml(x.title)}</b>\n${escapeHtml(x.body)}`),
  ].join("\n");
}

async function formatContacts(env: Env): Promise<string> {
  const row = await env.DB.prepare("SELECT phone, email, instagram, address, working_hours FROM contacts WHERE id = 1").first<{
    phone: string;
    email: string;
    instagram: string;
    address: string;
    working_hours: string;
  }>();

  if (!row) return "Контакти не налаштовані.";

  return `📞 Контакти:\nТелефон: ${row.phone}\nEmail: ${row.email}\nInstagram: ${row.instagram}\nАдреса: ${row.address}\nГрафік: ${row.working_hours}`;
}

async function findProductPriceByName(env: Env, name: string): Promise<number> {
  const row = await env.DB.prepare("SELECT price_uah FROM products WHERE lower(name) = lower(?1) LIMIT 1")
    .bind(name)
    .first<{ price_uah: number }>();
  return row?.price_uah ?? 0;
}

async function findWarehouses(env: Env, city: string): Promise<string> {
  // Cloudflare-compatible stub. Реальну інтеграцію можна додати через external API key.
  return `📦 Пошук відділень для міста: ${city}\n(Підключіть Nova Poshta API у Worker Secrets для live-результатів)`;
}

function safeJson(input: string): Record<string, unknown> {
  try {
    return JSON.parse(input) as Record<string, unknown>;
  } catch {
    return {};
  }
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
