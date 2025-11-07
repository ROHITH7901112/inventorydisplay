# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Saree(db.Model):
    __tablename__ = "sarees"
    id = db.Column(db.Integer, primary_key=True)
    saree_id = db.Column(db.String(128), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
