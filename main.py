# https://discord.com/api/oauth2/authorize?client_id=[CLIENTID]&permissions=8&scope=bot

from os import getcwd, path
import json
import aiohttp
import configparser
import asyncio
import pytz
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from slugify import slugify

config = configparser.ConfigParser()
config.read('config.ini')

DISCORD_TOKEN = config.get('DISCORD', 'TOKEN', fallback=None)
DISCORD_GUILD = config.get('DISCORD', 'GUILD', fallback=None)
DATE_TIMEZONE = config.getint('DATE', 'TIMEZONE', fallback=0)


# https://gist.github.com/adamsbytes/8445e2f9a97ae98052297a4415b5356f
class DiscordEvents:
    def __init__(self, discord_token: str) -> None:
        self.base_api_url = 'https://discord.com/api/v8'
        self.auth_headers = {
            'Authorization': f'Bot {discord_token}',
            'User-Agent': 'Twitch Calendar Python/3.9 aiohttp/3.8.1',
            'Content-Type': 'application/json'
        }

    async def list_guild_events(self, guild_id: str) -> list:
        event_retrieve_url = f'{self.base_api_url}/guilds/{guild_id}/scheduled-events'
        async with aiohttp.ClientSession(headers=self.auth_headers) as session:
            try:
                async with session.get(event_retrieve_url) as response:
                    response.raise_for_status()
                    assert response.status == 200
                    response_list = json.loads(await response.read())
            except Exception as e:
                print(f'EXCEPTION: {e}')
            finally:
                await session.close()
        return response_list


discord = DiscordEvents(DISCORD_TOKEN)
loop = asyncio.get_event_loop()
events = loop.run_until_complete(discord.list_guild_events(DISCORD_GUILD))

# print(events)

calendar = getcwd() + "\\calendar.html"

with open('template.html', encoding="utf-8") as template:
    tpl = template.read()
template.close()

utc = pytz.UTC
tz = pytz.timezone('Europe/Paris')

now = utc.localize(datetime.utcnow())
start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=1)
end = (start + timedelta(days=6)).replace(hour=23, minute=59, second=59)

eventsHTML = ""

for event in events:

    start_date = (datetime.fromisoformat(event['scheduled_start_time'])).replace(tzinfo=utc).astimezone(tz)
    end_date = (datetime.fromisoformat(event['scheduled_end_time'])).replace(tzinfo=utc).astimezone(tz)

    if start <= start_date <= end:

        html = """
            <div class="event col-start-#WEEKDAY# row-start-1 relative">
                #BACKGROUND#
                <div class="relative z-20 bg-black bg-opacity-30 h-full p-4 flex flex-wrap items-center text-center content-center gap-2">
                    <div class="start-end text-xl font-semibold">#START# - #END#</div>
                    #LOGO#
                    <div class="title text-3xl font-bold">#TITLE#</div>
                    #DESCRIPTION#
                </div>
            </div>
        """

        title = event['name'].replace('🔴', '').strip()

        image = ''
        if event['image'] is not None:
            image = '<div class="background w-full h-full absolute z-10"><img src="https://cdn.discordapp.com/guild-events/'+event['id']+'/'+event['image']+'.png?size=1024" class="object-cover w-full h-full" /></div>'

        description = ''
        if event['description'] is not None:
            description = '<div class="description text-xl font-semibold leading-6">'+event['description']+'</div>'

        logo = ''
        logoUrl = slugify(title) + '.png'
        print('logoUrl:', logoUrl)
        if path.exists('assets/img/'+logoUrl):
            logo = '<div class="icon"><img src="assets/img/'+logoUrl+'" class="w-3/5 mx-auto my-2" /></div>'

        html = html.replace('#START#', start_date.strftime('%H:%M'))
        html = html.replace('#END#', end_date.strftime('%H:%M'))
        html = html.replace('#TITLE#', title)
        html = html.replace('#DESCRIPTION#', description)
        html = html.replace('#BACKGROUND#', image)
        html = html.replace('#LOGO#', logo)
        html = html.replace('#WEEKDAY#', str(start_date.weekday()+1))

        eventsHTML = eventsHTML + html

tpl = tpl.replace('#EVENTS#', eventsHTML)
tpl = tpl.replace('#START#', start.strftime('%d/%m/%Y'))
tpl = tpl.replace('#END#', end.strftime('%d/%m/%Y'))

f = open('calendar.html', 'w+', encoding='utf-8')
f.write(tpl)
f.close()

options = webdriver.ChromeOptions()
options.headless = True
s = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=s, options=options)
driver.maximize_window()
driver.implicitly_wait(3)

driver.get("file:///" + calendar)

driver.fullscreen_window()

S = lambda X: driver.execute_script('return document.body.parentNode.scroll' + X)
driver.set_window_size(S('Width'), S('Height'))
driver.find_element(By.TAG_NAME, 'body').screenshot(f'calendar.png')

driver.quit()
