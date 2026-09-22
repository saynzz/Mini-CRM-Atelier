"""
Лабораторная работа №1. Отправка одноразового кода подтверждения на
электронную почту пользователя (второй фактор аутентификации).

Использует SMTP, если он сконфигурирован в config.py (Config.SMTP_HOST).
Если SMTP не настроен (типичная ситуация при выполнении и защите учебной
работы, когда нет доступа к реальному почтовому серверу), модуль работает
в тестовом режиме: "письмо" выводится в консоль и дописывается в файл
auth/outbox.log — это позволяет продемонстрировать работу второго фактора
без реальной инфраструктуры электронной почты, сохраняя при этом полностью
рабочий путь для боевого SMTP-сервера.
"""

import smtplib
import ssl
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

try:
    import certifi
except ImportError:
    certifi = None

OUTBOX_PATH = Path(__file__).parent / 'outbox.log'


def _fallback_deliver(to_email: str, subject: str, body: str) -> None:
    """"Отправка" в тестовом режиме: пишем письмо в лог-файл и в консоль."""
    entry = (
        f'--- {datetime.now().isoformat(timespec="seconds")} ---\n'
        f'Кому: {to_email}\n'
        f'Тема: {subject}\n'
        f'{body}\n'
    )
    print('[auth] SMTP не настроен — код выводится локально (тестовый режим):')
    print(entry)
    with open(OUTBOX_PATH, 'a', encoding='utf-8') as f:
        f.write(entry + '\n')


def send_otp_email(to_email: str, code: str) -> bool:
    """Отправляет одноразовый код на email пользователя.

    Возвращает True, если письмо реально отправлено через SMTP, и False,
    если сработал тестовый режим (код при этом всё равно доступен —
    см. auth/outbox.log и консоль)."""
    from config import Config

    subject = 'Код подтверждения входа — Mini-CRM Atelier'
    body = (
        f'Ваш одноразовый код для входа в систему: {code}\n'
        f'Код действителен {Config.OTP_TTL_SECONDS // 60} минут(ы).\n'
        'Если вы не запрашивали вход, просто проигнорируйте это письмо.'
    )

    smtp_host = getattr(Config, 'SMTP_HOST', '') or ''
    if not smtp_host:
        _fallback_deliver(to_email, subject, body)
        return False

    try:
        user = (getattr(Config, 'SMTP_USER', '') or '').strip()
        # Пароли приложений Google показываются с пробелами для читаемости
        # ("abcd efgh ijkl mnop") — для входа их нужно убрать.
        password = (getattr(Config, 'SMTP_PASSWORD', '') or '').replace(' ', '')
        # Большинство SMTP-провайдеров (в т. ч. Gmail) требуют, чтобы адрес
        # "От кого" совпадал с адресом авторизованной учётной записи —
        # иначе письмо может быть отклонено или помечено как подозрительное.
        from_addr = user or getattr(Config, 'EMAIL_FROM', smtp_host)

        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = from_addr
        msg['To'] = to_email

        port = getattr(Config, 'SMTP_PORT', 587)
        use_tls = getattr(Config, 'SMTP_USE_TLS', True)

        # На некоторых установках Python (типично для python.org на macOS)
        # не подключён системный набор корневых сертификатов, из-за чего
        # verify падает с CERTIFICATE_VERIFY_FAILED. Если установлен пакет
        # certifi, используем его набор сертификатов явно.
        if certifi is not None:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
        else:
            ssl_context = ssl.create_default_context()

        with smtplib.SMTP(smtp_host, port, timeout=10) as server:
            if use_tls:
                server.starttls(context=ssl_context)
            if user:
                server.login(user, password)
            server.sendmail(from_addr, [to_email], msg.as_string())
        return True
    except Exception as e:
        print(f'[auth] Ошибка отправки email ({e}), переключение на тестовый режим')
        _fallback_deliver(to_email, subject, body)
        return False
