from flask import Flask, render_template, request, jsonify, session
import os
import yfinance as yf
import pandas as pd

app = Flask(__name__)
# Secret key is required to use 'session'
app.secret_key = os.urandom(24)

def get_data(symbol):
    df = yf.download(symbol, period="5y", interval="1mo", progress=False)
    if df.empty:
        return []

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    df = df.reset_index()
    if 'Date' not in df.columns and 'index' in df.columns:
        df = df.rename(columns={'index': 'Date'})

    df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
    df = df.rename(columns={'Close': 'price', 'Date': 'date'})
    return df[['date', 'price']].dropna().to_dict('records')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/init', methods=['POST'])
def init_game():
    data = request.json
    
    # We store everything in 'session' instead of a global 'state'
    session["cash"] = float(data.get("cash", 10000))
    session["symbol"] = data.get("symbol", "SPY").upper()
    
    fetched_data = get_data(session["symbol"])
    if not fetched_data:
        return jsonify({"error": "Could not fetch data"}), 400
        
    session["history"] = fetched_data
    session["current_step"] = 0
    # Dictionary keys in session must be strings
    session["portfolio"] = {session["symbol"]: 0}
    
    return jsonify(get_status())

@app.route('/next', methods=['POST'])
def next_turn():
    # Update session step
    if session.get("current_step", 0) < len(session.get("history", [])) - 1:
        session["current_step"] += 1
    return jsonify(get_status())

@app.route('/trade', methods=['POST'])
def trade():
    data = request.json
    action = data.get("action")
    amount = int(data.get("amount", 0))
    
    # Pull current state from session
    history = session.get("history", [])
    step = session.get("current_step", 0)
    symbol = session.get("symbol")
    portfolio = session.get("portfolio", {})
    cash = session.get("cash", 0)

    current_price = float(history[step]["price"])
    cost = amount * current_price

    if action == "buy" and cash >= cost:
        cash -= cost
        portfolio[symbol] = portfolio.get(symbol, 0) + amount
    elif action == "sell" and portfolio.get(symbol, 0) >= amount:
        cash += cost
        portfolio[symbol] = portfolio.get(symbol, 0) - amount
    
    # Save changes back to session
    session["cash"] = cash
    session["portfolio"] = portfolio
        
    return jsonify(get_status())

def get_status():
    history = session.get("history", [])
    if not history:
        return {}
        
    step = session.get("current_step", 0)
    symbol = session.get("symbol")
    portfolio = session.get("portfolio", {})
    cash = session.get("cash", 0)
    
    current_data = history[step]
    shares = portfolio.get(symbol, 0)
    current_price = float(current_data["price"])
    holdings_value = shares * current_price
    
    pct_change = 0
    if step > 0:
        prev_price = float(history[step - 1]["price"])
        pct_change = ((current_price - prev_price) / prev_price) * 100
    
    return {
        "date": current_data["date"],
        "price": round(current_price, 2),
        "pct_change": round(pct_change, 2),
        "cash": round(cash, 2),
        "holdings": shares,
        "holdings_value": round(holdings_value, 2),
        "total_net_worth": round(cash + holdings_value, 2),
        "step": step
    }

if __name__ == '__main__':
    # When using sessions, the app needs to run with a stable environment
    app.run(debug=True, port=5001)