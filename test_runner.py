from django.test.runner import DiscoverRunner
from django.db import connection


class UnmanagedTestRunner(DiscoverRunner):
    """Creates unmanaged tables in the test DB before running tests."""

    def setup_databases(self, **kwargs):
        result = super().setup_databases(**kwargs)
        with connection.cursor() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS leaderboard (
                    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
                    user_id INT UNSIGNED NULL,
                    player_name VARCHAR(100) NOT NULL,
                    game VARCHAR(100) NOT NULL,
                    score INT NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id)
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    player_name VARCHAR(255) NOT NULL,
                    activity TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS achievements (
                    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
                    name VARCHAR(100) NOT NULL,
                    description TEXT NOT NULL,
                    icon VARCHAR(10) NOT NULL,
                    condition_type VARCHAR(50) NOT NULL,
                    condition_value INT NOT NULL,
                    game_specific VARCHAR(100) NULL,
                    PRIMARY KEY (id)
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS user_achievements (
                    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
                    user_id INT UNSIGNED NOT NULL,
                    achievement_id INT UNSIGNED NOT NULL,
                    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    UNIQUE KEY unique_user_achievement (user_id, achievement_id)
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS daily_challenges (
                    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
                    challenge_date DATE NOT NULL UNIQUE,
                    game VARCHAR(100) NOT NULL,
                    title VARCHAR(200) NOT NULL,
                    description TEXT NOT NULL,
                    target_type VARCHAR(50) NOT NULL DEFAULT 'win',
                    target_value INT NOT NULL DEFAULT 1,
                    bonus_points INT NOT NULL DEFAULT 50,
                    PRIMARY KEY (id)
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS daily_challenge_completions (
                    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
                    user_id INT UNSIGNED NOT NULL,
                    challenge_id INT UNSIGNED NOT NULL,
                    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    UNIQUE KEY unique_completion (user_id, challenge_id)
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS favorite_games (
                    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
                    user_id INT UNSIGNED NOT NULL,
                    game VARCHAR(100) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    UNIQUE KEY unique_fav_game (user_id, game)
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS favorite_words (
                    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
                    user_id INT UNSIGNED NOT NULL,
                    word VARCHAR(100) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    UNIQUE KEY unique_fav_word (user_id, word)
                )
            """)
        return result
