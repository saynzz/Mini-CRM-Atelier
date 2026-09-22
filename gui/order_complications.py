from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIntValidator
from database.db_connection import DatabaseConnection

class OrderComplicationsManager(QDialog):
    def __init__(self, parent=None, order_number=None):
        super().__init__(parent)
        self.db = DatabaseConnection()
        self.order_number = order_number
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        title = f'Усложнения заказа №{self.order_number}' if self.order_number else 'Управление усложнениями заказов'
        self.setWindowTitle(title)
        self.setMinimumSize(800, 500)
        
        layout = QVBoxLayout(self)
        
        # Панель инструментов
        toolbar = self.create_toolbar()
        layout.addLayout(toolbar)
        
        # Таблица усложнений заказа
        self.table = self.create_complications_table()
        layout.addWidget(self.table)
        
        # Статистика
        self.stats_label = QLabel('')
        layout.addWidget(self.stats_label)
        
        # Если не указан номер заказа, показываем фильтр
        if not self.order_number:
            filter_group = self.create_order_filter()
            layout.addWidget(filter_group)
    
    def create_toolbar(self):
        toolbar = QHBoxLayout()
        
        if self.order_number:
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
        
        if self.order_number:
            # Кнопка расчета стоимости
            calc_btn = QPushButton('Расчет стоимости')
            calc_btn.clicked.connect(self.calculate_total_cost)
            toolbar.addWidget(calc_btn)
        
        toolbar.addStretch()
        return toolbar
    
    def create_order_filter(self):
        group = QGroupBox('Фильтр по заказу')
        layout = QHBoxLayout()
        
        layout.addWidget(QLabel('Номер заказа:'))
        
        self.order_filter = QComboBox()
        self.order_filter.addItem('-- Все заказы --', None)
        
        # Загружаем заказы с усложнениями
        orders_query = """
        SELECT DISTINCT o.order_number, o.customer_name, o.order_date
        FROM orders o
        JOIN order_complications oc ON o.order_number = oc.order_number
        ORDER BY o.order_date DESC
        LIMIT 50
        """
        
        orders = self.db.fetch_all(orders_query)
        for order in orders:
            self.order_filter.addItem(
                f"№{order['order_number']} - {order['customer_name']} ({order['order_date']})",
                order['order_number']
            )
        
        self.order_filter.currentIndexChanged.connect(self.load_data)
        layout.addWidget(self.order_filter)
        
        group.setLayout(layout)
        return group
    
    def create_complications_table(self):
        table = QTableWidget()
        
        if self.order_number:
            table.setColumnCount(5)
            headers = ['ID', 'Усложнение', 'Цена за элемент', 'Количество', 'Сумма']
        else:
            table.setColumnCount(7)
            headers = ['Заказ', 'Клиент', 'Дата', 'Усложнение', 'Цена', 'Количество', 'Сумма']
        
        table.setHorizontalHeaderLabels(headers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.doubleClicked.connect(self.edit_complication)
        
        return table
    
    def load_data(self):
        try:
            if self.order_number:
                # Загрузка для конкретного заказа
                query = """
                SELECT oc.*, c.complication_name, c.price_per_element,
                       (c.price_per_element * oc.element_count) as total_amount
                FROM order_complications oc
                JOIN complications c ON oc.complication_id = c.complication_id
                WHERE oc.order_number = ?
                ORDER BY c.complication_name
                """
                results = self.db.fetch_all(query, (self.order_number,))
            else:
                # Загрузка для всех заказов или фильтрованных
                order_filter = self.order_filter.currentData() if hasattr(self, 'order_filter') else None
                
                if order_filter:
                    query = """
                    SELECT oc.*, c.complication_name, c.price_per_element,
                           (c.price_per_element * oc.element_count) as total_amount,
                           o.customer_name, o.order_date
                    FROM order_complications oc
                    JOIN complications c ON oc.complication_id = c.complication_id
                    JOIN orders o ON oc.order_number = o.order_number
                    WHERE oc.order_number = ?
                    ORDER BY o.order_date DESC, c.complication_name
                    """
                    results = self.db.fetch_all(query, (order_filter,))
                else:
                    query = """
                    SELECT oc.*, c.complication_name, c.price_per_element,
                           (c.price_per_element * oc.element_count) as total_amount,
                           o.customer_name, o.order_date
                    FROM order_complications oc
                    JOIN complications c ON oc.complication_id = c.complication_id
                    JOIN orders o ON oc.order_number = o.order_number
                    ORDER BY o.order_date DESC, c.complication_name
                    LIMIT 100
                    """
                    results = self.db.fetch_all(query)
            
            self.display_complications(results)
            
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Ошибка загрузки: {str(e)}')
    
    def display_complications(self, results):
        if self.order_number:
            self.table.setColumnCount(5)
            self.table.setRowCount(len(results))
            
            total_amount = 0
            total_elements = 0
            
            for i, row in enumerate(results):
                # Внутренний ID связи (не показываем)
                self.table.setItem(i, 0, QTableWidgetItem(str(row['order_number'])))
                self.table.setItem(i, 1, QTableWidgetItem(row['complication_name']))
                self.table.setItem(i, 2, QTableWidgetItem(f"{row['price_per_element']:,.2f}"))
                self.table.setItem(i, 3, QTableWidgetItem(str(row['element_count'])))
                self.table.setItem(i, 4, QTableWidgetItem(f"{row['total_amount']:,.2f}"))
                
                total_amount += row['total_amount']
                total_elements += row['element_count']
            
            self.stats_label.setText(
                f'Усложнений: {len(results)} | '
                f'Элементов: {total_elements} | '
                f'Общая стоимость: {total_amount:,.2f} руб'
            )
            
        else:
            self.table.setColumnCount(7)
            self.table.setRowCount(len(results))
            
            for i, row in enumerate(results):
                self.table.setItem(i, 0, QTableWidgetItem(str(row['order_number'])))
                self.table.setItem(i, 1, QTableWidgetItem(row['customer_name']))
                self.table.setItem(i, 2, QTableWidgetItem(row['order_date']))
                self.table.setItem(i, 3, QTableWidgetItem(row['complication_name']))
                self.table.setItem(i, 4, QTableWidgetItem(f"{row['price_per_element']:,.2f}"))
                self.table.setItem(i, 5, QTableWidgetItem(str(row['element_count'])))
                self.table.setItem(i, 6, QTableWidgetItem(f"{row['total_amount']:,.2f}"))
            
            total_amount = sum(row['total_amount'] for row in results)
            self.stats_label.setText(f'Записей: {len(results)} | Общая стоимость: {total_amount:,.2f} руб')
        
        self.table.resizeColumnsToContents()
    
    def add_complication(self):
        if not self.order_number:
            QMessageBox.warning(self, 'Ошибка', 'Не указан номер заказа')
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f'Добавить усложнение к заказу №{self.order_number}')
        
        layout = QFormLayout(dialog)
        
        # Выбор усложнения
        complication_combo = QComboBox()
        complications = self.db.fetch_all("SELECT * FROM complications ORDER BY complication_name")
        
        # Получаем уже добавленные усложнения
        existing_query = """
        SELECT complication_id 
        FROM order_complications 
        WHERE order_number = ?
        """
        existing = self.db.fetch_all(existing_query, (self.order_number,))
        existing_ids = [str(item['complication_id']) for item in existing]
        
        for comp in complications:
            if str(comp['complication_id']) not in existing_ids:
                complication_combo.addItem(
                    f"{comp['complication_name']} ({comp['price_per_element']:,.0f} руб/эл.)",
                    comp['complication_id']
                )
        
        if complication_combo.count() == 0:
            QMessageBox.information(self, 'Информация', 'Все доступные усложнения уже добавлены к заказу.')
            return
        
        # Количество элементов
        count_edit = QLineEdit('1')
        count_edit.setValidator(QIntValidator(1, 1000))
        
        layout.addRow('Усложнение:', complication_combo)
        layout.addRow('Количество элементов:', count_edit)
        
        # Кнопки
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(lambda: self.save_new_complication(
            dialog, complication_combo.currentData(), count_edit.text()
        ))
        btn_box.rejected.connect(dialog.reject)
        
        layout.addRow(btn_box)
        dialog.exec_()
    
    def save_new_complication(self, dialog, complication_id, count):
        if not count.strip():
            QMessageBox.warning(dialog, 'Ошибка', 'Введите количество элементов')
            return
        
        try:
            # Проверяем, нет ли уже такого усложнения
            check_query = """
            SELECT COUNT(*) as count 
            FROM order_complications 
            WHERE order_number = ? AND complication_id = ?
            """
            check_result = self.db.fetch_one(check_query, (self.order_number, complication_id))
            
            if check_result['count'] > 0:
                QMessageBox.warning(dialog, 'Ошибка', 'Это усложнение уже добавлено к заказу')
                return
            
            # Добавляем усложнение
            insert_query = """
            INSERT INTO order_complications (order_number, complication_id, element_count)
            VALUES (?, ?, ?)
            """
            self.db.execute_query(insert_query, (self.order_number, complication_id, int(count)))
            
            dialog.accept()
            self.load_data()
            QMessageBox.information(self, 'Успех', 'Усложнение успешно добавлено')
            
        except Exception as e:
            QMessageBox.critical(dialog, 'Ошибка', f'Ошибка сохранения: {str(e)}')
    
    def edit_complication(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, 'Предупреждение', 'Выберите усложнение для редактирования')
            return
        
        if self.order_number:
            # Для конкретного заказа
            complication_name = self.table.item(selected, 1).text()
            current_count = int(self.table.item(selected, 3).text())
            
            # Получаем ID усложнения из базы
            comp_query = """
            SELECT oc.complication_id 
            FROM order_complications oc
            JOIN complications c ON oc.complication_id = c.complication_id
            WHERE oc.order_number = ? AND c.complication_name = ?
            """
            comp_result = self.db.fetch_one(comp_query, (self.order_number, complication_name))
            
            if not comp_result:
                QMessageBox.warning(self, 'Ошибка', 'Усложнение не найдено')
                return
            
            complication_id = comp_result['complication_id']
            
        else:
            # Для общего просмотра
            order_number = int(self.table.item(selected, 0).text())
            complication_name = self.table.item(selected, 3).text()
            
            # Получаем ID усложнения
            comp_query = """
            SELECT oc.complication_id 
            FROM order_complications oc
            JOIN complications c ON oc.complication_id = c.complication_id
            WHERE oc.order_number = ? AND c.complication_name = ?
            """
            comp_result = self.db.fetch_one(comp_query, (order_number, complication_name))
            
            if not comp_result:
                QMessageBox.warning(self, 'Ошибка', 'Усложнение не найдено')
                return
            
            complication_id = comp_result['complication_id']
            current_count_item = self.table.item(selected, 5)
            current_count = int(current_count_item.text()) if current_count_item else 1
        
        self.show_edit_dialog(complication_id, current_count)
    
    def show_edit_dialog(self, complication_id, current_count):
        dialog = QDialog(self)
        dialog.setWindowTitle('Редактирование усложнения')
        
        layout = QFormLayout(dialog)
        
        # Получаем информацию об усложнении
        comp_query = "SELECT * FROM complications WHERE complication_id = ?"
        comp_data = self.db.fetch_one(comp_query, (complication_id,))
        
        if not comp_data:
            QMessageBox.warning(self, 'Ошибка', 'Усложнение не найдено')
            return
        
        # Показываем информацию
        info_label = QLabel(f"Усложнение: {comp_data['complication_name']}\nЦена за элемент: {comp_data['price_per_element']:,.2f} руб")
        layout.addRow(info_label)
        
        # Поле для редактирования количества
        count_edit = QLineEdit(str(current_count))
        count_edit.setValidator(QIntValidator(1, 1000))
        layout.addRow('Количество элементов:', count_edit)
        
        # Кнопки
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(lambda: self.update_complication(
            dialog, complication_id, count_edit.text()
        ))
        btn_box.rejected.connect(dialog.reject)
        
        layout.addRow(btn_box)
        dialog.exec_()
    
    def update_complication(self, dialog, complication_id, new_count):
        if not new_count.strip():
            QMessageBox.warning(dialog, 'Ошибка', 'Введите количество элементов')
            return
        
        try:
            # Находим запись для обновления
            if self.order_number:
                # Для конкретного заказа
                update_query = """
                UPDATE order_complications 
                SET element_count = ?
                WHERE order_number = ? AND complication_id = ?
                """
                params = (int(new_count), self.order_number, complication_id)
            else:
                # Нужно определить order_number из выбранной строки
                selected = self.table.currentRow()
                if selected < 0:
                    QMessageBox.warning(dialog, 'Ошибка', 'Выберите запись для обновления')
                    return
                
                order_number = int(self.table.item(selected, 0).text())
                update_query = """
                UPDATE order_complications 
                SET element_count = ?
                WHERE order_number = ? AND complication_id = ?
                """
                params = (int(new_count), order_number, complication_id)
            
            self.db.execute_query(update_query, params)
            
            dialog.accept()
            self.load_data()
            QMessageBox.information(self, 'Успех', 'Усложнение успешно обновлено')
            
        except Exception as e:
            QMessageBox.critical(dialog, 'Ошибка', f'Ошибка обновления: {str(e)}')
    
    def delete_complication(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, 'Предупреждение', 'Выберите усложнение для удаления')
            return
        
        if self.order_number:
            # Для конкретного заказа
            complication_name = self.table.item(selected, 1).text()
            element_count = self.table.item(selected, 3).text()
            total_amount = self.table.item(selected, 4).text()
            
            # Получаем ID усложнения
            comp_query = """
            SELECT oc.complication_id 
            FROM order_complications oc
            JOIN complications c ON oc.complication_id = c.complication_id
            WHERE oc.order_number = ? AND c.complication_name = ?
            """
            comp_result = self.db.fetch_one(comp_query, (self.order_number, complication_name))
            
            if not comp_result:
                QMessageBox.warning(self, 'Ошибка', 'Усложнение не найдено')
                return
            
            complication_id = comp_result['complication_id']
            order_number = self.order_number
            
        else:
            # Для общего просмотра
            order_number = int(self.table.item(selected, 0).text())
            complication_name = self.table.item(selected, 3).text()
            element_count = self.table.item(selected, 5).text()
            total_amount = self.table.item(selected, 6).text()
            
            # Получаем ID усложнения
            comp_query = """
            SELECT oc.complication_id 
            FROM order_complications oc
            JOIN complications c ON oc.complication_id = c.complication_id
            WHERE oc.order_number = ? AND c.complication_name = ?
            """
            comp_result = self.db.fetch_one(comp_query, (order_number, complication_name))
            
            if not comp_result:
                QMessageBox.warning(self, 'Ошибка', 'Усложнение не найдено')
                return
            
            complication_id = comp_result['complication_id']
        
        # Подтверждение удаления
        reply = QMessageBox.question(
            self, 'Подтверждение',
            f'Удалить усложнение "{complication_name}" из заказа №{order_number}?\n'
            f'Количество: {element_count} элементов\n'
            f'Стоимость: {total_amount} руб',
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                delete_query = """
                DELETE FROM order_complications 
                WHERE order_number = ? AND complication_id = ?
                """
                self.db.execute_query(delete_query, (order_number, complication_id))
                
                self.load_data()
                QMessageBox.information(self, 'Успех', 'Усложнение успешно удалено')
                
            except Exception as e:
                QMessageBox.critical(self, 'Ошибка', f'Ошибка удаления: {str(e)}')
    
    def calculate_total_cost(self):
        if not self.order_number:
            return
        
        try:
            query = """
            SELECT 
                SUM(c.price_per_element * oc.element_count) as total_cost,
                SUM(oc.element_count) as total_elements,
                COUNT(oc.complication_id) as complications_count
            FROM order_complications oc
            JOIN complications c ON oc.complication_id = c.complication_id
            WHERE oc.order_number = ?
            """
            
            result = self.db.fetch_one(query, (self.order_number,))
            
            if result and result['total_cost']:
                msg = f"Заказ №{self.order_number}\n\n"
                msg += f"Количество усложнений: {result['complications_count']}\n"
                msg += f"Всего элементов: {result['total_elements']}\n"
                msg += f"Общая стоимость усложнений: {result['total_cost']:,.2f} руб"
                
                QMessageBox.information(self, 'Расчет стоимости', msg)
            else:
                QMessageBox.information(self, 'Информация', 'Нет данных об усложнениях для этого заказа')
                
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Ошибка расчета: {str(e)}')