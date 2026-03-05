"use client";

import { useState, useRef, useEffect, useCallback } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// parse bot messages - handles bold, line breaks, code
function renderBotText(text) {
  if (!text) return "";
  return text
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/━+/g, '<hr class="msg-divider"/>')
    .replace(/\n/g, "<br/>");
}

function timeNow() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

// quick suggestions that show up on the welcome screen
const SUGGESTIONS = [
  { emoji: "🍕", title: "Pizza in Madhapur", query: "Show me pizza places in Madhapur", desc: "Find the best pizzerias nearby" },
  { emoji: "🍗", title: "Biryani Restaurants", query: "I want biryani", desc: "Discover top biryani spots" },
  { emoji: "🍔", title: "Burgers & Fast Food", query: "Show me burger places", desc: "Quick bites and tasty burgers" },
  { emoji: "🥘", title: "South Indian Food", query: "Find South Indian restaurants in Kukatpally", desc: "Dosas, idlis, and more" },
];

const FEATURES = [
  { icon: "🔍", color: "orange", title: "Restaurant Search", desc: "Find by location, cuisine, or name" },
  { icon: "📋", color: "green", title: "Menu Browsing", desc: "Browse full menus with ratings" },
  { icon: "🛒", color: "blue", title: "Smart Ordering", desc: "Natural language order placement" },
  { icon: "📦", color: "purple", title: "Live Tracking", desc: "Real-time order status updates" },
];

// smart quick replies based on what the bot just said
function getQuickReplies(botMsg, state) {
  if (!botMsg) return [];
  const msg = botMsg.toLowerCase();

  if (msg.includes("reply with a restaurant number")) {
    return [
      { label: "1", query: "1" },
      { label: "2", query: "2" },
      { label: "3", query: "3" },
    ];
  }
  if (msg.includes("to order, just tell me")) {
    return [
      { label: "🟢 Show Veg Only", query: "show veg items only" },
      { label: "⭐ Bestsellers", query: "show bestsellers" },
    ];
  }
  if (msg.includes("add more items") || msg.includes("say \"checkout\"")) {
    return [
      { label: "✅ Checkout", query: "checkout" },
      { label: "📋 Show Menu", query: "show menu" },
      { label: "🛒 View Cart", query: "show cart" },
    ];
  }
  if (msg.includes("share your delivery address")) {
    return [
      { label: "📍 Plot 42, Madhapur", query: "Plot 42, Madhapur, Hyderabad 500081" },
    ];
  }
  if (msg.includes("reply *yes* to confirm")) {
    return [
      { label: "✅ Yes, Place Order", query: "yes" },
      { label: "❌ Cancel", query: "no" },
    ];
  }
  if (msg.includes("order placed")) {
    return [
      { label: "📦 Track Order", query: "track my order" },
      { label: "🔄 New Order", query: "start over" },
    ];
  }
  if (msg.includes("what are you craving") || msg.includes("what would you like")) {
    return [
      { label: "🍕 Pizza", query: "show me pizza places" },
      { label: "🍗 Biryani", query: "I want biryani" },
      { label: "🍔 Burgers", query: "show burger restaurants" },
    ];
  }
  // order tracking - show refresh button
  if (msg.includes("order status") || msg.includes("← current") || msg.includes("order confirmed") || msg.includes("being prepared") || msg.includes("out for delivery")) {
    const replies = [{ label: "🔄 Refresh Status", query: "track my order" }];
    if (msg.includes("delivered")) {
      replies.push({ label: "🍽️ New Order", query: "start over" });
    }
    return replies;
  }
  // reply with item number
  if (msg.includes("reply with item number")) {
    return [
      { label: "🟢 Show Veg Only", query: "show veg items only" },
    ];
  }
  return [];
}

export default function Home() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [cartItems, setCartItems] = useState([]);
  const [cartOpen, setCartOpen] = useState(false);
  const [currentRestaurant, setCurrentRestaurant] = useState(null);
  const [quickReplies, setQuickReplies] = useState([]);
  const [showScrollBtn, setShowScrollBtn] = useState(false);
  const messagesEndRef = useRef(null);
  const messagesContainerRef = useRef(null);
  const inputRef = useRef(null);

  // keep user id across page reloads
  const userId = useRef(
    typeof window !== "undefined"
      ? sessionStorage.getItem("bot_user_id") || (() => {
        const id = `web_${Date.now()}`;
        sessionStorage.setItem("bot_user_id", id);
        return id;
      })()
      : `web_${Date.now()}`
  );

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, scrollToBottom]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // show "scroll to bottom" if user scrolls up
  const handleScroll = useCallback(() => {
    const container = messagesContainerRef.current;
    if (!container) return;
    const distFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
    setShowScrollBtn(distFromBottom > 150);
  }, []);

  const sendMessage = async (text) => {
    if (!text.trim() || isLoading) return;

    const userMsg = { role: "user", content: text.trim(), time: timeNow() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setQuickReplies([]);
    setIsLoading(true);

    try {
      const res = await fetch(`${API_URL}/api/chat/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text.trim(),
          user_id: userId.current,
          user_name: "Guest",
        }),
      });

      if (!res.ok) throw new Error("API error");
      const data = await res.json();

      const botMsg = { role: "bot", content: data.response, time: timeNow() };
      setMessages((prev) => [...prev, botMsg]);

      if (data.cart_items) setCartItems(data.cart_items);
      if (data.restaurant) setCurrentRestaurant(data.restaurant);

      // generate contextual quick replies
      const replies = getQuickReplies(data.response, data.state);
      setQuickReplies(replies);
    } catch (error) {
      console.error("Error:", error);
      setMessages((prev) => [
        ...prev,
        {
          role: "bot",
          content: "Couldn't connect to the server. Make sure the backend is running on http://localhost:8000\n\nRun: `cd backend && source venv/bin/activate && python main.py`",
          time: timeNow(),
        },
      ]);
      setQuickReplies([]);
    } finally {
      setIsLoading(false);
      // refocus input after sending
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage(input);
  };

  const handleNewChat = () => {
    setMessages([]);
    setCartItems([]);
    setCurrentRestaurant(null);
    setQuickReplies([]);
    // clear the stored session so we get a fresh one
    const newId = `web_${Date.now()}`;
    userId.current = newId;
    if (typeof window !== "undefined") sessionStorage.setItem("bot_user_id", newId);
  };

  const cartSubtotal = cartItems.reduce((sum, item) => sum + item.price * item.quantity, 0);
  const cartTax = Math.round(cartSubtotal * 0.05);
  const cartDelivery = currentRestaurant ? 35 : 0;
  const cartTotal = cartSubtotal + cartTax + cartDelivery;

  return (
    <div className="app-container">
      {/* sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="sidebar-logo">
            <div className="sidebar-logo-icon">🍕</div>
            <div>
              <h1>Swiggy Bot</h1>
              <p>AI Food Assistant</p>
            </div>
          </div>
        </div>

        <div className="sidebar-features">
          <div className="sidebar-section-title">Features</div>
          {FEATURES.map((f, i) => (
            <div className="feature-card" key={i}>
              <div className={`feature-card-icon ${f.color}`}>{f.icon}</div>
              <div>
                <h3>{f.title}</h3>
                <p>{f.desc}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="sidebar-quick-actions">
          <button className="quick-action-btn" onClick={() => sendMessage("help")}>
            ❓ Show Help
          </button>
          <button className="quick-action-btn" onClick={handleNewChat}>
            🔄 New Conversation
          </button>
        </div>
      </aside>

      {/* main chat */}
      <main className="main-content">
        <header className="chat-header">
          <div className="chat-header-left">
            <h2>🤖 Swiggy AI Assistant</h2>
            <div className="header-status">
              <div className="status-dot" />
              <span>Online</span>
            </div>
          </div>
          <div className="header-actions">
            {cartItems.length > 0 && (
              <button className="header-btn" onClick={() => setCartOpen(!cartOpen)} id="cart-toggle-btn">
                🛒 Cart ({cartItems.length})
              </button>
            )}
            <button className="header-btn" onClick={handleNewChat} id="new-chat-btn">
              🔄 New Chat
            </button>
          </div>
        </header>

        <div className="messages-container" ref={messagesContainerRef} onScroll={handleScroll}>
          {messages.length === 0 ? (
            <div className="welcome-screen">
              <div className="welcome-icon">🍽️</div>
              <h2>What are you craving today?</h2>
              <p>
                I&apos;m your AI food ordering assistant. Search restaurants,
                browse menus, and place orders — all through natural conversation!
              </p>
              <div className="welcome-suggestions">
                {SUGGESTIONS.map((s, i) => (
                  <div className="suggestion-card" key={i} onClick={() => sendMessage(s.query)} id={`suggestion-${i}`}>
                    <div className="suggestion-card-emoji">{s.emoji}</div>
                    <h4>{s.title}</h4>
                    <p>{s.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="messages-inner">
              {messages.map((msg, i) => (
                <div className={`message ${msg.role}`} key={i}>
                  <div className="message-avatar">
                    {msg.role === "bot" ? "🤖" : "👤"}
                  </div>
                  <div>
                    <div
                      className="message-bubble"
                      dangerouslySetInnerHTML={{ __html: renderBotText(msg.content) }}
                    />
                    <div className="message-time">{msg.time}</div>
                  </div>
                </div>
              ))}

              {isLoading && (
                <div className="typing-indicator">
                  <div className="message-avatar" style={{ background: "var(--brand-soft)" }}>🤖</div>
                  <div className="typing-dots">
                    <div className="typing-dot" />
                    <div className="typing-dot" />
                    <div className="typing-dot" />
                  </div>
                </div>
              )}

              {/* quick reply chips */}
              {!isLoading && quickReplies.length > 0 && (
                <div className="quick-replies">
                  {quickReplies.map((qr, i) => (
                    <button key={i} className="quick-reply-btn" onClick={() => sendMessage(qr.query)}>
                      {qr.label}
                    </button>
                  ))}
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}

          {showScrollBtn && messages.length > 0 && (
            <button className="scroll-bottom-btn" onClick={scrollToBottom}>
              ↓
            </button>
          )}
        </div>

        {/* input */}
        <div className="input-container">
          <form className="input-wrapper" onSubmit={handleSubmit}>
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={
                isLoading
                  ? "Thinking..."
                  : "Type your message... (e.g. 'Show me pizza places')"
              }
              disabled={isLoading}
              id="chat-input"
            />
            <button type="submit" className="send-btn" disabled={!input.trim() || isLoading} id="send-btn">
              ↑
            </button>
          </form>
          <div className="input-hint">AI-powered food ordering • Also available on Telegram</div>
        </div>
      </main>

      {/* cart panel */}
      <div className={`cart-panel ${cartOpen ? "open" : ""}`}>
        <div className="cart-panel-inner">
          <div className="cart-header">
            <h3>🛒 Your Cart</h3>
            <button className="cart-close-btn" onClick={() => setCartOpen(false)} id="cart-close-btn">✕</button>
          </div>

          {currentRestaurant && (
            <div style={{ marginBottom: "16px", fontSize: "13px", color: "var(--text-secondary)" }}>
              {currentRestaurant.image} {currentRestaurant.name}
              <br />
              <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                ⭐ {currentRestaurant.rating} • {currentRestaurant.delivery_time}
              </span>
            </div>
          )}

          <div className="cart-items">
            {cartItems.length === 0 ? (
              <p style={{ color: "var(--text-muted)", fontSize: "13px", textAlign: "center", padding: "40px 0" }}>
                Your cart is empty
              </p>
            ) : (
              cartItems.map((item, i) => (
                <div className="cart-item" key={i}>
                  <div className="cart-item-info">
                    <h4>{item.is_veg ? "🟢" : "🔴"} {item.name}</h4>
                    <p>{item.size ? `${item.size} • ` : ""}Qty: {item.quantity}</p>
                  </div>
                  <div className="cart-item-price">₹{item.price * item.quantity}</div>
                </div>
              ))
            )}
          </div>

          {cartItems.length > 0 && (
            <div className="cart-total">
              <div className="cart-total-row"><span>Subtotal</span><span>₹{cartSubtotal}</span></div>
              <div className="cart-total-row"><span>GST (5%)</span><span>₹{cartTax}</span></div>
              <div className="cart-total-row"><span>Delivery</span><span>₹{cartDelivery}</span></div>
              <div className="cart-total-row total"><span>Total</span><span>₹{cartTotal}</span></div>
              <button className="checkout-btn" onClick={() => { setCartOpen(false); sendMessage("checkout"); }}>
                Proceed to Checkout →
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
