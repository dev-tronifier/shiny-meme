import os
from discord.ext.commands import Bot
from discord.ext import tasks
from discord import Member
import discord
import datetime
import logging
import platform
from colorama import init
from termcolor import colored
import time
from datetime import timedelta
import matplotlib.pyplot as plt
machine = platform.node()
init()

logging.basicConfig(format="%(asctime)s %(message)s", level=logging.INFO)

class Logger:
    def __init__(self, app):
        self.app = app
    def info(self, message):
        print(colored(f'[{time.asctime(time.localtime())}] [{machine}] [{self.app}] {message}', 'yellow'))
    def success(self, message):
        print(colored(f'[{time.asctime(time.localtime())}] [{machine}] [{self.app}] {message}', 'green'))
    def error(self, message):
        print(colored(f'[{time.asctime(time.localtime())}] [{machine}] [{self.app}] {message}', 'red'))
    def color(self, message, color):
        print(colored(f'[{time.asctime(time.localtime())}] [{machine}] [{self.app}] {message}', color))

logger = Logger("kourage-presence")


intents = discord.Intents.all()
intents.members= True
bot = Bot(command_prefix='~', intents = intents)
data = {}   # creating a dict to stpre info in the following format {user:{total_time:'',start_time:''}}


@bot.event
async def on_ready():
    logger.success("~Kourage bot is running at 0.1.0")
    load_dictionary_koders.start()    #starts the task event

@tasks.loop(hours=24)
async def load_dictionary_koders():
    channel = await bot.fetch_channel(868036722326388736)
    guild = channel.guild
    logger.info('~load_dictionary_koders called for guild ' + str(guild.id) + '/' + guild.name + " : " + str(channel.id) + "/" + channel.name)
    global data
    #graph plotting from previous days data

    if len(data)!=0:
        ids = data.keys()
        totaltime = []
        for x in ids:
            totaltime.append(int(data[x]))#.total_seconds()))
        plt.bar(ids, totaltime)
        plt.xticks(range(len(ids)), ids, rotation=90, fontsize=3)
        plt.xlabel('Names')
        plt.ylabel('Total online time(hrs)')
        plt.title('Online status')
        plt.tight_layout()
        plt.savefig('temp.png')
        await channel.send(file=discord.File('temp.png'), delete_after = 43200)

    data = {}
    for member in guild.members:
        for role in member.roles:
            if role.name=="Koders":
                if member.status == discord.Status.online:   #to check user status when the task runs
                    data[member.name] = {"total_time": datetime.timedelta(0), 'start_time':datetime.datetime.now()}
                else:
                    data[member.name]= {'total_time':datetime.timedelta(days=0, seconds=0, microseconds=0, milliseconds=0, minutes=0, hours=0, weeks=0), 'start_time':0}
    
@bot.event
async def on_member_update(usr_before, usr_after):
    global data
    logger.info('Before status: ' + usr_before.name + '/' + str(usr_before.status))
    logger.info('After status: ' + usr_after.name + '/' + str(usr_after.status))
    try:
        if(data[usr_before.name]['start_time'] == 0):
            data[usr_before.name]['start_time'] = datetime.datetime.now()
        else:
            data[usr_before.name]['total_time'] += (datetime.datetime.now()-data[usr_before.name]['start_time'])
            data[usr_before.name]['start_time'] = 0
            print(data[usr_before.name]['total_time'])
    except Exception as err:
        pass

try:    
    bot.run(os.environ.get('TOKEN'))
except Exception as err:
    logger.error("Error in main worker.\n" + err)
