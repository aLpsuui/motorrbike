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

# ── Sticker definitions (used for prompt building) ─────────────────────────
STICKER_PROMPTS = {
    "flames":        "aggressive fire flames graphic along the tank and fairing",
    "racing_stripes":"bold racing stripes running the full length of the bike",
    "skull":         "skull and crossbones graphic on the tank",
    "tribal":        "tribal tattoo-style pattern wrapping the fairing and tank",
    "lightning":     "electric lightning bolt graphics across the body panels",
    "checkered":     "checkered flag pattern on the fairing edges",
    "japanese":      "Japanese kanji and cherry blossom decals on the tank",
    "carbon":        "carbon fiber texture pattern overlay on all body panels",
    "graffiti":      "urban graffiti-style street art lettering on the fairing",
    "wings":         "eagle wings spread graphic across both sides of the fairing",
}


# ── Helpers ────────────────────────────────────────────────────────────────
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def encode_image_to_base64(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def detect_motorbike(image_path):
    base64_image = encode_image_to_base64(image_path)
    ext = image_path.rsplit(".", 1)[1].lower()
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{base64_image}"}},
                {"type": "text", "text": (
                    "Does this image contain a motorbike, motorcycle, scooter, "
                    "or similar two-wheeled motor vehicle? Reply with ONLY 'YES' or 'NO'."
                )},
            ],
        }],
        max_tokens=5,
    )

    answer = response.choices[0].message.content.strip().upper()
    if answer.startswith("YES"):
        return True, "Motorbike detected ✓"
    return False, "No motorbike detected in this photo."


def build_prompt(color_name, color_hex, sticker_keys):
    """Build the AI prompt combining color + selected stickers."""
    parts = []

    # Color part
    if color_name and color_name != "none":
        parts.append(
            f"Repaint the motorbike body panels, tank, and fairing to {color_name} ({color_hex})."
        )

    # Stickers part
    if sticker_keys:
        sticker_descriptions = [
            STICKER_PROMPTS[k] for k in sticker_keys if k in STICKER_PROMPTS
        ]
        if sticker_descriptions:
            joined = "; ".join(sticker_descriptions)
            parts.append(
                f"Also apply the following sticker graphics over the full bike body: {joined}."
            )

    parts.append(
        "Keep the background, rider, road, and all non-motorbike elements exactly the same. "
        "Maintain realistic lighting, reflections, and metallic sheen. "
        "The result should look like a professional product photo."
    )

    return " ".join(parts)


def apply_customization(image_path, color_name, color_hex, sticker_keys):
    prompt = build_prompt(color_name, color_hex, sticker_keys)

    with open(image_path, "rb") as image_file:
        response = client.images.edit(
            model="gpt-image-1",
            image=image_file,
            prompt=prompt,
            n=1,
            size="1024x1024",
        )

    return response.data[0].b64_json


# ── Routes ─────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


def _process_request(file, color_name, color_hex, sticker_keys):
    """Shared logic for both /change-color and /change-color-anyway."""
    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed. Use PNG, JPG, or WEBP."}), 400

    filename = secure_filename(file.filename)
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(save_path)

    try:
        result_base64 = apply_customization(save_path, color_name, color_hex, sticker_keys)
        return jsonify({
            "success": True,
            "image_base64": result_base64,
            "color_name": color_name,
            "stickers": sticker_keys,
        })
    except Exception as e:
        return jsonify({"error": f"Something went wrong: {str(e)}"}), 500
    finally:
        if os.path.exists(save_path):
            os.remove(save_path)


@app.route("/change-color", methods=["POST"])
def change_color():
    if "photo" not in request.files:
        return jsonify({"error": "No photo uploaded."}), 400

    file = request.files["photo"]
    color_name  = request.form.get("color_name", "none")
    color_hex   = request.form.get("color_hex", "")
    sticker_keys = request.form.getlist("stickers")  # multi-value list

    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed. Use PNG, JPG, or WEBP."}), 400

    filename  = secure_filename(file.filename)
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(save_path)

    try:
        # Detect motorbike
        is_moto, detection_msg = detect_motorbike(save_path)

        if not is_moto:
            return jsonify({
                "warning": True,
                "message": (
                    "⚠️ We couldn't detect a motorbike in your photo. "
                    "You can still try, but results may vary."
                ),
                "detection_msg": detection_msg,
            })

        result_base64 = apply_customization(save_path, color_name, color_hex, sticker_keys)
        return jsonify({
            "success": True,
            "image_base64": result_base64,
            "color_name": color_name,
            "stickers": sticker_keys,
            "detection_msg": detection_msg,
        })

    except Exception as e:
        return jsonify({"error": f"Something went wrong: {str(e)}"}), 500
    finally:
        if os.path.exists(save_path):
            os.remove(save_path)


@app.route("/change-color-anyway", methods=["POST"])
def change_color_anyway():
    if "photo" not in request.files:
        return jsonify({"error": "No photo uploaded."}), 400

    file         = request.files["photo"]
    color_name   = request.form.get("color_name", "none")
    color_hex    = request.form.get("color_hex", "")
    sticker_keys = request.form.getlist("stickers")

    return _process_request(file, color_name, color_hex, sticker_keys)


# ── Entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
