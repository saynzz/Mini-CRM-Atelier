from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QDoubleValidator, QIntValidator
from database.db_connection import DatabaseConnection
from datetime import datetime, timedelta

class OrdersManager(QDialog):
    def __init__(self, parent=None, view_mode=False):
        super().__init__(parent)
        self.db = DatabaseConnection()
        self.current_order_number = None
        self.view_mode = view_mode  # Режим просмотра/редактирования
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        title = 'Просмотр заказов' if self.view_mode else 'Управление заказами'
        self.setWindowTitle(title)
        self.setMinimumSize(1200, 600)
        
        layout = QVBoxLayout(self)
        
        # Панель инструментов
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
        layout.addLayout(toolbar)
        
        # Таблица заказов
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        headers = [
            '№ накладной', 'Дата заказа', 'Закройщик', 'Изделие',
            'Заказчик', 'Телефон', 'Дата исполнения', 'Статус', 
            'Стоимость', 'Оплата'
        ]
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.doubleClicked.connect(self.edit_order)
        
        layout.addWidget(self.table)
        
        # Статистика
        self.stats_label = QLabel('')
        layout.addWidget(self.stats_label)
    
    def load_data(self):
        try:
            date_from = self.date_from.date().toString('yyyy-MM-dd')
            date_to = self.date_to.date().toString('yyyy-MM-dd')
            status = self.status_filter.currentData()
            
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
            
            if status == 'active':
                query += " AND cr.order_number IS NULL AND o.completion_date >= date('now')"
            elif status == 'overdue':
                query += " AND cr.order_number IS NULL AND o.completion_date < date('now')"
            elif status == 'completed':
                query += " AND cr.order_number IS NOT NULL"
            
            query += " ORDER BY o.order_date DESC, o.order_number DESC"
            
            results = self.db.fetch_all(query, params)
            
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
            
            self.stats_label.setText(
                f'Заказов: {len(results)} | '
                f'В работе: {active_orders} | '
                f'Просрочено: {overdue_orders} | '
                f'Завершено: {completed_orders} | '
                f'Общая стоимость: {total_amount:,.2f} руб'
            )
            
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Ошибка загрузки: {str(e)}')
    
    def create_new_order(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Новый заказ')
        dialog.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(dialog)
        
        # Основная информация
        info_group = QGroupBox('Основная информация')
        info_layout = QFormLayout()
        
        order_date = QDateEdit()
        order_date.setCalendarPopup(True)
        order_date.setDate(QDate.currentDate())
        order_date.setDisplayFormat('dd.MM.yyyy')
        
        cutter_combo = QComboBox()
        cutters = self.db.fetch_all("SELECT * FROM cutters ORDER BY full_name")
        for cutter in cutters:
            cutter_combo.addItem(cutter['full_name'], cutter['cutter_id'])
        
        product_combo = QComboBox()
        products = self.db.fetch_all("SELECT * FROM products ORDER BY product_name")
        for product in products:
            product_combo.addItem(
                f"{product['product_name']} ({product['base_price']:,.0f} руб)",
                product['product_id']
            )
        
        customer_name = QLineEdit()
        customer_address = QLineEdit()
        customer_phone = QLineEdit()
        
        completion_date = QDateEdit()
        completion_date.setCalendarPopup(True)
        completion_date.setDate(QDate.currentDate().addDays(7))
        completion_date.setDisplayFormat('dd.MM.yyyy')
        
        urgency_percent = QLineEdit('0')
        urgency_percent.setValidator(QDoubleValidator(0, 100, 2))
        urgency_percent.setPlaceholderText('Процент надбавки за срочность')
        
        info_layout.addRow('Дата заказа:', order_date)
        info_layout.addRow('Закройщик:', cutter_combo)
        info_layout.addRow('Изделие:', product_combo)
        info_layout.addRow('ФИО заказчика:', customer_name)
        info_layout.addRow('Адрес проживания:', customer_address)
        info_layout.addRow('Телефон:', customer_phone)
        info_layout.addRow('Дата исполнения:', completion_date)
        info_layout.addRow('% срочности:', urgency_percent)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Усложнения
        complications_group = QGroupBox('Усложнения')
        complications_layout = QVBoxLayout()
        
        self.complications_table = QTableWidget()
        self.complications_table.setColumnCount(3)
        self.complications_table.setHorizontalHeaderLabels(['Усложнение', 'Цена за элемент', 'Количество'])
        self.complications_table.setRowCount(0)
        
        complications_btn_layout = QHBoxLayout()
        add_complication_btn = QPushButton('Добавить усложнение')
        add_complication_btn.clicked.connect(lambda: self.add_complication_to_order(self.complications_table))
        remove_complication_btn = QPushButton('Удалить выбранное')
        remove_complication_btn.clicked.connect(lambda: self.remove_complication(self.complications_table))
        
        complications_btn_layout.addWidget(add_complication_btn)
        complications_btn_layout.addWidget(remove_complication_btn)
        complications_btn_layout.addStretch()
        
        complications_layout.addWidget(self.complications_table)
        complications_layout.addLayout(complications_btn_layout)
        complications_group.setLayout(complications_layout)
        layout.addWidget(complications_group)
        
        # Ткани
        fabrics_group = QGroupBox('Ткани')
        fabrics_layout = QVBoxLayout()
        
        self.fabrics_table = QTableWidget()
        self.fabrics_table.setColumnCount(4)
        self.fabrics_table.setHorizontalHeaderLabels(['Ткань', 'Цена', 'Доступно', 'Количество'])
        self.fabrics_table.setRowCount(0)
        
        fabrics_btn_layout = QHBoxLayout()
        add_fabric_btn = QPushButton('Добавить ткань')
        add_fabric_btn.clicked.connect(lambda: self.add_fabric_to_order(self.fabrics_table))
        remove_fabric_btn = QPushButton('Удалить выбранное')
        remove_fabric_btn.clicked.connect(lambda: self.remove_fabric(self.fabrics_table))
        
        fabrics_btn_layout.addWidget(add_fabric_btn)
        fabrics_btn_layout.addWidget(remove_fabric_btn)
        fabrics_btn_layout.addStretch()
        
        fabrics_layout.addWidget(self.fabrics_table)
        fabrics_layout.addLayout(fabrics_btn_layout)
        fabrics_group.setLayout(fabrics_layout)
        layout.addWidget(fabrics_group)
        
        # Расчет стоимости
        cost_group = QGroupBox('Расчет стоимости')
        cost_layout = QFormLayout()
        
        base_cost_label = QLabel('0.00')
        complications_cost_label = QLabel('0.00')
        fabrics_cost_label = QLabel('0.00')
        urgency_cost_label = QLabel('0.00')
        total_cost_label = QLabel('0.00')
        total_cost_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #d32f2f;")
        
        cost_layout.addRow('Основа изделия:', base_cost_label)
        cost_layout.addRow('Усложнения:', complications_cost_label)
        cost_layout.addRow('Ткани:', fabrics_cost_label)
        cost_layout.addRow('Срочность:', urgency_cost_label)
        cost_layout.addRow('ИТОГО:', total_cost_label)
        
        cost_group.setLayout(cost_layout)
        layout.addWidget(cost_group)
        
        # Кнопки сохранения/отмены
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(lambda: self.save_new_order(
            dialog, order_date.date(), cutter_combo.currentData(),
            product_combo.currentData(), customer_name.text(),
            customer_address.text(), customer_phone.text(),
            completion_date.date(), urgency_percent.text(),
            self.get_table_data(self.complications_table),
            self.get_table_data(self.fabrics_table)
        ))
        btn_box.rejected.connect(dialog.reject)
        
        layout.addWidget(btn_box)
        
        # Обновление стоимости при изменении
        product_combo.currentIndexChanged.connect(
            lambda: self.update_cost_calculation(
                product_combo, urgency_percent,
                self.complications_table, self.fabrics_table,
                base_cost_label, complications_cost_label,
                fabrics_cost_label, urgency_cost_label, total_cost_label
            )
        )
        urgency_percent.textChanged.connect(
            lambda: self.update_cost_calculation(
                product_combo, urgency_percent,
                self.complications_table, self.fabrics_table,
                base_cost_label, complications_cost_label,
                fabrics_cost_label, urgency_cost_label, total_cost_label
            )
        )
        
        dialog.exec_()
    
    def add_complication_to_order(self, table):
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
            dialog, table, complication_combo, count_edit
        ))
        btn_box.rejected.connect(dialog.reject)
        
        layout.addRow(btn_box)
        dialog.exec_()
    
    def save_complication_to_table(self, dialog, table, complication_combo, count_edit):
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
        
        row = table.rowCount()
        table.insertRow(row)
        
        table.setItem(row, 0, QTableWidgetItem(complication_text.split(' (')[0]))
        table.setItem(row, 1, QTableWidgetItem(str(price_result['price_per_element'])))
        table.setItem(row, 2, QTableWidgetItem(count))
        
        # Сохраняем ID в скрытых данных
        table.item(row, 0).setData(Qt.UserRole, complication_id)
        
        dialog.accept()
    
    def add_fabric_to_order(self, table):
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
        
        layout.addRow('Ткань:', fabric_combo)
        layout.addRow(f'Количество ({fabrics[0]["unit"] if fabrics else "ед."}):', quantity_edit)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(lambda: self.save_fabric_to_table(
            dialog, table, fabric_combo, quantity_edit
        ))
        btn_box.rejected.connect(dialog.reject)
        
        layout.addRow(btn_box)
        dialog.exec_()
    
    def save_fabric_to_table(self, dialog, table, fabric_combo, quantity_edit):
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
        
        row = table.rowCount()
        table.insertRow(row)
        
        table.setItem(row, 0, QTableWidgetItem(fabric_text.split(' (')[0]))
        table.setItem(row, 1, QTableWidgetItem(str(fabric_result['price'])))
        table.setItem(row, 2, QTableWidgetItem(f"{fabric_result['quantity']:.2f}"))
        table.setItem(row, 3, QTableWidgetItem(quantity))
        
        # Сохраняем артикул в скрытых данных
        table.item(row, 0).setData(Qt.UserRole, fabric_article)
        
        dialog.accept()
    
    def remove_complication(self, table):
        selected = table.currentRow()
        if selected >= 0:
            table.removeRow(selected)
    
    def remove_fabric(self, table):
        selected = table.currentRow()
        if selected >= 0:
            table.removeRow(selected)
    
    def get_table_data(self, table):
        data = []
        for row in range(table.rowCount()):
            row_data = {}
            for col in range(table.columnCount()):
                item = table.item(row, col)
                if item:
                    row_data[col] = item.text()
            # Получаем ID из скрытых данных
            id_item = table.item(row, 0)
            if id_item:
                row_data['id'] = id_item.data(Qt.UserRole)
            data.append(row_data)
        return data
    
    def update_cost_calculation(self, product_combo, urgency_edit, 
                               complications_table, fabrics_table,
                               base_label, complications_label,
                               fabrics_label, urgency_label, total_label):
        try:
            product_id = product_combo.currentData()
            if not product_id:
                return
            
            # Получаем цену основы
            product_query = "SELECT base_price FROM products WHERE product_id = ?"
            product_result = self.db.fetch_one(product_query, (product_id,))
            
            if not product_result:
                return
            
            base_price = product_result['base_price']
            base_label.setText(f"{base_price:,.2f}")
            
            # Считаем стоимость усложнений
            complications_cost = 0
            for row in range(complications_table.rowCount()):
                price_item = complications_table.item(row, 1)
                count_item = complications_table.item(row, 2)
                if price_item and count_item:
                    complications_cost += float(price_item.text()) * int(count_item.text())
            complications_label.setText(f"{complications_cost:,.2f}")
            
            # Считаем стоимость тканей
            fabrics_cost = 0
            for row in range(fabrics_table.rowCount()):
                price_item = fabrics_table.item(row, 1)
                quantity_item = fabrics_table.item(row, 3)
                if price_item and quantity_item:
                    fabrics_cost += float(price_item.text()) * float(quantity_item.text())
            fabrics_label.setText(f"{fabrics_cost:,.2f}")
            
            # Считаем надбавку за срочность
            urgency_percent = float(urgency_edit.text()) if urgency_edit.text().strip() else 0
            urgency_cost = base_price * urgency_percent / 100
            urgency_label.setText(f"{urgency_cost:,.2f}")
            
            # Итоговая стоимость
            total_cost = base_price + complications_cost + fabrics_cost + urgency_cost
            total_label.setText(f"{total_cost:,.2f}")
            
        except Exception as e:
            print(f"Ошибка расчета стоимости: {e}")
    
    def save_new_order(self, dialog, order_date, cutter_id, product_id,
                      customer_name, customer_address, customer_phone,
                      completion_date, urgency_percent,
                      complications_data, fabrics_data):
        # Валидация
        if not customer_name.strip():
            QMessageBox.warning(dialog, 'Ошибка', 'Введите ФИО заказчика')
            return
        
        try:
            # Сохраняем основной заказ
            order_query = """
            INSERT INTO orders (
                order_date, cutter_id, product_id, customer_name,
                customer_address, customer_phone, completion_date, urgency_percent
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            order_params = (
                order_date.toString('yyyy-MM-dd'),
                cutter_id,
                product_id,
                customer_name,
                customer_address,
                customer_phone,
                completion_date.toString('yyyy-MM-dd'),
                float(urgency_percent) if urgency_percent.strip() else 0
            )
            
            self.db.execute_query(order_query, order_params)
            
            # Получаем номер созданного заказа
            order_number = self.db.fetch_one("SELECT last_insert_rowid() as id")['id']
            
            # Сохраняем усложнения
            for comp_data in complications_data:
                complication_id = comp_data.get('id')
                if complication_id and '2' in comp_data:
                    comp_query = """
                    INSERT INTO order_complications 
                    (order_number, complication_id, element_count)
                    VALUES (?, ?, ?)
                    """
                    self.db.execute_query(comp_query, 
                        (order_number, complication_id, int(comp_data['2'])))
            
            # Сохраняем ткани и обновляем остатки
            for fabric_data in fabrics_data:
                fabric_article = fabric_data.get('id')
                if fabric_article and '3' in fabric_data:
                    # Добавляем ткань в заказ
                    fabric_query = """
                    INSERT INTO order_fabrics 
                    (order_number, fabric_article, quantity)
                    VALUES (?, ?, ?)
                    """
                    self.db.execute_query(fabric_query, 
                        (order_number, fabric_article, float(fabric_data['3'])))
                    
                    # Уменьшаем остаток на складе
                    update_query = """
                    UPDATE fabrics 
                    SET quantity = quantity - ?
                    WHERE fabric_article = ?
                    """
                    self.db.execute_query(update_query, 
                        (float(fabric_data['3']), fabric_article))
            
            dialog.accept()
            self.load_data()
            QMessageBox.information(self, 'Успех', f'Заказ №{order_number} успешно создан!')
            
        except Exception as e:
            QMessageBox.critical(dialog, 'Ошибка', f'Ошибка сохранения заказа: {str(e)}')
    
    def edit_order(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, 'Предупреждение', 'Выберите заказ')
            return
        
        order_number = int(self.table.item(selected, 0).text())
        
        if self.view_mode:
            # Режим просмотра - показываем детали
            self.view_order_details(order_number)
        else:
            # Режим редактирования
            QMessageBox.information(self, 'Информация', 
                'Редактирование заказов будет реализовано в следующей версии.')
    
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
                # Удаление заказа (каскадное удаление через foreign keys)
                query = "DELETE FROM orders WHERE order_number = ?"
                self.db.execute_query(query, (order_number,))
                self.load_data()
                QMessageBox.information(self, 'Успех', f'Заказ №{order_number} удален')
            except Exception as e:
                QMessageBox.critical(self, 'Ошибка', f'Ошибка удаления: {str(e)}')