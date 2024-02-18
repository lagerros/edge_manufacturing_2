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

from database import createPart, db 

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
    
    
    
   # createPart("sample gear", "The F-16A is a single-engine, single-seat, multirole tactical fighter with full air-to-air and air-to-surface combat capabilities. The F-16B is a two-seat (tandem) version and performs the secondary role of a trainer. The fuselage is characterized by a large bubble canopy, forebody strakes, and an under fuselage engine air inlet. The wing and tail surfaces are thin and feature moderate aft sweep. The wing has automatic leading edge flaps which enhance performance over a wide speed range. Flaperons are mounted on the trailing edge of the wing and combine the functions of flaps and ailerons. The horizontal tails have a small negative", None, None)

@app.route('/')
def index():
  return render_template('index.html')


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
   parts = Part.query.with_entities(Part.id, Part.name).all()
   return jsonify([{'id': part.id, 'name': part.name} for part in parts])

@app.route('/parts/<int:part_id>', methods=['GET'])
def get_part(part_id):
    part = Part.query.get(part_id)
    if part:
        return jsonify({'id': part.id, 'name': part.name, 'description': part.description})
    return jsonify({'error': 'Part not found'}), 404


app.run(host='0.0.0.0', port=8080)
