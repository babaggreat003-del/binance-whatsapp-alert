import os
import requests
import pandas as pd
from flask import Flask, request, jsonify
from twilio.rest import Client

app = Flask(__name__)

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.environ.get("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
YOUR_WHATSAPP_NUMBER = os.environ.get("YOUR_WHATSAPP_NUMBER")

BINANCE_24HR_URL = "https://api.binance.com/api/v3/ticker/24hr"

def send_whatsapp_alert(message_body):
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=message_body,
            to=YOUR_WHATSAPP_NUMBER
        )
        print(f"[+] WhatsApp message sent! SID: {message.sid}")
    except Exception as e:
        print(f"[-] Failed to send WhatsApp message: {e}")

def get_top_movers(limit=10):
    try:
        res = requests.get(BINANCE_24HR_URL, timeout=5)
        data = res.json()
        df = pd.DataFrame(data)
        
        df = df[df['symbol'].str.endswith('USDT')]
        df = df[~df['symbol'].str.contains('UP|DOWN|BEAR|BULL|USDC|FDUSD|TUSD')]
        df['priceChangePercent'] = df['priceChangePercent'].astype(float)
        
        gainers = df.sort_values(by='priceChangePercent', ascending=False).head(limit)['symbol'].tolist()
        losers = df.sort_values(by='priceChangePercent', ascending=True).head(limit)['symbol'].tolist()
        
        return gainers, losers
    except Exception as e:
        print(f"[-] Error fetching Binance data: {e}")
        return [], []

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No JSON payload received"}), 400

    symbol = data.get("symbol", "").upper()
    action = data.get("action", "").upper()
    price = data.get("price", "N/A")
    tf = data.get("timeframe", "15m")

    top_gainers, top_losers = get_top_movers(limit=10)

    is_gainer = symbol in top_gainers
    is_loser = symbol in top_losers

    msg = f"🚨 *TRADINGVIEW REVERSAL ALERT* 🚨\n\n"
    msg += f"• *Symbol:* {symbol}\n"
    msg += f"• *Signal:* {action}\n"
    msg += f"• *Price:* ${price}\n"
    msg += f"• *Timeframe:* {tf}\n\n"

    if is_gainer:
        msg += "🔥 *CONTEXT:* TOP GAINER on Binance! High probability SHORT setup."
    elif is_loser:
        msg += "📉 *CONTEXT:* TOP LOSER on Binance! High probability LONG bounce setup."
    else:
        msg += "ℹ️ *CONTEXT:* Neutral asset (Not in Top 10)."

    send_whatsapp_alert(msg)
    return jsonify({"status": "success", "message": "Alert processed"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
