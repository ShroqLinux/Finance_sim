from flask import Flask, render_template, request, jsonify, session
import os
import random

# Import your separated concerns
from market import get_data
from game import get_status

app = Flask(__name__)
app.secret_key = os.urandom(24)

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
        return jsonify({"error": f"No data found for {session['symbol']} starting five years ago. Try a different ticker like SPY or DIA."}), 400
        
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
    if amount <= 0:
        return jsonify({"error": "Trade amount must be greater than zero."}), 400

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

if __name__ == '__main__':
    app.run(debug=True, port=5001)