# ====== PulseGuard — Fixed final code ======

import io
import time
import random
import qrcode
import os
from difflib import get_close_matches
import gradio as gr
from PIL import Image

# Optional transformers support
try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except Exception:
    pipeline = None
    TRANSFORMERS_AVAILABLE = False


# -----------------------------
# Local Medicine DB
# -----------------------------
MED_DB = {
    "Dolo 650": {
        "dosage": "650 mg every 6-8 hours (max 4 tablets / 24 hrs)",
        "indications": ["fever", "pain", "headache"],
        "contraindications": ["severe liver disease", "alcoholism"],
        "side_effects": ["nausea", "stomach upset", "liver damage if overdosed"],
        "usage": "Analgesic & antipyretic (symptomatic relief)",
        "alternative": "Paracetamol 500 mg",
        "note": "Take after meals; avoid alcohol"
    },
    "Paracetamol 500": {
        "dosage": "500 mg every 6-8 hours (max 4 tablets / 24 hrs)",
        "indications": ["fever", "pain", "headache"],
        "contraindications": ["severe liver disease", "alcoholism"],
        "side_effects": ["rare allergic reaction", "liver damage if overdosed"],
        "usage": "Analgesic & antipyretic",
        "alternative": "Dolo 650",
        "note": "Safe at recommended doses; avoid alcohol"
    },
    "Ibuprofen 400": {
        "dosage": "200-400 mg every 4-6 hours (max 1200 mg OTC/day)",
        "indications": ["inflammation", "pain", "fever"],
        "contraindications": ["peptic ulcer", "severe kidney disease", "aspirin allergy"],
        "side_effects": ["stomach upset", "GI bleeding (rare)", "kidney risk"],
        "usage": "Anti-inflammatory & analgesic; take with food",
        "alternative": "Paracetamol",
        "note": "Avoid if kidney disease or active GI bleeding"
    }
}

LOWER_KEY_MAP = {k.lower(): k for k in MED_DB.keys()}


def best_med_match(user_med: str, cutoff=0.6):
    if not user_med:
        return None
    q = user_med.strip().lower()
    matches = get_close_matches(q, list(LOWER_KEY_MAP.keys()), n=1, cutoff=cutoff)
    return LOWER_KEY_MAP[matches[0]] if matches else None


def check_med_suitability(med_key, health_conditions, disease):

    entry = MED_DB[med_key]

    contraindications = [c.lower() for c in entry["contraindications"]]
    disease_ok = disease.lower() in entry["indications"] if disease else False

    reasons = []

    for hc in health_conditions:
        for contra in contraindications:
            if contra in hc.lower():
                reasons.append(contra)

    return {
        "is_suitable": len(reasons) == 0,
        "treats_disease": disease_ok,
        "reasons": reasons
    }


def medicine_checker(med_input, age, health_conditions, disease_to_treat):

    meds = [m.strip() for m in med_input.split(",") if m.strip()]
    health_list = [h.strip() for h in health_conditions.split(",") if h.strip()]

    cards = []

    for med in meds:

        match = best_med_match(med)

        if not match:
            cards.append(f"<b>{med}</b> not found in database.<br>")
            continue

        result = check_med_suitability(match, health_list, disease_to_treat)

        suitable = "✅ Suitable" if result["is_suitable"] else "⚠️ Not Suitable"

        html = f"""
        <div style='padding:10px;border-radius:10px;background:#f4faff;margin:5px'>
        <h3>{match}</h3>
        Dosage: {MED_DB[match]['dosage']}<br>
        Treats disease: {result['treats_disease']}<br>
        Status: {suitable}<br>
        Side Effects: {', '.join(MED_DB[match]['side_effects'])}
        </div>
        """

        cards.append(html)

    return "".join(cards)


# -----------------------------
# AI Doctor
# -----------------------------
def ai_doctor_strict(text):

    t = text.lower()

    if "fever" in t:
        return "Fever detected. Rest, hydration, and paracetamol recommended."

    if "headache" in t:
        return "Headache may be tension related. Rest and hydration recommended."

    return "Monitor symptoms and consult doctor if condition worsens."


# -----------------------------
# AI Chat
# -----------------------------
ai_pipe = None

if TRANSFORMERS_AVAILABLE:
    try:
        ai_pipe = pipeline("text-generation", model="gpt2")
    except:
        pass
else:
    reply = "Stay hydrated and monitor symptoms."


def ai_chat_short(user_text, history):

    history = history or []

    if ai_pipe:
        try:
            out = ai_pipe(user_text, max_new_tokens=30)[0]["generated_text"]
            reply = out.replace(user_text, "")
        except:
            reply = "Please consult doctor for serious symptoms."
    else:
        reply = "Stay hydrated and monitor symptoms."

    history.append((user_text, reply))

    return history


# -----------------------------
# QR generator
# -----------------------------
def generate_qr_image(link):

    if not link:
        return None, "Enter a link"

    img = qrcode.make(link)

    bio = io.BytesIO()

    img.save(bio, format="PNG")

    bio.seek(0)

    return Image.open(bio), "QR Generated"


# -----------------------------
# UI
# -----------------------------
CSS = "body{background:#f8fbff;font-family:Arial}"

with gr.Blocks(css=CSS, title="PulseGuard AI Prescription Guardian") as demo:

    gr.Markdown("# PulseGuard — AI Prescription Guardian")

    with gr.Tab("Medicine Checker"):

        meds = gr.Textbox(label="Medicines")
        age = gr.Number(label="Age", value=30)
        health = gr.Textbox(label="Health Conditions")
        disease = gr.Textbox(label="Disease")

        btn = gr.Button("Verify")

        result = gr.HTML()

        btn.click(medicine_checker, [meds, age, health, disease], result)


    with gr.Tab("AI Doctor"):

        doc_in = gr.Textbox(label="Symptoms")

        doc_btn = gr.Button("Check")

        doc_out = gr.Textbox()

        doc_btn.click(ai_doctor_strict, doc_in, doc_out)


    with gr.Tab("AI Chat"):

        chatbot = gr.Chatbot()

        msg = gr.Textbox()

        send = gr.Button("Send")

        state = gr.State([])

        def send_msg(m, h):

            h = ai_chat_short(m, h)

            return h, "", h

        send.click(send_msg, [msg, state], [chatbot, msg, state])


    with gr.Tab("QR Generator"):

        link = gr.Textbox(label="App Link")

        qr_btn = gr.Button("Generate QR")

        qr_img = gr.Image()

        status = gr.Textbox()

        qr_btn.click(generate_qr_image, link, [qr_img, status])


demo.launch(
    server_name="0.0.0.0",
    server_port=int(os.environ.get("PORT", 10000))
)
