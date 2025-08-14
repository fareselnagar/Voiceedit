
import os
import uuid
from flask import Flask, request, render_template, send_file, jsonify
from werkzeug.utils import secure_filename
from audio_processor import process_file, list_presets

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
ALLOWED_EXT = {"wav","mp3","ogg","flac","m4a","aac"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB

def allowed_file(filename):
    return "." in filename and filename.rsplit(".",1)[1].lower() in ALLOWED_EXT

@app.route("/")
def index():
    presets = list_presets()
    return render_template("index.html", presets=presets)

@app.route("/process", methods=["POST"])
def process():
    if 'file' not in request.files:
        return jsonify({"error":"no file part"}), 400
    file = request.files['file']
    preset = request.form.get("preset","master_auto")
    if file.filename == "":
        return jsonify({"error":"no selected file"}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique = uuid.uuid4().hex[:8]
        in_path = os.path.join(app.config['UPLOAD_FOLDER'], unique + "_" + filename)
        file.save(in_path)
        out_filename = os.path.splitext(filename)[0] + "_processed.wav"
        out_path = os.path.join(app.config['OUTPUT_FOLDER'], unique + "_" + out_filename)
        try:
            processed = process_file(in_path, out_path, preset=preset)
            return jsonify({"status":"done", "output": os.path.basename(processed)})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"error":"invalid file"}), 400

@app.route("/download/<path:filename>")
def download(filename):
    path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    if os.path.exists(path):
        return send_file(path, as_attachment=True)
    return "Not found", 404

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
