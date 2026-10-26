# 🇮🇳 BhashaSetu — WhatsApp Multilingual Chat (Powered by Sarvam AI)

An authentic WhatsApp Web clone that breaks language barriers across India for real-time one-to-one and group chats. People chat naturally in their native mother tongue, and every recipient instantly reads the message in their preferred language — with a 1-click toggle to view the original text.

Built for hackathons using **Sarvam AI** APIs, **FastAPI WebSockets**, and **Tailwind CSS**.

---

## 🌟 Key Features

- **Auto Language & Script Identification**: Uses Sarvam AI's Language Identification API (`client.text.identify_language`) to auto-detect input language and whether it was typed in native script (Devanagari, Tamil, Bengali) or **Roman script (Hinglish, Tanglish, etc.)**.
- **Roman Text & Hinglish Support**: Type naturally in Romanized script (e.g. *"mera naam abhinav hai"* or *"kya haal hai"*). Sarvam AI translates it directly into English (*"My name is Abhinav."*), Tamil (*"என் பெயர் அபிநவ்."*), or native Hindi (*"मेरा नाम अभिनव है।"*).
- **Real-Time Translation**: Powered by Sarvam AI's Translation API (`mayura:v1` & `sarvam-translate:v1`) supporting all 22 scheduled Indian languages + English.
- **WhatsApp Web UI**: Authentic WhatsApp interface with green branding (`#00a884`), chat doodle wallpaper, message bubbles, and blue double checkmarks (`✓✓`).
- **"View Original" Toggle**: Every translated message has a button to inspect the untranslated text and source script as typed by the sender.
- **Smart Translation Caching**: In-memory caching ensures that if multiple participants in a room share a language preference, Sarvam AI is queried once per unique language, maximizing speed and preserving API limits.
- **Multi-Room Support**: Switch between rooms (e.g. `#Global-Hackathon`, `#Developers-Lounge`).

---

## 📂 Project Structure

```
multilingual-chat/
├── .env.example        # Template for environment variables (API Key)
├── .gitignore          # Prevents committing secrets (.env) and caches
├── requirements.txt    # Project dependencies
├── main.py             # Quick verification script for Sarvam AI connection
├── translator.py       # Core Sarvam AI language detection & translation service
├── server.py           # FastAPI + WebSocket backend server
├── static/
│   └── index.html      # WhatsApp Web Single Page Application (Tailwind CSS)
└── README.md           # Documentation & setup guide
```

---

## 🚀 Setup & Installation

### 1. Prerequisites
- **Python 3.9+**
- A **Sarvam AI API Key** (Get one at [indus.sarvam.ai](https://indus.sarvam.ai/))

### 2. Clone the Repository
```bash
git clone https://github.com/your-username/multilingual-chat.git
cd multilingual-chat
```

### 3. Create & Activate a Virtual Environment
```bash
# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure Your Environment Variables
Copy the example environment file and add your Sarvam AI API Key:
```bash
cp .env.example .env
```
Open `.env` and set your key:
```env
SARVAM_API_KEY=your_actual_sarvam_api_key_here
```
> **Security Note**: `.env` is included in `.gitignore` and will never be committed to Git or pushed to GitHub.

---

## 🏃 Running the Application

### 1. Verify API Connection (Optional)
Run the test script to verify your Sarvam AI key:
```bash
python3 main.py
```

### 2. Start the Chat Server
```bash
python3 -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Open in Browser
Visit **[http://localhost:8000](http://localhost:8000)** in your browser.

---

## 🎭 Simulating a Multilingual Hackathon Demo

To test multi-user real-time translation on a single computer:

1. Open **Tab 1** ([http://localhost:8000](http://localhost:8000)):
   - Name: `Rahul`
   - Reading Language: `Hindi (हिंदी)`
2. Open **Tab 2** (or Incognito window):
   - Name: `Priya`
   - Reading Language: `Tamil (தமிழ்)`
3. Open **Tab 3**:
   - Name: `Alex`
   - Reading Language: `English`
4. Send a message from **Rahul** in Hindi:
   > *"अरे भाई! आज शाम को क्या प्लान है? क्या हम मैच देखने जा रहे हैं?"*
5. Instantly observe:
   - **Priya** sees: *"ஏய்! இன்னைக்கு சாயங்காலத்துக்கு உன்னோட திட்டம் என்ன? நாம ஆட்டத்துக்குப் போறோமா?"*
   - **Alex** sees: *"Hey! What's your plan for the evening? Are we going to the match?"*
   - Both can click **"View original (Hindi)"** to inspect Rahul's untranslated Hindi message.

---

## 🛡️ License
MIT License. Built for hackathons.
