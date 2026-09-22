from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QDoubleValidator, QIntValidator
from database.db_connection import DatabaseConnection
from datetime import datetime, timedelta
import sys

class OrdersManager(QDialog):
    def __init__(self, parent=None, view_mode=False):
        super().__init__(parent)
        self.db = DatabaseConnection()
        self.current_order_number = None
        self.view_mode = view_mode
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        title = 'Просмотр заказов' if self.view_mode else 'Управление заказами'
        self.setWindowTitle(title)
        self.setMinimumSize(1200, 600)
        
        layout = QVBoxLayout(self)
        
        # Панель инструментов
        toolbar = self.create_toolbar()
        layout.addLayout(toolbar)
        
        # Таблица заказов
        self.table = self.create_orders_table()
        layout.addWidget(self.table)
        
        # Статистика
        self.stats_label = QLabel('')
        layout.addWidget(self.stats_label)
    
    def create_toolbar(self):
        toolbar = QHBoxLayout()
        
        if not self.view_mode:
            new_order_btn = QPushButton('Новый заказ')
            new_order_btn.clicked.connect(self.create_new_order)
            toolbar.addWidget(new_order_btn)
        
        edit_btn = QPushButton('Редактировать' if self.view_mode else 'Просмотреть')
        edit_btn.clicked.connect(self.edit_order)
        toolbar.addWidget(edit_btn)
        
        if not self.view_mode:
            delete_btn = QPushButton('Удалить')
            delete_btn.clicked.connect(self.delete_order)
            toolbar.addWidget(delete_btn)
        
        refresh_btn = QPushButton('Обновить')
        refresh_btn.clicked.connect(self.load_data)
        toolbar.addWidget(refresh_btn)
        
        # Фильтры
        toolbar.addWidget(QLabel('Статус:'))
        self.status_filter = QComboBox()
        self.status_filter.addItem('Все', 'all')
        self.status_filter.addItem('В работе', 'active')
        self.status_filter.addItem('Просрочен', 'overdue')
        self.status_filter.addItem('Завершен', 'completed')
        self.status_filter.currentIndexChanged.connect(self.load_data)
        toolbar.addWidget(self.status_filter)
        
        toolbar.addWidget(QLabel('Период:'))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_from.setDisplayFormat('dd.MM.yyyy')
        toolbar.addWidget(self.date_from)
        
        toolbar.addWidget(QLabel('-'))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setDisplayFormat('dd.MM.yyyy')
        toolbar.addWidget(self.date_to)
        
        filter_btn = QPushButton('Фильтр')
        filter_btn.clicked.connect(self.load_data)
        toolbar.addWidget(filter_btn)
        
        toolbar.addStretch()
        return toolbar
    
    def create_orders_table(self):
        table = QTableWidget()
        table.setColumnCount(10)
        headers = [
            '№ накладной', 'Дата заказа', 'Закройщик', 'Изделие',
            'Заказчик', 'Телефон', 'Дата исполнения', 'Статус', 
            'Стоимость', 'Оплата'
        ]
        table.setHorizontalHeaderLabels(headers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.doubleClicked.connect(self.edit_order)
        return table
    
    def load_data(self):
        try:
            date_from = self.date_from.date().toString('yyyy-MM-dd')
            date_to = self.date_to.date().toString('yyyy-MM-dd')
            status = self.status_filter.currentData()
            
            # Базовый запрос
            query = """
            SELECT 
                o.order_number,
                o.order_date,
                c.full_name as cutter_name,
                p.product_name,
                o.customer_name,
                o.customer_phone,
                o.completion_date,
                o.urgency_percent,
                oc.total_amount,
                CASE 
                    WHEN cr.order_number IS NOT NULL THEN 'Оплачен'
                    WHEN o.completion_date < date('now') THEN 'Просрочен'
                    ELSE 'В работе'
                END as status,
                CASE WHEN cr.order_number IS NOT NULL THEN 'Да' ELSE 'Нет' END as paid
            FROM orders o
            JOIN cutters c ON o.cutter_id = c.cutter_id
            JOIN products p ON o.product_id = p.product_id
            LEFT JOIN order_costs oc ON o.order_number = oc.order_number
            LEFT JOIN cash_register cr ON o.order_number = cr.order_number
            WHERE o.order_date BETWEEN ? AND ?
            """
            
            params = [date_from, date_to]
            
            # Фильтрация по статусу
            if status == 'active':
                query += " AND cr.order_number IS NULL AND o.completion_date >= date('now')"
            elif status == 'overdue':
                query += " AND cr.order_number IS NULL AND o.completion_date < date('now')"
            elif status == 'completed':
                query += " AND cr.order_number IS NOT NULL"
            
            query += " ORDER BY o.order_date DESC, o.order_number DESC"
            
            results = self.db.fetch_all(query, params)
            self.display_orders(results)
            
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Ошибка загрузки: {str(e)}')
            print(f"Ошибка: {e}")
    
    def display_orders(self, results):
        self.table.setRowCount(len(results))
        
        total_amount = 0
        active_orders = 0
        overdue_orders = 0
        completed_orders = 0
        
        for i, row in enumerate(results):
            self.table.setItem(i, 0, QTableWidgetItem(str(row['order_number'])))
            self.table.setItem(i, 1, QTableWidgetItem(row['order_date']))
            self.table.setItem(i, 2, QTableWidgetItem(row['cutter_name']))
            self.table.setItem(i, 3, QTableWidgetItem(row['product_name']))
            self.table.setItem(i, 4, QTableWidgetItem(row['customer_name']))
            self.table.setItem(i, 5, QTableWidgetItem(row['customer_phone'] or ''))
            self.table.setItem(i, 6, QTableWidgetItem(row['completion_date']))
            
            # Статус с цветовой индикацией
            status_item = QTableWidgetItem(row['status'])
            if row['status'] == 'Просрочен':
                status_item.setBackground(Qt.red)
                status_item.setForeground(Qt.white)
                overdue_orders += 1
            elif row['status'] == 'В работе':
                status_item.setBackground(Qt.yellow)
                active_orders += 1
            else:
                status_item.setBackground(Qt.green)
                status_item.setForeground(Qt.white)
                completed_orders += 1
            self.table.setItem(i, 7, status_item)
            
            # Стоимость
            cost_item = QTableWidgetItem(f"{row['total_amount']:,.2f}" if row['total_amount'] else '0.00')
            self.table.setItem(i, 8, cost_item)
            
            # Оплата
            payment_item = QTableWidgetItem(row['paid'])
            if row['paid'] == 'Да':
                payment_item.setBackground(Qt.green)
                payment_item.setForeground(Qt.white)
            self.table.setItem(i, 9, payment_item)
            
            total_amount += row['total_amount'] or 0
        
        self.table.resizeColumnsToContents()
        
        # Обновляем статистику
        self.stats_label.setText(
            f'Заказов: {len(results)} | '
            f'В работе: {active_orders} | '
            f'Просрочено: {overdue_orders} | '
            f'Завершено: {completed_orders} | '
            f'Общая стоимость: {total_amount:,.2f} руб'
        )
    
    def create_new_order(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Новый заказ')
        dialog.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(dialog)
        
        # Основная информация
        info_group = self.create_order_info_group()
        layout.addWidget(info_group)
        
        # Усложнения
        complications_group = self.create_complications_group()
        layout.addWidget(complications_group)
        
        # Ткани
        fabrics_group = self.create_fabrics_group()
        layout.addWidget(fabrics_group)
        
        # Расчет стоимости
        cost_group = self.create_cost_calculation_group()
        layout.addWidget(cost_group)
        
        # Кнопки сохранения/отмены
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(lambda: self.save_new_order(dialog))
        btn_box.rejected.connect(dialog.reject)
        layout.addWidget(btn_box)
        
        dialog.exec_()
    
    def create_order_info_group(self):
        group = QGroupBox('Основная информация')
        layout = QFormLayout()
        
        self.order_date_edit = QDateEdit()
        self.order_date_edit.setCalendarPopup(True)
        self.order_date_edit.setDate(QDate.currentDate())
        self.order_date_edit.setDisplayFormat('dd.MM.yyyy')
        
        self.cutter_combo = QComboBox()
        cutters = self.db.fetch_all("SELECT * FROM cutters ORDER BY full_name")
        for cutter in cutters:
            self.cutter_combo.addItem(cutter['full_name'], cutter['cutter_id'])
        
        self.product_combo = QComboBox()
        products = self.db.fetch_all("SELECT * FROM products ORDER BY product_name")
        for product in products:
            self.product_combo.addItem(
                f"{product['product_name']} ({product['base_price']:,.0f} руб)",
                product['product_id']
            )
        
        self.customer_name_edit = QLineEdit()
        self.customer_address_edit = QLineEdit()
        self.customer_phone_edit = QLineEdit()
        
        self.completion_date_edit = QDateEdit()
        self.completion_date_edit.setCalendarPopup(True)
        self.completion_date_edit.setDate(QDate.currentDate().addDays(7))
        self.completion_date_edit.setDisplayFormat('dd.MM.yyyy')
        
        self.urgency_percent_edit = QLineEdit('0')
        self.urgency_percent_edit.setValidator(QDoubleValidator(0, 100, 2))
        self.urgency_percent_edit.setPlaceholderText('Процент надбавки за срочность')
        
        layout.addRow('Дата заказа:', self.order_date_edit)
        layout.addRow('Закройщик:', self.cutter_combo)
        layout.addRow('Изделие:', self.product_combo)
        layout.addRow('ФИО заказчика:', self.customer_name_edit)
        layout.addRow('Адрес проживания:', self.customer_address_edit)
        layout.addRow('Телефон:', self.customer_phone_edit)
        layout.addRow('Дата исполнения:', self.completion_date_edit)
        layout.addRow('% срочности:', self.urgency_percent_edit)
        
        group.setLayout(layout)
        return group
    
    def create_complications_group(self):
        group = QGroupBox('Усложнения')
        layout = QVBoxLayout()
        
        self.complications_table = QTableWidget()
        self.complications_table.setColumnCount(3)
        self.complications_table.setHorizontalHeaderLabels(['Усложнение', 'Цена за элемент', 'Количество'])
        self.complications_table.setRowCount(0)
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton('Добавить усложнение')
        add_btn.clicked.connect(self.add_complication)
        remove_btn = QPushButton('Удалить выбранное')
        remove_btn.clicked.connect(self.remove_selected_complication)
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)
        btn_layout.addStretch()
        
        layout.addWidget(self.complications_table)
        layout.addLayout(btn_layout)
        group.setLayout(layout)
        return group
    
    def create_fabrics_group(self):
        group = QGroupBox('Ткани')
        layout = QVBoxLayout()
        
        self.fabrics_table = QTableWidget()
        self.fabrics_table.setColumnCount(4)
        self.fabrics_table.setHorizontalHeaderLabels(['Ткань', 'Цена', 'Доступно', 'Количество'])
        self.fabrics_table.setRowCount(0)
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton('Добавить ткань')
        add_btn.clicked.connect(self.add_fabric)
        remove_btn = QPushButton('Удалить выбранное')
        remove_btn.clicked.connect(self.remove_selected_fabric)
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)
        btn_layout.addStretch()
        
        layout.addWidget(self.fabrics_table)
        layout.addLayout(btn_layout)
        group.setLayout(layout)
        return group
    
    def create_cost_calculation_group(self):
        group = QGroupBox('Расчет стоимости')
        layout = QFormLayout()
        
        self.base_cost_label = QLabel('0.00')
        self.complications_cost_label = QLabel('0.00')
        self.fabrics_cost_label = QLabel('0.00')
        self.urgency_cost_label = QLabel('0.00')
        self.total_cost_label = QLabel('0.00')
        self.total_cost_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #d32f2f;")
        
        layout.addRow('Основа изделия:', self.base_cost_label)
        layout.addRow('Усложнения:', self.complications_cost_label)
        layout.addRow('Ткани:', self.fabrics_cost_label)
        layout.addRow('Срочность:', self.urgency_cost_label)
        layout.addRow('ИТОГО:', self.total_cost_label)
        
        # Подключаем обновление стоимости
        self.product_combo.currentIndexChanged.connect(self.update_cost_calculation)
        self.urgency_percent_edit.textChanged.connect(self.update_cost_calculation)
        
        group.setLayout(layout)
        return group
    
    def add_complication(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Добавить усложнение')
        
        layout = QFormLayout(dialog)
        
        complication_combo = QComboBox()
        complications = self.db.fetch_all("SELECT * FROM complications ORDER BY complication_name")
        for comp in complications:
            complication_combo.addItem(
                f"{comp['complication_name']} ({comp['price_per_element']:,.0f} руб/эл.)",
                comp['complication_id']
            )
        
        count_edit = QLineEdit('1')
        count_edit.setValidator(QIntValidator(1, 100))
        
        layout.addRow('Усложнение:', complication_combo)
        layout.addRow('Количество элементов:', count_edit)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(lambda: self.save_complication_to_table(
            dialog, complication_combo, count_edit
        ))
        btn_box.rejected.connect(dialog.reject)
        
        layout.addRow(btn_box)
        dialog.exec_()
    
    def save_complication_to_table(self, dialog, complication_combo, count_edit):
        complication_text = complication_combo.currentText()
        complication_id = complication_combo.currentData()
        count = count_edit.text()
        
        if not count.strip():
            QMessageBox.warning(dialog, 'Ошибка', 'Введите количество элементов')
            return
        
        # Получаем цену за элемент
        price_query = "SELECT price_per_element FROM complications WHERE complication_id = ?"
        price_result = self.db.fetch_one(price_query, (complication_id,))
        
        if not price_result:
            QMessageBox.critical(dialog, 'Ошибка', 'Усложнение не найдено')
            return
        
        row = self.complications_table.rowCount()
        self.complications_table.insertRow(row)
        
        self.complications_table.setItem(row, 0, QTableWidgetItem(complication_text.split(' (')[0]))
        self.complications_table.setItem(row, 1, QTableWidgetItem(str(price_result['price_per_element'])))
        self.complications_table.setItem(row, 2, QTableWidgetItem(count))
        
        # Сохраняем ID в скрытых данных
        self.complications_table.item(row, 0).setData(Qt.UserRole, complication_id)
        
        dialog.accept()
        self.update_cost_calculation()
    
    def remove_selected_complication(self):
        selected = self.complications_table.currentRow()
        if selected >= 0:
            self.complications_table.removeRow(selected)
            self.update_cost_calculation()
    
    def add_fabric(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Добавить ткань')
        
        layout = QFormLayout(dialog)
        
        fabric_combo = QComboBox()
        fabrics = self.db.fetch_all("""
            SELECT f.*, ft.type_name 
            FROM fabrics f 
            JOIN fabric_types ft ON f.type_id = ft.type_id
            WHERE f.quantity > 0
            ORDER BY f.fabric_name
        """)
        
        for fabric in fabrics:
            fabric_combo.addItem(
                f"{fabric['fabric_name']} ({fabric['price']:,.0f} руб/{fabric['unit']})",
                fabric['fabric_article']
            )
        
        quantity_edit = QLineEdit()
        quantity_edit.setValidator(QDoubleValidator(0.01, 1000, 2))
        
        unit_label = fabrics[0]['unit'] if fabrics else "ед."
        layout.addRow('Ткань:', fabric_combo)
        layout.addRow(f'Количество ({unit_label}):', quantity_edit)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(lambda: self.save_fabric_to_table(
            dialog, fabric_combo, quantity_edit
        ))
        btn_box.rejected.connect(dialog.reject)
        
        layout.addRow(btn_box)
        dialog.exec_()
    
    def save_fabric_to_table(self, dialog, fabric_combo, quantity_edit):
        fabric_text = fabric_combo.currentText()
        fabric_article = fabric_combo.currentData()
        quantity = quantity_edit.text()
        
        if not quantity.strip():
            QMessageBox.warning(dialog, 'Ошибка', 'Введите количество ткани')
            return
        
        # Получаем информацию о ткани
        fabric_query = """
        SELECT f.*, ft.type_name 
        FROM fabrics f 
        JOIN fabric_types ft ON f.type_id = ft.type_id
        WHERE f.fabric_article = ?
        """
        fabric_result = self.db.fetch_one(fabric_query, (fabric_article,))
        
        if not fabric_result:
            QMessageBox.critical(dialog, 'Ошибка', 'Ткань не найдена')
            return
        
        # Проверяем остаток
        if float(quantity) > fabric_result['quantity']:
            QMessageBox.warning(
                dialog, 'Ошибка',
                f'Недостаточно ткани на складе. Доступно: {fabric_result["quantity"]} {fabric_result["unit"]}'
            )
            return
        
        row = self.fabrics_table.rowCount()
        self.fabrics_table.insertRow(row)
        
        self.fabrics_table.setItem(row, 0, QTableWidgetItem(fabric_text.split(' (')[0]))
        self.fabrics_table.setItem(row, 1, QTableWidgetItem(str(fabric_result['price'])))
        self.fabrics_table.setItem(row, 2, QTableWidgetItem(f"{fabric_result['quantity']:.2f}"))
        self.fabrics_table.setItem(row, 3, QTableWidgetItem(quantity))
        
        # Сохраняем артикул в скрытых данных
        self.fabrics_table.item(row, 0).setData(Qt.UserRole, fabric_article)
        
        dialog.accept()
        self.update_cost_calculation()
    
    def remove_selected_fabric(self):
        selected = self.fabrics_table.currentRow()
        if selected >= 0:
            self.fabrics_table.removeRow(selected)
            self.update_cost_calculation()
    
    def update_cost_calculation(self):
        try:
            product_id = self.product_combo.currentData()
            if not product_id:
                return
            
            # Получаем цену основы
            product_query = "SELECT base_price FROM products WHERE product_id = ?"
            product_result = self.db.fetch_one(product_query, (product_id,))
            
            if not product_result:
                return
            
            base_price = product_result['base_price']
            self.base_cost_label.setText(f"{base_price:,.2f}")
            
            # Считаем стоимость усложнений
            complications_cost = 0
            for row in range(self.complications_table.rowCount()):
                price_item = self.complications_table.item(row, 1)
                count_item = self.complications_table.item(row, 2)
                if price_item and count_item:
                    complications_cost += float(price_item.text()) * int(count_item.text())
            self.complications_cost_label.setText(f"{complications_cost:,.2f}")
            
            # Считаем стоимость тканей
            fabrics_cost = 0
            for row in range(self.fabrics_table.rowCount()):
                price_item = self.fabrics_table.item(row, 1)
                quantity_item = self.fabrics_table.item(row, 3)
                if price_item and quantity_item:
                    fabrics_cost += float(price_item.text()) * float(quantity_item.text())
            self.fabrics_cost_label.setText(f"{fabrics_cost:,.2f}")
            
            # Считаем надбавку за срочность
            urgency_percent = float(self.urgency_percent_edit.text()) if self.urgency_percent_edit.text().strip() else 0
            urgency_cost = base_price * urgency_percent / 100
            self.urgency_cost_label.setText(f"{urgency_cost:,.2f}")
            
            # Итоговая стоимость
            total_cost = base_price + complications_cost + fabrics_cost + urgency_cost
            self.total_cost_label.setText(f"{total_cost:,.2f}")
            
        except Exception as e:
            print(f"Ошибка расчета стоимости: {e}")
    
    def save_new_order(self, dialog):
        # Валидация
        if not self.customer_name_edit.text().strip():
            QMessageBox.warning(dialog, 'Ошибка', 'Введите ФИО заказчика')
            return
        
        try:
            # Получаем данные из полей
            order_date = self.order_date_edit.date().toString('yyyy-MM-dd')
            cutter_id = self.cutter_combo.currentData()
            product_id = self.product_combo.currentData()
            customer_name = self.customer_name_edit.text()
            customer_address = self.customer_address_edit.text()
            customer_phone = self.customer_phone_edit.text()
            completion_date = self.completion_date_edit.date().toString('yyyy-MM-dd')
            urgency_percent = self.urgency_percent_edit.text()
            
            # Собираем данные усложнений
            complications_data = []
            for row in range(self.complications_table.rowCount()):
                complication_id = self.complications_table.item(row, 0).data(Qt.UserRole)
                count_item = self.complications_table.item(row, 2)
                if complication_id and count_item:
                    complications_data.append({
                        'complication_id': complication_id,
                        'count': int(count_item.text())
                    })
            
            # Собираем данные тканей
            fabrics_data = []
            for row in range(self.fabrics_table.rowCount()):
                fabric_article = self.fabrics_table.item(row, 0).data(Qt.UserRole)
                quantity_item = self.fabrics_table.item(row, 3)
                if fabric_article and quantity_item:
                    fabrics_data.append({
                        'fabric_article': fabric_article,
                        'quantity': float(quantity_item.text())
                    })
            
            # Сохраняем основной заказ
            order_query = """
            INSERT INTO orders (
                order_date, cutter_id, product_id, customer_name,
                customer_address, customer_phone, completion_date, urgency_percent
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            order_params = (
                order_date,
                cutter_id,
                product_id,
                customer_name,
                customer_address,
                customer_phone,
                completion_date,
                float(urgency_percent) if urgency_percent.strip() else 0
            )
            
            self.db.execute_query(order_query, order_params)
            
            # Получаем номер созданного заказа
            order_number = self.db.fetch_one("SELECT last_insert_rowid() as id")['id']
            
            # Сохраняем усложнения
            for comp_data in complications_data:
                comp_query = """
                INSERT INTO order_complications 
                (order_number, complication_id, element_count)
                VALUES (?, ?, ?)
                """
                self.db.execute_query(comp_query, 
                    (order_number, comp_data['complication_id'], comp_data['count']))
            
            # Сохраняем ткани и обновляем остатки
            for fabric_data in fabrics_data:
                # Добавляем ткань в заказ
                fabric_query = """
                INSERT INTO order_fabrics 
                (order_number, fabric_article, quantity)
                VALUES (?, ?, ?)
                """
                self.db.execute_query(fabric_query, 
                    (order_number, fabric_data['fabric_article'], fabric_data['quantity']))
                
                # Уменьшаем остаток на складе
                update_query = """
                UPDATE fabrics 
                SET quantity = quantity - ?
                WHERE fabric_article = ?
                """
                self.db.execute_query(update_query, 
                    (fabric_data['quantity'], fabric_data['fabric_article']))
            
            dialog.accept()
            self.load_data()
            QMessageBox.information(self, 'Успех', f'Заказ №{order_number} успешно создан!')
            
        except Exception as e:
            QMessageBox.critical(dialog, 'Ошибка', f'Ошибка сохранения заказа: {str(e)}')
            print(f"Детали ошибки: {e}")
    
    def edit_order(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, 'Предупреждение', 'Выберите заказ')
            return
        
        order_number = int(self.table.item(selected, 0).text())
        self.view_order_details(order_number)
    
    def view_order_details(self, order_number):
        try:
            # Получаем основную информацию
            query = """
            SELECT o.*, c.full_name as cutter_name, p.product_name, p.base_price,
                   oc.base_amount, oc.complications_amount, oc.fabric_amount, 
                   oc.urgency_amount, oc.total_amount,
                   CASE 
                       WHEN cr.order_number IS NOT NULL THEN 'Оплачен'
                       WHEN o.completion_date < date('now') THEN 'Просрочен'
                       ELSE 'В работе'
                   END as status
            FROM orders o
            JOIN cutters c ON o.cutter_id = c.cutter_id
            JOIN products p ON o.product_id = p.product_id
            LEFT JOIN order_costs oc ON o.order_number = oc.order_number
            LEFT JOIN cash_register cr ON o.order_number = cr.order_number
            WHERE o.order_number = ?
            """
            
            order_data = self.db.fetch_one(query, (order_number,))
            
            if not order_data:
                QMessageBox.warning(self, 'Ошибка', 'Заказ не найден')
                return
            
            # Получаем усложнения
            complications_query = """
            SELECT c.complication_name, c.price_per_element, oc.element_count,
                   (c.price_per_element * oc.element_count) as total
            FROM order_complications oc
            JOIN complications c ON oc.complication_id = c.complication_id
            WHERE oc.order_number = ?
            """
            complications = self.db.fetch_all(complications_query, (order_number,))
            
            # Получаем ткани
            fabrics_query = """
            SELECT f.fabric_name, f.unit, f.price, of.quantity,
                   (f.price * of.quantity) as total
            FROM order_fabrics of
            JOIN fabrics f ON of.fabric_article = f.fabric_article
            WHERE of.order_number = ?
            """
            fabrics = self.db.fetch_all(fabrics_query, (order_number,))
            
            # Создаем диалог с деталями
            dialog = QDialog(self)
            dialog.setWindowTitle(f'Детали заказа №{order_number}')
            dialog.setMinimumSize(800, 600)
            
            layout = QVBoxLayout(dialog)
            
            # Основная информация
            info_group = QGroupBox('Основная информация')
            info_layout = QFormLayout()
            
            info_layout.addRow('Номер накладной:', QLabel(str(order_data['order_number'])))
            info_layout.addRow('Дата заказа:', QLabel(order_data['order_date']))
            info_layout.addRow('Закройщик:', QLabel(order_data['cutter_name']))
            info_layout.addRow('Изделие:', QLabel(order_data['product_name']))
            info_layout.addRow('Заказчик:', QLabel(order_data['customer_name']))
            info_layout.addRow('Адрес:', QLabel(order_data['customer_address'] or 'Не указан'))
            info_layout.addRow('Телефон:', QLabel(order_data['customer_phone'] or 'Не указан'))
            info_layout.addRow('Дата исполнения:', QLabel(order_data['completion_date']))
            info_layout.addRow('% срочности:', QLabel(f"{order_data['urgency_percent']}%"))
            info_layout.addRow('Статус:', QLabel(order_data['status']))
            
            info_group.setLayout(info_layout)
            layout.addWidget(info_group)
            
            # Усложнения
            if complications:
                comp_group = QGroupBox('Усложнения')
                comp_layout = QVBoxLayout()
                
                comp_table = QTableWidget()
                comp_table.setColumnCount(4)
                comp_table.setHorizontalHeaderLabels(['Усложнение', 'Цена за элемент', 'Количество', 'Сумма'])
                comp_table.setRowCount(len(complications))
                comp_table.setEditTriggers(QTableWidget.NoEditTriggers)
                
                for i, comp in enumerate(complications):
                    comp_table.setItem(i, 0, QTableWidgetItem(comp['complication_name']))
                    comp_table.setItem(i, 1, QTableWidgetItem(f"{comp['price_per_element']:,.2f}"))
                    comp_table.setItem(i, 2, QTableWidgetItem(str(comp['element_count'])))
                    comp_table.setItem(i, 3, QTableWidgetItem(f"{comp['total']:,.2f}"))
                
                comp_table.resizeColumnsToContents()
                comp_layout.addWidget(comp_table)
                comp_group.setLayout(comp_layout)
                layout.addWidget(comp_group)
            
            # Ткани
            if fabrics:
                fabric_group = QGroupBox('Ткани')
                fabric_layout = QVBoxLayout()
                
                fabric_table = QTableWidget()
                fabric_table.setColumnCount(5)
                fabric_table.setHorizontalHeaderLabels(['Ткань', 'Ед.изм', 'Цена', 'Количество', 'Сумма'])
                fabric_table.setRowCount(len(fabrics))
                fabric_table.setEditTriggers(QTableWidget.NoEditTriggers)
                
                for i, fabric in enumerate(fabrics):
                    fabric_table.setItem(i, 0, QTableWidgetItem(fabric['fabric_name']))
                    fabric_table.setItem(i, 1, QTableWidgetItem(fabric['unit']))
                    fabric_table.setItem(i, 2, QTableWidgetItem(f"{fabric['price']:,.2f}"))
                    fabric_table.setItem(i, 3, QTableWidgetItem(f"{fabric['quantity']:.2f}"))
                    fabric_table.setItem(i, 4, QTableWidgetItem(f"{fabric['total']:,.2f}"))
                
                fabric_table.resizeColumnsToContents()
                fabric_layout.addWidget(fabric_table)
                fabric_group.setLayout(fabric_layout)
                layout.addWidget(fabric_group)
            
            # Стоимость
            cost_group = QGroupBox('Расчет стоимости')
            cost_layout = QFormLayout()
            
            cost_layout.addRow('Основа изделия:', QLabel(f"{order_data['base_amount']:,.2f} руб"))
            cost_layout.addRow('Усложнения:', QLabel(f"{order_data['complications_amount']:,.2f} руб"))
            cost_layout.addRow('Ткани:', QLabel(f"{order_data['fabric_amount']:,.2f} руб"))
            cost_layout.addRow('Срочность:', QLabel(f"{order_data['urgency_amount']:,.2f} руб"))
            
            total_label = QLabel(f"{order_data['total_amount']:,.2f} руб")
            total_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #d32f2f;")
            cost_layout.addRow('ИТОГО:', total_label)
            
            cost_group.setLayout(cost_layout)
            layout.addWidget(cost_group)
            
            # Кнопка закрытия
            close_btn = QPushButton('Закрыть')
            close_btn.clicked.connect(dialog.close)
            layout.addWidget(close_btn)
            
            dialog.exec_()
            
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Ошибка загрузки деталей: {str(e)}')
    
    def delete_order(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, 'Предупреждение', 'Выберите заказ')
            return
        
        order_number = int(self.table.item(selected, 0).text())
        customer_name = self.table.item(selected, 4).text()
        
        # Проверяем, оплачен ли заказ
        check_query = "SELECT COUNT(*) as count FROM cash_register WHERE order_number = ?"
        result = self.db.fetch_one(check_query, (order_number,))
        
        if result['count'] > 0:
            QMessageBox.critical(
                self, 'Ошибка',
                f'Невозможно удалить заказ №{order_number}, так как он уже оплачен.'
            )
            return
        
        reply = QMessageBox.question(
            self, 'Подтверждение',
            f'Удалить заказ №{order_number} для {customer_name}?\n'
            'Внимание: это действие нельзя отменить.',
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Получаем ткани заказа для восстановления остатков
                fabrics_query = """
                SELECT fabric_article, quantity 
                FROM order_fabrics 
                WHERE order_number = ?
                """
                fabrics = self.db.fetch_all(fabrics_query, (order_number,))
                
                # Восстанавливаем остатки тканей
                for fabric in fabrics:
                    restore_query = """
                    UPDATE fabrics 
                    SET quantity = quantity + ?
                    WHERE fabric_article = ?
                    """
                    self.db.execute_query(restore_query, 
                        (fabric['quantity'], fabric['fabric_article']))
                
                # Удаление заказа (каскадное удаление через foreign keys)
                query = "DELETE FROM orders WHERE order_number = ?"
                self.db.execute_query(query, (order_number,))
                
                self.load_data()
                QMessageBox.information(self, 'Успех', f'Заказ №{order_number} удален')
                
            except Exception as e:
                QMessageBox.critical(self, 'Ошибка', f'Ошибка удаления: {str(e)}')