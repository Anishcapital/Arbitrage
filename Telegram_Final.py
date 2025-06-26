import sys
import requests
from datetime import datetime

# YAHAN APNA TOKEN AUR CHAT ID DAALO
BOT_TOKEN = "7513614371:AAEkHD-IdRdWowP87bfhAebpKjK4ZzLpIzs"
CHAT_ID = "6143839190"

def send_alert(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    alert_text = f"""
🚨 ARBITRAGE ALERT 🚨

{message}

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    data = {
        "chat_id": CHAT_ID,
        "text": alert_text,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            print("✅ Telegram alert sent!")
        else:
            print(f"❌ Failed to send alert: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

def send_output_file(file_path="Output.txt", caption="Arbitrage Output File"):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    try:
        with open(file_path, "rb") as f:
            files = {"document": f}
            data = {
                "chat_id": CHAT_ID,
                "caption": f"{caption}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
            response = requests.post(url, data=data, files=files)
        if response.status_code == 200:
            print("✅ Output.txt sent as document!")
        else:
            print(f"❌ Failed to send document: {response.text}")
    except Exception as e:
        print(f"❌ Error sending file: {e}")

def send_positive_arbitrage_alerts(file_path="Output.txt"):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"❌ Could not read {file_path}: {e}")
        return

    positive_lines = []
    for line in lines:
        if "%" in line:
            try:
                percent = float(line.split("=")[-1].replace("%", "").strip())
                if percent > 0:
                    positive_lines.append(line.strip())
            except:
                continue

    if positive_lines:
        # Telegram message limit is 4096 chars, so send in chunks
        chunk = ""
        for line in positive_lines:
            if len(chunk) + len(line) > 3500:
                send_alert(chunk)
                chunk = ""
            chunk += line + "\n"
        if chunk.strip():
            send_alert(chunk)
    else:
        send_alert("No positive arbitrage opportunities found.")

if __name__ == "__main__":
    # Usage:
    # python Telegram_alert.py "custom message"
    # python Telegram_alert.py --outputfile
    # python Telegram_alert.py --positive

    if len(sys.argv) > 1:
        if sys.argv[1] == "--outputfile":
            send_output_file("Output.txt")
        elif sys.argv[1] == "--positive":
            send_positive_arbitrage_alerts("Output.txt")
        else:
            message = " ".join(sys.argv[1:])
            send_alert(message)
    else:
        # Test message
        send_alert("Test alert from Arbitrage Scanner")