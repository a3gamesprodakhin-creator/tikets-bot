import disnake
from disnake.ext import commands

class ButtonView1(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @disnake.ui.button(label="Закрыть", style=disnake.ButtonStyle.red, custom_id="button2")
    async def button2(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        # Проверяем наличие канала
        channel_name = f"ticket-{interaction.user.id}"
        channel = disnake.utils.get(interaction.guild.channels, name=channel_name)

        if channel is not None:
            # Отправляем уведомление об успешном удалении канала
            response_channel = interaction.channel
            await response_channel.send(f"Канал {channel_name} был успешно удалён.")

            # Удаляем канал
            await channel.delete()
        else:
            # Если канала нет, отправим сообщение об этом
            await interaction.response.send_message("Такого канала не существует.")

class ButtonView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @disnake.ui.button(label="Создать", style=disnake.ButtonStyle.green, custom_id="button1")
    async def button1(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        member = interaction.user
        guild = interaction.guild

        existing_channel = disnake.utils.get(guild.text_channels, name=f"ticket-{member.id}")
        if existing_channel:
            await existing_channel.send(f"{member.mention} у вас уже есть открыт тикет\n Зачем абузить?")
            return

        overwrites = {
            guild.default_role: disnake.PermissionOverwrite(read_messages=False, send_messages=False),
            member: disnake.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        role = guild.get_role(1446341668461871214) #роль стафф (1 роль допустим "Staff" она у всех)
        if role:
            overwrites[role] = disnake.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(f"ticket-{member.id}", overwrites=overwrites)

        await channel.send(f"{member.mention} <@&1446341668461871214>")
        embed = disnake.Embed(color=0x3D85C6)
        embed.add_field(name="Техническая поддержка", value="Благодарим за обращение в поддержку. Опишите детально Вашу проблему, чтобы наши специалисты могли как можно быстрее Вам помочь. Ответ в поддержке занимает от 5 до 15 минут.", inline=False)
        pinned_message = await channel.send(embed=embed, view=ButtonView1())
        await pinned_message.pin()

class Ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ticket(self, ctx):
        embed = disnake.Embed(color=0x3D85C6)
        embed.add_field(name="**Связь с поддержкой**\n", value="\nПри нажатии на кнопку, Вы откроете тикет\n\n Powered by lisonok", inline=True)
        await ctx.send(embed=embed, view=ButtonView())

    @commands.Cog.listener()
    async def on_ready(self):
        print("ticket.py готов!")

def setup(bot):
    bot.add_cog(Ticket(bot))