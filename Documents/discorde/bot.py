import os
import re
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# --- Chargement insultes + abréviations ---
FILE_PATH = r"C:\Users\sacha\Documents\discorde\fr.txt"
if not os.path.isfile(FILE_PATH):
    print(f"❌ Fichier introuvable : {FILE_PATH}")
    exit(1)

with open(FILE_PATH, encoding="utf-8") as f:
    INSULTES = [line.strip().lower() for line in f if line.strip()]

ABREVIATIONS_INSULTANTES = [
    "tg",
    "fdp",
    "ntm",
    "tageul",
]

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

# --- Config bot ---

MOD_ROLE_NAMES = ['Admin']  # Rôles modérateurs

confirmation_messages = {}  # id_msg : {member_id, private_channel_id, insult}

async def get_or_create_muted_role(guild):
    muted_role = discord.utils.get(guild.roles, name="Muted")
    if not muted_role:
        muted_role = await guild.create_role(name="Muted", reason="Rôle Muted pour mute automatique")
        for channel in guild.channels:
            await channel.set_permissions(muted_role, speak=False, send_messages=False, read_messages=True)
    return muted_role

async def get_or_create_ban_confirmation_channel(guild):
    channel = discord.utils.get(guild.channels, name='ban-confirmation')
    if channel:
        return channel

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
    }
    for role_name in MOD_ROLE_NAMES:
        role = discord.utils.get(guild.roles, name=role_name)
        if role:
            overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    channel = await guild.create_text_channel('ban-confirmation', overwrites=overwrites, reason="Salon modération ban-confirmation")
    return channel

@bot.event
async def on_ready():
    print(f'Connecté en tant que {bot.user}')

@bot.event
async def on_message(message):
    if message.author == bot.user or message.author.bot:
        return

    insult_detected = detect_insultes(message.content)
    if insult_detected:
        await message.delete()

        guild = message.guild
        member = message.author

        muted_role = await get_or_create_muted_role(guild)
        await member.add_roles(muted_role)

        # Création salon privé mute
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        for role_name in MOD_ROLE_NAMES:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        private_channel_name = f"ban-{member.name.lower()}"
        existing_channel = discord.utils.get(guild.channels, name=private_channel_name)
        if existing_channel:
            private_channel = existing_channel
        else:
            private_channel = await guild.create_text_channel(private_channel_name, overwrites=overwrites)

        await private_channel.send(
            f"🔇 Vous avez été mute pour un langage inapproprié.\n"
            f"Mot détecté : `{insult_detected}`\n"
            "Ce salon privé vous est dédié pendant la modération."
        )

        ban_conf_channel = await get_or_create_ban_confirmation_channel(guild)

        alert_msg = await ban_conf_channel.send(
            f"🔴 {member.mention} a été mute pour insulte.\n"
            "Réagissez avec ✅ pour bannir définitivement, ❌ pour unmute."
        )
        await alert_msg.add_reaction('✅')
        await alert_msg.add_reaction('❌')

        confirmation_messages[alert_msg.id] = {'member_id': member.id, 'private_channel_id': private_channel.id, 'insult': insult_detected}

    await bot.process_commands(message)

@bot.event
async def on_reaction_add(reaction, user):
    if user == bot.user:
        return

    message = reaction.message
    if message.id not in confirmation_messages:
        return

    guild = message.guild
    data = confirmation_messages[message.id]
    member = guild.get_member(data['member_id'])
    private_channel = guild.get_channel(data['private_channel_id'])

    # Vérification rôle modérateur
    mod_roles = [discord.utils.get(guild.roles, name=r) for r in MOD_ROLE_NAMES]
    if not any(role in user.roles for role in mod_roles if role):
        await message.channel.send(f"{user.mention} n'a pas les permissions pour effectuer cette action.")
        return

    if member is None:
        await message.channel.send("Le membre concerné n'existe plus.")
        del confirmation_messages[message.id]
        return

    if reaction.emoji == '✅':
        try:
            await guild.ban(member, reason=f"Ban confirmé par modérateur suite à insulte : {data['insult']}")
            await message.channel.send(f"{member.mention} a été banni définitivement.")
        except Exception as e:
            await message.channel.send(f"Erreur lors du ban : {e}")

        if private_channel:
            try:
                await private_channel.delete()
            except Exception as e:
                await message.channel.send(f"Erreur lors de la suppression du salon privé : {e}")

        del confirmation_messages[message.id]

    elif reaction.emoji == '❌':
        muted_role = discord.utils.get(guild.roles, name="Muted")
        if muted_role and muted_role in member.roles:
            try:
                await member.remove_roles(muted_role)
            except Exception as e:
                await message.channel.send(f"Erreur lors du retrait du rôle Muted : {e}")
        else:
            await message.channel.send(f"{member.mention} n'a pas le rôle Muted.")

        await message.channel.send(f"{member.mention} a été unmute et peut reparler.")

        if private_channel:
            try:
                await private_channel.delete()
            except Exception as e:
                await message.channel.send(f"Erreur lors de la suppression du salon privé : {e}")

        del confirmation_messages[message.id]

@bot.command()
@commands.has_permissions(administrator=True)
async def addadmin(ctx, member: discord.Member):
    role = discord.utils.get(ctx.guild.roles, name="Admin")
    if not role:
        await ctx.send("Le rôle Admin n'existe pas.")
        return
    await member.add_roles(role)
    await ctx.send(f"Le rôle Admin a été ajouté à {member.mention}.")

bot.run(TOKEN)
