from flask import Flask, request, jsonify
import requests, os, json, re

app = Flask(__name__)

# ── ENV ─────────────────────────────
VERIFY_TOKEN    = os.environ.get("VERIFY_TOKEN", "Kayman178")
WHATSAPP_TOKEN  = os.environ.get("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "")
GEMINI_API_KEY  = os.environ.get("GEMINI_API_KEY", "")

# ── MEMORY (demo only) ──────────────
conversations = {}
leads = []

# ── HELPERS ─────────────────────────
def extract_json_block(text):
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group())
    except:
        return {}

def normalize_number(text):
    nums = re.findall(r'\d+', str(text))
    return nums[0] if nums else text

# ── GEMINI PROMPT ───────────────────
SYSTEM_PROMPT = """
You are a friendly real estate assistant in Malaysia.

Collect:
- intent (Buy/Rent/Sell)
- budget
- area
- contact

Respond ONLY in JSON:
{
  "reply": "friendly natural message",
  "intent": "",
  "budget": "",
  "area": "",
  "contact": "",
  "complete": false
}

Rules:
- Be conversational, not robotic
- Accept messy inputs like "600rm", "around 500k"
- Ask only missing info
- When all info collected → complete = true and summarize
"""

# ── GEMINI CALL ─────────────────────
def ask_gemini(phone, message):
    if phone not in conversations:
        conversations[phone] = []

    conversations[phone].append({
        "role": "user",
        "parts": [{"text": message}]
    })

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "system_instruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "contents": conversations[phone]
    }

    try:
        r = requests.post(url, json=payload, timeout=10)
        res = r.json()

        raw = res["candidates"][0]["content"]["parts"][0]["text"]
        print("GEMINI RAW:", raw)

        data = extract_json_block(raw)
        return data if data else {"reply": raw, "complete": False}

    except Exception as e:
        print("Gemini error:", e)
        return {"reply": "⚠️ Please try again later.", "complete": False}

# ── SEND WHATSAPP ───────────────────
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

    r = requests.post(url, headers=headers, json=data)
    print("WA:", r.status_code, r.text)

# ── HANDLE MESSAGE ──────────────────
def handle_message(phone, name, text):
    data = ask_gemini(phone, text)

    reply = data.get("reply", "Try again.")
    send_whatsapp(phone, reply)

    if data.get("complete"):
        lead = {
            "name": name,
            "phone": phone,
            "intent": data.get("intent"),
            "budget": normalize_number(data.get("budget")),
            "area": data.get("area"),
            "contact": data.get("contact")
        }

        leads.append(lead)
        print("✅ LEAD SAVED:", lead)

# ── LANDING PAGE ────────────────────
@app.route("/")
def home():
    return """
    <html>
    <head>
        <title>PropEase AI</title>
        <style>
            body { font-family: Arial; background:#020617; color:white; padding:60px; }
            h1 { color:#00f5d4; }
            .box { margin-top:20px; padding:20px; background:#1e293b; border-radius:10px; }
        </style>
    </head>
    <body>
        <h1>🏡 PropEase AI</h1>
        <div class="box">AI-powered WhatsApp lead automation</div>
        <div class="box">Send "hi" on WhatsApp to test</div>
        <a href="/leads">View Dashboard</a>
    </body>
    </html>
    """

# ── PREMIUM DASHBOARD ───────────────
@app.route("/leads")
def leads_page():
    rows = ""

    for l in leads:
        rows += f"""
        <div class="row">
            <div>{l['name']}</div>
            <div>{l['intent']}</div>
            <div>RM {l['budget']}</div>
            <div>{l['area']}</div>
            <div>{l['contact']}</div>
        </div>
        """

    return f"""
    <html>
    <head>
    <style>
    body {{
        margin:0;
        background:#020617;
        color:white;
        font-family:sans-serif;
    }}
    .container {{
        padding:50px;
        max-width:1000px;
        margin:auto;
    }}
    h1 {{
        font-size:40px;
        color:#00f5d4;
    }}
    .table {{
        margin-top:30px;
    }}
    .row {{
        display:grid;
        grid-template-columns: repeat(5,1fr);
        padding:15px;
        border-bottom:1px solid #333;
        transition:0.3s;
    }}
    .row:hover {{
        background:#1e293b;
        transform:scale(1.02);
    }}
    .header {{
        font-weight:bold;
        color:#94a3b8;
    }}
    </style>
    </head>

    <body>
        <div class="container">
            <h1>📊 Lead Intelligence</h1>

            <div class="row header">
                <div>Name</div>
                <div>Intent</div>
                <div>Budget</div>
                <div>Area</div>
                <div>Contact</div>
            </div>

            {rows}
        </div>
    </body>
    </html>
    """

# ── WEBHOOK VERIFY ──────────────────
@app.route("/verify", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "Error", 403

# ── WEBHOOK RECEIVE ─────────────────
@app.route("/verify", methods=["POST"])
def webhook():
    data = request.get_json()

    try:
        entry = data["entry"][0]["changes"][0]["value"]

        if "messages" not in entry:
            return jsonify({"status": "ok"}), 200

        msg = entry["messages"][0]

        if msg["type"] != "text":
            return jsonify({"status": "ok"}), 200

        phone = msg["from"]
        name  = entry["contacts"][0]["profile"]["name"]
        text  = msg["text"]["body"]

        handle_message(phone, name, text)

    except Exception as e:
        print("Webhook error:", e)

    return jsonify({"status": "ok"}), 200

# ── RUN ─────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)