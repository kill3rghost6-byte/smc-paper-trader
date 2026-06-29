import os
import requests
import time

TOKEN = "8233036914:AAF699ijYWDwJebEKu__CH6QUrNvLx2TPnA"
URL = f"https://api.telegram.org/bot{TOKEN}/getUpdates"

print("Waiting for user to send a message to the bot...")

while True:
    try:
        resp = requests.get(URL).json()
        if resp.get("ok") and len(resp.get("result", [])) > 0:
            chat_id = resp["result"][-1]["message"]["chat"]["id"]
            print(f"Got chat_id: {chat_id}")
            
            # Set GH Secrets
            os.system(f"gh secret set TELEGRAM_BOT_TOKEN --body '{TOKEN}'")
            os.system(f"gh secret set TELEGRAM_CHAT_ID --body '{chat_id}'")
            
            # Send confirmation
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={
                "chat_id": chat_id,
                "text": "✅ ارتباط با موفقیت برقرار شد!\n\nربات SMC شما رسماً متصل شد. از این لحظه به بعد، تمامی سیگنال‌های لایو، آپدیت اردرهای لیمیت و وضعیت کیف‌پول مجازی (Paper Trading) را مستقیماً همینجا دریافت خواهید کرد. 🚀"
            })
            break
    except Exception as e:
        print(e)
    time.sleep(3)

print("Telegram setup complete!")
