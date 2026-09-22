from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDoubleValidator
from database.db_connection import DatabaseConnection

class ProductsManager(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseConnection()
        self.current_product_id = None
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        self.setWindowTitle('Управление изделиями')
        self.setMinimumSize(800, 500)
        
        layout = QVBoxLayout(self)
        
        # Панель инструментов
        toolbar = QHBoxLayout()
        
        add_btn = QPushButton('Добавить изделие')
        add_btn.clicked.connect(self.add_product)
        toolbar.addWidget(add_btn)
        
        edit_btn = QPushButton('Редактировать')
        edit_btn.clicked.connect(self.edit_product)
        toolbar.addWidget(edit_btn)
        
        delete_btn = QPushButton('Удалить')
        delete_btn.clicked.connect(self.delete_product)
        toolbar.addWidget(delete_btn)
        
        refresh_btn = QPushButton('Обновить')
        refresh_btn.clicked.connect(self.load_data)
        toolbar.addWidget(refresh_btn)
        
        # Фильтр по категории
        toolbar.addWidget(QLabel('Категория:'))
        self.category_filter = QComboBox()
        self.category_filter.addItem('Все категории', None)
        self.load_categories_filter()
        self.category_filter.currentIndexChanged.connect(self.load_data)
        toolbar.addWidget(self.category_filter)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            'Код', 'Наименование', 'Цена основы', 'Категория', 'Заказов'
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.doubleClicked.connect(self.edit_product)
        
        layout.addWidget(self.table)
        
        # Статистика
        self.stats_label = QLabel('')
        layout.addWidget(self.stats_label)
    
    def load_categories_filter(self):
        categories = self.db.fetch_all("SELECT * FROM categories ORDER BY category_name")
        for cat in categories:
            self.category_filter.addItem(cat['category_name'], cat['category_id'])
    
    def load_data(self):
        try:
            category_id = self.category_filter.currentData()
            
            if category_id:
                query = """
                SELECT p.*, c.category_name, 
                       COUNT(o.order_number) as order_count
                FROM products p
                JOIN categories c ON p.category_id = c.category_id
                LEFT JOIN orders o ON p.product_id = o.product_id
                WHERE p.category_id = ?
                GROUP BY p.product_id
                ORDER BY p.product_name
                """
                params = (category_id,)
            else:
                query = """
                SELECT p.*, c.category_name,
                       COUNT(o.order_number) as order_count
                FROM products p
                JOIN categories c ON p.category_id = c.category_id
                LEFT JOIN orders o ON p.product_id = o.product_id
                GROUP BY p.product_id
                ORDER BY p.product_name
                """
                params = None
            
            results = self.db.fetch_all(query, params)
            
            self.table.setRowCount(len(results))
            
            total_price = 0
            total_orders = 0
            
            for i, row in enumerate(results):
                self.table.setItem(i, 0, QTableWidgetItem(str(row['product_id'])))
                self.table.setItem(i, 1, QTableWidgetItem(row['product_name']))
                self.table.setItem(i, 2, QTableWidgetItem(f"{row['base_price']:,.2f}"))
                self.table.setItem(i, 3, QTableWidgetItem(row['category_name']))
                self.table.setItem(i, 4, QTableWidgetItem(str(row['order_count'])))
                
                total_price += row['base_price']
                total_orders += row['order_count']
            
            self.table.resizeColumnsToContents()
            
            avg_price = total_price / len(results) if results else 0
            self.stats_label.setText(
                f'Изделий: {len(results)} | '
                f'Средняя цена: {avg_price:,.2f} руб | '
                f'Всего заказов: {total_orders}'
            )
            
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Ошибка загрузки: {str(e)}')
    
    def add_product(self):
        self.current_product_id = None
        self.show_product_dialog()
    
    def edit_product(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, 'Предупреждение', 'Выберите изделие')
            return
        
        product_id = int(self.table.item(selected, 0).text())
        self.current_product_id = product_id
        self.show_product_dialog()
    
    def show_product_dialog(self):
        dialog = QDialog(self)
        is_edit = self.current_product_id is not None
        dialog.setWindowTitle('Редактирование изделия' if is_edit else 'Добавление изделия')
        
        layout = QFormLayout(dialog)
        
        # Поля ввода
        name_edit = QLineEdit()
        price_edit = QLineEdit()
        price_edit.setValidator(QDoubleValidator(0, 1000000, 2))
        
        category_combo = QComboBox()
        categories = self.db.fetch_all("SELECT * FROM categories ORDER BY category_name")
        for cat in categories:
            category_combo.addItem(cat['category_name'], cat['category_id'])
        
        # Загружаем данные для редактирования
        if is_edit:
            query = """
            SELECT p.*, c.category_name 
            FROM products p 
            JOIN categories c ON p.category_id = c.category_id
            WHERE p.product_id = ?
            """
            data = self.db.fetch_one(query, (self.current_product_id,))
            
            if data:
                name_edit.setText(data['product_name'])
                price_edit.setText(str(data['base_price']))
                for i in range(category_combo.count()):
                    if category_combo.itemText(i) == data['category_name']:
                        category_combo.setCurrentIndex(i)
                        break
        
        layout.addRow('Наименование изделия:', name_edit)
        layout.addRow('Цена основы (руб):', price_edit)
        layout.addRow('Категория:', category_combo)
        
        # Кнопки
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(lambda: self.save_product(
            dialog, name_edit.text(), price_edit.text(), category_combo.currentData()
        ))
        btn_box.rejected.connect(dialog.reject)
        
        layout.addRow(btn_box)
        dialog.exec_()
    
    def save_product(self, dialog, name, price, category_id):
        if not name.strip():
            QMessageBox.warning(dialog, 'Ошибка', 'Введите наименование изделия')
            return
        
        if not price.strip():
            QMessageBox.warning(dialog, 'Ошибка', 'Введите цену основы')
            return
        
        try:
            price_value = float(price)
            
            if self.current_product_id:
                query = """
                UPDATE products 
                SET product_name = ?, base_price = ?, category_id = ?
                WHERE product_id = ?
                """
                params = (name, price_value, category_id, self.current_product_id)
            else:
                query = """
                INSERT INTO products (product_name, base_price, category_id)
                VALUES (?, ?, ?)
                """
                params = (name, price_value, category_id)
            
            self.db.execute_query(query, params)
            dialog.accept()
            self.load_data()
            
        except Exception as e:
            QMessageBox.critical(dialog, 'Ошибка', f'Ошибка сохранения: {str(e)}')
    
    def delete_product(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, 'Предупреждение', 'Выберите изделие')
            return
        
        product_id = int(self.table.item(selected, 0).text())
        product_name = self.table.item(selected, 1).text()
        
        # Проверяем, используется ли изделие
        query = "SELECT COUNT(*) as count FROM orders WHERE product_id = ?"
        result = self.db.fetch_one(query, (product_id,))
        
        if result['count'] > 0:
            QMessageBox.critical(
                self, 'Ошибка',
                f'Невозможно удалить изделие "{product_name}", '
                f'так как оно используется в {result["count"]} заказах.'
            )
            return
        
        reply = QMessageBox.question(
            self, 'Подтверждение',
            f'Удалить изделие "{product_name}"?',
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                query = "DELETE FROM products WHERE product_id = ?"
                self.db.execute_query(query, (product_id,))
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, 'Ошибка', f'Ошибка удаления: {str(e)}')