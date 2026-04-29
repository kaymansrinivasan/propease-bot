from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# ── ENV VARIABLES ─────────────────────────────
VERIFY_TOKEN    = os.environ.get("VERIFY_TOKEN", "Kayman178")
WHATSAPP_TOKEN  = os.environ.get("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "")
GEMINI_API_KEY  = os.environ.get("GEMINI_API_KEY", "")

# ── STORAGE (TEMP MEMORY) ─────────────────────
user_state = {}
leads = []

# ── LANDING PAGE ──────────────────────────────
@app.route("/")
def home():
    return """
    <html>
    <head>
        <title>PropEase AI</title>
        <style>
            body { font-family: Arial; background: #0f172a; color: white; margin: 0; }
            .container { max-width: 900px; margin: auto; padding: 60px; }
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
            <p>AI-powered WhatsApp lead automation system.</p>

            <div class="card">
                <h3>🚀 Features</h3>
                <ul>
                    <li>Lead qualification (Buy / Rent / Sell)</li>
                    <li>WhatsApp automation</li>
                    <li>Real-time lead dashboard</li>
                </ul>
            </div>

            <div class="card">
                <h3>📲 Try it</h3>
                <p>Send "hi" on WhatsApp to start.</p>
            </div>

            <a class="btn" href="/leads">View Leads</a>
        </div>
    </body>
    </html>
    """

# ── LEADS DASHBOARD ───────────────────────────
@app.route("/leads")
def view_leads():
    html = """
    <html>
    <head>
        <title>Leads Dashboard</title>
        <style>
            body { font-family: Arial; background: #0f172a; color: white; padding: 40px; }
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 12px; border-bottom: 1px solid #444; }
            th { background: #1e293b; }
            tr:hover { background: #1e293b; }
        </style>
    </head>
    <body>
        <h1>📊 Leads Dashboard</h1>
        <table>
            <tr>
                <th>Name</th>
                <th>Phone</th>
                <th>Intent</th>
                <th>Budget</th>
                <th>Area</th>
                <th>Contact</th>
            </tr>
    """

    for lead in leads:
        html += f"""
        <tr>
            <td>{lead.get('name')}</td>
            <td>{lead.get('phone')}</td>
            <td>{lead.get('intent')}</td>
            <td>{lead.get('budget')}</td>
            <td>{lead.get('area')}</td>
            <td>{lead.get('contact')}</td>
        </tr>
        """

    html += "</table></body></html>"
    return html

# ── SEND WHATSAPP ─────────────────────────────
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

# ── MESSAGE HANDLER (STATE-BASED) ─────────────
def handle_message(phone, name, text):

    # Start flow
    if text.lower() in ["hi", "hello", "start"]:
        user_state[phone] = {"step": 1}
        send_whatsapp(phone, "Hi! Are you looking to Buy, Rent, or Sell a property?")
        return

    if phone not in user_state:
        user_state[phone] = {"step": 1}
        send_whatsapp(phone, "Please type 'hi' to start.")
        return

    step = user_state[phone]["step"]

    if step == 1:
        user_state[phone]["intent"] = text
        user_state[phone]["step"] = 2
        send_whatsapp(phone, "What is your budget?")

    elif step == 2:
        user_state[phone]["budget"] = text
        user_state[phone]["step"] = 3
        send_whatsapp(phone, "Which area are you interested in?")

    elif step == 3:
        user_state[phone]["area"] = text
        user_state[phone]["step"] = 4
        send_whatsapp(phone, "Please provide your contact number.")

    elif step == 4:
        user_state[phone]["contact"] = text

        # SAVE LEAD
        leads.append({
            "name": name,
            "phone": phone,
            "intent": user_state[phone]["intent"],
            "budget": user_state[phone]["budget"],
            "area": user_state[phone]["area"],
            "contact": text
        })

        send_whatsapp(phone, "✅ Thank you! Our agent will contact you soon.")

        print("✅ LEAD SAVED:", leads[-1])

        # Reset state
        del user_state[phone]

# ── VERIFY WEBHOOK ────────────────────────────
@app.route("/verify", methods=["GET"])
def verify():
    mode      = request.args.get("hub.mode")
    token     = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200

    return "Forbidden", 403

# ── RECEIVE MESSAGE ───────────────────────────
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

# ── RUN ───────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)