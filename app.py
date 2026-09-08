from flask import Flask, render_template, request, jsonify
from retrieval import answer_question
import os
from werkzeug.utils import secure_filename
from ingest import process_one_file
from config import chunk_collection

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    question = request.json["question"]
    return answer_question(question)

@app.route("/upload", methods=["POST"])
def upload():
    folder_name = request.form["folder_name"]
    document = request.files["document"]
    secure_name = secure_filename(document.filename)
    temp_dir = "upload_temp"
    os.makedirs(temp_dir, exist_ok=True)
    saved_path = os.path.join(temp_dir, secure_name)
    document.save(saved_path)
    process_file =process_one_file(saved_path, folder_name)
    if process_file["status"] == "stored":
        return "File successfully uploaded and processed."
    elif process_file["status"] == "storage_error":
        return f"Error adding chunks to the collection: {secure_name} document file is now empty. Try again and alert Admin if the issue persists."
    elif process_file["status"] == "deletion_error":
        return f"Error deleting existing chunks for document {secure_name}: the existing version is still intact; safe to retry."
    elif process_file["status"] == "embedding_error":
        return f"Error embedding chunks for document {secure_name}: the process failed; check the document content and try again."
    else:
        return "Failed to process the uploaded file."

@app.route("/check-exists", methods=["POST"])
def checkExists():
    folder = request.json["folder_name"]
    filename = request.json["file_name"]
    secure_name = secure_filename(filename)
    doc_id = folder + "/" + secure_name
    check_id = chunk_collection.get(where={"doc_id": doc_id})
    exists = len(check_id["ids"]) > 0
    return jsonify({"exists": exists})




if __name__ == "__main__":
    app.run(debug=True)