import discord
import asyncio


class InteractiveEmbed(discord.Embed):
    PREV_PAGE = "⬅"
    NEXT_PAGE = "➡"

    def __init__(self, ctx, **kwargs):
        super().__init__(**kwargs)
        self.ctx = ctx
        self.on_timeout = None if "on_timeout" not in kwargs else kwargs["on_timeout"]
        self.action_buttons = {}
        if "on_page_change" in kwargs:
            self.action_buttons[InteractiveEmbed.PREV_PAGE] = kwargs["on_page_change"]
            self.action_buttons[InteractiveEmbed.NEXT_PAGE] = kwargs["on_page_change"]
        self.timeout = 30.0 if "timeout" not in kwargs else kwargs["timeout"]
        self.closed = False

        self.message = None

    async def send(self, synchronous=False):
        self.closed = False
        self.message = await self.ctx.send(embed=self)
        await self.refresh_reactions()
        if synchronous:
            await self._start_interactivity()
        else:
            asyncio.create_task(self._start_interactivity())

    async def _start_interactivity(self):
        def check_reaction(message):
            def inner(e_payload):
                return e_payload.user_id == self.ctx.message.author.id and \
                    e_payload.message_id == message.id and \
                    str(e_payload.emoji) in self.action_buttons.keys()
            return inner

        while not self.closed:
            try:
                pending = [
                    self.ctx.bot.wait_for("raw_reaction_add", timeout=self.timeout, check=check_reaction(self.message)),
                    self.ctx.bot.wait_for("raw_reaction_remove", timeout=self.timeout, check=check_reaction(self.message)),
                ]
                done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                for task in pending:
                    task.cancel()
                payload = await done.pop()
                reaction = str(payload.emoji)

                callback = self.action_buttons[reaction]
                change = 0
                if reaction == InteractiveEmbed.PREV_PAGE:
                    change = -1
                elif reaction == InteractiveEmbed.NEXT_PAGE:
                    change = 1
                if not self.closed:
                    await callback(caller=self, change=change, reaction=reaction)
            except asyncio.TimeoutError:
                self.closed = True
                await self.message.clear_reactions()

    def add_button(self, emoji, callback):
        self.action_buttons[emoji] = callback

    def remove_button(self, emoji):
        if emoji in self.action_buttons:
            del self.action_buttons[emoji]

    async def update(self):
        await self.message.edit(embed=self)

    async def refresh_reactions(self):
        if self.message is None:
            return
        for reaction in self.action_buttons:
            await self.message.add_reaction(reaction)

    async def close(self):
        self.closed = True

    async def delete(self):
        if self.message is not None:
            await self.message.delete()
            self.message = None
        self.closed = True

    @classmethod
    async def from_dict(cls, data, ctx, **kwargs):
        self = super().from_dict(data)
        self.ctx = ctx
        self.on_timeout = None if "on_timeout" not in kwargs else kwargs["on_timeout"]
        self.action_buttons = {}
        if "on_page_change" in kwargs:
            self.action_buttons[InteractiveEmbed.PREV_PAGE] = kwargs["on_page_change"]
            self.action_buttons[InteractiveEmbed.NEXT_PAGE] = kwargs["on_page_change"]
        self.timeout = 30.0 if "timeout" not in kwargs else kwargs["timeout"]
        self.closed = False

        self.message = None
        return self
