import os
import re
import discord
from dotenv import load_dotenv

# --- Charge le fichier .env pour récupérer DISCORD_TOKEN ---
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("❌ Token Discord non trouvé dans .env (variable DISCORD_TOKEN manquante)")
    exit(1)

# --- Configuration du fichier insultes ---
FILE_PATH = r"C:\Users\sacha\Documents\discorde\fr.txt"
if not os.path.isfile(FILE_PATH):
    print(f"❌ Fichier introuvable : {FILE_PATH}")
    exit(1)

with open(FILE_PATH, encoding="utf-8") as f:
    INSULTES = [line.strip().lower() for line in f if line.strip()]

# Liste des abréviations insultantes à détecter (à compléter si besoin)
ABREVIATIONS_INSULTANTES = [
    "tg",
    "fdp",
    "ntm",
    "tageul",
]

# Table d'équivalences pour détecter variantes de caractères
CARACTERE_EQUIVALENTS = {
    'a': ['a', '@', 'à', 'á', 'â', 'ä', '4'],
    'e': ['e', 'é', 'è', 'ê', 'ë', '3'],
    'i': ['i', '1', 'ï', 'î', '!', '|'],
    'o': ['o', '0', 'ö', 'ô'],
    'u': ['u', 'ù', 'ü', 'û'],
    'c': ['c', 'ç', '<', 'k'],
    'd': ['d'],
    'f': ['f'],
    'g': ['g', '9'],
    'h': ['h'],
    'l': ['l', '1', '|', '!'],
    'm': ['m'],
    'n': ['n'],
    'p': ['p'],
    'q': ['q'],
    'r': ['r'],
    's': ['s', '$', '5'],
    't': ['t', '+', '7'],
    'v': ['v'],
    'x': ['x'],
    'y': ['y'],
    'z': ['z', '2'],
}

def word_to_regex(word):
    """Convertit un mot en regex tolérant les variantes de caractères."""
    pattern = ""
    for letter in word.lower():
        equivalents = CARACTERE_EQUIVALENTS.get(letter, [letter])
        group = "[" + "".join(re.escape(c) for c in equivalents) + "]"
        pattern += group + r"[.,\s_\-]*"
    if pattern.endswith(r"[.,\s_\-]*"):
        pattern = pattern[:-len(r"[.,\s_\-]*")]
    return pattern

def detect_insultes(message):
    message = message.lower()
    mots_interdits = INSULTES + ABREVIATIONS_INSULTANTES
    for mot in mots_interdits:
        try:
            regex = word_to_regex(mot)
            pattern = rf"\b{regex}\b"
            if re.search(pattern, message):
                return mot
        except re.error as e:
            print(f"Erreur regex sur '{mot}': {e}")
    return None

# --- Configuration du bot Discord ---
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"✅ Connecté en tant que {client.user}")

@client.event
async def on_message(message):
    # Ignorer les messages envoyés par le bot
    if message.author == client.user:
        return

    insulte = detect_insultes(message.content)
    if insulte:
        print(f"❌ Insulte détectée dans #{message.channel} par {message.author}: '{message.content}' (mot détecté : {insulte})")

# Lance le bot
client.run(TOKEN)
