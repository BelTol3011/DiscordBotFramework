import asyncio
import random
import sys
import traceback
from asyncio import Event
from typing import Awaitable, Callable, Optional

import discord
from context_logger import Logger, log


def contruct_log_embed(log_: list[str]):
    logstr = "\n".join(log_)
    return discord.Embed(title="Log", description=f"```{logstr} ```")


class Log:
    log_list: list[str]
    log_message: discord.Message
    event: Event

    @classmethod
    async def create(cls, message: discord.Message):
        self = cls()
        self.message = message
        self.log_list = [" "]
        self.loop = True

        self.log_message = await message.channel.send(embed=self.get_log_embed(), reference=message)

        self.event = Event()

        asyncio.create_task(self.mainloop())

        return self

    def get_log_embed(self):
        return contruct_log_embed(self.log_list)

    def log(self, message: str, prefix: str, indentation: int):
        msg = prefix + ": " + (" " * indentation) + message
        print(msg)
        self.log_list.append(msg)
        self.event.set()

    async def mainloop(self):
        while self.loop:
            await self.event.wait()
            await self.log_message.edit(embed=self.get_log_embed())

    async def close(self, delete_after: int = 2 * 60):
        self.loop = False
        self.log("Closing (the end)", "", 0)
        await self.log_message.edit(content=f"Gets auto deleted after {delete_after} s.", delete_after=delete_after,
                                    embed=self.get_log_embed())


def construct_unauthorized_embed(unauthorized_user: discord.User):
    return discord.Embed(title="Unauthorized", color=discord.Color(0xFFA000),
                         description=f"You ({unauthorized_user}) are unathorized to perform this action.")


def construct_error_embed(err: str):
    # BTW, https://en.wikipedia.org/wiki/Minced_oath
    messages = ["Snap!", "Shoot!", "Shucks!", "Shizer!", "Darn!", "Frick!", "Juck!", "Dang!", "Frack!", "Frak!",
                "Frig!", "Fug!", "F!", "my gosh!"]
    return discord.Embed(title="Error",
                         description=f"{random.choice(['Oh ', 'Aw ', ''])}{random.choice(messages)} Something went "
                                     f"wrong:\n```{err}```"
                                     f"Don't be scared to read the error, most are simple mistakes and "
                                     f"can be easily resolved! 🧐. Sometimes, trying again 🔁 helps! Also make sure to "
                                     f"not run things in parallel.",
                         color=discord.Color(0xFF0000))


def parse_py_args(message: str):
    # TODO: remove remote code execution
    args = []
    start = 0
    for i in range(len(message)):
        try:
            arg = eval(message[start:i + 1])
            args.append(arg)
            start = i + 1
        except Exception:
            ...
    return args


class App:
    def __init__(self):
        self.commands: dict[str: Awaitable] = {}
        self.message_number = 0

    def route(self, alias: str, only_from_users: list[int] = None, only_from_roles: list[int] = None,
              do_log: bool = False, print_unauthorized: bool = False, raw_args: bool = False):
        only_from_roles = None if only_from_roles is None else set(only_from_roles)

        def decorator(func: Callable):
            async def wrapper(client: discord.Client, message: discord.Message, end: int):
                member: discord.Member = message.guild.get_member(message.author.id)

                if ((only_from_users and (message.author.id not in only_from_users)) or
                    not (only_from_roles and (set([role.id for role in member.roles]) & only_from_roles))) \
                        and print_unauthorized:
                    await message.channel.send(embed=construct_unauthorized_embed(message.author),
                                               reference=message)

                if not raw_args:
                    args = parse_py_args(message.content[end:])
                    log(f"Parsed args: {args!r}")
                else:
                    args = [message.content[end:]]

                kwargs = {}

                if do_log:
                    log_object = await Log.create(message)
                    with Logger(f"{self.message_number}", log_function=log_object.log):
                        await func(client, message, *args, **kwargs)
                    await log_object.close()
                else:
                    with Logger(f"{self.message_number}"):
                        await func(client, message, *args, **kwargs)

            self.commands.update({alias: wrapper})
            return wrapper

        return decorator

    def run(self, discord_token, game: str = None):
        client = discord.Client()

        @client.event
        async def on_ready():
            log(f'{client.user} has connected to Discord!')
            if game:
                await client.change_presence(activity=discord.Game(name="!wörterbuch"))

        @client.event
        async def on_message(message: discord.Message):
            self.message_number += 1

            try:
                record_alias: Optional[str] = None
                for alias in self.commands:
                    if message.content.startswith(alias) and (not record_alias or len(alias) > len(record_alias)):
                        record_alias = alias
                if record_alias is None:
                    return
                end = len(record_alias) + 1

                log(f"Relevant message recieved: {message.content}:")
                log(f"Decided on {message.content[:end]}, argstr is {message.content[end:]}")

                async with message.channel.typing():
                    log("Running wrapper:")
                    await self.commands[record_alias](client, message, end)
                    log(":Finished!")

            except Exception:
                err = traceback.format_exc()
                sys.stderr.write(err)
                await message.channel.send(embed=construct_error_embed(err))

        client.run(discord_token)
