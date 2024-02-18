from config import ProductionConfig  # Or whichever config you want to use
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from models import Part  # Adjust the import path based on your project structure
from extensions import db



## One time script for creating the db. Don't call from elsewhere 

app = Flask(__name__)
app.config.from_object(ProductionConfig)

db.init_app(app)



with app.app_context():
    db.create_all()
    print("db created!")
  
