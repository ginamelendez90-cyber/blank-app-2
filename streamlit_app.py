import json
from nba_api.live.nba.endpoints import scoreboard

def handler(event, context):
    """
    Función Serverless de Netlify que expone los datos en vivo de la NBA en formato JSON.
    Se puede consultar mediante una petición HTTP GET.
    """
    try:
        # Obtener el scoreboard oficial de la NBA
        board = scoreboard.ScoreBoard()
        games_data = board.get_dict()
        
        games = games_data.get('scoreboard', {}).get('games', [])
        
        partidos_resumen = []
        for g in games:
            home_team = g.get('homeTeam', {})
            away_team = g.get('awayTeam', {})
            
            partido_info = {
                'GameID': g.get('gameId'),
                'Status': g.get('gameStatusText'),
                'Period': g.get('period'),
                'Clock': g.get('gameClock'),
                'HomeTeam': home_team.get('teamName'),
                'HomeCity': home_team.get('teamCity'),
                'HomeScore': home_team.get('score'),
                'AwayTeam': away_team.get('teamName'),
                'AwayCity': away_team.get('teamCity'),
                'AwayScore': away_team.get('score')
            }
            partidos_resumen.append(partido_info)
            
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*' # Permite consultas externas (CORS)
            },
            'body': json.dumps(partidos_resumen, ensure_ascii=False)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }
