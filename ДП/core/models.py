# core/models.py
from core.db import get_db
from flask import session, jsonify
from datetime import datetime, timedelta

def create_user(name, email, password):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, password))
    db.commit()

def get_user_by_email(email):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    return cursor.fetchone()

def get_categories():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, name, type FROM categories")
    return cursor.fetchall()

def create_category(name, type_):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO categories (name, type) VALUES (?, ?)", (name, type_))
    db.commit()

def create_record(user_id, category_id, amount):
    db = get_db()
    cursor = db.cursor()
    # Додаємо поточну дату і час при створенні запису
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("INSERT INTO records (user_id, category_id, amount, created_at) VALUES (?, ?, ?, ?)", 
                   (user_id, category_id, amount, current_time))
    db.commit()

def get_user_records(user_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT r.id, r.created_at, c.name, r.amount, c.type
        FROM records r
        JOIN categories c ON r.category_id = c.id
        WHERE r.user_id = ?
        ORDER BY r.created_at DESC
    """, (user_id,))
    return cursor.fetchall()

#  Видалення запису
def delete_record(record_id, user_id):
    db = get_db()
    cursor = db.cursor()
    # Перевіряємо, чи належить запис поточному користувачу перед видаленням
    cursor.execute("SELECT id FROM records WHERE id = ? AND user_id = ?", (record_id, user_id))
    existing_record = cursor.fetchone()
    if existing_record:
        cursor.execute("DELETE FROM records WHERE id = ?", (record_id,))
        db.commit()
        return True # Успішно видалено
    return False # Запис не знайдено або не належить користувачу


def get_today_expenses_by_category(user_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT c.name, SUM(r.amount) as total, c.id
        FROM records r
        JOIN categories c ON r.category_id = c.id
        WHERE r.user_id = ?
          AND c.type = 'expense'
          AND DATE(r.created_at) = DATE('now', 'localtime')
        GROUP BY c.name, c.id
    """, (user_id,))
    return cursor.fetchall()


def get_monthly_flow(user_id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT c.type, SUM(r.amount) as total
        FROM records r
        JOIN categories c ON r.category_id = c.id
        WHERE r.user_id = ?
          AND strftime('%Y-%m', r.created_at) = strftime('%Y-%m', 'now', 'localtime')
        GROUP BY c.type
    """, (user_id,))
    
    result = { 'income': 0, 'expense': 0 }
    for row in cursor.fetchall():
        result[row[0]] = row[1]

    result["balance"] = result["income"] - result["expense"]
    return result


def daily_cashflow(user_id): 
    db = get_db()
    cursor = db.cursor()

    today = datetime.now()
    days = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in reversed(range(7))]

    cursor.execute("""
        SELECT
            date(r.created_at) as day,
            c.type,
            SUM(r.amount)
        FROM records r
        JOIN categories c ON r.category_id = c.id
        WHERE r.user_id = ?
          AND date(r.created_at) BETWEEN date('now', '-6 days') AND date('now')
        GROUP BY day, c.type
        ORDER BY day
    """, (user_id,)) # Використовуємо user_id з параметрів

    data = {
        "income": [0]*7,
        "expense": [0]*7,
        "labels": days
    }

    rows = cursor.fetchall()
    for day_str, rec_type, amount in rows:
        if day_str in days:
            idx = days.index(day_str)
            data[rec_type][idx] = amount

    return data # Повертаємо чистий словник, не jsonify

def get_monthly_expenses_for_prediction(user_id, months_back=6):
    db = get_db()
    cursor = db.cursor()
    
    
    start_date = (datetime.now() - timedelta(days=30 * months_back)).strftime('%Y-%m-01 00:00:00')

    cursor.execute("""
        SELECT
            strftime('%Y-%m', r.created_at) AS month_year,
            SUM(r.amount) AS total_expense
        FROM records r
        JOIN categories c ON r.category_id = c.id
        WHERE r.user_id = ?
          AND c.type = 'expense'
          AND r.created_at >= ?
        GROUP BY month_year
        ORDER BY month_year ASC
    """, (user_id, start_date))

    results = cursor.fetchall()
    
    
    current_date = datetime.now()
    
    
    all_months = []
    # Генеруємо назви місяців, починаючи з найбільш давнього до поточного
    for i in range(months_back - 1, -1, -1):
        month_to_add = (current_date.replace(day=1) - timedelta(days=30 * i)).strftime('%Y-%m')
        all_months.append(month_to_add)
    
    
    fetched_expenses = {row[0]: round(row[1], 2) for row in results}
    
    
    final_historical_data = []
    for month_year in all_months:
        final_historical_data.append({
            'month_year': month_year,
            'total_expense': fetched_expenses.get(month_year, 0.0)
        })
        
    return final_historical_data