import os
from pathlib import Path

class Config:
    DB_NAME = 'atelier.db'
    DB_PATH = Path(__file__).parent / DB_NAME

    BASE_DIR = Path(__file__).parent
    REPORTS_DIR = BASE_DIR / 'reports'

    APP_NAME = "Ателье - система управления заказами"
    APP_VERSION = "1.0"

    REPORTS_DIR.mkdir(exist_ok=True)

    SMTP_HOST = ''
    SMTP_PORT = 587
    SMTP_USER = ''
    SMTP_PASSWORD = ''
    SMTP_USE_TLS = True
    EMAIL_FROM = 'no-reply@mini-crm-atelier.local'

    OTP_LENGTH = 6            # длина одноразового кода
    OTP_TTL_SECONDS = 300     # срок действия кода, сек. (5 минут)
    OTP_MAX_ATTEMPTS = 5      # число попыток ввода кода до блокировки

    CUTTER_CATEGORIES = [
        'верхняя одежда',
        'легкое платье',
        'мужская одежда',
        'шляпы',
        'меховые изделия'
    ]

    FABRIC_TYPES = [
        'шелк',
        'хлопок',
        'лен',
        'шерсть',
        'синтетика',
        'кожа',
        'джинсовая',
        'трикотаж'
    ]
