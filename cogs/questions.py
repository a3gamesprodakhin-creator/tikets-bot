import disnake
from disnake.ext import commands
from datetime import datetime
import asyncio
import io

active_tickets = {}
user_tickets = {}
dm_tickets = {}

class CloseTicketView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @disnake.ui.button(label="Закрыть тикет", style=disnake.ButtonStyle.red, custom_id="close_ticket", emoji="🔒")
    async def close_button(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        await interaction.response.defer()
        
        questions_cog = interaction.bot.get_cog("Questions")
        config = questions_cog.config
        
        has_permission = False
        staff_role = interaction.guild.get_role(config["STAFFROLE"])
        support_role = interaction.guild.get_role(config["SUPPORTROLEID"])
        
        if staff_role and staff_role in interaction.user.roles:
            has_permission = True
        if support_role and support_role in interaction.user.roles:
            has_permission = True
        
        ticket_info = active_tickets.get(interaction.channel.id)
        if ticket_info and ticket_info.get("support") == interaction.user.id:
            has_permission = True
        
        if not has_permission:
            await interaction.followup.send("❌ У вас нет прав для закрытия этого тикета!", ephemeral=True)
            return
        
        # Получаем информацию о тикете
        ticket_owner = None
        question_message = None
        
        if ticket_info:
            ticket_owner = interaction.guild.get_member(ticket_info["user"])
            question_message_id = ticket_info.get("question_message")
            
            if question_message_id:
                # Получаем канал вопросов и находим исходное сообщение
                questions_channel = interaction.guild.get_channel(config["QUESTIONS_CHANNEL_ID"])
                if questions_channel:
                    try:
                        question_message = await questions_channel.fetch_message(question_message_id)
                    except:
                        pass
        
        if not ticket_owner and interaction.channel.name.startswith("тикет-"):
            username = interaction.channel.name.replace("тикет-", "").split("-")[0]
            for member in interaction.guild.members:
                if member.name == username:
                    ticket_owner = member
                    break
        
        # 1. ОБНОВЛЯЕМ СТАТУС В КАНАЛЕ ВОПРОСОВ
        if question_message:
            try:
                embed = question_message.embeds[0]
                embed.color = disnake.Color.dark_gray()
                
                for i, field in enumerate(embed.fields):
                    if field.name == "📊 Статус":
                        embed.set_field_at(i, name=field.name, value=f"🔒 Закрыто\n👤 {interaction.user.mention}", inline=True)
                
                await question_message.edit(embed=embed, view=None)
            except Exception as e:
                print(f"Ошибка обновления статуса: {e}")
        
        # 2. СОБИРАЕМ ЛОГ ПЕРЕПИСКИ
        log_content = []
        log_content.append(f"=" * 50)
        log_content.append(f"ЛОГ ТИКЕТА #{interaction.channel.name}")
        log_content.append(f"Время закрытия: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log_content.append(f"Закрыл: {interaction.user.name} ({interaction.user.id})")
        
        if ticket_owner:
            log_content.append(f"Пользователь: {ticket_owner.name} ({ticket_owner.id})")
        
        ticket_info_local = active_tickets.get(interaction.channel.id)
        if ticket_info_local:
            support_user = interaction.guild.get_member(ticket_info_local.get("support"))
            if support_user:
                log_content.append(f"Поддержка: {support_user.name} ({support_user.id})")
            
            created_at = ticket_info_local.get("created_at")
            if created_at:
                log_content.append(f"Создан: {created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        log_content.append(f"=" * 50)
        log_content.append("\nПЕРЕПИСКА:\n")
        
        # Собираем все сообщения из тикета
        try:
            async for msg in interaction.channel.history(limit=500, oldest_first=True):
                timestamp = msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
                author = msg.author.name
                
                if msg.embeds:
                    # Обрабатываем embed сообщения
                    for embed in msg.embeds:
                        log_content.append(f"\n[{timestamp}] [{author}] [EMBED]")
                        if embed.title:
                            log_content.append(f"Заголовок: {embed.title}")
                        if embed.description:
                            log_content.append(f"Описание: {embed.description}")
                        for field in embed.fields:
                            log_content.append(f"{field.name}: {field.value}")
                elif msg.content:
                    # Обычные текстовые сообщения
                    log_content.append(f"[{timestamp}] [{author}] {msg.content}")
                elif msg.attachments:
                    # Сообщения с вложениями
                    attachments = ", ".join([att.filename for att in msg.attachments])
                    log_content.append(f"[{timestamp}] [{author}] [Вложения: {attachments}]")
        except Exception as e:
            log_content.append(f"\nОшибка при сборе переписки: {e}")
        
        log_content.append(f"\n" + "=" * 50)
        log_content.append("КОНЕЦ ЛОГА")
        
        # Создаем файл с логом
        log_text = "\n".join(log_content)
        log_file = disnake.File(
            io.StringIO(log_text),
            filename=f"ticket_log_{interaction.channel.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        
        # 3. ОТПРАВЛЯЕМ ЛОГ В КАНАЛ ЛОГОВ
        log_sent = False
        log_channel = interaction.guild.get_channel(config["LOG_CHANNEL_ID"])
        if log_channel:
            try:
                log_embed = disnake.Embed(
                    title="📝 Лог закрытого тикета",
                    description=f"Тикет #{interaction.channel.name} был закрыт",
                    color=disnake.Color.dark_gray(),
                    timestamp=datetime.now()
                )
                
                if ticket_owner:
                    log_embed.add_field(name="Пользователь", value=f"{ticket_owner.mention}\n`{ticket_owner.id}`", inline=True)
                
                log_embed.add_field(name="Закрыл", value=interaction.user.mention, inline=True)
                log_embed.add_field(name="Длительность", value=f"<t:{int(datetime.now().timestamp())}:R>", inline=True)
                
                await log_channel.send(embed=log_embed, file=log_file)
                log_sent = True
            except Exception as e:
                print(f"Ошибка отправки лога: {e}")
        
        # 4. ОТПРАВЛЯЕМ СООБЩЕНИЕ О ЗАКРЫТИИ
        close_embed = disnake.Embed(
            title="🔒 Тикет закрывается",
            description=f"Тикет закрыт {interaction.user.mention}",
            color=disnake.Color.red()
        )
        close_embed.add_field(name="Время закрытия", value=f"<t:{int(datetime.now().timestamp())}:F>", inline=False)
        
        if log_sent and log_channel:
            close_embed.add_field(name="Лог переписки", value=f"Сохранен в {log_channel.mention}", inline=False)
        
        await interaction.followup.send(embed=close_embed)
        
        # 5. ОТПРАВЛЯЕМ УВЕДОМЛЕНИЕ В ЛС ПОЛЬЗОВАТЕЛЮ
        if ticket_owner:
            try:
                user_dm_embed = disnake.Embed(
                    title="❌ Служба поддержки",
                    description=f"Привет, ваш вопрос был отклонен, так как он нарушает правило 1.3",
                    color=disnake.Color.red()
                )
                user_dm_embed.set_footer(text="Служба поддержки")
                await self.send_dm(ticket_owner, embed=user_dm_embed)
            except:
                pass
        
        # 6. УДАЛЯЕМ ИЗ СЛОВАРЕЙ И КАНАЛ
        if ticket_info and "user" in ticket_info:
            user_id = ticket_info["user"]
            if user_id in user_tickets:
                del user_tickets[user_id]
            if user_id in dm_tickets:
                del dm_tickets[user_id]
        
        if interaction.channel.id in active_tickets:
            del active_tickets[interaction.channel.id]
        
        await asyncio.sleep(3)
        await interaction.channel.delete()
    
    async def send_dm(self, user, **kwargs):
        try:
            await user.send(**kwargs)
            return True
        except:
            try:
                dm_channel = await user.create_dm()
                await dm_channel.send(**kwargs)
                return True
            except:
                return False

class QuestionModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="Ваш вопрос",
                placeholder="Опишите вашу проблему или вопрос подробно...",
                custom_id="question_text",
                style=disnake.TextInputStyle.paragraph,
                min_length=5,
                max_length=1000
            ),
        ]
        super().__init__(
            title="Задать вопрос в поддержку",
            custom_id="question_modal",
            components=components,
            timeout=300
        )

    async def callback(self, interaction: disnake.ModalInteraction):
        await interaction.response.defer(ephemeral=True)
        
        if interaction.user.id in user_tickets:
            existing_channel_id = user_tickets[interaction.user.id]
            existing_channel = interaction.guild.get_channel(existing_channel_id)
            
            if existing_channel:
                error_embed = disnake.Embed(
                    title="❌ У вас уже есть активный тикет",
                    description=f"У вас уже есть открытый тикет: {existing_channel.mention}\n\nПожалуйста, дождитесь ответа поддержки в существующем тикете.",
                    color=disnake.Color.red()
                )
                await interaction.followup.send(embed=error_embed, ephemeral=True)
                return
        
        question = interaction.text_values["question_text"]
        user = interaction.user
        
        questions_cog = interaction.bot.get_cog("Questions")
        config = questions_cog.config
        
        channel = interaction.guild.get_channel(config["QUESTIONS_CHANNEL_ID"])
        
        if not channel:
            error_embed = disnake.Embed(
                title="❌ Ошибка",
                description="Канал для вопросов не настроен. Обратитесь к администратору.",
                color=disnake.Color.red()
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            return
        
        async for message in channel.history(limit=50):
            if message.embeds:
                embed = message.embeds[0]
                for field in embed.fields:
                    if f"ID: `{user.id}`" in field.value or f"ID: {user.id}" in field.value:
                        status_field = next((f for f in embed.fields if f.name == "📊 Статус"), None)
                        if status_field and "⏳ Ожидание" in status_field.value:
                            error_embed = disnake.Embed(
                                title="❌ У вас уже есть ожидающий вопрос",
                                description="У вас уже есть вопрос, ожидающий ответа поддержки. Пожалуйста, дождитесь ответа.",
                                color=disnake.Color.red()
                            )
                            await interaction.followup.send(embed=error_embed, ephemeral=True)
                            return
        
        embed = disnake.Embed(
            title="🎫 Новое обращение",
            color=disnake.Color.orange(),
            timestamp=datetime.now()
        )
        embed.add_field(name="👤 Пользователь", value=f"**Имя:** {user.name}\n**ID:** `{user.id}`", inline=False)
        embed.add_field(name="📝 Вопрос", value=f"```{question}```", inline=False)
        embed.add_field(name="📊 Статус", value="⏳ Ожидание", inline=True)
        embed.add_field(name="🕐 Дата", value=f"<t:{int(datetime.now().timestamp())}:R>", inline=True)
        embed.set_footer(text=f"ID: {user.id}")
        embed.set_thumbnail(url=user.display_avatar.url)
        
        buttons = QuestionButtons()
        
        role_ping = ""
        if config.get('SUPPORTROLEID'):
            role_ping = f"<@&{config['SUPPORTROLEID']}>"
            try:
                ping_msg = await channel.send(role_ping)
                await asyncio.sleep(2)
                await ping_msg.delete()
            except:
                pass
        
        message = await channel.send(embed=embed, view=buttons)
        
        confirm_embed = disnake.Embed(
            title="✅ Служба поддержки",
            description="**Ваше обращение успешно отправлено\nОжидайте...**",
            color=disnake.Color.green()
        )
        confirm_embed.set_footer(text="Служба поддержки")
        
        await interaction.followup.send(embed=confirm_embed, ephemeral=True)

class QuestionButtons(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @disnake.ui.button(label="Принять диалог", style=disnake.ButtonStyle.green, custom_id="accept_question", emoji="✅")
    async def accept_button(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        await self.handle_question(interaction, True)
    
    @disnake.ui.button(label="Отклонить", style=disnake.ButtonStyle.red, custom_id="reject_question", emoji="❌")
    async def reject_button(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        await self.handle_question(interaction, False)
    
    async def send_dm(self, user, **kwargs):
        try:
            await user.send(**kwargs)
            return True
        except:
            try:
                dm_channel = await user.create_dm()
                await dm_channel.send(**kwargs)
                return True
            except:
                return False
    
    async def handle_question(self, interaction: disnake.Interaction, accept: bool):
        await interaction.response.defer(ephemeral=True)
        
        questions_cog = interaction.bot.get_cog("Questions")
        config = questions_cog.config
        
        staff_role = interaction.guild.get_role(config["STAFFROLE"])
        support_role = interaction.guild.get_role(config["SUPPORTROLEID"])
        
        has_permission = False
        if staff_role and staff_role in interaction.user.roles:
            has_permission = True
        if support_role and support_role in interaction.user.roles:
            has_permission = True
        
        if not has_permission:
            await interaction.followup.send("❌ Нет прав!", ephemeral=True)
            return
        
        embed = interaction.message.embeds[0]
        user_id = None
        
        try:
            footer_text = embed.footer.text
            if "ID:" in footer_text:
                user_id = int(footer_text.split("ID: ")[1])
            else:
                user_id = int(footer_text.split(": ")[1])
        except:
            for field in embed.fields:
                if "ID:" in field.value:
                    try:
                        user_id = int(field.value.split("`")[1])
                        break
                    except:
                        continue
        
        if not user_id:
            await interaction.followup.send("❌ Не найден пользователь!", ephemeral=True)
            return
        
        user = interaction.guild.get_member(user_id)
        if not user:
            await interaction.followup.send("❌ Пользователь не на сервере!", ephemeral=True)
            return
        
        if accept:
            if user.id in user_tickets:
                existing_channel_id = user_tickets[user.id]
                existing_channel = interaction.guild.get_channel(existing_channel_id)
                
                if existing_channel:
                    error_embed = disnake.Embed(
                        title="❌ У пользователя уже есть активный тикет",
                        description=f"У {user.mention} уже есть открытый тикет: {existing_channel.mention}\n\nЗакройте существующий тикет перед созданием нового.",
                        color=disnake.Color.red()
                    )
                    await interaction.followup.send(embed=error_embed, ephemeral=True)
                    return
            
            embed.color = disnake.Color.green()
            for i, field in enumerate(embed.fields):
                if field.name == "📊 Статус":
                    embed.set_field_at(i, name=field.name, value=f"✅ Принято\n👤 {interaction.user.mention}", inline=True)
            
            await interaction.message.edit(embed=embed, view=None)
            
            category = None
            if config.get("CATEGORY_ID"):
                category = interaction.guild.get_channel(config["CATEGORY_ID"])
            
            channel_name = f"тикет-{user.name}"
            counter = 1
            original_name = channel_name
            while disnake.utils.get(interaction.guild.text_channels, name=channel_name):
                channel_name = f"{original_name}-{counter}"
                counter += 1
            
            overwrites = {
                interaction.guild.default_role: disnake.PermissionOverwrite(read_messages=False),
                user: disnake.PermissionOverwrite(read_messages=True, send_messages=True),
                interaction.user: disnake.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            
            admin_role = interaction.guild.get_role(config["STAFFROLE"])
            if admin_role:
                overwrites[admin_role] = disnake.PermissionOverwrite(
                    read_messages=True,
                    send_messages=False
                )
            
            if support_role:
                overwrites[support_role] = disnake.PermissionOverwrite(
                    read_messages=True,
                    send_messages=False
                )
            
            ticket_channel = await interaction.guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                reason=f"Тикет для {user.name}"
            )
            
            # Сохраняем ID сообщения для обновления статуса
            active_tickets[ticket_channel.id] = {
                "user": user.id,
                "support": interaction.user.id,
                "created_at": datetime.now(),
                "question_message": interaction.message.id  # Сохраняем ID сообщения вопроса
            }
            
            user_tickets[user.id] = ticket_channel.id
            dm_tickets[user.id] = ticket_channel.id
            
            thread_embed = disnake.Embed(
                title="🎫 Служба поддержки",
                color=disnake.Color.blue()
            )
            thread_embed.add_field(
                name="👋",
                value="Пиши сообщения прямо сюда\nСпасибо за обращение в нашу службу поддержки\nСейчас постараемся решить твой вопрос, оставайся на связи",
                inline=False
            )
            
            thread_view = disnake.ui.View()
            thread_view.add_item(disnake.ui.Button(
                label="Принять диалог", 
                style=disnake.ButtonStyle.green,
                disabled=True,
                emoji="✅"
            ))
            
            await ticket_channel.send(f"{user.mention} {interaction.user.mention}")
            await ticket_channel.send(embed=thread_embed, view=thread_view)
            
            close_view = CloseTicketView()
            await ticket_channel.send(view=close_view)
            
            try:
                user_dm_embed = disnake.Embed(
                    title="🎫 Служба поддержки",
                    description="**Пиши сообщения прямо сюда\nСпасибо за обращение в нашу службу поддержки\nСейчас постараемся решить твой вопрос, оставайся на связи**",
                    color=disnake.Color.green()
                )
                user_dm_embed.set_footer(text="Служба поддержки")
                
                success = await self.send_dm(user, embed=user_dm_embed)
                if not success:
                    print(f"Не удалось отправить ЛС пользователю {user.name}")
            except Exception as e:
                print(f"Ошибка отправки ЛС: {e}")
            
            await interaction.followup.send(f"✅ Тикет создан: {ticket_channel.mention}", ephemeral=True)
            
        else:
            # ОБНОВЛЯЕМ СТАТУС ПРИ ОТКЛОНЕНИИ
            embed.color = disnake.Color.red()
            for i, field in enumerate(embed.fields):
                if field.name == "📊 Статус":
                    embed.set_field_at(i, name=field.name, value=f"❌ Отклонено\n👤 {interaction.user.mention}", inline=True)
            
            await interaction.message.edit(embed=embed, view=None)
            
            if user:
                try:
                    reject_embed = disnake.Embed(
                        title="❌ Служба поддержки",
                        description="Привет, ваш вопрос был отклонен, так как он нарушает правило 1.3",
                        color=disnake.Color.red()
                    )
                    reject_embed.set_footer(text="Служба поддержки")
                    
                    success = await self.send_dm(user, embed=reject_embed)
                    if not success:
                        print(f"Не удалось отправить ЛС об отклонении {user.name}")
                except Exception as e:
                    print(f"Ошибка отправки ЛС об отклонении: {e}")
            
            await interaction.followup.send("❌ Вопрос отклонен.", ephemeral=True)

class Questions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = {}
    
    async def load_config(self):
        try:
            from config import settings
            self.config = {
                'QUESTIONS_CHANNEL_ID': int(settings.get('QUESTIONS_CHANNEL_ID', 0)),
                'LOG_CHANNEL_ID': int(settings.get('LOG_CHANNEL_ID', 0)),  # Обязательно для логов
                'CATEGORY_ID': int(settings.get('CATEGORY_ID', 0)),
                'STAFFROLE': int(settings.get('STAFFROLE', 0)),
                'SUPPORTROLEID': int(settings.get('SUPPORTROLEID', 0)),
                'OWNERID': int(settings.get('OWNERID', 0))
            }
        except:
            self.config = {
                'QUESTIONS_CHANNEL_ID': 0,
                'LOG_CHANNEL_ID': 0,
                'CATEGORY_ID': 0,
                'STAFFROLE': 0,
                'SUPPORTROLEID': 0,
                'OWNERID': 0
            }
    
    @commands.Cog.listener()
    async def on_ready(self):
        await self.load_config()
        self.bot.add_view(QuestionButtons())
        self.bot.add_view(CloseTicketView())
        
        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                if channel.name.startswith("тикет-"):
                    username = channel.name.replace("тикет-", "").split("-")[0]
                    for member in guild.members:
                        if member.name == username:
                            support_user = None
                            for chan_member in channel.members:
                                if chan_member != member and not chan_member.bot:
                                    staff_role = guild.get_role(self.config["STAFFROLE"])
                                    support_role = guild.get_role(self.config["SUPPORTROLEID"])
                                    
                                    if (staff_role and staff_role in chan_member.roles) or \
                                       (support_role and support_role in chan_member.roles):
                                        support_user = chan_member
                                        break
                            
                            if support_user:
                                active_tickets[channel.id] = {
                                    "user": member.id,
                                    "support": support_user.id,
                                    "created_at": datetime.now()
                                }
                                user_tickets[member.id] = channel.id
                                dm_tickets[member.id] = channel.id
                            break
        
        print("✅ Модуль вопросов готов!")
    
    @commands.slash_command(name="помощь", description="Задать вопрос поддержке")
    async def help_command(self, inter: disnake.ApplicationCommandInteraction):
        if inter.user.id in user_tickets:
            existing_channel_id = user_tickets[inter.user.id]
            existing_channel = inter.guild.get_channel(existing_channel_id)
            
            if existing_channel:
                error_embed = disnake.Embed(
                    title="❌ У вас уже есть активный тикет",
                    description=f"У вас уже есть открытый тикет: {existing_channel.mention}\n\nПожалуйста, дождитесь ответа поддержки в существующем тикете.",
                    color=disnake.Color.red()
                )
                await inter.response.send_message(embed=error_embed, ephemeral=True)
                return
        
        channel = inter.guild.get_channel(self.config["QUESTIONS_CHANNEL_ID"])
        if channel:
            async for message in channel.history(limit=50):
                if message.embeds:
                    embed = message.embeds[0]
                    for field in embed.fields:
                        if f"ID: `{inter.user.id}`" in field.value or f"ID: {inter.user.id}" in field.value:
                            status_field = next((f for f in embed.fields if f.name == "📊 Статус"), None)
                            if status_field and "⏳ Ожидание" in status_field.value:
                                error_embed = disnake.Embed(
                                    title="❌ У вас уже есть ожидающий вопрос",
                                    description="У вас уже есть вопрос, ожидающий ответа поддержки. Пожалуйста, дождитесь ответа.",
                                    color=disnake.Color.red()
                                )
                                await inter.response.send_message(embed=error_embed, ephemeral=True)
                                return
        
        modal = QuestionModal()
        await inter.response.send_modal(modal)
    
    @commands.slash_command(name="help", description="Ask a question to support")
    async def help_en(self, inter: disnake.ApplicationCommandInteraction):
        if inter.user.id in user_tickets:
            existing_channel_id = user_tickets[inter.user.id]
            existing_channel = inter.guild.get_channel(existing_channel_id)
            
            if existing_channel:
                error_embed = disnake.Embed(
                    title="❌ You already have an active ticket",
                    description=f"You already have an open ticket: {existing_channel.mention}\n\nPlease wait for support response in existing ticket.",
                    color=disnake.Color.red()
                )
                await inter.response.send_message(embed=error_embed, ephemeral=True)
                return
        
        modal = QuestionModal()
        await inter.response.send_modal(modal)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        if isinstance(message.channel, disnake.DMChannel):
            if message.author.id in dm_tickets:
                channel_id = dm_tickets[message.author.id]
                channel = self.bot.get_channel(channel_id)
                
                if channel and channel.id in active_tickets:
                    ticket_embed = disnake.Embed(
                        title=f"💬 Сообщение из ЛС",
                        description=message.content,
                        color=disnake.Color.blue(),
                        timestamp=datetime.now()
                    )
                    ticket_embed.set_author(name=message.author.name, icon_url=message.author.display_avatar.url)
                    
                    if message.attachments:
                        attachment_text = "\n".join([f"📎 {att.filename}" for att in message.attachments])
                        ticket_embed.add_field(name="Вложения", value=attachment_text, inline=False)
                    
                    await channel.send(embed=ticket_embed)
                    
                    try:
                        confirm_embed = disnake.Embed(
                            title="✅ Сообщение отправлено",
                            description="Ваше сообщение было отправлено в тикет поддержки.",
                            color=disnake.Color.green()
                        )
                        confirm_embed.set_footer(text="Служба поддержки")
                        await message.author.send(embed=confirm_embed)
                    except:
                        pass
                else:
                    try:
                        error_embed = disnake.Embed(
                            title="❌ Ошибка",
                            description="Ваш тикет не найден или был закрыт. Используйте команду `/помощь` на сервере для создания нового тикета.",
                            color=disnake.Color.red()
                        )
                        await message.author.send(embed=error_embed)
                    except:
                        pass
            else:
                try:
                    help_embed = disnake.Embed(
                        title="🎫 Служба поддержки",
                        description="У вас нет активного тикета. Чтобы обратиться в поддержку, используйте команду `/помощь` на сервере.",
                        color=disnake.Color.orange()
                    )
                    help_embed.add_field(
                        name="Инструкция:",
                        value="1. Перейдите на сервер\n2. Используйте команду `/помощь`\n3. Опишите ваш вопрос\n4. Дождитесь ответа поддержки",
                        inline=False
                    )
                    await message.author.send(embed=help_embed)
                except:
                    pass
        
        elif message.channel.id in active_tickets:
            ticket_info = active_tickets[message.channel.id]
            
            is_support = message.author.id == ticket_info["support"]
            is_user = message.author.id == ticket_info["user"]
            
            if not (is_support or is_user):
                try:
                    await message.delete()
                    warning = await message.channel.send(
                        f"{message.author.mention}, вы не можете писать в этом тикете!",
                        delete_after=5
                    )
                    return
                except:
                    return
            
            if is_support and not message.content.startswith("!"):
                user = message.guild.get_member(ticket_info["user"])
                if user:
                    try:
                        dm_embed = disnake.Embed(
                            title="💬 Служба поддержки",
                            description=message.content,
                            color=disnake.Color.blue(),
                            timestamp=datetime.now()
                        )
                        
                        if message.attachments:
                            attachment_text = "\n".join([f"📎 {att.filename}" for att in message.attachments])
                            dm_embed.add_field(name="Вложения", value=attachment_text, inline=False)
                        
                        dm_embed.set_footer(text="Служба поддержки")
                        
                        try:
                            await user.send(embed=dm_embed)
                            confirm_msg = await message.channel.send(
                                f"📨 **Сообщение отправлено в ЛС пользователю**",
                                delete_after=5
                            )
                        except:
                            error_msg = await message.channel.send(
                                f"❌ Не удалось отправить сообщение в ЛС. Пользователь запретил ЛС от ботов.",
                                delete_after=10
                            )
                    
                    except Exception as e:
                        print(f"Ошибка отправки ЛС: {e}")
    
    @commands.Cog.listener()
    async def on_channel_delete(self, channel):
        if channel.id in active_tickets:
            ticket_info = active_tickets[channel.id]
            
            if ticket_info["user"] in user_tickets:
                del user_tickets[ticket_info["user"]]
            if ticket_info["user"] in dm_tickets:
                del dm_tickets[ticket_info["user"]]
            
            del active_tickets[channel.id]
    
    # Команда для принудительного закрытия с логами
    @commands.slash_command(name="закрыть", description="Принудительно закрыть тикет с логами")
    @commands.has_permissions(administrator=True)
    async def force_close(self, inter: disnake.ApplicationCommandInteraction):
        if not inter.channel.name.startswith("тикет-"):
            await inter.response.send_message("❌ Эта команда работает только в тикетах!", ephemeral=True)
            return
        
        # Создаем экземпляр CloseTicketView и вызываем его обработчик
        view = CloseTicketView()
        button = disnake.ui.Button(style=disnake.ButtonStyle.red, label="Закрыть тикет")
        
        # Создаем фиктивное взаимодействие
        class FakeInteraction:
            def __init__(self, real_inter, channel):
                self.response = real_inter.response
                self.followup = real_inter.followup
                self.channel = channel
                self.user = real_inter.user
                self.guild = real_inter.guild
        
        fake_inter = FakeInteraction(inter, inter.channel)
        
        # Вызываем обработчик кнопки закрытия
        await view.close_button(button, fake_inter)
    
    @commands.slash_command(name="тикеты", description="Показать активные тикеты")
    @commands.has_permissions(administrator=True)
    async def show_tickets(self, inter: disnake.ApplicationCommandInteraction):
        if not active_tickets:
            embed = disnake.Embed(
                title="📊 Активные тикеты",
                description="Нет активных тикетов",
                color=disnake.Color.green()
            )
            await inter.response.send_message(embed=embed, ephemeral=True)
            return
        
        embed = disnake.Embed(
            title="📊 Активные тикеты",
            color=disnake.Color.blue()
        )
        
        for channel_id, info in list(active_tickets.items()):
            channel = inter.guild.get_channel(channel_id)
            user = inter.guild.get_member(info["user"])
            support = inter.guild.get_member(info["support"])
            
            if channel and user and support:
                embed.add_field(
                    name=f"#{channel.name}",
                    value=f"**Пользователь:** {user.mention}\n**Поддержка:** {support.mention}\n**Создан:** <t:{int(info['created_at'].timestamp())}:R>",
                    inline=False
                )
        
        await inter.response.send_message(embed=embed, ephemeral=True)
    
    @commands.slash_command(name="передать", description="Передать тикет другому саппорту")
    async def transfer_ticket(self, inter: disnake.ApplicationCommandInteraction, новый_саппорт: disnake.Member):
        if inter.channel.id not in active_tickets:
            await inter.response.send_message("❌ Это не активный тикет!", ephemeral=True)
            return
        
        ticket_info = active_tickets[inter.channel.id]
        
        if inter.user.id != ticket_info["support"]:
            await inter.response.send_message("❌ Вы не являетесь текущим саппортом этого тикета!", ephemeral=True)
            return
        
        config = self.config
        staff_role = inter.guild.get_role(config["STAFFROLE"])
        support_role = inter.guild.get_role(config["SUPPORTROLEID"])
        
        has_permission = False
        if staff_role and staff_role in новый_саппорт.roles:
            has_permission = True
        if support_role and support_role in новый_саппорт.roles:
            has_permission = True
        
        if not has_permission:
            await inter.response.send_message("❌ Указанный пользователь не является саппортом!", ephemeral=True)
            return
        
        old_support = inter.guild.get_member(ticket_info["support"])
        ticket_info["support"] = новый_саппорт.id
        active_tickets[inter.channel.id] = ticket_info
        
        overwrites = inter.channel.overwrites
        
        if old_support:
            overwrites[old_support] = disnake.PermissionOverwrite(
                read_messages=True,
                send_messages=False
            )
        
        overwrites[новый_саппорт] = disnake.PermissionOverwrite(
            read_messages=True,
            send_messages=True
        )
        
        await inter.channel.edit(overwrites=overwrites)
        
        transfer_embed = disnake.Embed(
            title="🔄 Тикет передан",
            description=f"Тикет передан от {old_support.mention if old_support else 'бывшего саппорта'} к {новый_саппорт.mention}",
            color=disnake.Color.orange()
        )
        transfer_embed.add_field(name="Передал", value=inter.user.mention, inline=False)
        transfer_embed.add_field(name="Время", value=f"<t:{int(datetime.now().timestamp())}:R>", inline=False)
        
        await inter.response.send_message(embed=transfer_embed)
        
        user = inter.guild.get_member(ticket_info["user"])
        if user:
            try:
                user_dm_embed = disnake.Embed(
                    title="🔄 Смена поддержки",
                    description=f"Ваш тикет теперь ведет {новый_саппорт.mention}",
                    color=disnake.Color.blue()
                )
                user_dm_embed.set_footer(text="Служба поддержки")
                await user.send(embed=user_dm_embed)
            except:
                pass

def setup(bot):
    bot.add_cog(Questions(bot))