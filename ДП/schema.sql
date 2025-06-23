DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS records;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
);

CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL  -- 'income' або 'expense'
);

CREATE TABLE records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    category_id INTEGER,
    amount REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

INSERT INTO categories (name, type) VALUES
('Їжа', 'expense'),
('Кафе та ресторани', 'expense'),
('Пальне', 'expense'),
('Дитячий садок', 'expense'),
('Оренда', 'expense'),
('Транспорт', 'expense'),
('Комунальні послуги', 'expense'),
('Розваги', 'expense'),
('Одяг', 'expense'),
('Освіта', 'expense');


INSERT INTO categories (name, type) VALUES
('Зарплата', 'income'),
('Премія', 'income'),
('Стипендія', 'income'),
('Пенсія', 'income'),
('Соціальні виплати', 'income'),
('Фріланс', 'income'),
('Підробіток', 'income'),
('Подарунок', 'income'),
('Грошова допомога', 'income'),
('Повернення боргу', 'income');



CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    method TEXT,
    period_months INTEGER,
    predicted_expense REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);