from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
# З core.models тепер імпортуємо оновлену daily_cashflow, яка приймає user_id
# та нову функцію delete_record
from core.models import daily_cashflow, get_user_by_email, create_user, get_categories, create_record, get_user_records, delete_record
from core.models import get_today_expenses_by_category, get_monthly_flow, get_monthly_expenses_for_prediction
from werkzeug.security import generate_password_hash, check_password_hash
import re
from datetime import datetime, timedelta
from core.db import get_db
import numpy as np

try:
    from oikonomika.timeseries import TimeSeries
    from oikonomika.forecasting import HoltWinters
    OIKONOMIKA_AVAILABLE = True
except ImportError:
    OIKONOMIKA_AVAILABLE = False

bp = Blueprint('main', __name__)

MOCK_NBU_INFLATION_DATA = [
    {"date": "2023-01", "rate": 0.008},
    {"date": "2023-02", "rate": 0.007},
    {"date": "2023-03", "rate": 0.006},
    {"date": "2023-04", "rate": 0.005},
    {"date": "2023-05", "rate": 0.004},
    {"date": "2023-06", "rate": 0.003},
    {"date": "2023-07", "rate": 0.004},
    {"date": "2023-08", "rate": 0.005},
    {"date": "2023-09", "rate": 0.006},
    {"date": "2023-10", "rate": 0.005},
    {"date": "2023-11", "rate": 0.004},
    {"date": "2023-12", "rate": 0.003},
    {"date": "2024-01", "rate": 0.002},
    {"date": "2024-02", "rate": 0.003},
    {"date": "2024-03", "rate": 0.004},
    {"date": "2024-04", "rate": 0.003},
    {"date": "2024-05", "rate": 0.002},
    {"date": "2024-06", "rate": 0.001},
]

def _get_nbu_inflation_data_mock():
    return MOCK_NBU_INFLATION_DATA


@bp.route('/api/predict', methods=['POST'])
def predict():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    months = int(data.get("period_months", 3))
    method_index = int(data.get("method_index", 0))
    user_id = session['user_id']

    if months not in [3, 6, 12]:
        return jsonify({"error": "Invalid period"}), 400

    db = get_db()
    cursor = db.cursor()

    historical_data_raw = get_monthly_expenses_for_prediction(user_id, 6)
    
    historical_labels = [m['month_year'] for m in historical_data_raw]
    historical_values = [m['total_expense'] for m in historical_data_raw]

    if historical_values:
        monthly_avg = sum(historical_values) / len(historical_values)
    else:
        monthly_avg = 0 

    method_names = [
        "Базове прогнозування (історичне середнє)",
        "Прогнозування з урахуванням макроекономічних факторів",
        "Сценарний аналіз"
    ]

    forecast_details = []
    scenario_predictions = {}
    forecast_labels = []

    last_hist_date = None
    if historical_labels:
        last_hist_date = datetime.strptime(historical_labels[-1], '%Y-%m')
    else:
        last_hist_date = datetime.now().replace(day=1)

    for i in range(1, months + 1):
        year = last_hist_date.year + (last_hist_date.month + i - 1) // 12
        month = (last_hist_date.month + i - 1) % 12 + 1
        future_date = datetime(year, month, 1)
        forecast_labels.append(future_date.strftime('%Y-%m'))


    if method_index == 0:
        base_trend_rate = 0.0005  # 0.05% щомісячного зростання/спаду
        current_forecast_value = monthly_avg
        np.random.seed(42) # Для відтворюваності
        for m in range(months):
            # Невелике випадкове коливання, щоб уникнути абсолютно рівної лінії
            small_random_shock = np.random.uniform(-0.0001, 0.0001) 
            current_forecast_value *= (1 + base_trend_rate + small_random_shock)
            forecast_details.append(round(max(0, current_forecast_value), 2))

    elif method_index == 1:
        nbu_inflation_data = _get_nbu_inflation_data_mock()
        
        if nbu_inflation_data:
            average_inflation_rate = np.mean([d["rate"] for d in nbu_inflation_data[-6:]]) 
        else:
            average_inflation_rate = 0.004

        current_forecast_value = monthly_avg
        for m in range(months):
            effective_rate = average_inflation_rate 
            np.random.seed(42 + m)
            random_shock = np.random.uniform(-0.001, 0.001)
            
            current_forecast_value *= (1 + effective_rate + random_shock)
            forecast_details.append(round(max(0, current_forecast_value), 2))

    elif method_index == 2:
        growth_rates = {
            "Песимістичний": -0.02,
            "Базовий": 0.0,        
            "Оптимістичний": 0.03  
        }
        for scenario, rate in growth_rates.items():
            monthly_values = []
            current_scenario_value = monthly_avg
            for m in range(months):
                current_scenario_value *= (1 + rate)
                monthly_values.append(round(current_scenario_value, 2))
            scenario_predictions[scenario] = monthly_values

    else:
        return jsonify({"error": "Invalid method index"}), 400

    if method_index != 2:
        cursor.execute("""
            INSERT INTO predictions (user_id, method, period_months, predicted_expense)
            VALUES (?, ?, ?, ?)
        """, (user_id, method_names[method_index], months, round(sum(forecast_details), 2)))
        db.commit()

    response = {
        "method": method_names[method_index],
        "months": months,
        "monthly_forecast": forecast_details if method_index != 2 else None,
        "total_forecast": round(sum(forecast_details), 2) if method_index != 2 else None,
        "scenario_predictions": scenario_predictions if method_index == 2 else None,
        "historical_labels": historical_labels,
        "historical_data": historical_values,   
        "forecast_labels": forecast_labels      
    }

    return jsonify(response)


@bp.route('/prediction/history')
def prediction_history():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT method, period_months, predicted_expense, created_at
        FROM predictions
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 20
    """, (session['user_id'],))
    predictions = cursor.fetchall()
    return render_template('prediction_history.html', predictions=predictions)


@bp.route('/prediction')
def prediction():
    if 'user_id' not in session:
        flash("Будь ласка, увійдіть", "error")
        return redirect(url_for('main.login'))

    return render_template('prediction.html', username=session['user_name'])

@bp.route("/api/expenses")
def get_expenses():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    period = request.args.get("period", "today")
    now = datetime.now()
    start_date = end_date = None

    if period == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now
    elif period == "yesterday":
        start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
    elif period == "day_before_yesterday":
        start_date = (now - timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
    elif period == "week":
        start_date = now - timedelta(days=7)
        end_date = now
    elif period == "month":
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now
    else:
        return jsonify({"error": "Invalid period"}), 400

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT c.name, SUM(r.amount)
        FROM records r
        JOIN categories c ON r.category_id = c.id
        WHERE r.user_id = ?
          AND c.type = 'expense'
          AND datetime(r.created_at) BETWEEN ? AND ?
        GROUP BY c.name
    """, (
        session['user_id'],
        start_date.strftime('%Y-%m-%d %H:%M:%S'),
        end_date.strftime('%Y-%m-%d %H:%M:%S')
    ))

    results = cursor.fetchall()
    categories = [{"name": row[0], "amount": round(row[1], 2)} for row in results]
    total = sum(c["amount"] for c in categories)

    return jsonify({"total": total, "categories": categories})

@bp.route('/api/daily-cashflow')
def api_daily_cashflow():
    # Перевіряємо авторизацію
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    # daily_cashflow в models.py приймає user_id і повертає чисті дані, які ми серіалізуємо
    return jsonify(daily_cashflow(session['user_id'])) 


@bp.route('/api/monthly-flow')
def monthly_flow():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = get_monthly_flow(session['user_id'])
    return jsonify(data)

@bp.route('/api/today-expenses')
def today_expenses():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = get_today_expenses_by_category(session['user_id'])

    total = sum(row[1] for row in data)
    result = {
        "total": total,
        "categories": [
            {"name": row[0], "amount": row[1]} for row in data
        ]
    }
    return jsonify(result)

# ЕНДПОІНТ ДЛЯ ОТРИМАННЯ ЗАПИСІВ КОРИСТУВАЧА ДЛЯ ТАБЛИЦІ
@bp.route('/api/get_records')
def api_get_user_records():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    # Викликаємо функцію з core.models, яка отримує записи користувача
    records = get_user_records(session['user_id'])
    
    # Повертаємо записи у форматі JSON
    return jsonify({"records": records})


@bp.route('/index', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        flash("Будь ласка, увійдіть", "error")
        return redirect(url_for('main.login'))

    if request.method == 'POST':
        category_id = request.form.get("category_id")
        amount = request.form.get("amount")
        rec_type = request.form.get("type")

        if not (category_id and amount and rec_type):
            flash("Виберіть категорію, тип і введіть суму", "error")
            return redirect(url_for('main.dashboard'))

        categories = get_categories()
        valid_category = any(str(cat[0]) == category_id and cat[2] == rec_type for cat in categories)
        if not valid_category:
            flash("Некоректна категорія для вибраного типу", "error")
            return redirect(url_for('main.dashboard'))

        try:
            amount_float = float(amount)
            create_record(session['user_id'], category_id, amount_float)
            # flash("Запис додано!", "success")   # Цей рядок закоментований або видалений
        except ValueError:
            flash("Некоректна сума", "error")

        return redirect(url_for('main.dashboard'))

   
    categories = get_categories()
    records = get_user_records(session['user_id']) # Цей рядок був закоментований раніше
    return render_template('index.html', categories=categories, records=records, username=session['user_name']) # Повернуто records


@bp.route('/')
def home():
    return redirect(url_for('main.login'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name').strip()
        email = request.form.get('email').strip()
        password = request.form.get('password')

        if not name or not email or not password:
            flash("Всі поля мають бути заповнені", "error")
            return render_template('reg.html')

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash("Некоректний email", "error")
            return render_template('reg.html')

        if get_user_by_email(email):
            flash("Користувач з таким email вже існує", "error")
            return render_template('reg.html')

        hashed_password = generate_password_hash(password)
        create_user(name, email, hashed_password)

        flash("Реєстрація успішна! Тепер можете увійти.", "success")
        return redirect(url_for('main.login'))

    return render_template('reg.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email').strip()
        password = request.form.get('password')

        if not email or not password:
            flash("Всі поля мають бути заповнені", "error")
            return render_template('login.html')

        user = get_user_by_email(email)
        if user is None:
            flash("Користувача з таким email не знайдено", "error")
            return render_template('login.html')

        if not check_password_hash(user[3], password):
            flash("Неправильний пароль", "error")
            return render_template('login.html')

        session['user_id'] = user[0]
        session['user_name'] = user[1]
        flash(f"Вітаємо, {user[1]}! Ви увійшли.", "success")
        return redirect(url_for('main.dashboard'))

    return render_template('login.html')

@bp.route('/logout')
def logout():
    session.clear()
    flash("Ви вийшли з системи", "success")
    return redirect(url_for('main.login'))

@bp.route('/api/transactions/<int:record_id>', methods=['DELETE'])
def delete_transaction(record_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session['user_id']
    
    try:
        # Тепер використовуємо нову функцію delete_record з core.models
        # Вона вже перевіряє user_id і видаляє запис
        deleted = delete_record(record_id, user_id)
        
        if deleted:
            return jsonify({"message": "Record deleted successfully"}), 200
        else:
            # Якщо delete_record повернула False, це означає, що запис не знайдено або не належить користувачу
            return jsonify({"error": "Record not found or not authorized to delete"}), 404

    except Exception as e:
        # Логуємо помилку для налагодження
        print(f"Error deleting record: {e}")
        return jsonify({"error": "Internal server error"}), 500