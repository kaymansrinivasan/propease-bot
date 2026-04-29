from flask import Flask, request, jsonify
import requests
import os
import time

app = Flask(__name__)

# ── ENV VARIABLES ─────────────────────────────────────
VERIFY_TOKEN    = os.environ.get("VERIFY_TOKEN", "Kayman178")
WHATSAPP_TOKEN  = os.environ.get("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "")
GEMINI_API_KEY  = os.environ.get("GEMINI_API_KEY", "")

# ── MEMORY STORAGE ────────────────────────────────────
conversations = {}
leads = []

# ── LANDING PAGE ──────────────────────────────────────
@app.route("/")
def home():
    return """
    <html>
    <head>
        <title>PropEase AI</title>
        <style>
            body {
                font-family: Arial;
                background: #0f172a;
                color: white;
                margin: 0;
            }
            .container {
                max-width: 900px;
                margin: auto;
                padding: 60px;
            }
            h1 { color: #38bdf8; }
            .card {
                background: #1e293b;
                padding: 20px;
                border-radius: 10px;
                margin-top: 20px;
            }
            .btn {
                display: inline-block;
                padding: 12px 20px;
                background: #38bdf8;
                color: black;
                text-decoration: none;
                border-radius: 8px;
                margin-top: 20px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏡 PropEase AI</h1>
            <p>AI-powered WhatsApp assistant for real estate lead automation.</p>

            <div class="card">
                <h3>🚀 Features</h3>
                <ul>
                    <li>AI conversation (Gemini)</li>
                    <li>Lead qualification</li>
                    <li>WhatsApp automation</li>
                </ul>
            </div>

            <div class="card">
                <h3>📲 Try it</h3>
                <p>Send "hi" to the WhatsApp bot</p>
            </div>

            <div class="card">
                <h3>🟢 Status: LIVE</h3>
            </div>

            <a class="btn" href="/leads">View Leads</a>
        </div>
    </body>
    </html>
    """

# ── STATUS API ────────────────────────────────────────
@app.route("/status")
def status():
    return {
        "status": "running",
        "service": "PropEase AI Bot"
    }

# ── VIEW LEADS ────────────────────────────────────────
@app.route("/leads")
def view_leads():
    return {"leads": leads}

# ── SEND WHATSAPP ─────────────────────────────────────
def send_whatsapp(phone, message):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": message}
    }

    response = requests.post(url, headers=headers, json=data)

    print("WhatsApp Status:", response.status_code)
    print("WhatsApp Response:", response.text)

# ── GEMINI AI ─────────────────────────────────────────
def ask_gemini(phone, name, user_message):

    # Basic fallback (save quota)
    if user_message.lower() in ["hi", "hello"]:
        return "Hi! Are you looking to Buy, Rent, or Sell a property?"

    if phone not in conversations:
        conversations[phone] = []

    conversations[phone].append({
        "role": "user",
        "parts": [{"text": user_message}]
    })

    system_prompt = f"""
    You are a real estate assistant for PropEase Realty.
    Customer name: {name}

    Ask step-by-step:
    1. Buy/Rent/Sell
    2. Budget
    3. Area
    4. Contact

    When done, end with LEAD_COMPLETE
    """

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "system_instruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": conversations[phone]
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        result = response.json()

        print("Gemini:", result)

        # Handle quota error
        if "error" in result:
            code = result["error"]["code"]

            if code == 429:
                return "⚠️ I'm currently busy. Please try again later."

        reply = result["candidates"][0]["content"]["parts"][0]["text"]

    except Exception as e:
        print("Gemini Error:", e)
        return "⚠️ Error processing request."

    conversations[phone].append({
        "role": "model",
        "parts": [{"text": reply}]
    })

    return reply

# ── HANDLE MESSAGE ────────────────────────────────────
def handle_message(phone, name, text):
    reply = ask_gemini(phone, name, text)

    if "LEAD_COMPLETE" in reply:
        clean_reply = reply.replace("LEAD_COMPLETE", "").strip()

        # Save lead
        leads.append({
            "name": name,
            "phone": phone,
            "summary": clean_reply
        })

        send_whatsapp(phone, clean_reply)
    else:
        send_whatsapp(phone, reply)

# ── VERIFY WEBHOOK ────────────────────────────────────
@app.route("/verify", methods=["GET"])
def verify():
    mode      = request.args.get("hub.mode")
    token     = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200

    return "Forbidden", 403

# ── RECEIVE MESSAGE ───────────────────────────────────
@app.route("/verify", methods=["POST"])
def webhook():
    data = request.get_json()

    try:
        entry = data["entry"][0]["changes"][0]["value"]

        if "messages" not in entry:
            return jsonify({"status": "ok"}), 200

        message = entry["messages"][0]

        if message.get("type") != "text":
            return jsonify({"status": "ok"}), 200

        phone = message["from"]
        name  = entry["contacts"][0]["profile"]["name"]
        text  = message["text"]["body"]

        handle_message(phone, name, text)

    except Exception as e:
        print("Webhook Error:", e)

    return jsonify({"status": "ok"}), 200

# ── RUN ───────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)