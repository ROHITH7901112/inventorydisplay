import os
import uuid
import numpy as np
import cv2
from PIL import Image
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from models import db, Saree

ALLOWED_EXT = {"png", "jpg", "jpeg", "gif"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def create_app():
    app = Flask(__name__)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    app.config["SECRET_KEY"] = "change-this-secret"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "sarees.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

    db.init_app(app)
    with app.app_context():
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        db.create_all()

    # Home page – show all sarees
    @app.route("/")
    def index():
        sarees = Saree.query.order_by(Saree.created_at.desc()).all()
        results = []
        for s in sarees:
            folder = os.path.join(app.config["UPLOAD_FOLDER"], s.saree_id)
            images = []
            if os.path.isdir(folder):
                for fn in sorted(os.listdir(folder)):
                    if fn.lower().endswith(tuple(ALLOWED_EXT)):
                        images.append(fn)
            results.append({"saree_id": s.saree_id, "images": images})
        return render_template("index.html", sarees=results)

    # Add new saree page
    @app.route("/add", methods=["GET", "POST"])
    def add_saree():
        if request.method == "POST":
            saree_id = request.form.get("saree_id", "").strip()
            if not saree_id:
                flash("Please provide or scan a Saree ID first.", "danger")
                return redirect(url_for("add_saree"))

            # Save to DB if not existing
            existing = Saree.query.filter_by(saree_id=saree_id).first()
            if not existing:
                saree = Saree(saree_id=saree_id)
                db.session.add(saree)
                db.session.commit()

            # Save uploaded images
            folder = os.path.join(app.config["UPLOAD_FOLDER"], saree_id)
            os.makedirs(folder, exist_ok=True)
            files = request.files.getlist("images")
            for f in files:
                if f and allowed_file(f.filename):
                    filename = f"{uuid.uuid4().hex}_{secure_filename(f.filename)}"
                    f.save(os.path.join(folder, filename))

            flash(f"Saree '{saree_id}' added successfully.", "success")
            return redirect(url_for("index"))

        return render_template("add_saree.html")

    # QR decoding endpoint (using OpenCV)
    @app.route("/decode-qr", methods=["POST"])
    def decode_qr():
        if 'qr_image' not in request.files:
            return jsonify({"ok": False, "error": "No file part 'qr_image'"}), 400

        f = request.files['qr_image']
        if f.filename == '':
            return jsonify({"ok": False, "error": "No selected file"}), 400

        try:
            # Open image with Pillow
            img = Image.open(f.stream).convert("RGB")
            # Convert to OpenCV format
            arr = np.array(img)
            frame = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

            # Detect and decode QR
            detector = cv2.QRCodeDetector()
            data, points, _ = detector.detectAndDecode(frame)
            if data:
                return jsonify({"ok": True, "results": [data]})
            else:
                return jsonify({"ok": False, "error": "No QR code found"}), 200
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/uploads/<saree_id>/<filename>")
    def uploaded_file(saree_id, filename):
        return send_from_directory(os.path.join(app.config["UPLOAD_FOLDER"], saree_id), filename)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="localhost", port=5000)
