import json
import embeds
import os
import sqlite3
import discord
import requests
import redmine_api
from discord.ext import commands
from discord.ext.tasks import loop
from sqlite3.dbapi2 import Cursor

## FIXME: Change the webpage accordingly.
webpage = "https://kore.koders.in/"

## FIXME: Instead of maintaining issue_set it would be much better to fetch it via the channel list
issue_dict = dict()

logger = embeds.Logger("kourage-operations")
bot = commands.Bot(command_prefix="~")
guild = None
hdr = {'Content-Type': 'application/json'}

def environ_check(var):
    if not var in os.environ:
        raise Exception("'" + var + "' not found in the environ list.")

@bot.event
async def on_ready():
    global hdr
    global guild
    global issue_dict

    try:
        environ_check('GUILD_ID')
        environ_check('REDMINE_KEY')

        guild = bot.get_guild(int(os.environ.get('GUILD_ID')))
        hdr['X-Redmine-API-Key'] = os.environ.get('REDMINE_KEY')
        
        categories = {i.name : i for i in guild.categories}
        if "ISSUES" in categories:
            category = categories['ISSUES']
            channels = category.channels
            try:
                for channel in channels:
                    issue_dict[int(channel.name)] = channel
            except Exception as e:
                pass
        check_new_issues.start()
    except Exception as err:
        logger.error('~on_ready: ' + str(err))
        exit(-1)
    logger.success("Kourage is running at version {0}".format("0.1.0"))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.NoPrivateMessage):
        await ctx.send("*Private messages.* ", delete_after = 60)
    elif isinstance(error, commands.MissingAnyRole):
        await ctx.send("*~Not have enough permission.*", delete_after = 60)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("*Command is missing an argument:* ", delete_after = 60)
    elif isinstance(error, commands.DisabledCommand):
        await ctx.send("*This command is currenlty disabled. Please try again later.* ", delete_after = 60)
    elif isinstance(error, commands.CheckFailure):
        await ctx.send("*You do not have the permissions to do this.* ", delete_after = 60)
    logger.error(error)


async def add_issue(issue_id):
    logger.info('~add_issue called')
    global guild
    
    categories = {i.name : i for i in guild.categories}
    if not "ISSUES" in categories:
        category = await guild.create_category('ISSUES')
    else:
        category = categories['ISSUES']

    issue = redmine_api.get_json(webpage + 'issues/' + str(issue_id) + '.json?include=watchers', hdr)
    watcher_id_list = list()
    try:
        watcher_id_list.append(issue['issue']['assigned_to']['id'])
    except Exception as err:
        pass

    try:
        watchers = issue['issue']['watchers']
        for watcher in watchers:
            watcher_id_list.append(watcher['id'])
    except Exception as err:
        pass

    if len(watcher_id_list) == 0:
        logger.info('No watchers in the issue.')
        return

    channel_name = issue['issue']['subject'].replace(' ', '_')
    api_key_list = list()
    
    for i in watcher_id_list:
        _api = redmine_api.get_json(webpage + "users/" + str(i) + ".json", hdr)
        api_key_list.append(str(_api["user"]["api_key"]))

    conn = sqlite3.connect('db/main.sqlite')
    cur = conn.cursor()

    users = set()
    for i in api_key_list:
        try:
            cur.execute('''SELECT DISCORD_ID FROM MAIN WHERE REDMINE = ?''', (i, ))
            discord_id = cur.fetchone()
        except Exception as err:
            logger.error('SQLite Error: ' + str(err))
            return

        if not discord_id:
            continue
        users.add(await bot.fetch_user(discord_id[0]))

    overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
    }
    for i in users:
        overwrites[i] = discord.PermissionOverwrite(read_messages=True)

    channel = await guild.create_text_channel(str(issue_id), overwrites = overwrites, category = category)
    issue_dict[issue_id] = channel
    logger.success('~add_issue executed successfully.')

async def archive_channel(issue_id):
    global issue_dict
    global guild

    await issue_dict[issue_id].send('~archive')
    del issue_dict[issue_id]

@loop(minutes = 1)
async def check_new_issues():
    logger.info('~check_new_issue called.')
    global issue_dict
    issues = redmine_api.get_json(webpage + 'issues.json?status=open&limit=100', hdr)
    
    if True:
        for issue in issues["issues"]:
            if issue['id'] not in issue_dict:
                await add_issue(issue['id'])
        tmp_issue_dict = issue_dict.copy()

        open_issues = [_issue['id'] for _issue in issues['issues']]
        for issue in tmp_issue_dict:
            if not issue in open_issues:
                await archive_channel(issue)
    #except Exception as err:
    else:
        logger.error('~check_new_issues: ' + str(err))
        return
    logger.success('~check_new_issues executed successfully.')

if __name__ == "__main__":
    try:
        bot.run(os.environ.get('TOKEN'))
    except Exception as _e:
        logger.error("Exception found at main worker.\n" + str(_e))
