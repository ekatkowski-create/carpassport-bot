# 🔧 CarPassport Bot — Setup instrukcija

## Kas reikia prieš pradedant
- ✅ Telegram Bot Token (jau turi)
- ✅ Google Sheets ID (jau turi)
- ✅ Google Service Account JSON (jau turi)

---

## 1 ŽINGSNIS — GitHub (2 min)

1. Eik į **github.com** → prisijunk / sukurk paskyrą
2. Spausk **"New repository"**
3. Pavadinimas: `carpassport-bot`
4. Pasirink **Private**
5. Spausk **"Create repository"**
6. Spausk **"uploading an existing file"**
7. Įkelk šiuos failus:
   - `bot.py`
   - `requirements.txt`
   - `railway.toml`
8. Spausk **"Commit changes"**

---

## 2 ŽINGSNIS — Railway (5 min)

1. Eik į **railway.app**
2. Prisijunk su GitHub
3. Spausk **"New Project"** → **"Deploy from GitHub repo"**
4. Pasirink `carpassport-bot`
5. Spausk **"Deploy Now"**

---

## 3 ŽINGSNIS — Environment Variables (svarbu!)

Railway projekte eik į **"Variables"** ir pridėk:

**Variable 1:**
- Name: `GOOGLE_CREDS`
- Value: *visas JSON failo turinys* (atidaryk `carpassport-cd043de1988b.json`, pasirink viską, nukopijuok)

Railway automatiškai perkraus botą — ir viskas veiks! 🚀

---

## Kaip naudotis botu

- `/start` — pradžia
- 🚗 Mano automobiliai — peržiūrėti
- ➕ Pridėti automobilį — naujas automobilis
- 🔧 Dalys / Mazgai — peržiūrėti dalis
- ➕ Pridėti dalį — nauja dalis
- `/delpart_XXXXX` — ištrinti dalį

---

## Duomenys Google Sheets

Visi duomenys matomi ir redaguojami tiesiai Google Sheets:
- **cars** lapas — automobiliai
- **parts** lapas — dalys

sheets.google.com → CarPassport
