import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError(
        "TOKEN was not found in .env file."
    )

loaded_cogs = 0
failed_cogs = 0

intents = discord.Intents.default()

intents.message_content = False
intents.presences = False
intents.members = False

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

bot.remove_command("help")

async def load_cogs():

    global loaded_cogs, failed_cogs

    loaded_cogs = 0
    failed_cogs = 0

    commands_folder = "commands"

    if not os.path.isdir(commands_folder):
        print(
            f"Folder '{commands_folder}' was not found."
        )
        return
    for root, _, files in os.walk(commands_folder):

        for file in sorted(files):

            if not file.endswith(".py"):
                continue

            if file == "__init__.py":
                continue

            full_path = os.path.join(root, file)

            extension = os.path.splitext(
                full_path
            )[0].replace(os.sep, ".")

            try:

                await bot.load_extension(extension)

                loaded_cogs += 1

            except Exception as e:

                failed_cogs += 1

                print(
                    f"Failed: {extension}"
                )
                print(
                    f"   ↳ {type(e).__name__}: {e}"
                )

@bot.event
async def on_ready():

    await bot.change_presence(
        activity=discord.Game(name="/help")
    )

    print(
        f"{bot.user} is online"
    )

    print()
    print(
        f"Cogs              : {loaded_cogs}"
    )
    print(
        f"Slash Commands    : {len(bot.tree.get_commands())}"
    )
    print(
        f"Failed Cogs       : {failed_cogs}"
    )

async def main():

    async with bot:

        await load_cogs()
        
        await bot.login(TOKEN)

        try:

            synced = await bot.tree.sync()

            print(
                f"Synced            : {len(synced)} slash commands"
            )

        except Exception as e:

            print(
                f"Failed to sync slash commands: {e}"
            )

        await bot.connect()

if __name__ == "__main__":
    asyncio.run(main())
