from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDoubleValidator
from database.db_connection import DatabaseConnection

class ComplicationsManager(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseConnection()
        self.current_complication_id = None
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        self.setWindowTitle('Управление усложнениями')
        self.setMinimumSize(700, 400)
        
        layout = QVBoxLayout(self)
        
        # Информация
        info_label = QLabel(
        )
        info_label.setStyleSheet("background-color: #f0f8ff; padding: 10px; border-radius: 5px;")
        layout.addWidget(info_label)
        
        # Панель инструментов
        toolbar = QHBoxLayout()
        
        add_btn = QPushButton('Добавить усложнение')
        add_btn.clicked.connect(self.add_complication)
        toolbar.addWidget(add_btn)
        
        edit_btn = QPushButton('Редактировать')
        edit_btn.clicked.connect(self.edit_complication)
        toolbar.addWidget(edit_btn)
        
        delete_btn = QPushButton('Удалить')
        delete_btn.clicked.connect(self.delete_complication)
        toolbar.addWidget(delete_btn)
        
        refresh_btn = QPushButton('Обновить')
        refresh_btn.clicked.connect(self.load_data)
        toolbar.addWidget(refresh_btn)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            '№', 'Наименование', 'Цена за элемент', 'Использований'
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.doubleClicked.connect(self.edit_complication)
        
        layout.addWidget(self.table)
        
        # Статистика
        self.stats_label = QLabel('')
        layout.addWidget(self.stats_label)
    
    def load_data(self):
        try:
            query = """
            SELECT c.*, COUNT(oc.complication_id) as usage_count
            FROM complications c
            LEFT JOIN order_complications oc ON c.complication_id = oc.complication_id
            GROUP BY c.complication_id
            ORDER BY c.complication_name
            """
            results = self.db.fetch_all(query)
            
            self.table.setRowCount(len(results))
            
            total_uses = sum(r['usage_count'] for r in results)
            avg_price = sum(r['price_per_element'] for r in results) / len(results) if results else 0
            
            for i, row in enumerate(results):
                self.table.setItem(i, 0, QTableWidgetItem(str(row['complication_id'])))
                self.table.setItem(i, 1, QTableWidgetItem(row['complication_name']))
                self.table.setItem(i, 2, QTableWidgetItem(f"{row['price_per_element']:,.2f}"))
                self.table.setItem(i, 3, QTableWidgetItem(str(row['usage_count'])))
            
            self.table.resizeColumnsToContents()
            
            self.stats_label.setText(
                f'Усложнений: {len(results)} | '
                f'Средняя цена: {avg_price:,.2f} руб | '
                f'Всего использований: {total_uses}'
            )
            
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Ошибка загрузки: {str(e)}')
    
    def add_complication(self):
        self.current_complication_id = None
        self.show_complication_dialog()
    
    def edit_complication(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, 'Предупреждение', 'Выберите усложнение')
            return
        
        complication_id = int(self.table.item(selected, 0).text())
        self.current_complication_id = complication_id
        self.show_complication_dialog()
    
    def show_complication_dialog(self):
        dialog = QDialog(self)
        is_edit = self.current_complication_id is not None
        dialog.setWindowTitle('Редактирование усложнения' if is_edit else 'Добавление усложнения')
        
        layout = QFormLayout(dialog)
        
        # Поля ввода
        name_edit = QLineEdit()
        price_edit = QLineEdit()
        price_edit.setValidator(QDoubleValidator(0, 10000, 2))
        
        # Примеры популярных усложнений
        examples_label = QLabel(
            "Примеры: Вышивка, Аппликация, Стразы, Перфорация, Инкрустация,\n"
            "Кружево, Бисер, Паетки, Вырезка, Комбинирование материалов"
        )
        examples_label.setStyleSheet("color: #666; font-size: 10px;")
        
        # Загружаем данные для редактирования
        if is_edit:
            query = "SELECT * FROM complications WHERE complication_id = ?"
            data = self.db.fetch_one(query, (self.current_complication_id,))
            
            if data:
                name_edit.setText(data['complication_name'])
                price_edit.setText(str(data['price_per_element']))
        
        layout.addRow('Наименование усложнения:', name_edit)
        layout.addRow('Цена за один элемент (руб):', price_edit)
        layout.addRow(examples_label)
        
        # Кнопки
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(lambda: self.save_complication(
            dialog, name_edit.text(), price_edit.text()
        ))
        btn_box.rejected.connect(dialog.reject)
        
        layout.addRow(btn_box)
        dialog.exec_()
    
    def save_complication(self, dialog, name, price):
        if not name.strip():
            QMessageBox.warning(dialog, 'Ошибка', 'Введите наименование усложнения')
            return
        
        if not price.strip():
            QMessageBox.warning(dialog, 'Ошибка', 'Введите цену за элемент')
            return
        
        try:
            price_value = float(price)
            
            if self.current_complication_id:
                query = """
                UPDATE complications 
                SET complication_name = ?, price_per_element = ?
                WHERE complication_id = ?
                """
                params = (name, price_value, self.current_complication_id)
            else:
                query = """
                INSERT INTO complications (complication_name, price_per_element)
                VALUES (?, ?)
                """
                params = (name, price_value)
            
            self.db.execute_query(query, params)
            dialog.accept()
            self.load_data()
            
        except Exception as e:
            QMessageBox.critical(dialog, 'Ошибка', f'Ошибка сохранения: {str(e)}')
    
    def delete_complication(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, 'Предупреждение', 'Выберите усложнение')
            return
        
        complication_id = int(self.table.item(selected, 0).text())
        complication_name = self.table.item(selected, 1).text()
        
        # Проверяем, используется ли усложнение
        query = "SELECT COUNT(*) as count FROM order_complications WHERE complication_id = ?"
        result = self.db.fetch_one(query, (complication_id,))
        
        if result['count'] > 0:
            QMessageBox.critical(
                self, 'Ошибка',
                f'Невозможно удалить усложнение "{complication_name}", '
                f'так как оно используется в {result["count"]} заказах.'
            )
            return
        
        reply = QMessageBox.question(
            self, 'Подтверждение',
            f'Удалить усложнение "{complication_name}"?',
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                query = "DELETE FROM complications WHERE complication_id = ?"
                self.db.execute_query(query, (complication_id,))
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, 'Ошибка', f'Ошибка удаления: {str(e)}')