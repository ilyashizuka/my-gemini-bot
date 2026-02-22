import os
import telebot
import google.generativeai as genai

# 1. Get keys from Render settings
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')

# 2. Configure the Gemini neural network (with the corrected model path)
genai.configure(api_key=GOOGLE_API_KEY)
# Added 'models/' before the name — this will solve the 404 problem
model = genai.GenerativeModel('models/gemini-1.5-flash')

# 3. Start the bot
bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        # "Typing..." status in Telegram
        bot.send_chat_action(message.chat.id, 'typing')
        
        # Request to the neural network
        response = model.generate_content(message.text)
        
        # Check: if the answer is empty (happens when blocked by security)
        if response.text:
            bot.reply_to(message, response.text)
        else:
            bot.reply_to(message, "The neural network was silent (security filters may have been triggered).")
        
    except Exception as e:
        # Output technical error to the chat for debugging
        error_text = str(e)
        bot.reply_to(message, f"Error from Google: {error_text}")
        print(f"Error in logs: {error_text}")

# Message to the Render console
print("The bot is running and ready to work!")

# Infinite work cycle
bot.infinity_polling()
