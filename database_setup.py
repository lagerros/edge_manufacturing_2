from config import ProductionConfig  # Or whichever config you want to use
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from models import Part  # Adjust the import path based on your project structure

app = Flask('app')
app.config.from_object(ProductionConfig)

db = SQLAlchemy(app)



with app.app_context():
    db.create_all()
    print("db created!")
