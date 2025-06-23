from flask import Flask
from core.routes import bp
from core.db import init_db, init_app

app = Flask(__name__)
app.secret_key = 'your-secret-key'

# Реєстрируєм blueprint і закриті зв'язки
app.register_blueprint(bp)
init_app(app)

# Викликаємо ініціалізацію бази даних в контексті застосунку
with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(debug=True)
