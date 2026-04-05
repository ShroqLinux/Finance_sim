from flask import session
import random

def get_status():
    history = session.get("history", [])
    step = session.get("current_step", 0)
    
    if not history: return {"error": "Game not initialized"}
    
    symbol = session.get("symbol")
    portfolio = session.get("portfolio", {})
    curr = history[step]
    price = float(curr["price"])
    shares = portfolio.get(symbol, 0)
    h_val = shares * price
    
    pct_change = 0
    if step > 0:
        prev_price = float(history[step - 1]["price"])
        pct_change = ((price - prev_price) / prev_price) * 100

    first_price = float(history[0]["price"])
    total_market_roi = ((price - first_price) / first_price) * 100
    savings_rate = ((session["cum_earned"] - session["cum_spent"]) / session["cum_earned"] * 100) if session["cum_earned"] > 0 else 0

    headlines = ["Stable markets.", "High volatility.", "Bullish run!", "Bearish slide."]
    if pct_change > 2: headline = "🚀 " + headlines[2]
    elif pct_change < -2: headline = "📉 " + headlines[3]
    else: headline = "📰 " + random.choice(headlines[:2])

    return {
        "date": curr["date"], "price": round(price, 2), "pct_change": round(pct_change, 2),
        "investing_cash": round(session["investing_cash"], 2), "checking_cash": round(session["checking_cash"], 2),
        "last_var_expense": session["last_var_expense"], "event_message": session.get("event_message", ""),
        "holdings": shares, "holdings_value": round(h_val, 2),
        "net_worth": round(session["investing_cash"] + session["checking_cash"] + h_val, 2),
        "step": step, "headline": headline,
        "report": {
            "show": step > 0 and step % 6 == 0,
            "earned": round(session["cum_earned"], 2), "spent": round(session["cum_spent"], 2),
            "savings_rate": round(savings_rate, 1), "market_roi": round(total_market_roi, 1)
        }
    }