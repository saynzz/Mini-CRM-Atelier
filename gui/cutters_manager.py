from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from database.db_connection import DatabaseConnection

class CuttersManager(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseConnection()
        self.current_cutter_id = None
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        self.setWindowTitle('Управление закройщиками')
        self.setMinimumSize(700, 400)
        
        layout = QVBoxLayout(self)
        
        # Панель инструментов
        toolbar = QHBoxLayout()
        
        buttons = [
            ('Добавить', self.add_cutter),
            ('Редактировать', self.edit_cutter),
            ('Удалить', self.delete_cutter),
            ('Обновить', self.load_data)
        ]
        
        for text, handler in buttons:
            btn = QPushButton(text)
            btn.clicked.connect(handler)
            toolbar.addWidget(btn)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            'Код', 'ФИО', 'Категория', 'Специализация'
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.doubleClicked.connect(self.edit_cutter)
        
        layout.addWidget(self.table)
        
        # Статус
        self.status_label = QLabel('Готово')
        layout.addWidget(self.status_label)
    
    def load_data(self):
        try:
            query = """
            SELECT c.cutter_id, c.full_name, cat.category_name
            FROM cutters c
            JOIN categories cat ON c.category_id = cat.category_id
            ORDER BY c.full_name
            """
            results = self.db.fetch_all(query)
            
            self.table.setRowCount(len(results))
            
            for i, row in enumerate(results):
                self.table.setItem(i, 0, QTableWidgetItem(str(row['cutter_id'])))
                self.table.setItem(i, 1, QTableWidgetItem(row['full_name']))
                self.table.setItem(i, 2, QTableWidgetItem(row['category_name']))
                
                # Специализация на основе категории
                specialization = {
                    'верхняя одежда': 'Пальто, куртки, плащи',
                    'мужская одежда': 'Костюмы, пиджаки, брюки',
                    'легкое платье': 'Платья, юбки, блузки',
                    'шляпы': 'Головные уборы',
                    'меховые изделия': 'Шубы, меховые жилеты'
                }.get(row['category_name'], 'Общая специализация')
                
                self.table.setItem(i, 3, QTableWidgetItem(specialization))
            
            self.table.resizeColumnsToContents()
            self.status_label.setText(f'Загружено закройщиков: {len(results)}')
            
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Ошибка загрузки: {str(e)}')
    
    def add_cutter(self):
        self.current_cutter_id = None
        self.show_cutter_dialog()
    
    def edit_cutter(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, 'Предупреждение', 'Выберите закройщика')
            return
        
        cutter_id = int(self.table.item(selected, 0).text())
        self.current_cutter_id = cutter_id
        self.show_cutter_dialog()
    
    def show_cutter_dialog(self):
        dialog = QDialog(self)
        is_edit = self.current_cutter_id is not None
        dialog.setWindowTitle('Редактирование' if is_edit else 'Добавление закройщика')
        
        layout = QFormLayout(dialog)
        
        # Поля ввода
        name_edit = QLineEdit()
        category_combo = QComboBox()
        
        # Загружаем категории
        categories = self.db.fetch_all("SELECT * FROM categories ORDER BY category_name")
        for cat in categories:
            category_combo.addItem(cat['category_name'], cat['category_id'])
        
        # Загружаем данные для редактирования
        if is_edit:
            query = """
            SELECT c.*, cat.category_name 
            FROM cutters c 
            JOIN categories cat ON c.category_id = cat.category_id
            WHERE c.cutter_id = ?
            """
            data = self.db.fetch_one(query, (self.current_cutter_id,))
            
            if data:
                name_edit.setText(data['full_name'])
                for i in range(category_combo.count()):
                    if category_combo.itemText(i) == data['category_name']:
                        category_combo.setCurrentIndex(i)
                        break
        
        layout.addRow('ФИО закройщика:', name_edit)
        layout.addRow('Категория:', category_combo)
        
        # Кнопки
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(lambda: self.save_cutter(
            dialog, name_edit.text(), category_combo.currentData()
        ))
        btn_box.rejected.connect(dialog.reject)
        
        layout.addRow(btn_box)
        dialog.exec_()
    
    def save_cutter(self, dialog, name, category_id):
        if not name.strip():
            QMessageBox.warning(dialog, 'Ошибка', 'Введите ФИО закройщика')
            return
        
        try:
            if self.current_cutter_id:
                # Обновление
                query = "UPDATE cutters SET full_name = ?, category_id = ? WHERE cutter_id = ?"
                params = (name, category_id, self.current_cutter_id)
            else:
                # Добавление
                query = "INSERT INTO cutters (full_name, category_id) VALUES (?, ?)"
                params = (name, category_id)
            
            self.db.execute_query(query, params)
            dialog.accept()
            self.load_data()
            
        except Exception as e:
            QMessageBox.critical(dialog, 'Ошибка', f'Ошибка сохранения: {str(e)}')
    
    def delete_cutter(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, 'Предупреждение', 'Выберите закройщика')
            return
        
        cutter_id = int(self.table.item(selected, 0).text())
        cutter_name = self.table.item(selected, 1).text()
        
        reply = QMessageBox.question(
            self, 'Подтверждение',
            f'Удалить закройщика {cutter_name}?\n'
            'Внимание: если есть связанные заказы, удаление невозможно.',
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                query = "DELETE FROM cutters WHERE cutter_id = ?"
                self.db.execute_query(query, (cutter_id,))
                self.load_data()
            except Exception as e:
                if 'FOREIGN KEY' in str(e):
                    QMessageBox.critical(
                        self, 'Ошибка',
                        'Невозможно удалить закройщика, так как есть связанные заказы.'
                    )
                else:
                    QMessageBox.critical(self, 'Ошибка', f'Ошибка удаления: {str(e)}')