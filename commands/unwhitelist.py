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

        # Manage Server
        if member.guild_permissions.manage_guild:
            return True

        return False

    return app_commands.check(predicate)


# =========================================================
# COG
# =========================================================

class Unwhitelist(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        await init_database()

    # -----------------------------------------------------
    # /unwhitelist botid
    # -----------------------------------------------------

    @app_commands.command(
        name="unwhitelist",
        description="Remove a User Install application from the whitelist."
    )
    @app_commands.describe(
        botid="The application ID of the User Install bot."
    )
    @can_manage_whitelist()
    async def unwhitelist(
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

        if application_id <= 0:
            await interaction.response.send_message(
                "❌ Invalid application ID.",
                ephemeral=True
            )
            return

        async with aiosqlite.connect(DB_PATH) as db:

            cursor = await db.execute(
                """
                DELETE FROM whitelisted_userinstall
                WHERE guild_id = ?
                AND application_id = ?
                """,
                (
                    interaction.guild.id,
                    application_id
                )
            )

            deleted = cursor.rowcount

            await cursor.close()
            await db.commit()

        if deleted == 0:
            await interaction.response.send_message(
                f"⚠️ `{application_id}` is not whitelisted.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"✅ User Install application `{application_id}` "
            f"has been removed from the whitelist.",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Unwhitelist(bot))