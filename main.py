import os
import time
from flask import Flask, render_template, request, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
import re
import random
from config import ProductionConfig  # Or whichever config you want to use
from models import Part


from kittycad.api.ai import create_text_to_cad, get_text_to_cad_model_for_user
from kittycad.client import ClientFromEnv
from kittycad.models.api_call_status import ApiCallStatus
from kittycad.models.file_export_format import FileExportFormat
from kittycad.models.text_to_cad_create_body import TextToCadCreateBody

from whoosh.fields import Schema, TEXT, ID
from whoosh.index import create_in, open_dir
from whoosh.qparser import MultifieldParser, OrGroup
from whoosh.qparser import FuzzyTermPlugin, WildcardPlugin, PhrasePlugin

from extensions import db
from database import createPart

# Create our client.
token = os.environ["KITTYCAD_API_TOKEN"]

client = ClientFromEnv(token=token, timeout=30, verify_ssl=True)

app = Flask('app')
app.config.from_object(ProductionConfig)

db.init_app(app)

class ModelInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_prompt = db.Column(db.String(120), unique=True, nullable=False)
    file_name = db.Column(db.String(120), unique=True, nullable=False)
    status = db.Column(db.String(20), nullable=False)

    def __repr__(self):
        return f'<ModelInfo {self.user_prompt}>'



@app.route('/')
def index():
  return render_template('index.html')

def getSimilarItems(image, prompt):
    print("get similar stuff")

# with app.app_context():
#   createPart("motor handle", "The fire control system includes a fire control radar with search and tracking capability, a radar electro-optical (REO) display, and a head-up display (RUD). A stores management system (SMS) presents a control panel and visual display for inventory, control, and release of all stores. Basic armament includes afuselage-mounted multibarrel 20 mm gun and anai -to-air missile on each wingtip. Additional stores of various types can be carried on pylons mounted under the wings and on the fuselage centerline. ", None, None)


@app.route('/submit', methods=['POST'])
def submit():
  user_prompt = request.form['prompt']
  print("received new api call with", user_prompt)
  clean_prompt = re.sub(r'\W+', '', user_prompt)  # Remove all non-word characters
  random_numbers = ''.join(random.choices('0123456789', k=5))  # Generate 5 random numbers
  file_name = f"{clean_prompt}_{random_numbers}.stl"  # Append random numbers to the cleaned prompt
  # Prompt the API to generate a 3D model from text.
  response = create_text_to_cad.sync(
      client=client,
      output_format=FileExportFormat.STL,
      body=TextToCadCreateBody(prompt=user_prompt, ),
  )

  # Polling to check if the task is complete
  while response.completed_at is None:
    # Wait for 5 seconds before checking again
    time.sleep(5)

    # Check the status of the task
    response = get_text_to_cad_model_for_user.sync(
        client=client,
        id=response.id,
    )

  if response.status == ApiCallStatus.FAILED:
    # Print out the error message
    print(f"Text-to-CAD failed: {response.error}")

  elif response.status == ApiCallStatus.COMPLETED:
    # Print out the names of the generated files
    print(f"Text-to-CAD completed and returned {len(response.outputs)} files:")
    for name in response.outputs:
      print(f"  * {name}")

    final_result = response.outputs["source.stl"]
    with open(file_name, "w", encoding="utf-8") as output_file:
      output_file.write(final_result.get_decoded().decode("utf-8"))
      print(f"Saved output to {output_file.name}")

  # Assuming the rest of the code remains the same, including the file saving part
  # After saving the file, return the file name to the client
  return jsonify({'fileName': file_name})


@app.route('/download/<filename>')
def download_file(filename):
  return send_from_directory(directory=".", path=filename, as_attachment=True)


@app.route('/parts', methods=['GET'])
def get_parts():
   parts = Part.query.with_entities(Part.id, Part.name, Part.description, Part.img_filename, Part.stl_filename).all()
   return jsonify([{'id': part.id, 'name': part.name, 'description': part.description, 'img_filename': part.img_filename, 'stl_filename': part.stl_filename} for part in parts])


@app.route('/parts/<int:part_id>', methods=['GET'])
def get_part(part_id):
    part = Part.query.get(part_id)
    if part:
        return jsonify({'id': part.id, 'name': part.name, 'description': part.description})
    return jsonify({'error': 'Part not found'}), 404


from whoosh.qparser import QueryParser
from whoosh.index import open_dir

def search_parts(query_str):
  ix = open_dir("indexdir")
  search_results = []  # Initialize an empty list to hold the results
  with ix.searcher() as searcher:
    # Enhance the parser with plugins for fuzzy, wildcard, and phrase searches
    parser = MultifieldParser(["name", "description"], schema=ix.schema, group=OrGroup)
    parser.add_plugin(FuzzyTermPlugin())
    parser.add_plugin(WildcardPlugin())
    parser.add_plugin(PhrasePlugin())

    # Example query that uses fuzzy search, wildcards, and phrase search
    # Adjust the query according to your needs
   # query_str = 'fire control~2 OR "exact phrase" OR F-16*'
    query = parser.parse(query_str)

    # Execute the search
    results = searcher.search(query, limit=None)
    return results 


@app.route('/search')
def search():
    query_str = request.args.get('query')
    print(f"Received search query: {query_str}")
    results = search_parts(query_str)
    # Convert results to a list of dictionaries with 'name' and 'description'
    results_json = [{'name': result["name"], 'description': result["description"]} for result in results]
    return jsonify(results_json)


app.run(host='0.0.0.0', port=8080)
