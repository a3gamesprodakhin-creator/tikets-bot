import os
import disnake
import discord
from discord.ext import commands
from config import settings
from disnake.ext import commands

#  Создается экземпляр класса Bot с префиксом команд "!" и указанными разрешениями.
intents = disnake.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)  # Вместо 1234567890 указать id сервера
bot.remove_command( 'help' )

@bot.event
async def on_ready():
    print("Бот Успешно Активирован")

@bot.slash_command(name= 'аватар')
async def avatar(ctx, member: disnake.Member = None):
    # Получаем пользователя, чью аватарку нужно показать
    if not member:
        member = ctx.author

    # Отправляем в чат аватарку пользователя
    await ctx.send(member.display_avatar.url, ephemeral=True)  # Обрабатываем команду


@bot.command()
async def send(ctx, channel_id, *, message):
    try:
        channel = bot.get_channel(int(channel_id))
        if channel:
            await channel.send(message)
            await ctx.send(f"Сообщение успешно отправлено в канал {channel.name}")
        else:
            await ctx.send("Канал с указанным ID не найден.")
    except ValueError:  
        await ctx.send("ID канала должен быть числом.") #[preifx]send <id канала> <сообщение>

# При готовности бота, загружает расширения из папки "cogs"
for file in os.listdir("./cogs"):
    if file.endswith(".py"):
        bot.load_extension(f"cogs.{file[:-3]}")



bot.run(settings['TOKEN']) #токен из config.py (не нужно писать его сюда)