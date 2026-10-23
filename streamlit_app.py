import time
import pandas as pd
from nba_api.live.nba.endpoints import scoreboard, boxscore

def obtener_partidos_en_vivo():
    """
    Obtiene el scoreboard actual de la NBA utilizando los endpoints en vivo de la CDN.
    Retorna una lista de diccionarios con la información clave de cada encuentro.
    """
    try:
        board = scoreboard.ScoreBoard()
        games_data = board.get_dict()
        
        # El JSON contiene la estructura 'scoreboard' -> 'games'
        games = games_data.get('scoreboard', {}).get('games', [])
        
        partidos_resumen = []
        for g in games:
            game_id = g.get('gameId')
            status = g.get('gameStatusText') # Ejemplo: "Q4 02:15" o "Final"
            period = g.get('period')
            clock = g.get('gameClock')
            
            home_team = g.get('homeTeam', {})
            away_team = g.get('awayTeam', {})
            
            partido_info = {
                'GameID': game_id,
                'Status': status,
                'Period': period,
                'Clock': clock,
                'HomeTeam': home_team.get('teamName'),
                'HomeCity': home_team.get('teamCity'),
                'HomeScore': home_team.get('score'),
                'AwayTeam': away_team.get('teamName'),
                'AwayCity': away_team.get('teamCity'),
                'AwayScore': away_team.get('score')
            }
            partidos_resumen.append(partido_info)
            
        return pd.DataFrame(partidos_resumen)
    
    except Exception as e:
        print(f"Error al obtener el scoreboard: {e}")
        return pd.DataFrame()

def obtener_estadisticas_detalladas(game_id):
    """
    Obtiene el box score detallado en tiempo real de un partido específico 
    para extraer métricas esenciales para pronósticos (tiros de campo, eficiencias, etc.).
    """
    try:
        bs = boxscore.BoxScore(game_id=game_id)
        data = bs.get_dict().get('game', {})
        
        home_stats = data.get('homeTeam', {})
        away_stats = data.get('awayTeam', {})
        
        return {
            'HomeStats': home_stats.get('statistics', {}),
            'AwayStats': away_stats.get('statistics', {})
        }
    except Exception as e:
        print(f"Error al obtener el box score para el juego {game_id}: {e}")
        return None

if __name__ == "__main__":
    print("--- MONITOR DE PARTIDOS NBA EN VIVO PARA PRONÓSTICOS ---")
    
    # Bucle de monitoreo simulado (polling)
    # En un entorno de producción, puedes ajustar este intervalo o conectarlo a WebSockets/Streamlit
    intentos = 1
    while intentos <= 2:
        print(f"\n[Consulta #{intentos}] Consultando estado de la jornada...")
        df_partidos = obtener_partidos_en_vivo()
        
        if df_partidos.empty:
            print("No se encontraron partidos activos en este momento o la jornada no ha iniciado.")
        else:
            print(df_partidos[['GameID', 'Status', 'AwayCity', 'AwayScore', '@', 'HomeScore', 'HomeCity']].to_string(index=False) if ' @ ' in str(df_partidos.columns) else df_partidos)
            
            # Ejemplo analítico: Si hay un juego en curso, extraer sus métricas profundas
            for idx, row in df_partidos.iterrows():
                if "Final" not in str(row['Status']) and "ET" not in str(row['Status']): # Si el juego está en vivo
                    print(f"\n-> Analizando métricas en vivo para: {row['AwayTeam']} vs {row['HomeTeam']} (ID: {row['GameID']})")
                    stats = obtener_estadisticas_detalladas(row['GameID'])
                    # Aquí puedes integrar tus modelos de Machine Learning o matrices de Poisson
                    
        print("\nEsperando 60 segundos para la siguiente actualización...")
        time.sleep(60)
        intentos += 1
