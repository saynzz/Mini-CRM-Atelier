"""
Лабораторная работа №1. Вспомогательный CLI-скрипт для демонстрации и
защиты работы.

В боевом режиме одноразовый код уходит пользователю по реальной почте
(если в config.py указан SMTP_HOST). Если SMTP не настроен, приложение
само показывает код во всплывающем окне (см. auth/login_dialog.py,
функция _issue_and_send) — но на случай, если это окно уже закрыли,
этот скрипт позволяет посмотреть последний код, записанный в тестовый
"почтовый ящик" auth/outbox.log.

Использование:
    python -m auth.show_last_code <email>
"""

import re
import sys

from auth.email_service import OUTBOX_PATH

CODE_RE = re.compile(r'одноразовый код для входа в систему:\s*(\d+)')


def main():
    if len(sys.argv) != 2:
        print('Использование: python -m auth.show_last_code <email>')
        sys.exit(1)

    email = sys.argv[1]

    if not OUTBOX_PATH.exists():
        print('Тестовый почтовый ящик пуст (auth/outbox.log ещё не создан).')
        sys.exit(1)

    entries = OUTBOX_PATH.read_text(encoding='utf-8').split('--- ')
    for raw in reversed(entries):
        if not raw.strip():
            continue
        block = '--- ' + raw
        if f'Кому: {email}' not in block:
            continue
        match = CODE_RE.search(block)
        if match:
            print(f'Последний код, отправленный на {email}: {match.group(1)}')
            return

    print(f'Писем для {email} в auth/outbox.log не найдено.')


if __name__ == '__main__':
    main()
