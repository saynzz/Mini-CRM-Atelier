from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDoubleValidator
from database.db_connection import DatabaseConnection

class FabricTypesManager(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseConnection()
        self.current_type_id = None
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        self.setWindowTitle('Типы ткани')
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Панель инструментов
        toolbar = QHBoxLayout()
        
        add_btn = QPushButton('Добавить')
        add_btn.clicked.connect(self.add_type)
        toolbar.addWidget(add_btn)
        
        edit_btn = QPushButton('Редактировать')
        edit_btn.clicked.connect(self.edit_type)
        toolbar.addWidget(edit_btn)
        
        delete_btn = QPushButton('Удалить')
        delete_btn.clicked.connect(self.delete_type)
        toolbar.addWidget(delete_btn)
        
        refresh_btn = QPushButton('Обновить')
        refresh_btn.clicked.connect(self.load_data)
        toolbar.addWidget(refresh_btn)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(['Код', 'Наименование', 'Кол-во тканей'])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.doubleClicked.connect(self.edit_type)
        
        layout.addWidget(self.table)
        
        # Статистика
        self.stats_label = QLabel('')
        layout.addWidget(self.stats_label)
    
    def load_data(self):
        try:
            query = """
            SELECT ft.*, COUNT(f.fabric_article) as fabric_count
            FROM fabric_types ft
            LEFT JOIN fabrics f ON ft.type_id = f.type_id
            GROUP BY ft.type_id
            ORDER BY ft.type_name
            """
            results = self.db.fetch_all(query)
            
            self.table.setRowCount(len(results))
            
            total_types = len(results)
            total_fabrics = sum(r['fabric_count'] for r in results)
            
            for i, row in enumerate(results):
                self.table.setItem(i, 0, QTableWidgetItem(str(row['type_id'])))
                self.table.setItem(i, 1, QTableWidgetItem(row['type_name']))
                self.table.setItem(i, 2, QTableWidgetItem(str(row['fabric_count'])))
            
            self.table.resizeColumnsToContents()
            self.stats_label.setText(f'Типов ткани: {total_types}, Всего тканей: {total_fabrics}')
            
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Ошибка загрузки: {str(e)}')
    
    def add_type(self):
        self.current_type_id = None
        self.show_type_dialog()
    
    def edit_type(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, 'Предупреждение', 'Выберите тип ткани')
            return
        
        type_id = int(self.table.item(selected, 0).text())
        self.current_type_id = type_id
        self.show_type_dialog()
    
    def show_type_dialog(self):
        dialog = QDialog(self)
        is_edit = self.current_type_id is not None
        dialog.setWindowTitle('Редактирование типа ткани' if is_edit else 'Добавление типа ткани')
        
        layout = QFormLayout(dialog)
        
        # Поле ввода
        name_edit = QLineEdit()
        
        # Загружаем данные для редактирования
        if is_edit:
            query = "SELECT * FROM fabric_types WHERE type_id = ?"
            data = self.db.fetch_one(query, (self.current_type_id,))
            if data:
                name_edit.setText(data['type_name'])
        
        layout.addRow('Наименование типа:', name_edit)
        
        # Кнопки
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(lambda: self.save_type(dialog, name_edit.text()))
        btn_box.rejected.connect(dialog.reject)
        
        layout.addRow(btn_box)
        dialog.exec_()
    
    def save_type(self, dialog, name):
        if not name.strip():
            QMessageBox.warning(dialog, 'Ошибка', 'Введите наименование типа')
            return
        
        try:
            if self.current_type_id:
                query = "UPDATE fabric_types SET type_name = ? WHERE type_id = ?"
                params = (name, self.current_type_id)
            else:
                query = "INSERT INTO fabric_types (type_name) VALUES (?)"
                params = (name,)
            
            self.db.execute_query(query, params)
            dialog.accept()
            self.load_data()
            
        except Exception as e:
            if 'UNIQUE constraint failed' in str(e):
                QMessageBox.warning(dialog, 'Ошибка', 'Тип ткани с таким названием уже существует')
            else:
                QMessageBox.critical(dialog, 'Ошибка', f'Ошибка сохранения: {str(e)}')
    
    def delete_type(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, 'Предупреждение', 'Выберите тип ткани')
            return
        
        type_id = int(self.table.item(selected, 0).text())
        type_name = self.table.item(selected, 1).text()
        
        # Проверяем, используется ли тип
        query = "SELECT COUNT(*) as count FROM fabrics WHERE type_id = ?"
        result = self.db.fetch_one(query, (type_id,))
        
        if result['count'] > 0:
            QMessageBox.critical(
                self, 'Ошибка',
                f'Невозможно удалить тип "{type_name}", так как он используется в {result["count"]} тканях.'
            )
            return
        
        reply = QMessageBox.question(
            self, 'Подтверждение',
            f'Удалить тип ткани "{type_name}"?',
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                query = "DELETE FROM fabric_types WHERE type_id = ?"
                self.db.execute_query(query, (type_id,))
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, 'Ошибка', f'Ошибка удаления: {str(e)}')