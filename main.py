import os
import time
from flask import Flask, render_template, request, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
import re
import random
from config import ProductionConfig  # Or whichever config you want to use
from models import Part
#import pandas as pd
import requests

from kittycad.api.ai import create_text_to_cad, get_text_to_cad_model_for_user
from kittycad.client import ClientFromEnv
from kittycad.models.api_call_status import ApiCallStatus
from kittycad.models.file_export_format import FileExportFormat
from kittycad.models.text_to_cad_create_body import TextToCadCreateBody

from whoosh.fields import Schema, TEXT, ID
from whoosh.index import create_in, open_dir
from whoosh.qparser import FuzzyTermPlugin, WildcardPlugin, PhrasePlugin, PrefixPlugin, MultifieldParser, OrGroup

from extensions import db
from database import createPart, createOrUpdatePart, deletePart

# Create our client.
# token = os.environ["KITTYCAD_API_TOKEN"]

# client = ClientFromEnv(token=token, timeout=30, verify_ssl=True)

app = Flask('app')
app.config.from_object(ProductionConfig)
app.config['OCTOPRINT_API_KEY'] = 'F789415192EB43EE97C6029CD46FDCB1'
app.config['OCTOPRINT_URL'] = 'http://localhost'

db.init_app(app)

class ModelInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_prompt = db.Column(db.String(120), unique=True, nullable=False)
    file_name = db.Column(db.String(120), unique=True, nullable=False)
    status = db.Column(db.String(20), nullable=False)

    def __repr__(self):
        return f'<ModelInfo {self.user_prompt}>'


def format_part_info(part):
    """
    Formats a single part's information, handling potentially missing properties.

    :param part: A Part object or a dictionary containing part information.
    :return: A dictionary with the part's information, with defaults for missing properties.
    """
    # If part is a model instance, convert to dictionary, else assume it's already a dictionary
    part_info = {
        'id': getattr(part, 'id', 'N/A'),
        'name': getattr(part, 'name', 'N/A'),
        'description': getattr(part, 'description', 'N/A'),
        'img_filename': getattr(part, 'img_filename', 'N/A'),
        'stl_filename': getattr(part, 'stl_filename', 'N/A')
    } if not isinstance(part, dict) else part

    return part_info

def jsonify_parts(parts):
    """
    Converts a list of parts into a JSON-friendly format, using format_part_info for each part.

    :param parts: A list of Part objects or dictionaries containing part information.
    :return: A JSON response containing the parts information.
    """
    parts_list = [format_part_info(part) for part in parts]
    return jsonify(parts_list)

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
  return send_from_directory(directory="./print", path=filename, as_attachment=True)


@app.route('/parts', methods=['GET'])
def get_parts():
   parts = Part.query.with_entities(Part.id, Part.name, Part.description, Part.img_filename, Part.stl_filename).all()
   return jsonify_parts(parts)


@app.route('/parts/<int:part_id>', methods=['GET'])
def get_part(part_id):
    part = Part.query.get(part_id)
    if part:
        part_info = format_part_info(part)
        return jsonify(part_info)
    return jsonify({'error': 'Part not found'}), 404


from whoosh.qparser import QueryParser
from whoosh.index import open_dir

def search_parts(query_str):
  ix = open_dir("indexdir")
  search_results = []  # Initialize an empty list to hold the results

  with ix.searcher() as searcher:
      parser = MultifieldParser(["name", "description"], schema=ix.schema, group=OrGroup)
      parser.add_plugin(FuzzyTermPlugin())
      parser.add_plugin(WildcardPlugin())
      parser.add_plugin(PhrasePlugin())
      parser.add_plugin(PrefixPlugin()) 


      query = parser.parse(query_str+"*")
    # TODO: improve query
      results = searcher.search(query, limit=None)

      # Extract necessary data within the context manager
      for result in results:
          print(result)
          # Make sure to call .fields() to get a dictionary of the stored fields
          result_data = result.fields()
          search_results.append(format_part_info(result_data))

  # Now search_results contains all the data needed, and can be used outside the context manager
  return search_results


@app.route('/search')
def search():
    query_str = request.args.get('query')
    print(f"Received search query: {query_str}")
    results = search_parts(query_str)
    # Convert results to a list of dictionaries with 'name' and 'description'
    return jsonify_parts(results)


# @app.route('/upload_csv', methods=['POST'])
# def upload_csv():
#     if 'csv_file' not in request.files:
#         return jsonify({'error': 'No file part'}), 400
#     file = request.files['csv_file']
#     if file.filename == '':
#         return jsonify({'error': 'No selected file'}), 400
#     if file and file.filename.endswith('.csv'):
#         df = pd.read_csv(file, keep_default_na=False)  # keep_default_na=False prevents pandas from converting empty strings to NaN
#         for _, row in df.iterrows():
#             # Use .get() with a default of None for optional columns
#             createOrUpdatePart(
#                 name=row.get('name'),
#                 description=row.get('description', None),
#                 img_filename=row.get('img_filename', None),
#                 stl_filename=row.get('stl_filename', None)
#             )
#         return jsonify({'message': 'CSV processed successfully'}), 200
#     else:
#         return jsonify({'error': 'Invalid file format'}), 400

@app.route('/parts/delete/<int:part_id>', methods=['POST'])
def delete_part(part_id):
    if deletePart(part_id):
        return jsonify({'message': 'Part deleted successfully'}), 200
    else:
        return jsonify({'error': 'Part not found'}), 404

@app.route('/images/<filename>')
def serve_image(filename):
    return send_from_directory('images', filename)

@app.route('/print/<gcode_path>')
def print_gcode(gcode_path):
    disk_gcode_path = 'print/' + gcode_path
    files = {'file': open(disk_gcode_path, 'rb')}

    headers = {'X-Api-Key': app.config['OCTOPRINT_API_KEY']}

    response = requests.post(f'{app.config["OCTOPRINT_URL"]}/api/files/local', files=files, headers=headers)

    if response.status_code == 201:  # http 201 is 'created'
        print('File created')

    payload = {'command': 'select', 'print': True}
    headers = {'Content-Type': 'application/json', 'X-Api-Key': app.config['OCTOPRINT_API_KEY']}
    response = requests.post(f'{app.config["OCTOPRINT_URL"]}/api/files/local/{gcode_path}', json=payload, headers=headers)

    print('\n\n\n\n\n', response.status_code, '\n\n\n\n\n')

    if response.status_code == 204:
        print('Print job started successfully')
        return 'done', 200
    else:
        print('Error starting print job:', response.text)
        return 'error', 500





app.run(host='0.0.0.0', port=8080)
