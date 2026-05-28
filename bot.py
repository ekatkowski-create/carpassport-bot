import os
import json
import asyncio
import gspread
from google.oauth2.service_account import Credentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# ─── CONFIG ───────────────────────────────────────────────
TELEGRAM_TOKEN = "8826146999:AAEhtybgUCzTGgnohvMxl3rhUwtyDM1eHgA"
SHEETS_ID = "1-J1d0jqSxCWntwoy1QL-MpX621vnrZ7gf3_xqmxuZdw"
YOUR_TELEGRAM_ID = None  # bus nustatytas pirmo /start metu

CATEGORIES = [
    ("suspension", "⚙️ Pakaba"),
    ("brakes", "🔴 Stabdžiai"),
    ("engine", "🔧 Variklio skyrius"),
    ("fuel", "⛽ Kuro sistema"),
    ("interior", "🪑 Salonas"),
    ("transmission", "⚡ Transmisija"),
    ("electrical", "💡 Elektrika"),
    ("tires", "🔵 Padangos / Ratai"),
    ("body", "🚙 Kėbulas"),
    ("other", "📦 Kita"),
]

# ─── GOOGLE SHEETS ────────────────────────────────────────
def get_sheets():
    creds_data = json.loads(os.environ.get("GOOGLE_CREDS", "{}"))
    scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_data, scopes=scopes)
    client = gspread.authorize(creds)
    sh = client.open_by_key(SHEETS_ID)
    try:
        cars_ws = sh.worksheet("cars")
    except:
        cars_ws = sh.add_worksheet("cars", 1000, 10)
        cars_ws.append_row(["car_id","make","model","year","mileage","color","vin","notes"])
    try:
        parts_ws = sh.worksheet("parts")
    except:
        parts_ws = sh.add_worksheet("parts", 5000, 10)
        parts_ws.append_row(["part_id","car_id","category","name","brand","install_date","mileage_at_install","note"])
    return cars_ws, parts_ws

def get_cars():
    cars_ws, _ = get_sheets()
    rows = cars_ws.get_all_records()
    return rows

def get_parts(car_id=None):
    _, parts_ws = get_sheets()
    rows = parts_ws.get_all_records()
    if car_id:
        rows = [r for r in rows if str(r.get("car_id")) == str(car_id)]
    return rows

def add_car(data):
    cars_ws, _ = get_sheets()
    import time
    car_id = f"car_{int(time.time())}"
    cars_ws.append_row([
        car_id,
        data.get("make",""),
        data.get("model",""),
        data.get("year",""),
        data.get("mileage",""),
        data.get("color",""),
        data.get("vin",""),
        data.get("notes",""),
    ])
    return car_id

def add_part(car_id, data):
    _, parts_ws = get_sheets()
    import time
    part_id = f"p_{int(time.time())}"
    parts_ws.append_row([
        part_id,
        car_id,
        data.get("category",""),
        data.get("name",""),
        data.get("brand",""),
        data.get("install_date",""),
        data.get("mileage_at_install",""),
        data.get("note",""),
    ])
    return part_id

def delete_car(car_id):
    cars_ws, parts_ws = get_sheets()
    # Delete car
    cars = cars_ws.get_all_values()
    for i, row in enumerate(cars):
        if row and row[0] == car_id:
            cars_ws.delete_rows(i+1)
            break
    # Delete all parts
    parts = parts_ws.get_all_values()
    rows_to_del = [i+1 for i, row in enumerate(parts) if row and row[1] == car_id]
    for row_idx in reversed(rows_to_del):
        parts_ws.delete_rows(row_idx)

def delete_part(part_id):
    _, parts_ws = get_sheets()
    parts = parts_ws.get_all_values()
    for i, row in enumerate(parts):
        if row and row[0] == part_id:
            parts_ws.delete_rows(i+1)
            break

# ─── STATES ───────────────────────────────────────────────
(
    MAIN_MENU, CAR_LIST, CAR_DETAIL, CAR_ADD_MAKE, CAR_ADD_MODEL,
    CAR_ADD_YEAR, CAR_ADD_MILEAGE, CAR_ADD_COLOR, CAR_ADD_VIN, CAR_ADD_NOTES,
    PART_CAT, PART_LIST, PART_ADD_NAME, PART_ADD_BRAND,
    PART_ADD_DATE, PART_ADD_MILEAGE, PART_ADD_NOTE,
) = range(17)

# ─── KEYBOARDS ────────────────────────────────────────────
def main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚗 Mano automobiliai", callback_data="cars")],
        [InlineKeyboardButton("➕ Pridėti automobilį", callback_data="add_car")],
        [InlineKeyboardButton("☕ Paremk – Ko-Fi", url="https://ko-fi.com/edgar4159")],
    ])

def cars_kb(cars):
    rows = [[InlineKeyboardButton(f"🚗 {c['make']} {c['model']} ({c['year']})", callback_data=f"car_{c['car_id']}")] for c in cars]
    rows.append([InlineKeyboardButton("➕ Pridėti automobilį", callback_data="add_car")])
    rows.append([InlineKeyboardButton("🏠 Pradžia", callback_data="home")])
    return InlineKeyboardMarkup(rows)

def car_detail_kb(car_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔧 Dalys / Mazgai", callback_data=f"parts_{car_id}")],
        [InlineKeyboardButton("➕ Pridėti dalį", callback_data=f"addpart_{car_id}")],
        [InlineKeyboardButton("🗑 Ištrinti automobilį", callback_data=f"delcar_{car_id}")],
        [InlineKeyboardButton("◀️ Atgal", callback_data="cars")],
    ])

def categories_kb(car_id):
    rows = []
    for cat_id, cat_label in CATEGORIES:
        rows.append([InlineKeyboardButton(cat_label, callback_data=f"cat_{car_id}_{cat_id}")])
    rows.append([InlineKeyboardButton("◀️ Atgal", callback_data=f"car_{car_id}")])
    return InlineKeyboardMarkup(rows)

def skip_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⏭ Praleisti", callback_data="skip")]])

def back_kb(target):
    return InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Atgal", callback_data=target)]])

# ─── HANDLERS ─────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text(
        "🔧 *CarPassport Bot*\n\nLabas! Čia tavo automobilių istorijos žurnalas.\nVisi duomenys saugomi Google Sheets.\n\nKą darome?",
        parse_mode="Markdown",
        reply_markup=main_kb()
    )
    return MAIN_MENU

async def home(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ctx.user_data.clear()
    await q.edit_message_text(
        "🔧 *CarPassport Bot*\n\nKą darome?",
        parse_mode="Markdown",
        reply_markup=main_kb()
    )
    return MAIN_MENU

async def show_cars(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    cars = get_cars()
    if not cars:
        await q.edit_message_text(
            "🚗 *Mano automobiliai*\n\nDar nėra automobilių. Pridėk pirmą!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Pridėti automobilį", callback_data="add_car")],
                [InlineKeyboardButton("🏠 Pradžia", callback_data="home")],
            ])
        )
    else:
        text = f"🚗 *Mano automobiliai* ({len(cars)})\n\nPassirink automobilį:"
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=cars_kb(cars))
    return CAR_LIST

async def show_car(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    car_id = q.data.replace("car_","")
    cars = get_cars()
    car = next((c for c in cars if c["car_id"] == car_id), None)
    if not car:
        await q.edit_message_text("Automobilis nerastas.", reply_markup=back_kb("cars"))
        return CAR_LIST
    parts = get_parts(car_id)
    ctx.user_data["current_car_id"] = car_id

    text = (
        f"🚗 *{car['make']} {car['model']}*\n\n"
        f"📅 Metai: {car.get('year','—')}\n"
        f"🔢 Rida: {car.get('mileage','—')} km\n"
        f"🎨 Spalva: {car.get('color','—')}\n"
        f"🔑 VIN: {car.get('vin','—')}\n"
        f"📝 Pastabos: {car.get('notes','—')}\n\n"
        f"🔧 *Dalys:* {len(parts)} įrašų"
    )
    await q.edit_message_text(text, parse_mode="Markdown", reply_markup=car_detail_kb(car_id))
    return CAR_DETAIL

async def show_parts(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    car_id = q.data.replace("parts_","")
    ctx.user_data["current_car_id"] = car_id
    await q.edit_message_text(
        "🔧 *Pasirink mazgą:*",
        parse_mode="Markdown",
        reply_markup=categories_kb(car_id)
    )
    return PART_CAT

async def show_category_parts(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, car_id, cat_id = q.data.split("_", 2)
    parts = get_parts(car_id)
    cat_parts = [p for p in parts if p.get("category") == cat_id]
    cat_label = next((l for c, l in CATEGORIES if c == cat_id), cat_id)

    if not cat_parts:
        text = f"{cat_label}\n\n_Dar nėra įrašų šiame mazge._"
    else:
        text = f"{cat_label}\n\n"
        for p in cat_parts:
            text += f"▪️ *{p['name']}*"
            if p.get('brand'): text += f" — {p['brand']}"
            if p.get('install_date'): text += f"\n   📅 {p['install_date']}"
            if p.get('mileage_at_install'): text += f" · 🔢 {p['mileage_at_install']} km"
            if p.get('note'): text += f"\n   📝 {p['note']}"
            text += f"\n   🗑 /delpart_{p['part_id']}\n\n"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Pridėti dalį", callback_data=f"addpart_{car_id}")],
        [InlineKeyboardButton("◀️ Mazgai", callback_data=f"parts_{car_id}")],
    ])
    await q.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    return PART_LIST

async def delete_part_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text.startswith("/delpart_"):
        part_id = text.replace("/delpart_","").strip()
        delete_part(part_id)
        await update.message.reply_text("✅ Dalis ištrinta!", reply_markup=main_kb())
    return MAIN_MENU

async def delete_car_btn(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    car_id = q.data.replace("delcar_","")
    cars = get_cars()
    car = next((c for c in cars if c["car_id"] == car_id), None)
    name = f"{car['make']} {car['model']}" if car else car_id
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"✅ Taip, ištrinti {name}", callback_data=f"confirmdelcar_{car_id}")],
        [InlineKeyboardButton("❌ Atšaukti", callback_data=f"car_{car_id}")],
    ])
    await q.edit_message_text(f"⚠️ Tikrai ištrinti *{name}*?\n\nVisi dalių įrašai bus prarasti!", parse_mode="Markdown", reply_markup=kb)
    return CAR_DETAIL

async def confirm_delete_car(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    car_id = q.data.replace("confirmdelcar_","")
    delete_car(car_id)
    await q.edit_message_text("✅ Automobilis ištrintas!", reply_markup=main_kb())
    return MAIN_MENU

# ─── ADD CAR FLOW ─────────────────────────────────────────
async def add_car_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ctx.user_data["new_car"] = {}
    await q.edit_message_text("🚗 *Naujas automobilis*\n\n1️⃣ Markė (pvz. BMW, Toyota):", parse_mode="Markdown")
    return CAR_ADD_MAKE

async def car_make(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["new_car"]["make"] = update.message.text.strip()
    await update.message.reply_text("2️⃣ Modelis (pvz. E46 320i):")
    return CAR_ADD_MODEL

async def car_model(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["new_car"]["model"] = update.message.text.strip()
    await update.message.reply_text("3️⃣ Metai:", reply_markup=skip_kb())
    return CAR_ADD_YEAR

async def car_year(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        ctx.user_data["new_car"]["year"] = ""
        await update.callback_query.edit_message_text("4️⃣ Rida (km):", reply_markup=skip_kb())
    else:
        ctx.user_data["new_car"]["year"] = update.message.text.strip()
        await update.message.reply_text("4️⃣ Rida (km):", reply_markup=skip_kb())
    return CAR_ADD_MILEAGE

async def car_mileage(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        ctx.user_data["new_car"]["mileage"] = ""
        await update.callback_query.edit_message_text("5️⃣ Spalva:", reply_markup=skip_kb())
    else:
        ctx.user_data["new_car"]["mileage"] = update.message.text.strip()
        await update.message.reply_text("5️⃣ Spalva:", reply_markup=skip_kb())
    return CAR_ADD_COLOR

async def car_color(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        ctx.user_data["new_car"]["color"] = ""
        await update.callback_query.edit_message_text("6️⃣ VIN numeris:", reply_markup=skip_kb())
    else:
        ctx.user_data["new_car"]["color"] = update.message.text.strip()
        await update.message.reply_text("6️⃣ VIN numeris:", reply_markup=skip_kb())
    return CAR_ADD_VIN

async def car_vin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        ctx.user_data["new_car"]["vin"] = ""
        await update.callback_query.edit_message_text("7️⃣ Pastabos (kada pirktas, iš ko...):", reply_markup=skip_kb())
    else:
        ctx.user_data["new_car"]["vin"] = update.message.text.strip()
        await update.message.reply_text("7️⃣ Pastabos:", reply_markup=skip_kb())
    return CAR_ADD_NOTES

async def car_notes(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        ctx.user_data["new_car"]["notes"] = ""
    else:
        ctx.user_data["new_car"]["notes"] = update.message.text.strip()

    data = ctx.user_data["new_car"]
    car_id = add_car(data)
    text = (
        f"✅ *Automobilis pridėtas!*\n\n"
        f"🚗 {data['make']} {data['model']}\n"
        f"📅 {data.get('year','—')} · 🔢 {data.get('mileage','—')} km\n"
        f"🎨 {data.get('color','—')} · VIN: {data.get('vin','—')}"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔧 Pridėti dalį", callback_data=f"addpart_{car_id}")],
        [InlineKeyboardButton("🚗 Visi automobiliai", callback_data="cars")],
        [InlineKeyboardButton("🏠 Pradžia", callback_data="home")],
    ])
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)
    return MAIN_MENU

# ─── ADD PART FLOW ────────────────────────────────────────
async def add_part_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    car_id = q.data.replace("addpart_","")
    ctx.user_data["new_part"] = {"car_id": car_id}
    ctx.user_data["current_car_id"] = car_id

    rows = []
    for i in range(0, len(CATEGORIES), 2):
        row = [InlineKeyboardButton(CATEGORIES[i][1], callback_data=f"setcat_{CATEGORIES[i][0]}")]
        if i+1 < len(CATEGORIES):
            row.append(InlineKeyboardButton(CATEGORIES[i+1][1], callback_data=f"setcat_{CATEGORIES[i+1][0]}"))
        rows.append(row)
    await q.edit_message_text("🔧 *Pasirink mazgą:*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(rows))
    return PART_ADD_NAME

async def part_set_cat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    cat_id = q.data.replace("setcat_","")
    ctx.user_data["new_part"]["category"] = cat_id
    cat_label = next((l for c,l in CATEGORIES if c==cat_id), cat_id)
    await q.edit_message_text(f"Mazgas: *{cat_label}*\n\n1️⃣ Dalies pavadinimas (pvz. Priekiniai amortizatoriai):", parse_mode="Markdown")
    return PART_ADD_NAME

async def part_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["new_part"]["name"] = update.message.text.strip()
    await update.message.reply_text("2️⃣ Prekės ženklas / modelis (pvz. Bilstein B6):", reply_markup=skip_kb())
    return PART_ADD_BRAND

async def part_brand(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        ctx.user_data["new_part"]["brand"] = ""
        await update.callback_query.edit_message_text("3️⃣ Keitimo data (pvz. 2024-03):", reply_markup=skip_kb())
    else:
        ctx.user_data["new_part"]["brand"] = update.message.text.strip()
        await update.message.reply_text("3️⃣ Keitimo data (pvz. 2024-03):", reply_markup=skip_kb())
    return PART_ADD_DATE

async def part_date(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        ctx.user_data["new_part"]["install_date"] = ""
        await update.callback_query.edit_message_text("4️⃣ Rida keitimo metu (km):", reply_markup=skip_kb())
    else:
        ctx.user_data["new_part"]["install_date"] = update.message.text.strip()
        await update.message.reply_text("4️⃣ Rida keitimo metu (km):", reply_markup=skip_kb())
    return PART_ADD_MILEAGE

async def part_mileage(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        ctx.user_data["new_part"]["mileage_at_install"] = ""
        await update.callback_query.edit_message_text("5️⃣ Pastaba:", reply_markup=skip_kb())
    else:
        ctx.user_data["new_part"]["mileage_at_install"] = update.message.text.strip()
        await update.message.reply_text("5️⃣ Pastaba:", reply_markup=skip_kb())
    return PART_ADD_NOTE

async def part_note(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        ctx.user_data["new_part"]["note"] = ""
    else:
        ctx.user_data["new_part"]["note"] = update.message.text.strip()

    data = ctx.user_data["new_part"]
    car_id = data["car_id"]
    add_part(car_id, data)
    cat_label = next((l for c,l in CATEGORIES if c==data.get("category","")), "")

    text = (
        f"✅ *Dalis pridėta!*\n\n"
        f"{cat_label}\n"
        f"▪️ *{data['name']}*"
        + (f" — {data['brand']}" if data.get('brand') else "")
        + (f"\n📅 {data['install_date']}" if data.get('install_date') else "")
        + (f" · 🔢 {data['mileage_at_install']} km" if data.get('mileage_at_install') else "")
        + (f"\n📝 {data['note']}" if data.get('note') else "")
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Dar viena dalis", callback_data=f"addpart_{car_id}")],
        [InlineKeyboardButton("🚗 Automobilis", callback_data=f"car_{car_id}")],
        [InlineKeyboardButton("🏠 Pradžia", callback_data="home")],
    ])
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)
    return MAIN_MENU

async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Atšaukta.", reply_markup=main_kb())
    return MAIN_MENU

# ─── MAIN ─────────────────────────────────────────────────
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(show_cars, pattern="^cars$"),
                CallbackQueryHandler(add_car_start, pattern="^add_car$"),
                CallbackQueryHandler(home, pattern="^home$"),
            ],
            CAR_LIST: [
                CallbackQueryHandler(show_car, pattern="^car_car_"),
                CallbackQueryHandler(add_car_start, pattern="^add_car$"),
                CallbackQueryHandler(home, pattern="^home$"),
            ],
            CAR_DETAIL: [
                CallbackQueryHandler(show_parts, pattern="^parts_"),
                CallbackQueryHandler(add_part_start, pattern="^addpart_"),
                CallbackQueryHandler(delete_car_btn, pattern="^delcar_"),
                CallbackQueryHandler(confirm_delete_car, pattern="^confirmdelcar_"),
                CallbackQueryHandler(show_cars, pattern="^cars$"),
                CallbackQueryHandler(home, pattern="^home$"),
            ],
            PART_CAT: [
                CallbackQueryHandler(show_category_parts, pattern="^cat_"),
                CallbackQueryHandler(add_part_start, pattern="^addpart_"),
                CallbackQueryHandler(show_car, pattern="^car_car_"),
            ],
            PART_LIST: [
                CallbackQueryHandler(add_part_start, pattern="^addpart_"),
                CallbackQueryHandler(show_parts, pattern="^parts_"),
            ],
            CAR_ADD_MAKE: [MessageHandler(filters.TEXT & ~filters.COMMAND, car_make)],
            CAR_ADD_MODEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, car_model)],
            CAR_ADD_YEAR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, car_year),
                CallbackQueryHandler(car_year, pattern="^skip$"),
            ],
            CAR_ADD_MILEAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, car_mileage),
                CallbackQueryHandler(car_mileage, pattern="^skip$"),
            ],
            CAR_ADD_COLOR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, car_color),
                CallbackQueryHandler(car_color, pattern="^skip$"),
            ],
            CAR_ADD_VIN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, car_vin),
                CallbackQueryHandler(car_vin, pattern="^skip$"),
            ],
            CAR_ADD_NOTES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, car_notes),
                CallbackQueryHandler(car_notes, pattern="^skip$"),
            ],
            PART_ADD_NAME: [
                CallbackQueryHandler(part_set_cat, pattern="^setcat_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, part_name),
            ],
            PART_ADD_BRAND: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, part_brand),
                CallbackQueryHandler(part_brand, pattern="^skip$"),
            ],
            PART_ADD_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, part_date),
                CallbackQueryHandler(part_date, pattern="^skip$"),
            ],
            PART_ADD_MILEAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, part_mileage),
                CallbackQueryHandler(part_mileage, pattern="^skip$"),
            ],
            PART_ADD_NOTE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, part_note),
                CallbackQueryHandler(part_note, pattern="^skip$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.Regex(r"^/delpart_"), delete_part_cmd))
    print("🚀 CarPassport Bot paleistas!")
    app.run_polling()

if __name__ == "__main__":
    main()
