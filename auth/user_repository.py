"""
Лабораторная работа №1. Репозиторий учётных записей пользователей.

Хранит пользователей в таблице `users` базы данных ателье (atelier.db) и
реализует политику защиты парольной системы, описанную в методических
указаниях (табл. 2):
  - ограничение числа попыток ввода пароля и ввода одноразового кода;
  - временная блокировка учётной записи после превышения числа попыток;
  - хранение пароля и одноразового кода только в виде свёртки
    (см. auth/security.py) — никогда в открытом виде;
  - ограниченный срок действия одноразового кода (второй фактор).
"""

from datetime import datetime, timedelta

from config import Config
from database.db_connection import DatabaseConnection
from auth.security import hash_password, verify_password, generate_otp_code

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 5


class UserRepository:
    def __init__(self):
        self.db = DatabaseConnection()
        self._ensure_table()

    # ------------------------------------------------------------------
    def _ensure_table(self):
        self.db.execute_query('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                email TEXT NOT NULL DEFAULT '',
                email_confirmed INTEGER NOT NULL DEFAULT 0,
                otp_hash TEXT,
                otp_salt TEXT,
                otp_expires_at TEXT,
                otp_attempts INTEGER NOT NULL DEFAULT 0,
                failed_attempts INTEGER NOT NULL DEFAULT 0,
                locked_until TEXT,
                created_at TEXT NOT NULL,
                last_login TEXT
            )
        ''')
        self._migrate_legacy_columns()

    def _migrate_legacy_columns(self):
        """Мягкая миграция: если таблица users осталась от более ранней
        версии модуля (например, ещё с TOTP-полями totp_secret /
        totp_confirmed), добавляем недостающие новые столбцы, не трогая
        уже сохранённые записи, и убираем устаревшие столбцы со
        связывающим NOT NULL, которые иначе блокировали бы вставку новых
        пользователей (не знающих о totp_secret)."""
        existing = {row['name'] for row in self.db.fetch_all('PRAGMA table_info(users)')}
        required_columns = {
            'email': "TEXT NOT NULL DEFAULT ''",
            'email_confirmed': 'INTEGER NOT NULL DEFAULT 0',
            'otp_hash': 'TEXT',
            'otp_salt': 'TEXT',
            'otp_expires_at': 'TEXT',
            'otp_attempts': 'INTEGER NOT NULL DEFAULT 0',
        }
        for column, definition in required_columns.items():
            if column not in existing:
                self.db.execute_query(f'ALTER TABLE users ADD COLUMN {column} {definition}')

        for legacy_column in ('totp_secret', 'totp_confirmed'):
            if legacy_column in existing:
                try:
                    self.db.execute_query(f'ALTER TABLE users DROP COLUMN {legacy_column}')
                except Exception:
                    # Старая версия SQLite (< 3.35) не умеет DROP COLUMN —
                    # оставляем столбец как есть, это не критично, если
                    # он не NOT NULL без значения по умолчанию.
                    pass

    # ------------------------------------------------------------------
    def has_any_user(self) -> bool:
        row = self.db.fetch_one('SELECT COUNT(*) as cnt FROM users')
        return bool(row and row['cnt'] > 0)

    def get_user(self, username: str):
        return self.db.fetch_one('SELECT * FROM users WHERE username = ?', (username,))

    def create_user(self, username: str, password: str, email: str):
        password_hash, salt = hash_password(password)
        self.db.execute_query('''
            INSERT INTO users (username, password_hash, password_salt, email,
                                email_confirmed, otp_attempts, failed_attempts, created_at)
            VALUES (?, ?, ?, ?, 0, 0, 0, ?)
        ''', (username, password_hash, salt, email, datetime.now().isoformat()))

    def confirm_email(self, username: str):
        self.db.execute_query('UPDATE users SET email_confirmed = 1 WHERE username = ?', (username,))

    # ------------------------------------------------------------------ пароль (1-й фактор)
    def is_locked(self, user) -> bool:
        if not user['locked_until']:
            return False
        return datetime.now() < datetime.fromisoformat(user['locked_until'])

    def register_failed_attempt(self, username: str):
        user = self.get_user(username)
        if not user:
            return
        attempts = user['failed_attempts'] + 1
        locked_until = None
        if attempts >= MAX_FAILED_ATTEMPTS:
            locked_until = (datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
            attempts = 0
        self.db.execute_query(
            'UPDATE users SET failed_attempts = ?, locked_until = ? WHERE username = ?',
            (attempts, locked_until, username)
        )

    def reset_failed_attempts(self, username: str):
        self.db.execute_query(
            'UPDATE users SET failed_attempts = 0, locked_until = NULL, last_login = ? WHERE username = ?',
            (datetime.now().isoformat(), username)
        )

    def verify_first_factor(self, username: str, password: str):
        """Первый фактор — многоразовый пароль.
        Возвращает кортеж (user_row | None, error_message | None)."""
        user = self.get_user(username)
        if not user:
            return None, 'Пользователь не найден'
        if self.is_locked(user):
            until = user['locked_until']
            return None, f'Учётная запись временно заблокирована до {until}'
        if verify_password(password, user['password_salt'], user['password_hash']):
            return user, None
        self.register_failed_attempt(username)
        return None, 'Неверный пароль'

    # ------------------------------------------------------------------ email-код (2-й фактор)
    def issue_otp(self, username: str) -> str:
        """Генерирует новый одноразовый код, сохраняет в БД только его
        СВЁРТКУ (не сам код) со сроком действия Config.OTP_TTL_SECONDS и
        возвращает код в открытом виде — вызывающий код должен немедленно
        отправить его на email пользователя (см. auth/email_service.py)."""
        code = generate_otp_code(Config.OTP_LENGTH)
        code_hash, salt = hash_password(code)
        expires_at = (datetime.now() + timedelta(seconds=Config.OTP_TTL_SECONDS)).isoformat()
        self.db.execute_query(
            'UPDATE users SET otp_hash = ?, otp_salt = ?, otp_expires_at = ?, otp_attempts = 0 '
            'WHERE username = ?',
            (code_hash, salt, expires_at, username)
        )
        return code

    def verify_otp(self, username: str, code: str):
        """Проверяет одноразовый код, присланный на email.
        Возвращает кортеж (ok: bool, error_message | None)."""
        user = self.get_user(username)
        if not user or not user['otp_hash']:
            return False, 'Код не запрошен. Начните вход заново.'
        if datetime.now() > datetime.fromisoformat(user['otp_expires_at']):
            return False, 'Срок действия кода истёк. Запросите новый код.'
        if user['otp_attempts'] >= Config.OTP_MAX_ATTEMPTS:
            return False, 'Превышено число попыток ввода кода. Запросите новый код.'

        if verify_password(code, user['otp_salt'], user['otp_hash']):
            self.db.execute_query(
                'UPDATE users SET otp_hash = NULL, otp_salt = NULL, otp_expires_at = NULL, '
                'otp_attempts = 0, last_login = ? WHERE username = ?',
                (datetime.now().isoformat(), username)
            )
            return True, None

        self.db.execute_query(
            'UPDATE users SET otp_attempts = otp_attempts + 1 WHERE username = ?', (username,)
        )
        return False, 'Неверный код'
