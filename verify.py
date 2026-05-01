from flask import Flask, request, jsonify, Response
import requests, os, json, re
from datetime import datetime

app = Flask(__name__)

VERIFY_TOKEN    = os.environ.get("VERIFY_TOKEN", "Kayman178")
WHATSAPP_TOKEN  = os.environ.get("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "")
GEMINI_API_KEY  = os.environ.get("GEMINI_API_KEY", "")

conversations = {}
leads = []
stats = {"total": 0, "buy": 0, "rent": 0, "sell": 0, "today": 0}

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

SYSTEM_PROMPT = """
You are a concise, professional real estate assistant for PropEase Realty, Malaysia.

Collect exactly these fields through natural conversation:
- intent (Buy/Rent/Sell)
- budget (in RM)
- area (in Malaysia, prefer Johor)
- contact (phone or email)

Respond ONLY in valid JSON, no markdown, no explanation outside JSON:
{
  "reply": "your message to the user",
  "intent": "",
  "budget": "",
  "area": "",
  "contact": "",
  "complete": false
}

Rules:
- Professional but warm tone
- One question at a time
- Accept any input format (600rm, 500k, JB, KL)
- When all 4 fields collected, set complete to true with a clean summary
- Never repeat yourself
- No emojis
"""

def ask_gemini(phone, message):
    if phone not in conversations:
        conversations[phone] = []
    conversations[phone].append({"role": "user", "parts": [{"text": message}]})
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": conversations[phone]
    }
    for attempt in range(3):
        try:
            r = requests.post(url, json=payload, timeout=12)
            res = r.json()
            if "error" in res:
                code = res["error"]["code"]
                if code in [503, 429]:
                    import time; time.sleep(3)
                    continue
                break
            raw = res["candidates"][0]["content"]["parts"][0]["text"]
            data = extract_json_block(raw)
            if data:
                conversations[phone].append({"role": "model", "parts": [{"text": data.get("reply", "")}]})
                if len(conversations[phone]) > 20:
                    conversations[phone] = conversations[phone][-20:]
            return data if data else {"reply": raw, "complete": False}
        except Exception as e:
            print("Gemini error:", e)
            if attempt == 2:
                return {"reply": "I am experiencing a brief issue. Please send your message again.", "complete": False}
    return {"reply": "Please try again in a moment.", "complete": False}

def send_whatsapp(phone, message):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    data = {"messaging_product": "whatsapp", "to": phone, "type": "text", "text": {"body": message}}
    r = requests.post(url, headers=headers, json=data)
    print("WA:", r.status_code)

def handle_message(phone, name, text):
    data = ask_gemini(phone, text)
    reply = data.get("reply", "Please try again.")
    send_whatsapp(phone, reply)
    if data.get("complete"):
        intent = data.get("intent", "").lower()
        lead = {
            "name": name, "phone": phone,
            "intent": data.get("intent", ""),
            "budget": normalize_number(data.get("budget", "")),
            "area": data.get("area", ""),
            "contact": data.get("contact", ""),
            "time": datetime.now().strftime("%d %b %Y, %H:%M")
        }
        leads.append(lead)
        stats["total"] += 1
        stats["today"] += 1
        if "buy" in intent: stats["buy"] += 1
        elif "rent" in intent: stats["rent"] += 1
        elif "sell" in intent: stats["sell"] += 1
        print("LEAD SAVED:", lead)

HOME_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PropEase AI — Intelligent Real Estate Automation</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --black: #080a0f;
    --surface: #0d1117;
    --border: rgba(255,255,255,0.07);
    --border-bright: rgba(255,255,255,0.12);
    --text: #e8ecf0;
    --muted: #6b7280;
    --accent: #b8ff57;
    --accent-dim: rgba(184,255,87,0.08);
    --accent-glow: rgba(184,255,87,0.15);
    --blue: #4f8ef7;
    --blue-dim: rgba(79,142,247,0.08);
  }

  html { scroll-behavior: smooth; }

  body {
    font-family: 'DM Sans', sans-serif;
    background: var(--black);
    color: var(--text);
    overflow-x: hidden;
    line-height: 1.6;
  }

  /* NOISE OVERLAY */
  body::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.03'/%3E%3C/svg%3E");
    pointer-events: none;
    z-index: 0;
    opacity: 0.4;
  }

  /* NAV */
  nav {
    position: fixed;
    top: 0; left: 0; right: 0;
    z-index: 100;
    padding: 20px 60px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid var(--border);
    background: rgba(8,10,15,0.85);
    backdrop-filter: blur(20px);
  }

  .logo {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 18px;
    letter-spacing: -0.5px;
    color: var(--text);
    display: flex;
    align-items: center;
    gap: 10px;
    text-decoration: none;
  }

  .logo-dot {
    width: 8px; height: 8px;
    background: var(--accent);
    border-radius: 50%;
    display: inline-block;
    box-shadow: 0 0 10px var(--accent);
    animation: pulse 2s ease-in-out infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.6; transform: scale(0.8); }
  }

  nav-links { display: flex; gap: 32px; }
  .nav-link {
    font-size: 14px;
    color: var(--muted);
    text-decoration: none;
    transition: color 0.2s;
    font-weight: 400;
  }
  .nav-link:hover { color: var(--text); }

  .nav-cta {
    font-size: 13px;
    font-weight: 500;
    padding: 9px 20px;
    background: var(--accent);
    color: #080a0f;
    border-radius: 8px;
    text-decoration: none;
    transition: opacity 0.2s, transform 0.2s;
    font-family: 'DM Sans', sans-serif;
    letter-spacing: 0.01em;
  }
  .nav-cta:hover { opacity: 0.85; transform: translateY(-1px); }

  /* HERO */
  .hero {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 140px 40px 100px;
    position: relative;
  }

  .hero-bg {
    position: absolute;
    inset: 0;
    background:
      radial-gradient(ellipse 60% 50% at 50% 0%, rgba(184,255,87,0.06) 0%, transparent 70%),
      radial-gradient(ellipse 40% 40% at 80% 60%, rgba(79,142,247,0.05) 0%, transparent 60%);
    pointer-events: none;
  }

  .tag {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    font-weight: 500;
    color: var(--accent);
    background: var(--accent-dim);
    border: 1px solid rgba(184,255,87,0.2);
    padding: 6px 14px;
    border-radius: 100px;
    margin-bottom: 32px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    animation: fadeUp 0.6s ease both;
  }

  .tag-dot {
    width: 5px; height: 5px;
    background: var(--accent);
    border-radius: 50%;
    animation: pulse 1.5s ease-in-out infinite;
  }

  .hero h1 {
    font-family: 'Syne', sans-serif;
    font-size: clamp(48px, 7vw, 88px);
    font-weight: 800;
    line-height: 1.0;
    letter-spacing: -0.03em;
    color: var(--text);
    max-width: 900px;
    animation: fadeUp 0.6s ease 0.1s both;
  }

  .hero h1 .highlight {
    color: var(--accent);
    position: relative;
  }

  .hero-sub {
    margin-top: 24px;
    font-size: 18px;
    color: var(--muted);
    max-width: 560px;
    font-weight: 300;
    line-height: 1.7;
    animation: fadeUp 0.6s ease 0.2s both;
  }

  .hero-actions {
    margin-top: 48px;
    display: flex;
    gap: 16px;
    align-items: center;
    animation: fadeUp 0.6s ease 0.3s both;
  }

  .btn-primary {
    padding: 14px 32px;
    background: var(--accent);
    color: #080a0f;
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 14px;
    border-radius: 10px;
    text-decoration: none;
    transition: all 0.2s;
    letter-spacing: 0.02em;
  }
  .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 8px 30px rgba(184,255,87,0.25); }

  .btn-secondary {
    padding: 14px 32px;
    background: transparent;
    color: var(--text);
    font-family: 'DM Sans', sans-serif;
    font-weight: 400;
    font-size: 14px;
    border-radius: 10px;
    border: 1px solid var(--border-bright);
    text-decoration: none;
    transition: all 0.2s;
  }
  .btn-secondary:hover { border-color: rgba(255,255,255,0.25); background: rgba(255,255,255,0.04); }

  /* STATS BAR */
  .stats-bar {
    display: flex;
    justify-content: center;
    gap: 60px;
    margin-top: 80px;
    padding: 32px;
    border-top: 1px solid var(--border);
    border-bottom: 1px solid var(--border);
    animation: fadeUp 0.6s ease 0.4s both;
  }

  .stat-item { text-align: center; }
  .stat-num {
    font-family: 'Syne', sans-serif;
    font-size: 36px;
    font-weight: 800;
    color: var(--text);
    letter-spacing: -0.03em;
  }
  .stat-label {
    font-size: 12px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 4px;
  }

  /* SECTION */
  section {
    padding: 100px 60px;
    max-width: 1200px;
    margin: 0 auto;
  }

  .section-tag {
    font-size: 11px;
    font-weight: 600;
    color: var(--accent);
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 16px;
  }

  .section-title {
    font-family: 'Syne', sans-serif;
    font-size: clamp(32px, 4vw, 52px);
    font-weight: 800;
    letter-spacing: -0.02em;
    line-height: 1.1;
    margin-bottom: 20px;
  }

  .section-sub {
    font-size: 16px;
    color: var(--muted);
    max-width: 500px;
    font-weight: 300;
    line-height: 1.7;
  }

  /* HOW IT WORKS */
  .flow {
    margin-top: 60px;
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1px;
    background: var(--border);
    border: 1px solid var(--border);
    border-radius: 16px;
    overflow: hidden;
  }

  .flow-step {
    background: var(--surface);
    padding: 36px 28px;
    position: relative;
    transition: background 0.3s;
  }
  .flow-step:hover { background: #111720; }

  .flow-num {
    font-family: 'Syne', sans-serif;
    font-size: 11px;
    font-weight: 700;
    color: var(--muted);
    letter-spacing: 0.1em;
    margin-bottom: 20px;
  }

  .flow-icon {
    width: 40px; height: 40px;
    background: var(--accent-dim);
    border: 1px solid rgba(184,255,87,0.15);
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 20px;
    font-size: 18px;
  }

  .flow-title {
    font-family: 'Syne', sans-serif;
    font-size: 16px;
    font-weight: 700;
    margin-bottom: 10px;
    color: var(--text);
  }

  .flow-desc {
    font-size: 13px;
    color: var(--muted);
    line-height: 1.7;
    font-weight: 300;
  }

  /* FEATURES GRID */
  .features {
    margin-top: 60px;
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
  }

  .feature-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 32px;
    transition: border-color 0.3s, transform 0.3s;
    position: relative;
    overflow: hidden;
  }
  .feature-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--accent-glow), transparent);
    opacity: 0;
    transition: opacity 0.3s;
  }
  .feature-card:hover { border-color: var(--border-bright); transform: translateY(-4px); }
  .feature-card:hover::before { opacity: 1; }

  .feature-icon {
    width: 44px; height: 44px;
    background: var(--accent-dim);
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 20px;
    font-size: 20px;
    border: 1px solid rgba(184,255,87,0.1);
  }

  .feature-title {
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 15px;
    margin-bottom: 10px;
    color: var(--text);
  }

  .feature-desc {
    font-size: 13px;
    color: var(--muted);
    line-height: 1.7;
    font-weight: 300;
  }

  /* CHAT DEMO */
  .demo-section {
    padding: 100px 60px;
    background: var(--surface);
    border-top: 1px solid var(--border);
    border-bottom: 1px solid var(--border);
  }

  .demo-inner {
    max-width: 1200px;
    margin: 0 auto;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 80px;
    align-items: center;
  }

  .chat-window {
    background: #0a0f1a;
    border: 1px solid var(--border);
    border-radius: 20px;
    overflow: hidden;
    box-shadow: 0 40px 80px rgba(0,0,0,0.5);
  }

  .chat-header {
    background: #111720;
    padding: 16px 20px;
    display: flex;
    align-items: center;
    gap: 12px;
    border-bottom: 1px solid var(--border);
  }

  .chat-avatar {
    width: 36px; height: 36px;
    background: var(--accent);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    color: #080a0f;
    font-weight: 700;
    font-family: 'Syne', sans-serif;
  }

  .chat-name {
    font-size: 14px;
    font-weight: 500;
    color: var(--text);
  }
  .chat-status {
    font-size: 12px;
    color: var(--accent);
  }

  .chat-body {
    padding: 20px;
    min-height: 320px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .msg {
    max-width: 80%;
    padding: 12px 16px;
    border-radius: 12px;
    font-size: 13px;
    line-height: 1.6;
    animation: fadeUp 0.4s ease both;
  }

  .msg.bot {
    background: #1a2235;
    border: 1px solid var(--border);
    color: var(--text);
    align-self: flex-start;
    border-radius: 4px 12px 12px 12px;
  }

  .msg.user {
    background: var(--accent);
    color: #080a0f;
    align-self: flex-end;
    border-radius: 12px 4px 12px 12px;
    font-weight: 500;
  }

  .msg-time {
    font-size: 10px;
    color: var(--muted);
    text-align: right;
    margin-top: 4px;
  }

  /* TECH STACK */
  .stack {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 32px;
  }

  .stack-tag {
    font-size: 12px;
    padding: 6px 14px;
    background: rgba(255,255,255,0.04);
    border: 1px solid var(--border);
    border-radius: 100px;
    color: var(--muted);
    font-weight: 400;
  }

  /* GITHUB SECTION */
  .github-section {
    padding: 80px 60px;
    max-width: 1200px;
    margin: 0 auto;
  }

  .github-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 48px;
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 40px;
    align-items: center;
    position: relative;
    overflow: hidden;
  }

  .github-card::before {
    content: '';
    position: absolute;
    top: -100px; right: -100px;
    width: 300px; height: 300px;
    background: radial-gradient(circle, rgba(184,255,87,0.06) 0%, transparent 70%);
    pointer-events: none;
  }

  .github-label {
    font-size: 11px;
    font-weight: 600;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 12px;
  }

  .github-title {
    font-family: 'Syne', sans-serif;
    font-size: 28px;
    font-weight: 800;
    letter-spacing: -0.02em;
    margin-bottom: 16px;
  }

  .github-desc {
    font-size: 14px;
    color: var(--muted);
    line-height: 1.8;
    max-width: 500px;
    font-weight: 300;
  }

  .github-meta {
    display: flex;
    gap: 24px;
    margin-top: 24px;
  }

  .meta-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    color: var(--muted);
  }

  .meta-dot { width: 8px; height: 8px; border-radius: 50%; }

  .github-btn {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    padding: 16px 28px;
    background: var(--text);
    color: var(--black);
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 14px;
    border-radius: 12px;
    text-decoration: none;
    white-space: nowrap;
    transition: all 0.2s;
  }
  .github-btn:hover { transform: translateY(-2px); box-shadow: 0 8px 30px rgba(255,255,255,0.1); }

  /* FOOTER */
  footer {
    border-top: 1px solid var(--border);
    padding: 40px 60px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .footer-left { font-size: 13px; color: var(--muted); }
  .footer-left strong { color: var(--text); }
  .footer-right {
    font-size: 12px;
    color: var(--muted);
    text-align: right;
  }

  /* ANIMATIONS */
  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
  }

  .reveal {
    opacity: 0;
    transform: translateY(30px);
    transition: opacity 0.6s ease, transform 0.6s ease;
  }
  .reveal.visible { opacity: 1; transform: translateY(0); }

  /* DIVIDER */
  .divider {
    height: 1px;
    background: var(--border);
    margin: 0 60px;
  }
</style>
</head>

<body>

<nav>
  <a href="/" class="logo">
    <span class="logo-dot"></span>
    PropEase AI
  </a>
  <div style="display:flex;gap:32px;align-items:center;">
    <a href="#how" class="nav-link">How it works</a>
    <a href="#features" class="nav-link">Features</a>
    <a href="https://github.com/kaymansrinivasan/propease-bot" target="_blank" class="nav-link">GitHub</a>
    <a href="/leads" class="nav-cta">View Dashboard</a>
  </div>
</nav>

<!-- HERO -->
<section class="hero" style="max-width:100%;padding-top:140px;">
  <div class="hero-bg"></div>
  <div class="tag"><span class="tag-dot"></span>Live on WhatsApp</div>
  <h1>Real estate leads.<br>Captured <span class="highlight">automatically.</span></h1>
  <p class="hero-sub">An AI assistant that qualifies property inquiries on WhatsApp — capturing intent, budget, and contact details without any human intervention.</p>
  <div class="hero-actions">
    <a href="/leads" class="btn-primary">Open Dashboard</a>
    <a href="https://github.com/kaymansrinivasan/propease-bot" target="_blank" class="btn-secondary">View Source</a>
  </div>
  <div class="stats-bar">
    <div class="stat-item">
      <div class="stat-num">24/7</div>
      <div class="stat-label">Always on</div>
    </div>
    <div class="stat-item">
      <div class="stat-num">AI</div>
      <div class="stat-label">Gemini 2.5 Flash</div>
    </div>
    <div class="stat-item">
      <div class="stat-num">0</div>
      <div class="stat-label">Monthly cost</div>
    </div>
    <div class="stat-item">
      <div class="stat-num">EN/MY</div>
      <div class="stat-label">Bilingual</div>
    </div>
  </div>
</section>

<div class="divider"></div>

<!-- HOW IT WORKS -->
<section id="how">
  <div class="section-tag">Process</div>
  <h2 class="section-title">From inquiry to<br>qualified lead.</h2>
  <p class="section-sub">Four automated steps replace what previously required a human agent to handle manually.</p>

  <div class="flow reveal">
    <div class="flow-step">
      <div class="flow-num">01</div>
      <div class="flow-icon">💬</div>
      <div class="flow-title">Customer messages</div>
      <div class="flow-desc">Customer sends any message to the business WhatsApp number. The system activates instantly.</div>
    </div>
    <div class="flow-step">
      <div class="flow-num">02</div>
      <div class="flow-icon">🧠</div>
      <div class="flow-title">AI qualifies</div>
      <div class="flow-desc">Gemini AI guides the conversation, extracting intent, budget, area preference, and contact details naturally.</div>
    </div>
    <div class="flow-step">
      <div class="flow-num">03</div>
      <div class="flow-icon">✓</div>
      <div class="flow-title">Lead captured</div>
      <div class="flow-desc">Once all fields are collected, the lead is stored with a timestamp and full conversation summary.</div>
    </div>
    <div class="flow-step">
      <div class="flow-num">04</div>
      <div class="flow-icon">📊</div>
      <div class="flow-title">Agent reviews</div>
      <div class="flow-desc">The agent views structured, pre-qualified leads on the dashboard and follows up directly.</div>
    </div>
  </div>
</section>

<div class="divider"></div>

<!-- CHAT DEMO + TEXT -->
<div class="demo-section">
  <div class="demo-inner">
    <div>
      <div class="section-tag">Live Demo</div>
      <h2 class="section-title" style="font-size:clamp(28px,3vw,44px)">Natural conversation,<br>structured output.</h2>
      <p class="section-sub">The bot understands messy, real-world inputs like "600rm", "JB area", or "around 500k" and converts them into clean structured data.</p>
      <div class="stack">
        <span class="stack-tag">Python / Flask</span>
        <span class="stack-tag">Meta WhatsApp Cloud API</span>
        <span class="stack-tag">Google Gemini 2.5 Flash</span>
        <span class="stack-tag">Render.com</span>
        <span class="stack-tag">n8n Automation</span>
      </div>
    </div>
    <div class="chat-window reveal">
      <div class="chat-header">
        <div class="chat-avatar">P</div>
        <div>
          <div class="chat-name">PropEase AI</div>
          <div class="chat-status">Online — responds instantly</div>
        </div>
      </div>
      <div class="chat-body">
        <div class="msg bot" style="animation-delay:0.2s">Hello. You have reached PropEase Realty. Are you looking to buy, rent, or sell a property today?</div>
        <div class="msg user" style="animation-delay:0.4s">yeah i want to buy apartment in JB</div>
        <div class="msg bot" style="animation-delay:0.6s">Noted. What is your approximate budget for this apartment in Johor Bahru?</div>
        <div class="msg user" style="animation-delay:0.8s">around 300k</div>
        <div class="msg bot" style="animation-delay:1.0s">RM 300,000 — understood. Lastly, may I have your contact number or email so our agent can reach you?</div>
        <div class="msg user" style="animation-delay:1.2s">011-2345678</div>
        <div class="msg bot" style="animation-delay:1.4s">Thank you. Summary — Buy, RM 300k, Johor Bahru, 011-2345678. Our agent will be in touch shortly.</div>
        <div class="msg-time" style="animation-delay:1.4s">Lead saved to dashboard</div>
      </div>
    </div>
  </div>
</div>

<!-- FEATURES -->
<section id="features">
  <div class="section-tag reveal">Capabilities</div>
  <h2 class="section-title reveal">Built for real<br>business use.</h2>
  <div class="features">
    <div class="feature-card reveal" style="transition-delay:0.0s">
      <div class="feature-icon">🌐</div>
      <div class="feature-title">Bilingual support</div>
      <div class="feature-desc">Responds naturally in English and Bahasa Malaysia, detecting language automatically from the customer's input.</div>
    </div>
    <div class="feature-card reveal" style="transition-delay:0.05s">
      <div class="feature-icon">⚡</div>
      <div class="feature-title">Sub-second response</div>
      <div class="feature-desc">Gemini 2.5 Flash processes and replies to every message in under two seconds, keeping the conversation fluid.</div>
    </div>
    <div class="feature-card reveal" style="transition-delay:0.1s">
      <div class="feature-icon">🔁</div>
      <div class="feature-title">Auto retry logic</div>
      <div class="feature-desc">Built-in retry mechanism handles API rate limits and temporary outages without losing the customer conversation.</div>
    </div>
    <div class="feature-card reveal" style="transition-delay:0.15s">
      <div class="feature-icon">📋</div>
      <div class="feature-title">Structured lead data</div>
      <div class="feature-desc">Every completed conversation is parsed into clean fields — intent, budget, area, and contact — ready for the agent.</div>
    </div>
    <div class="feature-card reveal" style="transition-delay:0.2s">
      <div class="feature-icon">🔒</div>
      <div class="feature-title">Secure by design</div>
      <div class="feature-desc">All credentials stored as environment variables. No sensitive data in code. Webhook verification on every request.</div>
    </div>
    <div class="feature-card reveal" style="transition-delay:0.25s">
      <div class="feature-icon">♾</div>
      <div class="feature-title">Zero operational cost</div>
      <div class="feature-desc">Hosted on Render free tier. Meta WhatsApp Cloud API free tier. Gemini free quota. Total monthly cost: RM 0.</div>
    </div>
  </div>
</section>

<!-- GITHUB -->
<div class="github-section reveal">
  <div class="github-card">
    <div>
      <div class="github-label">Open Source</div>
      <div class="github-title">View the full source code</div>
      <p class="github-desc">This project was built as a final-year Industrial Training project at Multimedia University (MMU), Malaysia. The complete codebase — including Flask backend, AI integration, and deployment configuration — is available on GitHub.</p>
      <div class="github-meta">
        <div class="meta-item">
          <span class="meta-dot" style="background:#f59e0b"></span>
          Python
        </div>
        <div class="meta-item">
          <span class="meta-dot" style="background:#22c55e"></span>
          MIT License
        </div>
        <div class="meta-item">
          <span class="meta-dot" style="background:#3b82f6"></span>
          Active
        </div>
      </div>
    </div>
    <a href="https://github.com/kaymansrinivasan/propease-bot" target="_blank" class="github-btn">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z"/></svg>
      View on GitHub
    </a>
  </div>
</div>

<!-- FOOTER -->
<footer>
  <div class="footer-left">
    Built by <strong>Kayman Srinivasan</strong> — AI &amp; Data Science, Multimedia University (MMU) Malaysia<br>
    <span style="font-size:11px;margin-top:4px;display:block;">Final Year Industrial Training Project, 2026</span>
  </div>
  <div class="footer-right">
    <div>PropEase AI — WhatsApp Lead Automation</div>
    <div style="margin-top:4px;">Powered by Gemini 2.5 Flash &amp; Meta Cloud API</div>
  </div>
</footer>

<script>
  // Scroll reveal
  const reveals = document.querySelectorAll('.reveal');
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry, i) => {
      if (entry.isIntersecting) {
        setTimeout(() => entry.target.classList.add('visible'), i * 50);
      }
    });
  }, { threshold: 0.1 });
  reveals.forEach(el => observer.observe(el));

  // Smooth anchor scroll
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', e => {
      e.preventDefault();
      document.querySelector(a.getAttribute('href'))?.scrollIntoView({ behavior: 'smooth' });
    });
  });
</script>

</body>
</html>"""
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Lead Intelligence — PropEase AI</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --black: #080a0f;
    --surface: #0d1117;
    --surface2: #111720;
    --border: rgba(255,255,255,0.07);
    --border-bright: rgba(255,255,255,0.12);
    --text: #e8ecf0;
    --muted: #6b7280;
    --accent: #b8ff57;
    --accent-dim: rgba(184,255,87,0.08);
    --green: #22c55e;
    --blue: #4f8ef7;
    --amber: #f59e0b;
    --red: #ef4444;
  }

  body {
    font-family: 'DM Sans', sans-serif;
    background: var(--black);
    color: var(--text);
    min-height: 100vh;
  }

  /* SIDEBAR */
  .sidebar {
    position: fixed;
    top: 0; left: 0; bottom: 0;
    width: 220px;
    background: var(--surface);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    padding: 28px 0;
    z-index: 50;
  }

  .sidebar-logo {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 0 24px 28px;
    border-bottom: 1px solid var(--border);
    text-decoration: none;
  }

  .logo-mark {
    width: 32px; height: 32px;
    background: var(--accent);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 14px;
    color: #080a0f;
  }

  .logo-text {
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 15px;
    color: var(--text);
  }

  .sidebar-nav {
    padding: 20px 12px;
    flex: 1;
  }

  .nav-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    border-radius: 8px;
    font-size: 13px;
    color: var(--muted);
    text-decoration: none;
    transition: all 0.2s;
    cursor: pointer;
    margin-bottom: 2px;
  }

  .nav-item:hover { background: rgba(255,255,255,0.04); color: var(--text); }
  .nav-item.active { background: var(--accent-dim); color: var(--accent); }

  .nav-icon { font-size: 15px; width: 20px; text-align: center; }

  .sidebar-footer {
    padding: 20px 24px;
    border-top: 1px solid var(--border);
    font-size: 11px;
    color: var(--muted);
  }

  .status-dot {
    display: inline-block;
    width: 6px; height: 6px;
    background: var(--green);
    border-radius: 50%;
    margin-right: 6px;
    box-shadow: 0 0 6px var(--green);
    animation: pulse 2s ease-in-out infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }

  /* MAIN */
  .main {
    margin-left: 220px;
    padding: 0;
    min-height: 100vh;
  }

  /* TOPBAR */
  .topbar {
    padding: 20px 40px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: var(--surface);
    position: sticky;
    top: 0;
    z-index: 40;
  }

  .topbar-title {
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 18px;
    letter-spacing: -0.02em;
  }

  .topbar-right {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .export-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    background: transparent;
    border: 1px solid var(--border-bright);
    border-radius: 8px;
    color: var(--text);
    font-size: 13px;
    font-family: 'DM Sans', sans-serif;
    cursor: pointer;
    text-decoration: none;
    transition: all 0.2s;
  }
  .export-btn:hover { border-color: rgba(255,255,255,0.25); background: rgba(255,255,255,0.04); }

  /* CONTENT */
  .content {
    padding: 36px 40px;
  }

  /* STAT CARDS */
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 16px;
    margin-bottom: 32px;
  }

  .stat-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 24px;
    position: relative;
    overflow: hidden;
    transition: border-color 0.3s;
  }
  .stat-card:hover { border-color: var(--border-bright); }

  .stat-label {
    font-size: 11px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 12px;
    font-weight: 500;
  }

  .stat-value {
    font-family: 'Syne', sans-serif;
    font-size: 36px;
    font-weight: 800;
    letter-spacing: -0.03em;
    line-height: 1;
    margin-bottom: 8px;
  }

  .stat-sub {
    font-size: 12px;
    color: var(--muted);
  }

  .stat-bar {
    position: absolute;
    bottom: 0; left: 0; right: 0;
    height: 3px;
    background: var(--border);
    border-radius: 0 0 14px 14px;
    overflow: hidden;
  }

  .stat-bar-fill {
    height: 100%;
    border-radius: 0 0 14px 14px;
    transition: width 1s ease;
  }

  /* CHART SECTION */
  .charts-row {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 16px;
    margin-bottom: 32px;
  }

  .chart-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 28px;
  }

  .chart-title {
    font-family: 'Syne', sans-serif;
    font-size: 15px;
    font-weight: 700;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .chart-tag {
    font-size: 11px;
    font-weight: 400;
    font-family: 'DM Sans', sans-serif;
    color: var(--muted);
    background: rgba(255,255,255,0.04);
    padding: 4px 10px;
    border-radius: 100px;
    border: 1px solid var(--border);
  }

  /* DONUT CHART */
  .donut-wrap {
    display: flex;
    align-items: center;
    gap: 28px;
  }

  .donut-svg { flex-shrink: 0; }

  .donut-legend { flex: 1; }

  .legend-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 0;
    border-bottom: 1px solid var(--border);
  }
  .legend-item:last-child { border-bottom: none; }

  .legend-left {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 13px;
    color: var(--text);
  }

  .legend-dot {
    width: 10px; height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .legend-pct {
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 14px;
  }

  /* BAR CHART */
  .bar-chart {
    display: flex;
    align-items: flex-end;
    gap: 8px;
    height: 120px;
  }

  .bar-col {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    height: 100%;
    justify-content: flex-end;
  }

  .bar-fill {
    width: 100%;
    background: var(--accent-dim);
    border: 1px solid rgba(184,255,87,0.2);
    border-radius: 4px 4px 0 0;
    transition: height 1s ease;
    min-height: 4px;
  }

  .bar-label {
    font-size: 10px;
    color: var(--muted);
    text-align: center;
  }

  /* TABLE */
  .table-section {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    overflow: hidden;
  }

  .table-header {
    padding: 20px 28px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .table-title {
    font-family: 'Syne', sans-serif;
    font-size: 15px;
    font-weight: 700;
  }

  .table-count {
    font-size: 12px;
    color: var(--muted);
    background: rgba(255,255,255,0.04);
    border: 1px solid var(--border);
    padding: 4px 12px;
    border-radius: 100px;
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  thead th {
    padding: 12px 28px;
    text-align: left;
    font-size: 11px;
    font-weight: 500;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    border-bottom: 1px solid var(--border);
    background: rgba(255,255,255,0.015);
  }

  .lead-row td {
    padding: 16px 28px;
    border-bottom: 1px solid var(--border);
    font-size: 13px;
    vertical-align: middle;
    transition: background 0.2s;
  }

  .lead-row:last-child td { border-bottom: none; }
  .lead-row:hover td { background: rgba(255,255,255,0.02); }

  .name { font-weight: 500; color: var(--text); }
  .sub { font-size: 11px; color: var(--muted); margin-top: 3px; }
  .mono { font-family: 'DM Mono', monospace; font-size: 12px; color: var(--text); }
  .contact { color: var(--blue); }

  .badge {
    display: inline-flex;
    align-items: center;
    padding: 4px 10px;
    border-radius: 100px;
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.03em;
  }

  .empty-state {
    padding: 60px;
    text-align: center;
  }

  .empty-icon { font-size: 40px; margin-bottom: 16px; opacity: 0.3; }
  .empty-title { font-family: 'Syne', sans-serif; font-size: 18px; font-weight: 700; margin-bottom: 8px; color: var(--muted); }
  .empty-sub { font-size: 13px; color: var(--muted); }
</style>
</head>

<body>

<!-- SIDEBAR -->
<div class="sidebar">
  <a href="/" class="sidebar-logo">
    <div class="logo-mark">P</div>
    <div class="logo-text">PropEase AI</div>
  </a>
  <nav class="sidebar-nav">
    <a href="/" class="nav-item">
      <span class="nav-icon">⌂</span> Overview
    </a>
    <a href="/leads" class="nav-item active">
      <span class="nav-icon">◈</span> Lead Intelligence
    </a>
    <a href="https://github.com/kaymansrinivasan/propease-bot" target="_blank" class="nav-item">
      <span class="nav-icon">⌥</span> Source Code
    </a>
  </nav>
  <div class="sidebar-footer">
    <span class="status-dot"></span>Bot online
    <div style="margin-top:8px;line-height:1.5">
      Gemini 2.5 Flash<br>Meta Cloud API
    </div>
  </div>
</div>

<!-- MAIN -->
<div class="main">
  <div class="topbar">
    <div class="topbar-title">Lead Intelligence</div>
    <div class="topbar-right">
      <a href="/" class="export-btn">← Back to overview</a>
    </div>
  </div>

  <div class="content">

    <!-- STATS -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-label">Total Leads</div>
        <div class="stat-value">{{TOTAL}}</div>
        <div class="stat-sub">All time</div>
        <div class="stat-bar"><div class="stat-bar-fill" style="width:100%;background:var(--accent)"></div></div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Buyers</div>
        <div class="stat-value" style="color:var(--green)">{{BUY}}</div>
        <div class="stat-sub">{{BUY_PCT}}% of total</div>
        <div class="stat-bar"><div class="stat-bar-fill" style="width:{{BUY_PCT}}%;background:var(--green)"></div></div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Renters</div>
        <div class="stat-value" style="color:var(--blue)">{{RENT}}</div>
        <div class="stat-sub">{{RENT_PCT}}% of total</div>
        <div class="stat-bar"><div class="stat-bar-fill" style="width:{{RENT_PCT}}%;background:var(--blue)"></div></div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Sellers</div>
        <div class="stat-value" style="color:var(--amber)">{{SELL}}</div>
        <div class="stat-sub">{{SELL_PCT}}% of total</div>
        <div class="stat-bar"><div class="stat-bar-fill" style="width:{{SELL_PCT}}%;background:var(--amber)"></div></div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Today</div>
        <div class="stat-value" style="color:var(--accent)">{{TODAY}}</div>
        <div class="stat-sub">New leads</div>
        <div class="stat-bar"><div class="stat-bar-fill" style="width:60%;background:var(--accent)"></div></div>
      </div>
    </div>

    <!-- CHARTS -->
    <div class="charts-row">
      <div class="chart-card">
        <div class="chart-title">
          Intent Distribution
          <span class="chart-tag">All time</span>
        </div>
        <div class="bar-chart" id="barChart">
          <div class="bar-col">
            <div class="bar-fill" id="buyBar" style="height:0%"></div>
            <div class="bar-label">Buy</div>
          </div>
          <div class="bar-col">
            <div class="bar-fill" id="rentBar" style="height:0%;border-color:rgba(79,142,247,0.2);background:rgba(79,142,247,0.08)"></div>
            <div class="bar-label">Rent</div>
          </div>
          <div class="bar-col">
            <div class="bar-fill" id="sellBar" style="height:0%;border-color:rgba(245,158,11,0.2);background:rgba(245,158,11,0.08)"></div>
            <div class="bar-label">Sell</div>
          </div>
        </div>
      </div>

      <div class="chart-card">
        <div class="chart-title">Breakdown</div>
        <div class="donut-wrap">
          <svg class="donut-svg" width="100" height="100" viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="38" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="14"/>
            <circle cx="50" cy="50" r="38" fill="none" stroke="#22c55e" stroke-width="14"
              stroke-dasharray="{{BUY_PCT}} {{SELL_PCT_CALC}}" stroke-dashoffset="-25"
              stroke-linecap="round" transform="rotate(-90 50 50)"/>
            <circle cx="50" cy="50" r="38" fill="none" stroke="#4f8ef7" stroke-width="14"
              stroke-dasharray="{{RENT_PCT}} 100" stroke-dashoffset="-{{BUY_PCT_CALC}}"
              stroke-linecap="round" transform="rotate(-90 50 50)"/>
            <text x="50" y="46" text-anchor="middle" fill="#e8ecf0" font-size="14" font-family="Syne" font-weight="800">{{TOTAL}}</text>
            <text x="50" y="58" text-anchor="middle" fill="#6b7280" font-size="8" font-family="DM Sans">leads</text>
          </svg>
          <div class="donut-legend">
            <div class="legend-item">
              <div class="legend-left"><span class="legend-dot" style="background:#22c55e"></span>Buy</div>
              <span class="legend-pct" style="color:#22c55e">{{BUY_PCT}}%</span>
            </div>
            <div class="legend-item">
              <div class="legend-left"><span class="legend-dot" style="background:#4f8ef7"></span>Rent</div>
              <span class="legend-pct" style="color:#4f8ef7">{{RENT_PCT}}%</span>
            </div>
            <div class="legend-item">
              <div class="legend-left"><span class="legend-dot" style="background:#f59e0b"></span>Sell</div>
              <span class="legend-pct" style="color:#f59e0b">{{SELL_PCT}}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- TABLE -->
    <div class="table-section">
      <div class="table-header">
        <div class="table-title">All Leads</div>
        <div class="table-count">{{TOTAL}} records</div>
      </div>
      <table>
        <thead>
          <tr>
            <th>Customer</th>
            <th>Intent</th>
            <th>Budget</th>
            <th>Area</th>
            <th>Contact</th>
          </tr>
        </thead>
        <tbody>
          {{ROWS}}
        </tbody>
      </table>
      <div id="emptyState" style="display:{{EMPTY_DISPLAY}}">
        <div class="empty-state">
          <div class="empty-icon">◈</div>
          <div class="empty-title">No leads yet</div>
          <div class="empty-sub">Send "hi" to your WhatsApp bot number to generate the first lead.</div>
        </div>
      </div>
    </div>

  </div>
</div>

<script>
  // Animate bars on load
  const buyPct = {{BUY_PCT}};
  const rentPct = {{RENT_PCT}};
  const sellPct = {{SELL_PCT}};
  const total = {{TOTAL}};
  const max = Math.max(buyPct, rentPct, sellPct, 1);

  setTimeout(() => {
    document.getElementById('buyBar').style.height = ((buyPct/max)*90) + '%';
    document.getElementById('rentBar').style.height = ((rentPct/max)*90) + '%';
    document.getElementById('sellBar').style.height = ((sellPct/max)*90) + '%';
  }, 200);

  // Row animations
  document.querySelectorAll('.lead-row').forEach((row, i) => {
    row.style.opacity = '0';
    row.style.transform = 'translateY(10px)';
    row.style.transition = `opacity 0.4s ease ${i*0.05}s, transform 0.4s ease ${i*0.05}s`;
    setTimeout(() => {
      row.style.opacity = '1';
      row.style.transform = 'translateY(0)';
    }, 100 + i*50);
  });

  // Auto refresh every 30 seconds
  setTimeout(() => window.location.reload(), 30000);
</script>

</body>
</html>"""

@app.route("/")
def home():
    return Response(HOME_HTML, mimetype="text/html")

@app.route("/leads")
def leads_page():
    rows = ""
    for i, l in enumerate(reversed(leads)):
        intent_color = {"Buy": "#22c55e", "Rent": "#3b82f6", "Sell": "#f59e0b"}.get(l.get("intent",""), "#94a3b8")
        rows += f"""
        <tr class="lead-row">
            <td><span class="name">{l['name']}</span><br><span class="sub">{l['time']}</span></td>
            <td><span class="badge" style="background:{intent_color}20;color:{intent_color};border:1px solid {intent_color}40">{l['intent']}</span></td>
            <td class="mono">RM {l['budget']}</td>
            <td>{l['area']}</td>
            <td class="mono contact">{l['contact']}</td>
        </tr>"""
    buy_pct = round((stats['buy']/stats['total']*100) if stats['total'] else 0)
    rent_pct = round((stats['rent']/stats['total']*100) if stats['total'] else 0)
    sell_pct = round((stats['sell']/stats['total']*100) if stats['total'] else 0)
    empty_display = "none" if leads else "block"
    html = DASHBOARD_HTML
    html = html.replace("{{ROWS}}", rows)
    html = html.replace("{{TOTAL}}", str(stats['total']))
    html = html.replace("{{BUY}}", str(stats['buy']))
    html = html.replace("{{RENT}}", str(stats['rent']))
    html = html.replace("{{SELL}}", str(stats['sell']))
    html = html.replace("{{TODAY}}", str(stats['today']))
    html = html.replace("{{BUY_PCT}}", str(buy_pct))
    html = html.replace("{{RENT_PCT}}", str(rent_pct))
    html = html.replace("{{SELL_PCT}}", str(sell_pct))
    html = html.replace("{{SELL_PCT_CALC}}", str(100 - buy_pct))
    html = html.replace("{{BUY_PCT_CALC}}", str(buy_pct))
    html = html.replace("{{EMPTY_DISPLAY}}", empty_display)
    return Response(html, mimetype="text/html")

@app.route("/verify", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge"), 200
    return "Forbidden", 403

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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)