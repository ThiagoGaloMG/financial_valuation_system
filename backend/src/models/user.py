# backend/src/models/user.py

from flask import Blueprint
# from flask_sqlalchemy import SQLAlchemy # Descomente se for usar SQLAlchemy para banco de dados local

# db = SQLAlchemy() # Descomente se for usar SQLAlchemy para banco de dados local

user_bp = Blueprint('user', __name__)

# Exemplo de modelo de usuário (descomente e adapte se for usar um banco de dados)
# class User(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     username = db.Column(db.String(80), unique=True, nullable=False)
#     email = db.Column(db.String(120), unique=True, nullable=False)

#     def __repr__(self):
#         return '<User %r>' % self.username

