# 🧠 Characterinator

> A third-party desktop client for Character.AI that hopefully doesn’t suck. (CURRENTLY IN BETA, MOST FEATURES ARE INOPERABLE)

Characterinator is a passion-fueled, reverse-engineered PyQt5-based client for Character.AI, built because the official site is bloated, slow, and makes you pay to change your chat color.

- ✨ Supports both logged-in and guest modes
- 🦾 Lets you search and browse bots anonymously
- 🚫 No NSFW bypasses — but does allow local censorship via DistilBERT
- 🎨 Fully themeable via QSS (you can even blind yourself if you want to)
- 🧪 Powered by [PyCharacterAI](https://github.com/Xtr4F/PyCharacterAI) and some other libraries, including libanoncai.
- 💾 Has a full local settings system via XML
- 🔥 Fast, clean, and funny as hell

---

## 🔧 Features

- 🌐 Character.AI integration (login via token, guest mode supported)
- 🧍 Anonymous bot discovery: curated lists, categories, and search
- 💬 Chat system with swipe support
- 🎨 Themes via `styles.xml` (includes the infamous **Blinderinator** mode)
- 🔐 Local censorship option with DistilBERT
- 🧠 Configurable models for custom AI mode (OpenAI-compatible, Ollama, Local GGUF)
- 🗃️ XML-based settings that are both human-readable and machine-driven
- 🦝 Fully modular. Reverse engineered. Kinda janky. But it works.

---

## Actually implemented features
- Character.AI integration
- Anonymous bot discovery
- Themes
- Local GGUF
- XML settings
- Libanoncai separation to its own repo

## Planned or in development features
- Non-token login
- Anonymous temporary chats for CustomAI models
- DistilBERT censorship

There is an archived version of the app; mvp.py which is the Minimum Viable Product version. This is pre-alpha, and is quite bad.
main.py is the actual app python file.

---

## 🚀 Getting Started

1. Clone the repo  
2. Install dependencies (see below)  
3. Run `main.py`  
4. Paste your Character.AI token or use Guest Mode  
5. Enjoy bots with fewer breakdowns than the official site

---

## 🛠 Requirements

- Python 3.9+
- PyQt5
- `aiohttp`
- `defusedxml`
- `requests`
- `qasync`
- PyCharacterAI (for actual Character.AI access)
- Optional: `llama-cpp-python` if you plan on using Local GGUF models

Install everything:

```bash
pip install -r requirements.txt
```

## 🎨 Themes
Customize your entire UI through styles.xml.

Includes:

- Default — A clean dark mode
 
- Blinderinator — CSS so bad it loops back to being iconic

- Add your own! Just wrap QSS in a `<Theme name="...">` tag

## 🤝 Legal Disclaimer
Characterinator is a third-party client for Character.AI.
We are not affiliated with them in any way.
Use at your own risk.
Tokens are stored locally — don't share them.
We’re not responsible for bans, breakages, or psychological damage from the Blinderinator theme.
