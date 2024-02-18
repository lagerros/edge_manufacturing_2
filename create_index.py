from whoosh.index import create_in
from whoosh.fields import Schema, TEXT, ID
import os
from database import get_all_parts
from flask import Flask
from config import ProductionConfig  # Or whichever config you want to use
from extensions import db




app = Flask(__name__)
app.config.from_object(ProductionConfig)

db.init_app(app)

def create_search_index():
    if not os.path.exists("indexdir"):
        os.mkdir("indexdir")
    
    schema = Schema(id=ID(stored=True), name=TEXT(stored=True), description=TEXT)
    ix = create_in("indexdir", schema)
    writer = ix.writer()

    # Assuming you have a function to get all parts
    parts = get_all_parts()  # This should return all parts from your database
    for part in parts:
        print(part, part.id, part.name, part.description)
        writer.add_document(id=str(part.id), name=part.name, description=part.description)
    
    writer.commit()

# Call this function to create the index

with app.app_context():
  create_search_index()