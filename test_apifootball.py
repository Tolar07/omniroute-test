import os
os.environ['APIFOOTBALL_KEY'] = '95398d858ad3631f00abdabe08bbf619'

from olp_xdv_agent.olp_xdv.data.apifootball_client import APIFootballClient

client = APIFootballClient()
result = client.list_leagues('Premier League')
print(result)