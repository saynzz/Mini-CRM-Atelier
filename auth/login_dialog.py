"""
Лабораторная работа №1. Диалоговые окна двухфакторной аутентификации.

  WelcomeDialog — стартовый экран с выбором действия: «Войти» в
                существующую учётную запись или «Зарегистрироваться» —
                создать новую.

  SetupDialog — регистрация новой учётной записи: логин/пароль (первый
                фактор) и адрес электронной почты, на который в
                дальнейшем будут приходить одноразовые коды. Чтобы
                убедиться, что введённый email действительно принадлежит
                пользователю и доступен ему, сразу же отправляется
                проверочный код, который нужно ввести для завершения
                регистрации.

  LoginDialog  — собственно вход в систему в два шага:
                 шаг 1 — пароль (первый фактор),
                 шаг 2 — одноразовый код, отправленный на email
                         (второй фактор).

  run_authentication() — точка входа, вызываемая из main.py перед запуском
                 главного окна приложения. Показывает WelcomeDialog и, в
                 зависимости от выбора, ведёт пользователя через
                 LoginDialog или SetupDialog, пока тот не войдёт в систему
                 или не закроет окно выбора.
"""

import re

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QStackedWidget, QWidget
)

from auth.user_repository import UserRepository
from auth.email_service import send_otp_email

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def _issue_and_send(repo: UserRepository, username: str, email: str, parent):
    """Генерирует одноразовый код, отправляет его на email и — если
    реальный SMTP не настроен — показывает код прямо в окне (тестовый
    режим), чтобы демонстрация/защита работы не зависела от почтового
    сервера."""
    code = repo.issue_otp(username)
    delivered = send_otp_email(email, code)
    if not delivered:
        QMessageBox.information(
            parent, 'Тестовый режим (SMTP не настроен)',
            'Реальная отправка письма недоступна: SMTP не сконфигурирован '
            'в config.py.\n\n'
            f'Код для входа (только для демонстрации): {code}\n\n'
            'Код также записан в auth/outbox.log.'
        )


class WelcomeDialog(QDialog):
    """Стартовый экран: выбор между входом в существующую учётную запись
    и регистрацией новой. Выбор сохраняется в self.action ('login' или
    'register') и диалог закрывается через accept(); закрытие окна без
    выбора (крестик) соответствует reject()."""

    def __init__(self, repo: UserRepository, parent=None):
        super().__init__(parent)
        self.repo = repo
        self.action = None

        self.setWindowTitle('Mini-CRM Atelier — вход')
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('<b>Добро пожаловать</b>'))

        if repo.has_any_user():
            hint_text = 'Выберите действие: войти в существующую учётную запись ' \
                        'или зарегистрировать новую.'
        else:
            hint_text = 'В системе пока нет ни одной учётной записи. ' \
                        'Начните с регистрации.'
        hint = QLabel(hint_text)
        hint.setWordWrap(True)
        layout.addWidget(hint)

        login_btn = QPushButton('Войти')
        login_btn.clicked.connect(self._choose_login)
        layout.addWidget(login_btn)

        register_btn = QPushButton('Регистрация нового пользователя')
        register_btn.clicked.connect(self._choose_register)
        layout.addWidget(register_btn)

    def _choose_login(self):
        self.action = 'login'
        self.accept()

    def _choose_register(self):
        self.action = 'register'
        self.accept()


class SetupDialog(QDialog):
    """Регистрация новой учётной записи и привязка второго фактора (email)."""

    def __init__(self, repo: UserRepository, parent=None):
        super().__init__(parent)
        self.repo = repo
        self.username = None
        self.email = None
        self._pending_password = None

        self.setWindowTitle('Регистрация новой учётной записи')
        self.setMinimumWidth(480)

        self.stack = QStackedWidget()
        outer = QVBoxLayout(self)
        outer.addWidget(self.stack)

        self.stack.addWidget(self._build_account_page())
        self.stack.addWidget(self._build_email_confirm_page())

    # ------------------------------------------------------------------
    def _build_account_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel('<b>Шаг 1. Новая учётная запись</b>'))
        info = QLabel('Задайте логин и пароль (первый фактор) и email, на который '
                       'будут приходить одноразовые коды входа (второй фактор).')
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QFormLayout()
        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_confirm_edit = QLineEdit()
        self.password_confirm_edit.setEchoMode(QLineEdit.Password)
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText('example@mail.com')
        form.addRow('Логин:', self.username_edit)
        form.addRow('Пароль (мин. 6 символов):', self.password_edit)
        form.addRow('Повтор пароля:', self.password_confirm_edit)
        form.addRow('Email:', self.email_edit)
        layout.addLayout(form)

        next_btn = QPushButton('Далее — отправить код на email →')
        next_btn.clicked.connect(self._go_to_email_step)
        layout.addWidget(next_btn)

        back_btn = QPushButton('← Назад к выбору входа')
        back_btn.clicked.connect(self.reject)
        layout.addWidget(back_btn)
        return page

    def _build_email_confirm_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel('<b>Шаг 2. Подтверждение email (второй фактор)</b>'))

        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        layout.addWidget(QLabel('Введите код, полученный на email:'))
        self.confirm_code_edit = QLineEdit()
        self.confirm_code_edit.setMaxLength(6)
        self.confirm_code_edit.returnPressed.connect(self._finish_setup)
        layout.addWidget(self.confirm_code_edit)

        finish_btn = QPushButton('Завершить регистрацию')
        finish_btn.clicked.connect(self._finish_setup)
        layout.addWidget(finish_btn)

        resend_btn = QPushButton('Отправить код ещё раз')
        resend_btn.clicked.connect(self._resend_code)
        layout.addWidget(resend_btn)
        return page

    # ------------------------------------------------------------------
    def _go_to_email_step(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        confirm = self.password_confirm_edit.text()
        email = self.email_edit.text().strip()

        if not username or not password or not email:
            QMessageBox.warning(self, 'Ошибка', 'Заполните логин, пароль и email')
            return
        if len(password) < 6:
            QMessageBox.warning(self, 'Ошибка', 'Пароль должен содержать не менее 6 символов')
            return
        if password != confirm:
            QMessageBox.warning(self, 'Ошибка', 'Пароли не совпадают')
            return
        if not EMAIL_RE.match(email):
            QMessageBox.warning(self, 'Ошибка', 'Введите корректный email')
            return
        if self.repo.get_user(username):
            QMessageBox.warning(self, 'Ошибка', 'Пользователь с таким логином уже существует')
            return

        self.username = username
        self.email = email
        self._pending_password = password

        self.repo.create_user(username, password, email)
        self.info_label.setText(f'Код подтверждения отправлен на {email}.')
        self.confirm_code_edit.clear()
        _issue_and_send(self.repo, username, email, self)
        self.stack.setCurrentIndex(1)
        self.confirm_code_edit.setFocus()

    def _resend_code(self):
        if self.username:
            _issue_and_send(self.repo, self.username, self.email, self)

    def _finish_setup(self):
        code = self.confirm_code_edit.text().strip()
        ok, error = self.repo.verify_otp(self.username, code)
        if not ok:
            QMessageBox.warning(self, 'Ошибка', error)
            return

        self.repo.confirm_email(self.username)
        QMessageBox.information(self, 'Готово', 'Учётная запись создана и email подтверждён. '
                                                  'Выполняется вход...')
        self.accept()


class LoginDialog(QDialog):
    """Вход в систему в два шага: пароль → одноразовый код на email."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.repo = UserRepository()
        self.authenticated_user = None
        self._current_username = None
        self._current_email = None

        self.setWindowTitle('Вход в систему — Ателье')
        self.setMinimumWidth(420)

        self.stack = QStackedWidget()
        outer = QVBoxLayout(self)
        outer.addWidget(self.stack)

        self.stack.addWidget(self._build_password_page())
        self.stack.addWidget(self._build_otp_page())

    # ------------------------------------------------------------------
    def _build_password_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel('<b>Шаг 1 из 2 — пароль (первый фактор)</b>'))

        form = QFormLayout()
        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.returnPressed.connect(self._check_password)
        form.addRow('Логин:', self.username_edit)
        form.addRow('Пароль:', self.password_edit)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        login_btn = QPushButton('Войти')
        login_btn.clicked.connect(self._check_password)
        btn_row.addWidget(login_btn)
        layout.addLayout(btn_row)

        back_btn = QPushButton('← Назад к выбору входа')
        back_btn.clicked.connect(self.reject)
        layout.addWidget(back_btn)
        return page

    def _build_otp_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel('<b>Шаг 2 из 2 — код с email (второй фактор)</b>'))

        self.otp_hint = QLabel()
        self.otp_hint.setWordWrap(True)
        layout.addWidget(self.otp_hint)

        self.code_edit = QLineEdit()
        self.code_edit.setMaxLength(6)
        self.code_edit.returnPressed.connect(self._check_otp)
        layout.addWidget(self.code_edit)

        confirm_btn = QPushButton('Подтвердить')
        confirm_btn.clicked.connect(self._check_otp)
        layout.addWidget(confirm_btn)

        resend_btn = QPushButton('Отправить код ещё раз')
        resend_btn.clicked.connect(self._resend_code)
        layout.addWidget(resend_btn)

        back_btn = QPushButton('← Назад к вводу пароля')
        back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        layout.addWidget(back_btn)
        return page

    # ------------------------------------------------------------------
    def _check_password(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        if not username or not password:
            QMessageBox.warning(self, 'Ошибка', 'Введите логин и пароль')
            return

        user, error = self.repo.verify_first_factor(username, password)
        if error:
            QMessageBox.warning(self, 'Ошибка входа', error)
            return

        self._current_username = username
        self._current_email = user['email']
        self.otp_hint.setText(f'Код отправлен на {self._current_email}. Введите его ниже.')
        self.code_edit.clear()
        _issue_and_send(self.repo, username, self._current_email, self)
        self.stack.setCurrentIndex(1)
        self.code_edit.setFocus()

    def _resend_code(self):
        if self._current_username:
            _issue_and_send(self.repo, self._current_username, self._current_email, self)

    def _check_otp(self):
        code = self.code_edit.text().strip()
        ok, error = self.repo.verify_otp(self._current_username, code)
        if ok:
            self.authenticated_user = self._current_username
            self.accept()
        else:
            QMessageBox.warning(self, 'Ошибка входа', error)


def run_authentication(parent=None):
    """Полный цикл двухфакторной аутентификации перед запуском приложения.

    Показывает стартовый экран выбора (войти / зарегистрироваться) и
    ведёт пользователя дальше в зависимости от выбора. Цикл повторяется,
    пока пользователь не войдёт в систему либо не закроет окно выбора —
    в последнем случае возвращается None, и main.py завершает работу
    приложения.
    """
    repo = UserRepository()

    while True:
        welcome = WelcomeDialog(repo, parent)
        if welcome.exec_() != QDialog.Accepted:
            return None

        if welcome.action == 'register':
            setup = SetupDialog(repo, parent)
            if setup.exec_() == QDialog.Accepted:
                # Оба фактора (пароль и email-код) уже подтверждены в ходе
                # регистрации — сразу считаем пользователя вошедшим,
                # не заставляя вводить те же данные повторно.
                return setup.username
            # Регистрация отменена ("Назад") — возвращаемся к выбору.
            continue

        # welcome.action == 'login'
        login = LoginDialog(parent)
        if login.exec_() == QDialog.Accepted:
            return login.authenticated_user
        # Вход отменён ("Назад") — возвращаемся к экрану выбора.
        continue
