INSERT INTO products (name, volume_ml, price_uah, in_stock, description)
SELECT 'Chanel Coco Mademoiselle', 50, 5290, 1, 'Квітково-східний аромат із цитрусами, трояндою та пачулі.'
WHERE NOT EXISTS (SELECT 1 FROM products);

INSERT INTO products (name, volume_ml, price_uah, in_stock, description)
SELECT 'Dior Sauvage', 100, 4890, 1, 'Свіжий деревно-пряний аромат з бергамотом і амброксаном.'
WHERE (SELECT COUNT(*) FROM products) = 1;

INSERT INTO products (name, volume_ml, price_uah, in_stock, description)
SELECT 'YSL Libre', 90, 4590, 0, 'Квітковий аромат з лавандою, апельсиновим цвітом і ваніллю.'
WHERE (SELECT COUNT(*) FROM products) = 2;

INSERT INTO news (date, title, body)
SELECT '2026-04-20', 'Весняний sale -15%', 'Знижка -15% на вибрані аромати до кінця тижня.'
WHERE NOT EXISTS (SELECT 1 FROM news);

INSERT INTO contacts (id, phone, email, instagram, address, working_hours)
VALUES (1, '+380 67 123 45 67', 'hello@perfume-shop.ua', '@perfume_shop_ua', 'м. Київ, вул. Хрещатик, 10', 'Пн-Нд: 10:00-20:00')
ON CONFLICT(id) DO NOTHING;
