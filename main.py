import os
import base64

from typing import Any, List, Optional, Tuple, Union

from flask import Flask, render_template

from kittycad.api.ai import create_text_to_cad
from kittycad.client import ClientFromEnv
from kittycad.models.error import Error
from kittycad.models.file_export_format import FileExportFormat
from kittycad.models.text_to_cad import TextToCad
from kittycad.models.text_to_cad_create_body import TextToCadCreateBody
from kittycad.types import Response




def example_create_text_to_cad():
    # Create our client.
    token = os.environ["KITTYCAD_API_TOKEN"]
  
    client = ClientFromEnv(token=token, timeout=30, verify_ssl=True)

    result: Optional[Union[TextToCad, Error]] = create_text_to_cad.sync(
        client=client,
        output_format=FileExportFormat.STL,
        body=TextToCadCreateBody(
            prompt="pitot tube for an F16",
        ),
    )

    if isinstance(result, Error) or result == None:
        print(result)
        raise Exception("Error in response")

    body: TextToCad = result
    print(body)


def example_create_text_to_cad():
    # Create our client.
    token = os.environ["KITTYCAD_API_TOKEN"]
  
    client = ClientFromEnv(token=token, timeout=30, verify_ssl=True)

    result: Optional[Union[TextToCad, Error]] = create_text_to_cad.sync(
        client=client,
        output_format=FileExportFormat.STL,
        body=TextToCadCreateBody(
            prompt="pitot tube for an F16",
        ),
    )

    if isinstance(result, Error) or result == None:
        print(result)
        raise Exception("Error in response")

    body: TextToCad = result

    # Ensure the /files directory exists
    os.makedirs('files', exist_ok=True)

    # Assuming the output is in 'outputs' attribute and is a base64 encoded string
    for file_path, content in body.outputs.items():
        # Decode the base64 content
        file_content = base64.b64decode(content)
        # Write the decoded content to a file in the /files directory
        with open(f'files/{file_path}', 'wb') as file:
            file.write(file_content)

    print(f"File saved in /files/{file_path}")

example_create_text_to_cad()

app = Flask('app')

@app.route('/')
def hello_world():
  return 'Hello, World!'

app.run(host='0.0.0.0', port=8080)
