import sys
import os
from PyQt5.QtWidgets import QApplication, QMessageBox
from gui.main_window import MainWindow
from database.db_connection import DatabaseConnection
from auth.login_dialog import run_authentication
from pathlib import Path

def check_database():
    from config import Config
    
    if not Config.DB_PATH.exists():
        reply = QMessageBox.question(
            None, 'База данных не найдена',
            'База данных не найдена. Создать новую с тестовыми данными?',
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            from create_database import create_database
            create_database()
            return True
        else:
            return False
    
    db = DatabaseConnection()
    try:
        result = db.fetch_one("SELECT name FROM sqlite_master WHERE type='table' AND name='cutters'")
        if not result:
            QMessageBox.critical(None, 'Ошибка', 'База данных повреждена или имеет неверную структуру')
            return False
        return True
    except:
        return False
    finally:
        db.close()

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    if not check_database():
        sys.exit(1)

    # Лабораторная работа №1: двухфакторная аутентификация
    # (первый фактор - многоразовый пароль, второй фактор - TOTP-код)
    # перед входом в систему.
    current_user = run_authentication()
    if not current_user:
        sys.exit(0)

    window = MainWindow(current_user=current_user)
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()