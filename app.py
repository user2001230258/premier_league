from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
import requests
import threading
import time
from datetime import datetime, timedelta
from config import FOOTBALL_DATA_API_KEY, PREMIER_LEAGUE_ID, UPDATE_INTERVAL
import logging
import eventlet



# Patch để tránh lỗi với eventlet
eventlet.monkey_patch()

# Thiết lập logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Headers cho API requests
headers = {
    'X-Auth-Token': FOOTBALL_DATA_API_KEY
}

def fetch_matches():
    """Lấy dữ liệu trận đấu từ API"""
    try:
        # Lấy ngày hiện tại và ngày mai (UTC)
        today = datetime.utcnow().date()
        tomorrow = today + timedelta(days=1)
        
        # Format ngày theo yêu cầu của API
        dateFrom = today.strftime('%Y-%m-%d')
        dateTo = tomorrow.strftime('%Y-%m-%d')
        
        # Thêm filter ngày vào URL
        url = f'http://api.football-data.org/v4/competitions/{PREMIER_LEAGUE_ID}/matches'
        params = {
            'dateFrom': dateFrom,
            'dateTo': dateTo,
        }
        
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            matches_data = response.json()
            current_matches = []
            
            # Lấy thông tin giải đấu
            competition_data = matches_data.get('competition', {})
            competition_logo = competition_data.get('emblem', '')
            
            for match in matches_data['matches']:
                # Lấy logo của các đội
                home_team_logo = match['homeTeam'].get('crest', '')
                away_team_logo = match['awayTeam'].get('crest', '')
                
                match_info = {
                    'home_team': match['homeTeam']['name'],
                    'home_team_logo': home_team_logo,
                    'away_team': match['awayTeam']['name'],
                    'away_team_logo': away_team_logo,
                    'score': f"{match['score'].get('fullTime', {}).get('home', 0)}-{match['score'].get('fullTime', {}).get('away', 0)}",
                    'status': match['status'],
                    'utcDate': match['utcDate'],
                    'competition_logo': competition_logo
                }
                current_matches.append(match_info)
            
            logger.debug(f"Fetched matches: {current_matches}")
            return current_matches
    except Exception as e:
        logger.error(f"Error fetching matches: {str(e)}")
        return []
def fetch_standings():
    """Lấy dữ liệu bảng xếp hạng từ API"""
    try:
        url = f'http://api.football-data.org/v4/competitions/{PREMIER_LEAGUE_ID}/standings'
        logger.debug(f"Calling standings API: {url}")
        
        response = requests.get(url, headers=headers)
        logger.debug(f"API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            standings_data = response.json()
            
            if not standings_data.get('standings'):
                logger.error("No standings data found in API response")
                return []
            
            competition_logo = standings_data.get('competition', {}).get('emblem', '')
            
            # Lấy bảng xếp hạng tổng thể (TOTAL)
            total_standings = next((standing for standing in standings_data['standings'] 
                                if standing['type'] == 'TOTAL'), None)
            
            if not total_standings:
                logger.error("No TOTAL standings found in API response")
                return []
            
            standings = []
            for team in total_standings['table']:
                standings.append({
                    'position': team['position'],
                    'team': team['team']['name'],
                    'team_logo': team['team'].get('crest', ''),
                    'played': team['playedGames'],
                    'won': team['won'],
                    'draw': team['draw'],
                    'lost': team['lost'],
                    'points': team['points'],
                    'goalDifference': team['goalDifference']
                })
            return {
                'standings': standings,
                'competition_logo': competition_logo
            }
    except Exception as e:
        logger.error(f"Error fetching standings: {str(e)}")
        return {'standings': [], 'competition_logo': ''}

def background_update():
    """Hàm cập nhật dữ liệu trong nền"""
    while True:
        try:
            matches = fetch_matches()
            standings = fetch_standings()
            data = {
                'matches': matches,
                'standings': standings,
                'last_updated': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            }
            socketio.emit('update_data', data)
        except Exception as e:
            logger.error(f"Background update error: {str(e)}")
        eventlet.sleep(UPDATE_INTERVAL)

app.route('/')
def index():
    """Route chính của ứng dụng"""
    matches = fetch_matches()
    standings = fetch_standings()
    initial_data = {
        'matches': matches,
        'standings': standings,
        'last_updated': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    }
    return render_template('index.html', initial_data=initial_data)

@app.route('/api/refresh')
def refresh_data():
    """API endpoint để làm mới dữ liệu theo yêu cầu"""
    matches = fetch_matches()
    standings = fetch_standings()
    data = {
        'matches': matches,
        'standings': standings,
        'last_updated': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    }
    return jsonify(data)

@app.route('/api/test')
def test_api():
    """Route để test API connection"""
    try:
        url = f'http://api.football-data.org/v4/competitions/{PREMIER_LEAGUE_ID}/standings'
        response = requests.get(url, headers=headers)
        return jsonify({
            'status_code': response.status_code,
            'headers': dict(response.headers),
            'data': response.json() if response.status_code == 200 else None,
            'api_key_used': FOOTBALL_DATA_API_KEY[:5] + '...'
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'api_key_used': FOOTBALL_DATA_API_KEY[:5] + '...'
        })

if __name__ == '__main__':
    # Khởi động thread cập nhật trong nền
    update_thread = threading.Thread(target=background_update)
    update_thread.daemon = True
    update_thread.start()
    
    # Chạy ứng dụng với eventlet
    socketio.run(app, debug=True)

if __name__ == '__main__':
    app.run(debug=True)
