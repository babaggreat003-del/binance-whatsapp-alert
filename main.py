import os
import requests
import pandas as pd
from flask import Flask, request, jsonify

app = Flask(__name__)

BINANCE_24HR_URL = "https://api.binance.com/api/v3/ticker/24hr"

def get_top_movers(limit=10):
    """Fetch top gainers and losers from Binance."""
    try:
        res = requests.get(BINANCE_24HR_URL, timeout=5)
        data = res.json()
        df = pd.DataFrame(data)
        
        # Filter active USDT trading pairs
        df = df[df['symbol'].str.endswith('USDT')]
        df = df[~df['symbol'].str.contains('UP|DOWN|BEAR|BULL|USDC|FDUSD|TUSD')]
        df['priceChangePercent'] = df['priceChangePercent'].astype(float)
        
        gainers = df.sort_values(by='priceChangePercent', ascending=False).head(limit)['symbol'].tolist()
        losers = df.sort_values(by='priceChangePercent', ascending=True).head(limit)['symbol'].tolist()
        
        return gainers, losers
    except Exception as e:
        print(f"[-] Error fetching Binance data: {e}")
        return [], []

@app.route('/', methods=['GET'])
def home():
    return "Binance Top Movers Webhook is Live and Ready!", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No JSON payload received"}), 400

    symbol = data.get("symbol", "").upper()
    action = data.get("action", "").upper()
    price = data.get("price", "N/A")
    tf = data.get("timeframe", "15m")

    # Fetch top movers in real-time from Binance
    top_gainers, top_losers = get_top_movers(limit=10)

    is_gainer = symbol in top_gainers
    is_loser = symbol in top_losers

    # Highlight alert in Cloud Server Logs
    print("\n" + "="*60)
    print("🚨 TRADINGVIEW REVERSAL SIGNAL RECEIVED 🚨")
    print(f"• Symbol:    {symbol}")
    print(f"• Action:    {action}")
    print(f"• Price:     ${price}")
    print(f"• Timeframe: {tf}")
    
    if is_gainer:
        print(f"🔥 ALERT: {symbol} is currently a TOP GAINER on Binance! High probability SHORT reversal setup.")
    elif is_loser:
        print(f"📉 ALERT: {symbol} is currently a TOP LOSER on Binance! High probability LONG bounce setup.")
    else:
        print(f"ℹ️ CONTEXT: {symbol} is neutral (Not in Binance Top 10 Gainers/Losers).")
    print("="*60 + "\n")

    return jsonify({"status": "success", "message": "Signal received and logged successfully!"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
