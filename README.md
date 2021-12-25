# Sarto Helper Bot
It's a private bot made to make me manage my own server and projects. That's about it.

## Dependencies
This bot requires a PostgreSQL server to store data.

## Running
1. Clone this repo:
```bash
git clone https://github.com/SartoRiccardo/sarto-helper-bot.git
cd sarto-helper-bot
```

2. Install the required modules in `requirements.txt`
```bash
pip install -r requirements.txt
```

3. Put the correct values in `config.example.py` and rename it to `config.py`.
4. Run the `setup.sql` in your PostgreSQL server.

## Modules

### Feeds
The Feed module of the bot manages the danbooru discord bot clonable
at [this repo](https://github.com/SartoRiccardo/discordbooru).
Type `,feeds` to access all commands dedicated to the feeds.

### EDOPro server
The EDOpro module manages the hosted EDOPro server with my own custom cards.
Type `,edopro` to access all commands dedicated to the server.

### REditor
The REditor module manages the creation of r/AskReddit text-to-speech videos.
Type `,reditor` to access all commands dedicated to it.

#### Installation
The REditor module requires `tesseract`, `chromium-browser`.