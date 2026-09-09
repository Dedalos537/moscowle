import json
import os

from flask import current_app, url_for

from app.models.game import Game


class GameService:
    @staticmethod
    def list_games():
        games_dir = os.path.join(current_app.root_path, 'static', 'games')
        try:
            return [f for f in os.listdir(games_dir) if f.lower().endswith('.html') and not f.startswith('_')]
        except Exception:
            return []

    @staticmethod
    def list_meta():
        files = GameService.list_games()
        by_name = {g.filename: g for g in Game.query.filter(Game.is_active.is_(True)).all()}
        out = []
        for fname in files:
            game = by_name.get(fname)
            out.append(
                {
                    'filename': fname,
                    'title': game.title if game else fname.replace('.html', '').replace('_', ' ').title(),
                    'filetype': game.filetype if game else 'html',
                    'thumbnail': game.thumbnail if game else None,
                    'meta': (json.loads(game.meta) if game and game.meta else None),
                    'is_active': bool(game.is_active) if game else True,
                    'url': url_for('static', filename=f'games/{fname}'),
                }
            )
        return out
