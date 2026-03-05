# 🍕 AI Restaurant Order Bot

An AI-powered restaurant order automation bot that connects to Swiggy (simulated) and enables customers to place orders through **Telegram** or a **Web Chat Interface** using natural language conversation.

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────────────────────────┐
│                 │     │         FastAPI Backend (Python)      │
│   Telegram      │◄───►│                                      │
│   Bot API       │     │  ┌──────────────────────────────────┐│
│                 │     │  │ Google Gemini AI Agent            ││
└─────────────────┘     │  │ (Natural Language Understanding)  ││
                        │  └──────────┬───────────────────────┘│
┌─────────────────┐     │             │                        │
│                 │     │  ┌──────────▼───────────────────────┐│
│   Next.js       │◄───►│  │ Services Layer                   ││
│   Web Chat UI   │     │  │ • Restaurant Service (Mock API)  ││
│                 │     │  │ • Order Service                  ││
└─────────────────┘     │  │ • Session Service                ││
                        │  └──────────────────────────────────┘│
                        └──────────────────────────────────────┘
```

## 🚀 Tech Stack

| Component | Technology |
|-----------|-----------|
| **Frontend** | Next.js (React), Vanilla CSS |
| **Backend** | FastAPI (Python) |
| **AI/LLM** | Google Gemini 2.0 Flash |
| **Messaging** | Telegram Bot API |
| **Food Platform** | Mock Swiggy MCP Server |
| **Data** | In-memory + JSON persistence |

## ✨ Features

### 🔍 Restaurant Discovery
- Search by location, cuisine type, or restaurant name
- View ratings, delivery time, pricing, and offers
- Filter vegetarian restaurants

### 📋 Menu Browsing
- Complete menu with categories
- Veg/Non-veg indicators (🟢/🔴)
- Bestseller badges
- Dietary filters

### 🛒 Order Placement
- Natural language order parsing
- Multi-item ordering in one message
- Cart management (add/remove/modify)
- Order summary with itemized pricing
- Tax and delivery fee calculation

### 📦 Order Tracking
- Real-time status simulation
- Status: Confirmed → Preparing → Out for Delivery → Delivered
- Delivery partner details
- Proactive status notifications (Telegram)

### 🤖 Conversational AI
- Context-aware multi-turn conversations
- Natural language variations support
- Clarifying questions for ambiguity
- Graceful error handling

## 📋 Prerequisites

- **Python** 3.10+
- **Node.js** 18+
- **npm**
- **Google Gemini API Key** (get from https://aistudio.google.com/apikey)
- **Telegram Bot Token** (optional, get from @BotFather)

## 🛠️ Setup & Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd "GENAI Assignment"
```

### 2. Configure Environment Variables
```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Backend Setup (FastAPI)
```bash
# Create virtual environment
cd backend
python -m venv venv
source venv/bin/activate  # macOS/Linux
# On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the server
python main.py
```

The backend will start on `http://localhost:8000`

### 4. Frontend Setup (Next.js)
```bash
# In a new terminal
cd frontend
npm install
npm run dev
```

The frontend will start on `http://localhost:3000`

### 5. Telegram Bot Setup (Optional)
1. Talk to **@BotFather** on Telegram
2. Create a new bot with `/newbot`
3. Copy the bot token
4. Add it to `.env` as `TELEGRAM_BOT_TOKEN`
5. Restart the backend
6. Start chatting with your bot on Telegram!

## 🧪 Testing

### Web Chat
1. Open `http://localhost:3000`
2. Click a suggestion card or type a message
3. Try the complete flow:
   - "Show me pizza places in Koramangala"
   - Select a restaurant (e.g., "1" or "Domino's")
   - "1 Farmhouse Pizza and 1 Garlic Bread"
   - "Checkout"
   - Provide address: "123 MG Road, Koramangala, Bangalore"
   - "Yes" to confirm

### Telegram Bot
1. Find your bot on Telegram
2. Send `/start`
3. Follow the same conversational flow

### API Endpoints
- `GET http://localhost:8000/` — Health check
- `GET http://localhost:8000/docs` — Swagger API docs
- `POST http://localhost:8000/api/chat/message` — Send chat message
- `GET http://localhost:8000/api/restaurants/` — List restaurants
- `GET http://localhost:8000/api/restaurants/{id}/menu` — Get menu

## 📁 Project Structure

```
GENAI Assignment/
├── backend/                    # FastAPI Python Backend
│   ├── app/
│   │   ├── mock_data/
│   │   │   └── swiggy_data.py  # Mock restaurant & menu data
│   │   ├── models/
│   │   │   └── schemas.py      # Pydantic data models
│   │   ├── routes/
│   │   │   ├── chat.py         # Chat API endpoints
│   │   │   └── restaurants.py  # Restaurant API endpoints
│   │   └── services/
│   │       ├── gemini_agent.py   # 🧠 AI brain (Gemini integration)
│   │       ├── order_service.py  # Order management
│   │       ├── restaurant_service.py # Restaurant search
│   │       ├── session_service.py    # Session management
│   │       └── telegram_bot.py   # Telegram bot integration
│   ├── main.py                 # FastAPI entry point
│   └── requirements.txt
├── frontend/                   # Next.js Web Interface
│   ├── app/
│   │   ├── globals.css         # Design system & styles
│   │   ├── layout.js           # Root layout
│   │   └── page.js             # Main chat interface
│   └── package.json
├── data/                       # Persisted order data
├── .env.example                # Environment template
├── .gitignore
└── README.md
```

## 🎯 Key Design Decisions

1. **Gemini AI + Fallback**: Uses Google Gemini for NLU with keyword-based fallback when AI is unavailable
2. **State Machine**: Conversation flow managed via explicit states (IDLE → SEARCHING → BROWSING → ORDERING → etc.)
3. **Mock Swiggy API**: Realistic restaurant data with 10 Bangalore restaurants and full menus
4. **Dual Interface**: Both Telegram bot and web chat share the same AI agent and business logic
5. **Order Simulation**: Async order progress simulation with real-time status updates

## 🔧 Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| Swiggy API not publicly available | Created realistic mock MCP server with 10 restaurants |
| Natural language ambiguity | Gemini AI with structured intent extraction + fallback parser |
| Maintaining conversation context | Session service with state machine + history |
| Real-time order updates | Async background tasks with Telegram push notifications |
| Complex menu parsing | Fuzzy matching for item search across categories |

## 📝 License

MIT License - Free to use and modify.
