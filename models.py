from config import ProductionConfig  # Or whichever config you want to use
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from extensions import db

app = Flask('app')
app.config.from_object(ProductionConfig)

class Part(db.Model):
    __tablename__ = 'parts'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    img_filename = db.Column(db.String(255), nullable=True)
    stl_filename = db.Column(db.String(255), nullable=True)