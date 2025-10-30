import json
import datetime
import pytz
import warnings
import random
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.error import NetworkError

# ---------- Timezone ----------
IST = pytz.timezone("Asia/Kolkata")

# ---------- Utility Functions ----------
def load_json(filename):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

# ---------- Chat Assistant Handler ----------
async def assistant_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now(IST)
    weekday = now.strftime("%A")
    current_time_obj = now.time()
    schedule = load_json("schedule.json")
    syllabus = load_json("syllabus.json")
    quotes = load_json("quotes.json").get("quotes", [])
    user_text = update.message.text.lower().strip()

    # Check if user is currently in a class
    in_class = None
    next_class = None
    class_duration = datetime.timedelta(minutes=60)  # Assume 1hr per class

    for cls in schedule.get(weekday, []):
        start_time_obj = datetime.datetime.strptime(cls["time"], "%H:%M").time()
        end_time = (datetime.datetime.combine(now.date(), start_time_obj) + class_duration).time()
        if start_time_obj <= current_time_obj < end_time:
            in_class = cls["subject"]
            break
        elif current_time_obj < start_time_obj:
            if (not next_class) or (start_time_obj < datetime.datetime.strptime(next_class["time"], "%H:%M").time()):
                next_class = cls

    try:
        if in_class:
            await update.message.reply_text(f"🎓 Listen to the class! You have {in_class} now.")
            return

        # Suggest actions if not in class
        if "what should i do" in user_text or "lost" in user_text or "confused" in user_text:
            suggestions = []
            for subj, info in syllabus.items():
                topics = info.get("topics", [])
                completed = info.get("completed", 0)
                pct = completed / (len(topics)*10) * 100 if topics else 0
                if pct < 100:
                    suggestions.append((subj, pct))
            if suggestions:
                # Suggest subject with lowest completion
                suggestions.sort(key=lambda x: x[1])
                study_subj, percent = suggestions[0]
                await update.message.reply_text(
                    f"🧭 How about reviewing **{study_subj}**? You're {percent:.1f}% done."
                )
            else:
                quote = random.choice(quotes) if quotes else "🌟 Great job! All syllabus complete. Take a break or revise."
                await update.message.reply_text(quote)
            return

        elif any(greet in user_text for greet in ["hello", "hi", "hey"]):
            await update.message.reply_text("Hello! How can I help you today?")
            return

        # Not in class and no specific query, suggest next scheduled class or revision
        if next_class:
            await update.message.reply_text(
                f"✅ No class right now! Next: {next_class['subject']} at {next_class['time']}."
            )
        else:
            # No more classes today
            suggestions = []
            for subj, info in syllabus.items():
                topics = info.get("topics", [])
                completed = info.get("completed", 0)
                pct = completed / (len(topics)*10) * 100 if topics else 0
                if pct < 100:
                    suggestions.append((subj, pct))
            if suggestions:
                suggestions.sort(key=lambda x: x[1])
                study_subj, percent = suggestions[0]
                await update.message.reply_text(
                    f"☑️ All classes are done! Suggestion: Revise **{study_subj}** ({percent:.1f}% done)."
                )
            else:
                quote = random.choice(quotes) if quotes else "🎉 Take a break or read something new!"
                await update.message.reply_text(quote)
    except NetworkError as e:
        print(f"NetworkError in assistant_chat: {e}")

# ---------- Basic Handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Received /start command")
    try:
        await update.message.reply_text(
            "👋 Hey! I'm your personal study assistant.\n\n"
            "I'll remind you about classes, help with decisions, and suggest what to study next!"
        )
    except NetworkError as e:
        print(f"NetworkError in /start: {e}")

async def holiday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.datetime.now(IST).strftime("%A")
    schedule_data = load_json("schedule.json")
    schedule_data[today] = []
    save_json("schedule.json", schedule_data)
    try:
        await update.message.reply_text(f"📅 Marked {today} as a holiday. No reminders today!")
    except NetworkError as e:
        print(f"NetworkError in /holiday: {e}")

# ---------- Motivation Job ----------
async def daily_motivation(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.data["chat_id"]
    quotes = load_json("quotes.json").get("quotes", [])
    quote = random.choice(quotes) if quotes else "🌞 Every day is a new chance to learn and grow!"
    try:
        await context.bot.send_message(chat_id=chat_id, text=quote)
    except NetworkError as e:
        print(f"NetworkError in daily_motivation: {e}")

# ---------- Main ----------
def main():
    TOKEN = "8405841092:AAGNKZTCDrtEgw8vfJst-FjwQfZPTqoFDWg"  # <-- Replace with your actual bot token!

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("holiday", holiday))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, assistant_chat))  # Smart chat assistant!

    jobq = app.job_queue
    chat_id = 1418401168  # <-- Replace with your actual chat ID!

    jobq.run_daily(daily_motivation, time=datetime.time(7, 0, tzinfo=IST), data={"chat_id": chat_id})

    print("✅ Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    main()

