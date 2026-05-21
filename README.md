# 🏍️ MotoChroma — AI Motorbike Color Changer

Change the color of any motorbike photo using AI (OpenAI GPT-Image-1).

---

## What It Does

1. **Upload** a motorbike photo (PNG, JPG, or WEBP)
2. **Detect** — GPT-4o-mini checks if there's actually a motorbike in the image
3. **Recolor** — GPT-Image-1 repaints the bike body in your chosen color
4. **Download** your result as a PNG

---

## Setup (Step-by-Step)

### 1. Get an OpenAI API Key
- Go to https://platform.openai.com/api-keys
- Create a new secret key and copy it

### 2. Install Python dependencies
```bash
cd moto-color-changer
pip install -r requirements.txt
```

### 3. Set your API key

**Mac/Linux:**
```bash
export OPENAI_API_KEY="sk-..."
```

**Windows (Command Prompt):**
```cmd
set OPENAI_API_KEY=sk-...
```

**Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY="sk-..."
```

### 4. Run the app
```bash
python app.py
```

### 5. Open in browser
Visit: **http://localhost:5000**

---

## Project Structure

```
moto-color-changer/
├── app.py               ← Flask backend (all the AI logic)
├── requirements.txt     ← Python packages needed
├── README.md            ← This file
├── static/
│   └── uploads/         ← Temp folder (auto-created, auto-cleaned)
└── templates/
    └── index.html       ← The web UI
```

---

## How the AI Works

| Step | Model | What it does |
|------|-------|--------------|
| Detection | `gpt-4o-mini` (vision) | Looks at your photo and answers YES/NO: is there a motorbike? |
| Recoloring | `gpt-image-1` (image edit) | Takes your photo + a prompt, repaints the bike body panels |

The prompt sent to GPT-Image-1 instructs it to:
- Change only the bike body (tank, fairing, panels)
- Keep the background untouched
- Maintain realistic lighting and metallic reflections

---

## Tips for Best Results

- Use photos where the **motorbike is the main subject**
- **Side or 3/4 angle** shots work better than top-down views
- Good **lighting** in the original = better AI results
- Avoid photos with heavy blur or very dark conditions

---

## Costs

Each color change uses:
- 1× GPT-4o-mini call (detection) — very cheap (~$0.001)
- 1× GPT-Image-1 edit (1024×1024) — check OpenAI pricing page

---

## Troubleshooting

**"No motorbike detected" warning**
→ The AI wasn't confident there's a bike. You can still click "Proceed anyway".

**"Something went wrong" error**
→ Check your API key is set correctly and has billing enabled.

**Image looks weird**
→ Try a cleaner photo with better lighting. Complex backgrounds can confuse the model.
