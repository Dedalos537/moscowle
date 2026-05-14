import os
from flask import current_app

class GameService:
    @staticmethod
    def list_games():
        games_dir = os.path.join(current_app.root_path, 'static', 'games')
        try:
            return [f for f in os.listdir(games_dir) if f.lower().endswith('.html')]
        except Exception:
            return []
