from flask import Flask, render_template, request, jsonify, session
import os
import yfinance as yf
import pandas as pd
import random
from datetime import datetime
from dateutil.relativedelta import relativedelta

app = Flask(__name__)
app.secret_key = os.urandom(24)

def get_data(symbol):
    try:
        # Calculate exactly 5 years ago from today
        five_years_ago = (datetime.now() - relativedelta(years=5)).strftime('%Y-%m-%d')
        
        df = yf.download(symbol, start=five_years_ago, interval="1mo", progress=False)
        if df.empty: return []
        if isinstance(df.columns, pd.MultiIndex): 
            df.columns = df.columns.get_level_values(0)
        df = df.reset_index()
        if 'Date' not in df.columns and 'index' in df.columns: 
            df = df.rename(columns={'index': 'Date'})
        df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
        df = df.rename(columns={'Close': 'price', 'Date': 'date'})
        return df[['date', 'price']].dropna().to_dict('records')
    except Exception as e:
        print(f"Data Fetch Error: {e}")
        return []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/init', methods=['POST'])
def init_game():
    data = request.json
    session["investing_cash"] = float(data.get("cash", 10000))
    session["checking_cash"] = 2000.0
    session["salary"] = float(data.get("salary", 4500))
    session["fixed_expenses"] = float(data.get("expenses", 2200))
    session["symbol"] = data.get("symbol", "SPY").upper()
    session["cum_earned"] = 0.0
    session["cum_spent"] = 0.0
    
    fetched_data = get_data(session["symbol"])
    if not fetched_data or len(fetched_data) == 0: 
        return jsonify({"error": f"No data found for {session['symbol']} starting in 2000. Try a different ticker like SPY or DIA."}), 400
        
    session["history"] = fetched_data
    session["current_step"] = 0
    session["portfolio"] = {session["symbol"]: 0}
    session["last_var_expense"] = 0
    session["event_message"] = ""
    return jsonify(get_status())

@app.route('/next', methods=['POST'])
def next_turn():
    history = session.get("history", [])
    step = session.get("current_step", 0)
    
    if step < len(history) - 1:
        session["current_step"] = step + 1
        session["fixed_expenses"] *= 1.0025 # Inflation
        
        var_expense = random.randint(100, 700)
        emergency = 0
        if session["current_step"] % 6 == 0:
            emergency = random.randint(1500, 2500)
            session["event_message"] = f"🚨 EMERGENCY: ${emergency} unexpected cost!"
        else:
            session["event_message"] = ""

        total_spent = session["fixed_expenses"] + var_expense + emergency
        session["checking_cash"] += (session["salary"] - total_spent)
        
        session["cum_earned"] += session["salary"]
        session["cum_spent"] += total_spent
        session["last_var_expense"] = var_expense
        
    return jsonify(get_status())

@app.route('/transfer', methods=['POST'])
def transfer():
    data = request.json
    amount = float(data.get("amount", 0))
    if amount > 0 and session["checking_cash"] >= amount:
        session["checking_cash"] -= amount
        session["investing_cash"] += amount
    elif amount < 0 and session["investing_cash"] >= abs(amount):
        session["investing_cash"] -= abs(amount)
        session["checking_cash"] += abs(amount)
    return jsonify(get_status())

@app.route('/trade', methods=['POST'])
def trade():
    data = request.json
    action, amount = data.get("action"), int(data.get("amount", 0))
    history = session.get("history", [])
    step = session.get("current_step", 0)
    symbol = session.get("symbol")
    portfolio = session.get("portfolio", {})
    
    # SAFETY CHECK
    if not history or step >= len(history):
        return jsonify({"error": "No market data available to trade."}), 400
    
    price = float(history[step]["price"])
    cost = amount * price

    if action == "buy" and session["investing_cash"] >= cost:
        session["investing_cash"] -= cost
        portfolio[symbol] = portfolio.get(symbol, 0) + amount
    elif action == "sell" and portfolio.get(symbol, 0) >= amount:
        session["investing_cash"] += cost
        portfolio[symbol] = portfolio.get(symbol, 0) - amount
    
    session["portfolio"] = portfolio
    return jsonify(get_status())

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

if __name__ == '__main__':
    app.run(debug=True, port=5001)