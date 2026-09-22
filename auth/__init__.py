"""
Пакет `auth` — реализация двухфакторной аутентификации (лабораторная
работа №1 по дисциплине "Проектирование систем защиты информации").

Первый фактор — многоразовый пароль.
Второй фактор — одноразовый код, отправляемый на email пользователя.
"""

from .security import (
    hash_password, verify_password, generate_otp_code,
)
from .user_repository import UserRepository
from .email_service import send_otp_email
from .login_dialog import WelcomeDialog, LoginDialog, SetupDialog, run_authentication

__all__ = [
    'hash_password', 'verify_password', 'generate_otp_code',
    'UserRepository',
    'send_otp_email',
    'WelcomeDialog', 'LoginDialog', 'SetupDialog', 'run_authentication',
]
