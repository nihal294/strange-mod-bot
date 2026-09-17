import os

import discord
from discord import app_commands
from discord.ext import commands

import aiosqlite


DB_PATH = os.path.join("data", "userinstall.db")


# =========================================================
# DATABASE
# =========================================================

async def init_database():
    os.makedirs("data", exist_ok=True)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS whitelisted_userinstall (
                guild_id INTEGER NOT NULL,
                application_id INTEGER NOT NULL,
                PRIMARY KEY (guild_id, application_id)
            )
        """)

        await db.commit()


# =========================================================
# PERMISSION CHECK
# =========================================================

def can_manage_whitelist():
    async def predicate(interaction: discord.Interaction):

        if interaction.guild is None:
            return False

        member = interaction.user

        # Server owner
        if interaction.guild.owner_id == member.id:
            return True

        # Manage Server permission
        if member.guild_permissions.manage_guild:
            return True

        return False

    return app_commands.check(predicate)


# =========================================================
# COG
# =========================================================

class WhitelistUserInstall(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        await init_database()

    # -----------------------------------------------------
    # /whitelist botid
    # -----------------------------------------------------

    @app_commands.command(
        name="whitelist",
        description="Whitelist a User Install application."
    )
    @app_commands.describe(
        botid="The application ID of the User Install bot."
    )
    @can_manage_whitelist()
    async def whitelist(
        self,
        interaction: discord.Interaction,
        botid: str
    ):

        # Validate ID
        try:
            application_id = int(botid)

        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid application ID.",
                ephemeral=True
            )
            return

        # Discord snowflake sanity check
        if application_id <= 0:
            await interaction.response.send_message(
                "❌ Invalid application ID.",
                ephemeral=True
            )
            return

        async with aiosqlite.connect(DB_PATH) as db:

            cursor = await db.execute(
                """
                SELECT 1
                FROM whitelisted_userinstall
                WHERE guild_id = ?
                AND application_id = ?
                LIMIT 1
                """,
                (
                    interaction.guild.id,
                    application_id
                )
            )

            exists = await cursor.fetchone()
            await cursor.close()

            if exists:
                await interaction.response.send_message(
                    f"⚠️ `{application_id}` is already whitelisted.",
                    ephemeral=True
                )
                return

            await db.execute(
                """
                INSERT INTO whitelisted_userinstall
                (guild_id, application_id)
                VALUES (?, ?)
                """,
                (
                    interaction.guild.id,
                    application_id
                )
            )

            await db.commit()

        await interaction.response.send_message(
            f"✅ User Install application `{application_id}` "
            f"has been whitelisted for this server.",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(WhitelistUserInstall(bot))