from flask import Flask, request, jsonify
import requests
import os
import time

app = Flask(__name__)

# ── Your credentials ─────────────────────────────────────────────
VERIFY_TOKEN    = os.environ.get("VERIFY_TOKEN", "Kayman178")
WHATSAPP_TOKEN  = os.environ.get("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "")
GEMINI_API_KEY  = os.environ.get("GEMINI_API_KEY", "")
# ─────────────────────────────────────────────────────────────────

conversations = {}

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

    print("WhatsApp API Status:", response.status_code)
    print("WhatsApp API Response:", response.text)

def ask_gemini(phone, name, user_message):
    if user_message.strip().lower() in ["hi", "hello", "hey", "start"]:
        conversations[phone] = []

    if phone not in conversations:
        conversations[phone] = []

    conversations[phone].append({
        "role": "user",
        "parts": [{"text": user_message}]
    })

    system_prompt = f"""You are a friendly real estate assistant for PropEase Realty in Johor Bahru, Malaysia.
The customer's name is {name}.

Your job is to collect this information step by step, one question at a time:
1. Are they looking to Buy, Rent, or Sell?
2. What is their budget?
3. Which area in Johor? (Johor Bahru, Iskandar Puteri, Skudai, or Other)
4. Their contact number (if not already known)

Rules:
- Be friendly and professional
- Ask only ONE question at a time
- Keep replies short and clear
- Only discuss real estate topics
- Reply in the same language the customer uses (English or Malay)
- When you have collected all 4 pieces of info, end your reply with exactly:
  LEAD_COMPLETE
  and give a clean summary before it"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "system_instruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": conversations[phone]
    }

    reply = "Sorry, I am a bit busy right now. Please send your message again in a moment!"

    # Retry up to 3 times
    for attempt in range(3):
        try:
            response = requests.post(url, json=payload)
            result = response.json()
            print(f"Gemini response: {result}")

            # Handle errors from Gemini
            if "error" in result:
                code = result["error"]["code"]
                msg  = result["error"]["message"]
                print(f"Gemini error code {code}: {msg}")

                if code in [503, 429]:
                    # Overloaded or rate limited — wait and retry
                    print(f"Retrying in 3s... (attempt {attempt + 1})")
                    time.sleep(3)
                    continue
                else:
                    # Other errors — don't retry
                    break

            reply = result["candidates"][0]["content"]["parts"][0]["text"]
            break  # Success — exit retry loop

        except Exception as e:
            print(f"Gemini exception: {e}")
            if attempt < 2:
                time.sleep(3)
                continue
            break

    # Save reply to conversation history
    conversations[phone].append({
        "role": "model",
        "parts": [{"text": reply}]
    })

    # Keep last 20 messages only
    if len(conversations[phone]) > 20:
        conversations[phone] = conversations[phone][-20:]

    return reply

def handle_message(phone, name, text):
    reply = ask_gemini(phone, name, text)

    if "LEAD_COMPLETE" in reply:
        clean_reply = reply.replace("LEAD_COMPLETE", "").strip()
        send_whatsapp(phone, clean_reply)
    else:
        send_whatsapp(phone, reply)

verify = Flask(__name__)

# ✅ ADD IT HERE
@app.route("/")
def home():
    return """
    <h1>🏡 PropEase AI WhatsApp Assistant</h1>
    <p>This bot helps real estate companies capture leads automatically via WhatsApp.</p>

    <h3>💡 Features:</h3>
    <ul>
        <li>✔ AI-powered conversation (Gemini)</li>
        <li>✔ Lead qualification (Buy/Rent/Sell)</li>
        <li>✔ Budget & location capture</li>
        <li>✔ Automated WhatsApp replies</li>
    </ul>

    <h3>📲 How it works:</h3>
    <p>Send "hi" to the WhatsApp test number and experience the flow.</p>

    <h3>⚙️ Tech Stack:</h3>
    <p>Flask | WhatsApp Cloud API | Gemini API | Render</p>
    """

# ── Meta verification ───────────────────────────
@app.route("/verify", methods=["GET"])
def verify():
    mode      = request.args.get("hub.mode")
    token     = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403

# ── Incoming WhatsApp messages ───────────────────────────────────
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
        print(f"Error: {e}")
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
