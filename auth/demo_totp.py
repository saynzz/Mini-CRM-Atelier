"""
Лабораторная работа №1. Второй фактор аутентификации изменён с TOTP на
одноразовый код по email — см. auth/email_service.py и
auth/user_repository.py (issue_otp/verify_otp).

Этот файл оставлен как заглушка на случай, если что-то в проекте всё ещё
на него ссылается. Для просмотра последнего отправленного кода (в
тестовом режиме, когда SMTP не настроен) используйте:

    python -m auth.show_last_code <email>
"""

import sys

if __name__ == '__main__':
    print('Второй фактор теперь — код на email, а не TOTP.')
    print('Используйте: python -m auth.show_last_code <email>')
    sys.exit(0)
