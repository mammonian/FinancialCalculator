import sqlite3
from flask import g

DATABASE = 'database.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

def init_db():
    with open('schema.sql', encoding='utf-8') as f:
        get_db().executescript(f.read())

def init_app(app):
    @app.teardown_appcontext
    def close_connection(exception):
        db = g.pop('_database', None)
        if db is not None:
            db.close()
