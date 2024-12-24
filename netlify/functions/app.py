import os
import csv
import requests
from io import BytesIO
from flask import Flask, request, jsonify
from PIL import Image
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import flask_lambda

# Initialize Flask app with Flask-Lambda support
app = Flask(__name__)
app = flask_lambda.Flask(app)

# Set up Azure credentials and endpoint
endpoint = "https://docintelaipoc.cognitiveservices.azure.com/"
api_key = "13aDp7dBirv1gKuLxTYZ3v2dn7AORCILO3Xw80tWFZ0s4At8aGiEJQQJ99ALACYeBjFXJ3w3AAALACOG9hSN"
client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(api_key))

# Function to extract text and other information from PDF
def extract_pdf_content(file):
    # Use the prebuilt-document model to analyze the document
    poller = client.begin_analyze_document("prebuilt-document", file)
    result = poller.result()

    text = ""
    tables = []
    images = []

    # Extract text
    for page_num, page in enumerate(result.pages):
        text += f"--- Page {page_num + 1} ---\n"
        for line in page.lines:
            text += line.content + "\n"

    # Extract tables
    for page_num, page in enumerate(result.pages):
        if hasattr(page, 'tables'):
            for table in page.tables:
                table_data = []
                for row in table.rows:
                    row_data = [cell.content for cell in row.cells]
                    table_data.append(row_data)
                tables.append({"page": page_num + 1, "table": table_data})

    # Extract images
    for page_num, page in enumerate(result.pages):
        if hasattr(page, 'images') and page.images:
            for i, image in enumerate(page.images):
                image_url = image.content
                image_data = requests.get(image_url).content
                img = Image.open(BytesIO(image_data))
                img_path = f"extracted_image_page_{page_num + 1}_image_{i + 1}.png"
                img.save(img_path)
                images.append(img_path)

    return {
        "text": text,
        "tables": tables,
        "images": images
    }

# API Endpoint to upload PDF and get extracted content
@app.route('/extract', methods=['POST'])
def extract_content():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    result = extract_pdf_content(file)

    # Return extracted text, tables, and images as a response
    return jsonify({
        "text": result["text"],
        "tables": result["tables"],
        "images": result["images"]
    })

if __name__ == '__main__':
    app.run(debug=True)
