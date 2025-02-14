import os
from dotenv import load_dotenv

load_dotenv()

FOOTBALL_DATA_API_KEY = os.getenv('FOOTBALL_DATA_API_KEY')
PREMIER_LEAGUE_ID = 'PL'
UPDATE_INTERVAL = 60  # Cập nhật mỗi 60 giây
