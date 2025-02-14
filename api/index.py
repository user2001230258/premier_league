from flask import Flask, render_template, jsonify, request
import requests
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__, 
    template_folder='../templates',  # Điều chỉnh đường dẫn template
    static_folder='../static'        # Điều chỉnh đường dẫn static
)

# Cấu hình API
FOOTBALL_DATA_API_KEY = os.getenv('FOOTBALL_DATA_API_KEY')
PREMIER_LEAGUE_ID = 'PL'

# Headers cho API requests
headers = {
    'X-Auth-Token': FOOTBALL_DATA_API_KEY
}

def fetch_matches(date=None):
    """Lấy dữ liệu trận đấu từ API"""
    try:
        if date is None:
            # Lấy ngày hiện tại và ngày mai (UTC)
            today = datetime.utcnow().date()
            tomorrow = today + timedelta(days=1)
            dateFrom = today.strftime('%Y-%m-%d')
            dateTo = tomorrow.strftime('%Y-%m-%d')
        else:
            # Sử dụng ngày được chỉ định
            match_date = datetime.strptime(date, '%Y-%m-%d').date()
            dateFrom = match_date.strftime('%Y-%m-%d')
            dateTo = (match_date + timedelta(days=1)).strftime('%Y-%m-%d')
        
        url = f'http://api.football-data.org/v4/competitions/{PREMIER_LEAGUE_ID}/matches'
        params = {
            'dateFrom': dateFrom,
            'dateTo': dateTo,
            'status': 'SCHEDULED,LIVE,IN_PLAY,PAUSED,FINISHED'
        }
        
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            matches_data = response.json()
            matches = []
            competition_logo = matches_data.get('competition', {}).get('emblem', '')
            
            for match in matches_data.get('matches', []):
                if match['status'] in ['FINISHED', 'IN_PLAY', 'PAUSED']:
                    score = (
                        f"{match['score']['fullTime'].get('home', 0) or 0}-"
                        f"{match['score']['fullTime'].get('away', 0) or 0}"
                    )
                else:
                    score = "vs"
                
                matches.append({
                    'home_team': match['homeTeam']['name'],
                    'home_team_logo': match['homeTeam'].get('crest', ''),
                    'away_team': match['awayTeam']['name'],
                    'away_team_logo': match['awayTeam'].get('crest', ''),
                    'score': score,
                    'status': match['status'],
                    'utcDate': match['utcDate'],
                    'competition_logo': competition_logo
                })
            
            return matches, None
        else:
            error_msg = f"API returned status code: {response.status_code}"
            return [], error_msg
            
    except Exception as e:
        return [], str(e)

def fetch_standings():
    """Lấy dữ liệu bảng xếp hạng từ API"""
    try:
        url = f'http://api.football-data.org/v4/competitions/{PREMIER_LEAGUE_ID}/standings'
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            standings_data = response.json()
            competition_logo = standings_data.get('competition', {}).get('emblem', '')
            
            total_standings = next((standing for standing in standings_data.get('standings', []) 
                                if standing['type'] == 'TOTAL'), None)
            
            if not total_standings:
                return {'standings': [], 'competition_logo': ''}
            
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
        return {'standings': [], 'competition_logo': '', 'error': str(e)}

@app.route('/')
def index():
    """Route chính của ứng dụng"""
    matches, error = fetch_matches()
    standings_data = fetch_standings()
    
    initial_data = {
        'matches': matches,
        'standings': standings_data,
        'last_updated': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        'error': error
    }
    return render_template('index.html', initial_data=initial_data)

@app.route('/api/matches')
def get_matches_by_date():
    """API endpoint để lấy trận đấu theo ngày"""
    date = request.args.get('date')
    
    if not date:
        return jsonify({
            'matches': [],
            'status': 'error',
            'message': 'No date provided'
        })
    
    matches, error = fetch_matches(date)
    
    return jsonify({
        'matches': matches,
        'date': date,
        'status': 'success' if not error else 'error',
        'message': error if error else None
    })

@app.route('/api/refresh')
def refresh_data():
    """API endpoint để làm mới dữ liệu theo yêu cầu"""
    matches, error = fetch_matches()
    standings_data = fetch_standings()
    
    data = {
        'matches': matches,
        'standings': standings_data,
        'last_updated': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        'error': error
    }
    return jsonify(data)

# For local development
if __name__ == '__main__':
    app.run(debug=True)
