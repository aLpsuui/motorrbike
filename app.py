import os
import base64
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from openai import OpenAI

# ── App setup ──────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "static/uploads"
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB max upload

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "YOUR_API_KEY_HERE")
client = OpenAI(api_key=OPENAI_API_KEY)


# ── Helpers ────────────────────────────────────────────────────────────────
def allowed_file(filename):
    """Return True if the file extension is in the allowed list."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def encode_image_to_base64(image_path):
    """Read an image from disk and return a base64 string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def detect_motorbike(image_path):
    """
    Use GPT-4o-mini vision to check whether a motorbike is visible.
    Returns (is_motorbike: bool, message: str).
    """
    base64_image = encode_image_to_base64(image_path)
    ext = image_path.rsplit(".", 1)[1].lower()
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{base64_image}"},
                    },
                    {
                        "type": "text",
                        "text": (
                            "Does this image contain a motorbike, motorcycle, scooter, "
                            "or similar two-wheeled motor vehicle? "
                            "Reply with ONLY 'YES' or 'NO'."
                        ),
                    },
                ],
            }
        ],
        max_tokens=5,
    )

    answer = response.choices[0].message.content.strip().upper()
    if answer.startswith("YES"):
        return True, "Motorbike detected ✓"
    return False, "No motorbike detected in this photo."


def change_motorbike_color(image_path, color_name, color_hex):
    """
    Send the image to gpt-image-1 with an edit prompt to repaint the motorbike.
    Returns a URL to the generated image.
    """
    prompt = (
        f"Change the color of the motorbike in this image to {color_name} ({color_hex}). "
        "Repaint only the motorbike body panels, tank, and fairing with this new color. "
        "Keep the background, rider, road, and all non-motorbike elements exactly the same. "
        "Maintain realistic lighting, reflections, and metallic sheen. "
        "The result should look like a professional product photo."
    )

    with open(image_path, "rb") as image_file:
        response = client.images.edit(
            model="gpt-image-1",
            image=image_file,
            prompt=prompt,
            n=1,
            size="1024x1024",
        )

    # gpt-image-1 returns base64 by default
    image_base64 = response.data[0].b64_json
    return image_base64


# ── Routes ─────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/change-color", methods=["POST"])
def change_color():
    # ── 1. Validate file upload ──────────────────────────────────────────
    if "photo" not in request.files:
        return jsonify({"error": "No photo uploaded."}), 400

    file = request.files["photo"]
    color_name = request.form.get("color_name", "red")
    color_hex = request.form.get("color_hex", "#FF0000")

    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed. Use PNG, JPG, or WEBP."}), 400

    # ── 2. Save file ─────────────────────────────────────────────────────
    filename = secure_filename(file.filename)
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(save_path)

    try:
        # ── 3. Detect motorbike ──────────────────────────────────────────
        is_moto, detection_msg = detect_motorbike(save_path)

        if not is_moto:
            return jsonify({
                "warning": True,
                "message": (
                    "⚠️ We couldn't detect a motorbike in your photo. "
                    "You can still try the color change, but results may vary."
                ),
                "detection_msg": detection_msg,
            })

        # ── 4. Change color ──────────────────────────────────────────────
        result_base64 = change_motorbike_color(save_path, color_name, color_hex)

        return jsonify({
            "success": True,
            "image_base64": result_base64,
            "color_name": color_name,
            "detection_msg": detection_msg,
        })

    except Exception as e:
        return jsonify({"error": f"Something went wrong: {str(e)}"}), 500

    finally:
        # Clean up uploaded file
        if os.path.exists(save_path):
            os.remove(save_path)


@app.route("/change-color-anyway", methods=["POST"])
def change_color_anyway():
    """Called when user ignores the no-motorbike warning and proceeds."""
    if "photo" not in request.files:
        return jsonify({"error": "No photo uploaded."}), 400

    file = request.files["photo"]
    color_name = request.form.get("color_name", "red")
    color_hex = request.form.get("color_hex", "#FF0000")

    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed."}), 400

    filename = secure_filename(file.filename)
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(save_path)

    try:
        result_base64 = change_motorbike_color(save_path, color_name, color_hex)
        return jsonify({
            "success": True,
            "image_base64": result_base64,
            "color_name": color_name,
        })
    except Exception as e:
        return jsonify({"error": f"Something went wrong: {str(e)}"}), 500
    finally:
        if os.path.exists(save_path):
            os.remove(save_path)


# ── Entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    app.run(debug=True)
