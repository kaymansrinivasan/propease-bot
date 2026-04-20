# PropEase Realty — WhatsApp AI Chatbot

An AI-powered WhatsApp chatbot for a real estate business built with Python (Flask), Meta WhatsApp Cloud API, and Google Gemini AI. The bot automatically captures and qualifies leads 24/7 through WhatsApp conversations.

---

## What It Does

- Greets customers automatically on WhatsApp
- Collects lead information through natural AI conversation (Buy / Rent / Sell, budget, area, contact)
- Remembers conversation context per user session
- Responds in English or Malay depending on the customer
- Runs 24/7 with zero manual effort

---

## System Architecture

```
Customer (WhatsApp)
        ↓
Meta WhatsApp Cloud API
        ↓
Flask Server (verify.py)
        ↓
Google Gemini AI (generates smart replies)
        ↓
WhatsApp API (sends reply back to customer)
```

---

## Tech Stack

| Component | Tool | Cost |
|---|---|---|
| WhatsApp API | Meta Cloud API | Free |
| AI Brain | Google Gemini 2.5 Flash | Free |
| Backend | Python + Flask | Free |
| Hosting | Render.com | Free |
| Automation (dev) | n8n (local) | Free |

---

## Project Structure

```
propease-bot/
├── verify.py          # Main Flask app — all bot logic lives here
├── requirements.txt   # Python dependencies
├── Procfile           # For deployment (Render / Railway)
├── runtime.txt        # Python version
└── README.md          # This file
```

---

## Setup Guide

### Prerequisites
- Python 3.11+
- Meta Developer account with WhatsApp app
- Google AI Studio account (for Gemini API key)
- GitHub account
- Render.com account (for free hosting)

---

### Step 1 — Clone the repository

```bash
git clone https://github.com/YOURUSERNAME/propease-bot.git
cd propease-bot
```

### Step 2 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 3 — Set environment variables

Create a `.env` file locally (never commit this to GitHub):

```
VERIFY_TOKEN=your_verify_token
WHATSAPP_TOKEN=your_meta_access_token
PHONE_NUMBER_ID=your_whatsapp_phone_number_id
GEMINI_API_KEY=your_gemini_api_key
```

Or export them directly in your terminal:

```bash
export VERIFY_TOKEN="your_verify_token"
export WHATSAPP_TOKEN="your_meta_access_token"
export PHONE_NUMBER_ID="your_phone_number_id"
export GEMINI_API_KEY="your_gemini_api_key"
```

### Step 4 — Run locally

```bash
python verify.py
```

Server runs at `http://localhost:5001`

### Step 5 — Expose locally with ngrok (for testing)

```bash
ngrok http 5001
```

Copy the `https://xxxx.ngrok-free.app` URL.

### Step 6 — Configure Meta Webhook

1. Go to [developers.facebook.com](https://developers.facebook.com)
2. Select your App → WhatsApp → Configuration
3. Set Callback URL: `https://xxxx.ngrok-free.app/verify`
4. Set Verify Token: same as your `VERIFY_TOKEN`
5. Click **Verify and Save**
6. Subscribe to the **messages** field

---

## Getting Your API Credentials

### Meta WhatsApp Credentials
1. Go to [developers.facebook.com](https://developers.facebook.com) → Your App
2. WhatsApp → API Setup
3. Copy **Phone Number ID** and **Temporary Access Token**
4. For permanent token: Business Settings → System Users → Generate Token

### Google Gemini API Key
1. Go to [aistudio.google.com](https://aistudio.google.com)
2. Click **"Get API Key"** → **"Create API key"**
3. Copy the key

---

## Deployment on Render.com (Free)

1. Push code to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Set:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn verify:app`
5. Add environment variables in the **Environment** tab
6. Deploy — you get a permanent URL like `https://propease-bot.onrender.com`
7. Update your Meta webhook URL to the Render URL

---

## How the Conversation Works

```
User: Hi
Bot:  Hi Kayman! Welcome to PropEase Realty.
      What are you looking for?
      1 = Buy  2 = Rent  3 = Sell

User: 1
Bot:  Great! You want to Buy.
      What is your budget?
      ...

User: Below RM300k
Bot:  Which area are you interested in?
      ...

[After all info collected]
Bot:  Thank you! Here is your summary:
      Intent: Buy
      Budget: Below RM300k
      Area: Johor Bahru
      Our agent will contact you shortly!
```

---

## Environment Variables Reference

| Variable | Description | Example |
|---|---|---|
| `VERIFY_TOKEN` | Secret token for Meta webhook verification | `Kayman178` |
| `WHATSAPP_TOKEN` | Meta access token for sending messages | `EAAG...` |
| `PHONE_NUMBER_ID` | Your WhatsApp phone number ID from Meta | `1033958343...` |
| `GEMINI_API_KEY` | Google Gemini API key for AI responses | `AIza...` |
| `PORT` | Server port (auto-set by hosting platform) | `5001` |

---

## Important Notes

- Never commit real tokens or API keys to GitHub — use environment variables
- Meta temporary tokens expire every 24 hours — use a System User token for production
- Gemini free tier allows 250 requests/day — sufficient for small business use
- Sessions are stored in memory — they reset if the server restarts

---

## Built With

- [Flask](https://flask.palletsprojects.com/) — Python web framework
- [Meta WhatsApp Cloud API](https://developers.facebook.com/docs/whatsapp/cloud-api/) — WhatsApp messaging
- [Google Gemini AI](https://aistudio.google.com/) — AI conversation engine
- [n8n](https://n8n.io/) — Workflow automation (development)
- [Render.com](https://render.com/) — Free cloud hosting

---

## Author

**Kayman Srinivasan**
Final Year Student — AI & Data Science, Multimedia University (MMU)
Industrial Training Project — Real Estate Digital Transformation

---

## License

This project is for educational and client demonstration purposes.
