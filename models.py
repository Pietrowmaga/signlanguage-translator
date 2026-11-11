from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id           = db.Column(db.Integer, primary_key=True)
    username     = db.Column(db.String(80), unique=True, nullable=False)
    email        = db.Column(db.String(120), unique=True, nullable=False)
    password_hash= db.Column(db.String(256), nullable=False)
    avatar_color   = db.Column(db.String(20), default='#7c3aed')
    practice_score = db.Column(db.Integer, default=0)
    practice_streak= db.Column(db.Integer, default=0)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    sessions = db.relationship('TranslationSession', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def total_words(self):
        return sum(s.word_count or 0 for s in self.sessions)

    @property
    def total_sessions(self):
        return len(self.sessions)


class TranslationSession(db.Model):
    __tablename__ = 'translation_sessions'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at   = db.Column(db.DateTime, nullable=True)
    word_count = db.Column(db.Integer, default=0)
    result_text= db.Column(db.Text, default='')

    words = db.relationship('TranslationHistory', backref='session', lazy=True, cascade='all, delete-orphan')


class TranslationHistory(db.Model):
    __tablename__ = 'translation_history'

    id          = db.Column(db.Integer, primary_key=True)
    session_id  = db.Column(db.Integer, db.ForeignKey('translation_sessions.id'), nullable=False)
    word        = db.Column(db.String(100), nullable=False)
    confidence  = db.Column(db.Float, default=0.0)
    detected_at = db.Column(db.DateTime, default=datetime.utcnow)
