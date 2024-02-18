from config import ProductionConfig  # Or whichever config you want to use
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from extensions import db
from models import Part

app = Flask('app')
app.config.from_object(ProductionConfig)

from models import Part  # Adjust the import path based on your project structure


    
def getPart(part_id):
    return Part.query.get(part_id)

def createPart(name, description, img_filename, stl_filename):
    new_part = Part(name=name, description=description, img_filename=img_filename, stl_filename=stl_filename)
    db.session.add(new_part)
    db.session.commit()
    return new_part

def updatePart(part_id, name=None, description=None, img_filename=None, stl_filename=None):
    part = Part.query.get(part_id)
    if part:
        if name:
            part.name = name
        if description:
            part.description = description
        if img_filename:
            part.img_filename = img_filename
        if stl_filename:
            part.stl_filename = stl_filename
        db.session.commit()
        return part
    return None

def get_all_parts():
    return Part.query.all()