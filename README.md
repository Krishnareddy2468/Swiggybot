# Zomato Order Bot — AI Restaurant Ordering Assistant

An AI-powered food ordering bot that lets users browse restaurants, view menus, and place orders through natural conversation. Built with FastAPI, Next.js, Google Gemini AI, and Telegram Bot API.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Running the Application](#running-the-application)
- [Testing the Bot](#testing-the-bot)
- [API Endpoints](#api-endpoints)
- [How It Works](#how-it-works)
- [Challenges & Solutions](#challenges--solutions)

---

## Overview

This project implements a conversational AI bot that automates food ordering from Zomato. Instead of navigating the app manually, users can simply chat with the bot in plain English — search for restaurants, browse menus, add items to cart, and place orders.

The bot is accessible through two channels:
- **Web Chat** — A Next.js frontend with a modern dark-themed UI
- **Telegram** — Search for `@Zomatofoodbot` on Telegram

Since Zomato doesn't provide a public API, the project uses a **Mock Zomato MCP Server** with 10 real-style restaurants and 150+ menu items across Hyderabad locations.

---

## Architecture

```
                    +------------------+     +------------------+
                    |   Telegram App   |     |  Web Chat (Next) |
                    +--------+---------+     +--------+---------+
                             |                        |
                    Telegram Bot API            HTTP REST API
                             |                        |
                    +--------v------------------------v---------+
                    |              FastAPI Backend               |
                    |                (Port 8000)                 |
                    +-------------------------------------------+
                    |                                           |
                    |   +------------+    +-----------------+   |
                    |   | Chat Route |    | Restaurant Route|   |
                    |   +-----+------+    +--------+--------+   |
                    |         |                    |             |
                    |   +-----v--------------------v--------+   |
                    |   |         Gemini AI Agent            |   |
                    |   |  (Intent Detection + NLU Engine)   |   |
                    |   +--+----------+----------+----------+   |
                    |      |          |          |              |
                    |  +---v---+ +----v----+ +---v----------+  |
                    |  |Session| |Order    | |Restaurant    |  |
                    |  |Service| |Service  | |Service       |  |
                    |  +---+---+ +----+----+ +---+----------+  |
                    |      |          |          |              |
                    +------+----------+----------+--------------+
                           |          |          |
                    +------v---+ +----v----+ +---v--------------+
                    |In-Memory | |JSON File| |Mock Zomato Data  |
                    |Sessions  | |Orders   | |10 Restaurants    |
                    +----------+ +---------+ +------------------+
```

### Request Flow

1. User sends a message (via Telegram or Web Chat)
2. Message hits the FastAPI backend through the appropriate route
3. **Gemini AI Agent** analyzes the message to extract:
   - **Intent** (e.g., `search_restaurants`, `add_to_cart`, `checkout`)
   - **Entities** (e.g., location: "Madhapur", item: "Margherita", quantity: 2)
4. Based on the intent, the agent calls the relevant service
5. Response is formatted and sent back to the user
6. Session state is updated (conversation state machine)

### Conversation State Machine

```
IDLE --> SEARCHING --> BROWSING_MENU --> ORDERING --> AWAITING_ADDRESS --> CONFIRMING_ORDER --> ORDER_PLACED
  ^                                                                                              |
  +------ (start over) -------------------------------------------------------------------------+
```

Each state determines what kind of input the bot expects and how it responds.

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Backend | Python + FastAPI | Async support, auto-generated docs, Pydantic validation |
| Frontend | Next.js 16 (React) | SSR, fast dev server, component-based UI |
| AI/NLU | Google Gemini 2.0 Flash | Fast inference, good at structured JSON output |
| Messaging | python-telegram-bot | Official Telegram library with async support |
| Data Models | Pydantic v2 | Runtime validation for orders, sessions, cart items |
| Styling | Vanilla CSS | Full control, no framework overhead |

---

## Project Structure

```
GENAI Assignment/
├── backend/
│   ├── main.py                    # FastAPI entry point, CORS, lifecycle
│   ├── requirements.txt           # Python dependencies
│   └── app/
│       ├── models/
│       │   └── schemas.py         # Pydantic models (Order, Cart, Session)
│       ├── services/
│       │   ├── gemini_agent.py    # Core AI agent — NLU + response generation
│       │   ├── session_service.py # In-memory session management
│       │   ├── order_service.py   # Order placement + tracking simulation
│       │   ├── restaurant_service.py  # Restaurant search + menu lookup
│       │   └── telegram_bot.py    # Telegram bot handlers
│       ├── routes/
│       │   ├── chat.py            # POST /api/chat/message
│       │   └── restaurants.py     # GET /api/restaurants/
│       └── mock_data/
│           └── zomato_data.py     # 10 restaurants, 150+ items, Hyderabad
│
├── frontend/
│   ├── app/
│   │   ├── page.js                # Main chat interface
│   │   ├── layout.js              # Root layout
│   │   └── globals.css            # Full CSS (dark theme)
│   ├── package.json
│   └── next.config.mjs
│
├── .env                           # API keys (not committed)
├── .env.example                   # Template for env vars
├── .gitignore
└── README.md
```

---

## Setup & Installation

### Prerequisites

- Python 3.9+
- Node.js 18+
- A Google Gemini API key ([get one here](https://aistudio.google.com/apikey))
- A Telegram Bot Token ([create via @BotFather](https://t.me/BotFather))

### 1. Clone the Repository

```bash
git clone https://github.com/Krishnareddy2468/Zomato Bot.git
cd Zomato Bot
```

### 2. Set Up Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and add your keys:
```
GEMINI_API_KEY=your_gemini_api_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
```

### 3. Backend Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Frontend Setup

```bash
cd frontend
npm install
```

---

## Running the Application

### Start the Backend (Terminal 1)

```bash
cd backend
source venv/bin/activate
python main.py
```

The API will be available at `http://localhost:8000`. Swagger docs at `http://localhost:8000/docs`.

### Start the Frontend (Terminal 2)

```bash
cd frontend
npm run dev
```

The web chat will be available at `http://localhost:3000`.

Both need to be running simultaneously for the full experience.

---

## Testing the Bot

### Web Chat

1. Open `http://localhost:3000` in your browser
2. Click any suggestion card or type a message like "Show me restaurants in Madhapur"
3. Select a restaurant by number
4. Browse the menu and add items by number or name
5. Say "checkout" to start the order flow
6. Provide an address and confirm the order
7. Track the order status

### Telegram

1. Open Telegram and search for your bot (the username you set with @BotFather)
2. Send `/start` to begin
3. Use the same conversational flow as the web chat

### API Testing (curl)

```bash
# Health check
curl http://localhost:8000/

# Search restaurants
curl "http://localhost:8000/api/restaurants/?location=Madhapur"

# Send a chat message
curl -X POST http://localhost:8000/api/chat/message \
  -H "Content-Type: application/json" \
  -d '{"message": "show me pizza places", "user_id": "test1", "user_name": "Test"}'
```

### Sample Conversation Flow

```
User: Hi
Bot:  Welcome! I can help you order food. What are you craving?

User: Show me restaurants in Madhapur
Bot:  Here are the top restaurants:
      1. Meghana Foods (4.5 rating)
      2. Domino's Pizza (4.2 rating)
      ...

User: 1
Bot:  Menu - Meghana Foods
      1. Chicken Dum Biryani - Rs.299
      2. Andhra Chicken Curry Meals - Rs.249
      ...

User: 1
Bot:  Added to cart: 1x Chicken Dum Biryani
      Cart Total: Rs.338

User: checkout
Bot:  Please share your delivery address.

User: Plot 42, Madhapur, Hyderabad
Bot:  Order summary... Shall I place this order? Yes/No

User: yes
Bot:  Order Placed! Order ID: SWG070575EAE2
      Estimated delivery: 30-35 mins

User: track my order
Bot:  Order Status:
      * Order Confirmed
      * Being Prepared  <-- Current
      * Out for Delivery
      * Delivered
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check, service status |
| GET | `/docs` | Interactive API documentation (Swagger) |
| POST | `/api/chat/message` | Process a chat message |
| GET | `/api/chat/session/{user_id}` | Get session state |
| POST | `/api/chat/reset/{user_id}` | Reset user session |
| GET | `/api/restaurants/` | Search restaurants (query, location, cuisine) |
| GET | `/api/restaurants/locations` | List all available locations |
| GET | `/api/restaurants/cuisines` | List all cuisine types |
| GET | `/api/restaurants/{id}` | Get restaurant details with full menu |
| GET | `/api/restaurants/{id}/menu` | Get filtered menu |

---

## How It Works

### AI Intent Detection

The Gemini AI agent receives the user's message along with:
- Current conversation state
- Selected restaurant context (if any)
- Cart contents
- Recent conversation history (last 6 messages)

It returns a structured JSON with the detected intent and extracted entities. For example, the message "add 2 margherita pizza" returns:

```json
{
  "intent": "add_to_cart",
  "entities": {
    "items": [{"name": "margherita pizza", "quantity": 2}]
  }
}
```

If the Gemini API is unavailable, a keyword-based fallback parser handles the intent detection using pattern matching and the current session state.

### Mock Zomato Integration

Since Zomato doesn't expose a public API, I built a mock data layer that simulates what a real Zomato MCP Server would return. It includes:

- 10 restaurants across Hyderabad (Madhapur, HITEC City, Gachibowli, etc.)
- Real restaurant names (Domino's, Pizza Hut, Meghana Foods, McDonald's, etc.)
- 150+ menu items with prices, descriptions, veg/non-veg flags, ratings
- Delivery fees, time estimates, and promotional offers
- Fuzzy search across restaurant names, cuisines, and locations

### Order Simulation

When an order is placed, the system simulates the delivery lifecycle:
- Order Confirmed (immediate)
- Being Prepared (after ~30 seconds)
- Out for Delivery (after ~60 seconds)
- Delivered (after ~90 seconds)

On Telegram, the bot sends push notifications as the status changes. On the web, users can click "Refresh Status" to see updates.

---

## Challenges & Solutions

### 1. Substring Matching Bug in Fallback Parser

**Problem:** The keyword-based fallback parser matched "hi" as a substring inside words like "Shahi" (as in "Shahi Gulab Jamun"), incorrectly triggering a greeting response instead of an add-to-cart action.

**Solution:** Switched from substring matching (`"hi" in message`) to word-level matching using `set.intersection()` on split words. Also restructured the fallback logic to prioritize menu-state actions — when a user is browsing a menu, any unrecognized input defaults to add-to-cart rather than falling through to greeting detection.

### 2. Session Loss on Backend Reload

**Problem:** During development, editing backend files triggered uvicorn's auto-reload, which wiped all in-memory sessions. Users would add items to cart, then get "cart is empty" errors.

**Solution:** On the frontend side, I stored the user ID in `sessionStorage` so page reloads don't generate new IDs. The in-memory session approach is acceptable for a prototype — in production, this would use Redis or a database.

### 3. Gemini JSON Parsing

**Problem:** Gemini sometimes returns JSON wrapped in markdown code blocks (```json ... ```), causing parse failures.

**Solution:** Added a cleanup step that strips markdown fencing and the "json" language hint before parsing. If parsing still fails, the system falls back to the keyword-based parser.

### 4. Telegram Message Length Limits

**Problem:** Restaurant menus with 20+ items exceed Telegram's 4096 character limit per message.

**Solution:** Implemented automatic message splitting — long responses are chunked into parts under 4000 characters and sent sequentially. Markdown formatting is attempted first, with a plaintext fallback if parsing fails.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `TELEGRAM_BOT_TOKEN` | Yes | Telegram bot token from @BotFather |
| `PORT` | No | Backend port (default: 8000) |
| `NEXT_PUBLIC_API_URL` | No | Backend URL for frontend (default: http://localhost:8000) |

---

## License

This project was built as part of a technical assignment for an AI Full-Stack Developer position.
