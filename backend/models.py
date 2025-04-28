from flask_sqlalchemy import SQLAlchemy
from datetime import date

db = SQLAlchemy()

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    policy_due_date = db.Column(db.Date, nullable=False)
    policy_number = db.Column(db.String(32), unique=True, nullable=False)
    policy_cost = db.Column(db.String(32), nullable=False)

    def __repr__(self):
        return f'<Client {self.username}>'