from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDoubleValidator
from database.db_connection import DatabaseConnection

class FabricsManager(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseConnection()
        self.current_fabric_article = None
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        self.setWindowTitle('Управление тканями')
        self.setMinimumSize(900, 500)
        
        layout = QVBoxLayout(self)
        
        # Панель инструментов
        toolbar = QHBoxLayout()
        
        add_btn = QPushButton('Добавить ткань')
        add_btn.clicked.connect(self.add_fabric)
        toolbar.addWidget(add_btn)
        
        edit_btn = QPushButton('Редактировать')
        edit_btn.clicked.connect(self.edit_fabric)
        toolbar.addWidget(edit_btn)
        
        delete_btn = QPushButton('Удалить')
        delete_btn.clicked.connect(self.delete_fabric)
        toolbar.addWidget(delete_btn)
        
        refresh_btn = QPushButton('Обновить')
        refresh_btn.clicked.connect(self.load_data)
        toolbar.addWidget(refresh_btn)
        
        # Фильтр по типу
        toolbar.addWidget(QLabel('Тип ткани:'))
        self.type_filter = QComboBox()
        self.type_filter.addItem('Все типы', None)
        self.load_types_filter()
        self.type_filter.currentIndexChanged.connect(self.load_data)
        toolbar.addWidget(self.type_filter)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            'Артикул', 'Наименование', 'Ед.изм', 'Цена', 'Тип', 'Кол-во', 'Стоимость'
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.doubleClicked.connect(self.edit_fabric)
        
        layout.addWidget(self.table)
        
        # Статистика
        self.stats_label = QLabel('')
        layout.addWidget(self.stats_label)
    
    def load_types_filter(self):
        types = self.db.fetch_all("SELECT * FROM fabric_types ORDER BY type_name")
        for t in types:
            self.type_filter.addItem(t['type_name'], t['type_id'])
    
    def load_data(self):
        try:
            type_id = self.type_filter.currentData()
            
            if type_id:
                query = """
                SELECT f.*, ft.type_name,
                       (f.quantity * f.price) as total_value
                FROM fabrics f
                JOIN fabric_types ft ON f.type_id = ft.type_id
                WHERE f.type_id = ?
                ORDER BY f.fabric_name
                """
                params = (type_id,)
            else:
                query = """
                SELECT f.*, ft.type_name,
                       (f.quantity * f.price) as total_value
                FROM fabrics f
                JOIN fabric_types ft ON f.type_id = ft.type_id
                ORDER BY f.fabric_name
                """
                params = None
            
            results = self.db.fetch_all(query, params)
            
            self.table.setRowCount(len(results))
            
            total_quantity = 0
            total_value = 0
            
            for i, row in enumerate(results):
                self.table.setItem(i, 0, QTableWidgetItem(row['fabric_article']))
                self.table.setItem(i, 1, QTableWidgetItem(row['fabric_name']))
                self.table.setItem(i, 2, QTableWidgetItem(row['unit']))
                self.table.setItem(i, 3, QTableWidgetItem(f"{row['price']:,.2f}"))
                self.table.setItem(i, 4, QTableWidgetItem(row['type_name']))
                self.table.setItem(i, 5, QTableWidgetItem(f"{row['quantity']:.2f}"))
                self.table.setItem(i, 6, QTableWidgetItem(f"{row['total_value']:,.2f}"))
                
                total_quantity += row['quantity']
                total_value += row['total_value']
            
            self.table.resizeColumnsToContents()
            
            self.stats_label.setText(
                f'Тканей: {len(results)} | '
                f'Общее количество: {total_quantity:.2f} {results[0]["unit"] if results else ""} | '
                f'Общая стоимость: {total_value:,.2f} руб'
            )
            
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Ошибка загрузки: {str(e)}')
    
    def add_fabric(self):
        self.current_fabric_article = None
        self.show_fabric_dialog()
    
    def edit_fabric(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, 'Предупреждение', 'Выберите ткань')
            return
        
        article = self.table.item(selected, 0).text()
        self.current_fabric_article = article
        self.show_fabric_dialog()
    
    def show_fabric_dialog(self):
        dialog = QDialog(self)
        is_edit = self.current_fabric_article is not None
        dialog.setWindowTitle('Редактирование ткани' if is_edit else 'Добавление ткани')
        
        layout = QFormLayout(dialog)
        
        # Поля ввода
        article_edit = QLineEdit()
        if is_edit:
            article_edit.setText(self.current_fabric_article)
            article_edit.setReadOnly(True)
        
        name_edit = QLineEdit()
        unit_combo = QComboBox()
        unit_combo.addItems(['метр', 'упаковка', 'рулон', 'кг'])
        
        price_edit = QLineEdit()
        price_edit.setValidator(QDoubleValidator(0, 100000, 2))
        
        quantity_edit = QLineEdit()
        quantity_edit.setValidator(QDoubleValidator(0, 100000, 2))
        
        type_combo = QComboBox()
        types = self.db.fetch_all("SELECT * FROM fabric_types ORDER BY type_name")
        for t in types:
            type_combo.addItem(t['type_name'], t['type_id'])
        
        # Загружаем данные для редактирования
        if is_edit:
            query = """
            SELECT f.*, ft.type_name 
            FROM fabrics f 
            JOIN fabric_types ft ON f.type_id = ft.type_id
            WHERE f.fabric_article = ?
            """
            data = self.db.fetch_one(query, (self.current_fabric_article,))
            
            if data:
                name_edit.setText(data['fabric_name'])
                unit_combo.setCurrentText(data['unit'])
                price_edit.setText(str(data['price']))
                quantity_edit.setText(str(data['quantity']))
                for i in range(type_combo.count()):
                    if type_combo.itemText(i) == data['type_name']:
                        type_combo.setCurrentIndex(i)
                        break
        
        layout.addRow('Артикул ткани:', article_edit)
        layout.addRow('Наименование:', name_edit)
        layout.addRow('Единица измерения:', unit_combo)
        layout.addRow('Цена за единицу (руб):', price_edit)
        layout.addRow('Количество на складе:', quantity_edit)
        layout.addRow('Тип ткани:', type_combo)
        
        # Кнопки
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(lambda: self.save_fabric(
            dialog, article_edit.text(), name_edit.text(), 
            unit_combo.currentText(), price_edit.text(),
            quantity_edit.text(), type_combo.currentData()
        ))
        btn_box.rejected.connect(dialog.reject)
        
        layout.addRow(btn_box)
        dialog.exec_()
    
    def save_fabric(self, dialog, article, name, unit, price, quantity, type_id):
        if not article.strip():
            QMessageBox.warning(dialog, 'Ошибка', 'Введите артикул ткани')
            return
        
        if not name.strip():
            QMessageBox.warning(dialog, 'Ошибка', 'Введите наименование ткани')
            return
        
        if not price.strip():
            QMessageBox.warning(dialog, 'Ошибка', 'Введите цену ткани')
            return
        
        if not quantity.strip():
            QMessageBox.warning(dialog, 'Ошибка', 'Введите количество ткани')
            return
        
        try:
            price_value = float(price)
            quantity_value = float(quantity)
            
            if self.current_fabric_article:
                query = """
                UPDATE fabrics 
                SET fabric_name = ?, unit = ?, price = ?, 
                    type_id = ?, quantity = ?
                WHERE fabric_article = ?
                """
                params = (name, unit, price_value, type_id, quantity_value, article)
            else:
                query = """
                INSERT INTO fabrics 
                (fabric_article, fabric_name, unit, price, type_id, quantity)
                VALUES (?, ?, ?, ?, ?, ?)
                """
                params = (article, name, unit, price_value, type_id, quantity_value)
            
            self.db.execute_query(query, params)
            dialog.accept()
            self.load_data()
            
        except Exception as e:
            if 'UNIQUE constraint failed' in str(e):
                QMessageBox.warning(dialog, 'Ошибка', 'Ткань с таким артикулом уже существует')
            else:
                QMessageBox.critical(dialog, 'Ошибка', f'Ошибка сохранения: {str(e)}')
    
    def delete_fabric(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, 'Предупреждение', 'Выберите ткань')
            return
        
        article = self.table.item(selected, 0).text()
        fabric_name = self.table.item(selected, 1).text()
        
        # Проверяем, используется ли ткань
        query = "SELECT COUNT(*) as count FROM order_fabrics WHERE fabric_article = ?"
        result = self.db.fetch_one(query, (article,))
        
        if result['count'] > 0:
            QMessageBox.critical(
                self, 'Ошибка',
                f'Невозможно удалить ткань "{fabric_name}", '
                f'так как она используется в {result["count"]} заказах.'
            )
            return
        
        reply = QMessageBox.question(
            self, 'Подтверждение',
            f'Удалить ткань "{fabric_name}" (арт. {article})?',
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                query = "DELETE FROM fabrics WHERE fabric_article = ?"
                self.db.execute_query(query, (article,))
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, 'Ошибка', f'Ошибка удаления: {str(e)}')