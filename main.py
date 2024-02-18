import os
import time
from flask import Flask, render_template, request, send_from_directory, jsonify

from kittycad.api.ai import create_text_to_cad, get_text_to_cad_model_for_user
from kittycad.client import ClientFromEnv
from kittycad.models.api_call_status import ApiCallStatus
from kittycad.models.file_export_format import FileExportFormat
from kittycad.models.text_to_cad_create_body import TextToCadCreateBody

# Create our client.
token = os.environ["KITTYCAD_API_TOKEN"]

client = ClientFromEnv(token=token, timeout=30, verify_ssl=True)

app = Flask('app')


@app.route('/')
def index():
  return render_template('index.html')


@app.route('/submit', methods=['POST'])
def submit():
  user_prompt = request.form['prompt']
  print("received new api call with", user_prompt)
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

    # Save the STEP data as text-to-cad-output.step
    final_result = response.outputs["source.step"]
    with open("text-to-cad-output.step", "w", encoding="utf-8") as output_file:
      output_file.write(final_result.get_decoded().decode("utf-8"))
      print(f"Saved output to {output_file.name}")
  # Ensure you save the output file with a unique name, e.g., using a UUID
  file_name = "unique_output_file_name_here.stl"  # Use actual logic to generate unique file names

  # Assuming the rest of the code remains the same, including the file saving part
  # After saving the file, return the file name to the client
  return jsonify({'fileName': file_name})


@app.route('/download/<filename>')
def download_file(filename):
  return send_from_directory(directory=".", path=filename, as_attachment=True)


app.run(host='0.0.0.0', port=8080)
