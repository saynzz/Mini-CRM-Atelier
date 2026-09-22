from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QDoubleValidator
from database.db_connection import DatabaseConnection
from datetime import datetime

class CashRegisterManager(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseConnection()
        self.current_receipt_number = None
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        self.setWindowTitle('Касса - учет оплат')
        self.setMinimumSize(900, 500)
        
        layout = QVBoxLayout(self)
        
        # Панель инструментов
        toolbar = QHBoxLayout()
        
        add_btn = QPushButton('Новая оплата')
        add_btn.clicked.connect(self.add_payment)
        toolbar.addWidget(add_btn)
        
        delete_btn = QPushButton('Удалить')
        delete_btn.clicked.connect(self.delete_payment)
        toolbar.addWidget(delete_btn)
        
        refresh_btn = QPushButton('Обновить')
        refresh_btn.clicked.connect(self.load_data)
        toolbar.addWidget(refresh_btn)
        
        # Фильтры
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
        
        daily_report_btn = QPushButton('Дневной отчет')
        daily_report_btn.clicked.connect(self.generate_daily_report)
        toolbar.addWidget(daily_report_btn)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            '№ квитанции', 'Дата', '№ заказа', 'Заказчик', 'Сумма', 'Примечание'
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        layout.addWidget(self.table)
        
        # Статистика
        self.stats_label = QLabel('')
        layout.addWidget(self.stats_label)
    
    def load_data(self):
        try:
            date_from = self.date_from.date().toString('yyyy-MM-dd')
            date_to = self.date_to.date().toString('yyyy-MM-dd')
            
            query = """
            SELECT cr.*, o.customer_name, oc.total_amount
            FROM cash_register cr
            JOIN orders o ON cr.order_number = o.order_number
            LEFT JOIN order_costs oc ON cr.order_number = oc.order_number
            WHERE cr.receipt_date BETWEEN ? AND ?
            ORDER BY cr.receipt_date DESC, cr.receipt_number DESC
            """
            
            results = self.db.fetch_all(query, (date_from, date_to))
            
            self.table.setRowCount(len(results))
            
            total_amount = 0
            payments_count = len(results)
            
            for i, row in enumerate(results):
                self.table.setItem(i, 0, QTableWidgetItem(str(row['receipt_number'])))
                self.table.setItem(i, 1, QTableWidgetItem(row['receipt_date']))
                self.table.setItem(i, 2, QTableWidgetItem(str(row['order_number'])))
                self.table.setItem(i, 3, QTableWidgetItem(row['customer_name']))
                self.table.setItem(i, 4, QTableWidgetItem(f"{row['amount']:,.2f}"))
                
                # Примечание: сравнение суммы оплаты с расчетной стоимостью
                note = ''
                if row['total_amount']:
                    if abs(row['amount'] - row['total_amount']) < 0.01:
                        note = 'Полная оплата'
                    elif row['amount'] < row['total_amount']:
                        note = f'Аванс {row["amount"]/row["total_amount"]*100:.0f}%'
                    else:
                        note = 'Переплата'
                self.table.setItem(i, 5, QTableWidgetItem(note))
                
                total_amount += row['amount']
            
            self.table.resizeColumnsToContents()
            
            avg_payment = total_amount / payments_count if payments_count > 0 else 0
            self.stats_label.setText(
                f'Период: {date_from} - {date_to} | '
                f'Оплат: {payments_count} | '
                f'Общая сумма: {total_amount:,.2f} руб | '
                f'Средний чек: {avg_payment:,.2f} руб'
            )
            
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Ошибка загрузки: {str(e)}')
    
    def add_payment(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Новая оплата')
        dialog.setMinimumSize(500, 300)
        
        layout = QFormLayout(dialog)
        
        # Выбор заказа
        order_combo = QComboBox()
        order_combo.addItem('-- Выберите заказ --', None)
        
        # Загружаем неоплаченные заказы
        query = """
        SELECT o.order_number, o.customer_name, p.product_name, oc.total_amount
        FROM orders o
        JOIN products p ON o.product_id = p.product_id
        LEFT JOIN order_costs oc ON o.order_number = oc.order_number
        WHERE o.order_number NOT IN (SELECT order_number FROM cash_register)
        ORDER BY o.order_date DESC
        """
        
        orders = self.db.fetch_all(query)
        for order in orders:
            order_combo.addItem(
                f"№{order['order_number']} - {order['customer_name']} "
                f"({order['product_name']}, {order['total_amount']:,.0f} руб)",
                order['order_number']
            )
        
        # Поля ввода
        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        date_edit.setDate(QDate.currentDate())
        date_edit.setDisplayFormat('dd.MM.yyyy')
        
        amount_edit = QLineEdit()
        amount_edit.setValidator(QDoubleValidator(0, 1000000, 2))
        
        # Расчетная стоимость (обновляется при выборе заказа)
        calculated_amount_label = QLabel('0.00')
        
        # При выборе заказа обновляем расчетную стоимость
        def update_calculated_amount():
            order_number = order_combo.currentData()
            if order_number:
                query = "SELECT total_amount FROM order_costs WHERE order_number = ?"
                result = self.db.fetch_one(query, (order_number,))
                if result and result['total_amount']:
                    calculated_amount_label.setText(f"{result['total_amount']:,.2f}")
                    amount_edit.setText(str(result['total_amount']))
                else:
                    calculated_amount_label.setText('Не рассчитана')
        
        order_combo.currentIndexChanged.connect(update_calculated_amount)
        
        layout.addRow('Заказ:', order_combo)
        layout.addRow('Дата оплаты:', date_edit)
        layout.addRow('Расчетная стоимость:', calculated_amount_label)
        layout.addRow('Сумма оплаты (руб):', amount_edit)
        
        # Кнопки
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(lambda: self.save_payment(
            dialog, order_combo.currentData(), date_edit.date(),
            amount_edit.text()
        ))
        btn_box.rejected.connect(dialog.reject)
        
        layout.addRow(btn_box)
        dialog.exec_()
    
    def save_payment(self, dialog, order_number, payment_date, amount):
        if not order_number:
            QMessageBox.warning(dialog, 'Ошибка', 'Выберите заказ')
            return
        
        if not amount.strip():
            QMessageBox.warning(dialog, 'Ошибка', 'Введите сумму оплаты')
            return
        
        try:
            amount_value = float(amount)
            
            # Проверяем, не оплачен ли уже заказ
            check_query = "SELECT COUNT(*) as count FROM cash_register WHERE order_number = ?"
            check_result = self.db.fetch_one(check_query, (order_number,))
            
            if check_result['count'] > 0:
                QMessageBox.warning(dialog, 'Ошибка', 'Этот заказ уже оплачен')
                return
            
            # Сохраняем оплату
            query = """
            INSERT INTO cash_register (order_number, receipt_date, amount)
            VALUES (?, ?, ?)
            """
            
            self.db.execute_query(query, (
                order_number,
                payment_date.toString('yyyy-MM-dd'),
                amount_value
            ))
            
            dialog.accept()
            self.load_data()
            QMessageBox.information(self, 'Успех', 'Оплата успешно добавлена')
            
        except Exception as e:
            QMessageBox.critical(dialog, 'Ошибка', f'Ошибка сохранения: {str(e)}')
    
    def delete_payment(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, 'Предупреждение', 'Выберите оплату для удаления')
            return
        
        receipt_number = int(self.table.item(selected, 0).text())
        order_number = int(self.table.item(selected, 2).text())
        amount = self.table.item(selected, 4).text()
        
        reply = QMessageBox.question(
            self, 'Подтверждение',
            f'Удалить оплату №{receipt_number} по заказу №{order_number} '
            f'на сумму {amount} руб?\n'
            'Внимание: это действие нельзя отменить.',
            QMessageBox.Yes | QDialogButtonBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                query = "DELETE FROM cash_register WHERE receipt_number = ?"
                self.db.execute_query(query, (receipt_number,))
                self.load_data()
                QMessageBox.information(self, 'Успех', 'Оплата удалена')
            except Exception as e:
                QMessageBox.critical(self, 'Ошибка', f'Ошибка удаления: {str(e)}')
    
    def generate_daily_report(self):
        today = QDate.currentDate().toString('yyyy-MM-dd')
        
        try:
            # Получаем данные за сегодня
            query = """
            SELECT 
                COUNT(*) as payments_count,
                SUM(amount) as total_amount,
                MIN(amount) as min_amount,
                MAX(amount) as max_amount,
                AVG(amount) as avg_amount
            FROM cash_register 
            WHERE receipt_date = ?
            """
            
            stats = self.db.fetch_one(query, (today,))
            
            # Детали по оплатам
            details_query = """
            SELECT cr.*, o.customer_name
            FROM cash_register cr
            JOIN orders o ON cr.order_number = o.order_number
            WHERE cr.receipt_date = ?
            ORDER BY cr.receipt_number
            """
            
            details = self.db.fetch_all(details_query, (today,))
            
            # Создаем диалог отчета
            dialog = QDialog(self)
            dialog.setWindowTitle(f'Дневной отчет по кассе - {today}')
            dialog.setMinimumSize(800, 500)
            
            layout = QVBoxLayout(dialog)
            
            # Статистика
            stats_group = QGroupBox('Статистика за день')
            stats_layout = QFormLayout()
            
            stats_layout.addRow('Дата:', QLabel(today))
            stats_layout.addRow('Количество оплат:', QLabel(str(stats['payments_count'] or 0)))
            stats_layout.addRow('Общая сумма:', QLabel(f"{stats['total_amount'] or 0:,.2f} руб"))
            stats_layout.addRow('Минимальный чек:', QLabel(f"{stats['min_amount'] or 0:,.2f} руб"))
            stats_layout.addRow('Максимальный чек:', QLabel(f"{stats['max_amount'] or 0:,.2f} руб"))
            stats_layout.addRow('Средний чек:', QLabel(f"{stats['avg_amount'] or 0:,.2f} руб"))
            
            stats_group.setLayout(stats_layout)
            layout.addWidget(stats_group)
            
            # Детали оплат
            if details:
                details_group = QGroupBox('Детали оплат')
                details_layout = QVBoxLayout()
                
                details_table = QTableWidget()
                details_table.setColumnCount(5)
                details_table.setHorizontalHeaderLabels([
                    '№ квитанции', '№ заказа', 'Заказчик', 'Сумма', 'Время'
                ])
                details_table.setRowCount(len(details))
                details_table.setEditTriggers(QTableWidget.NoEditTriggers)
                
                for i, detail in enumerate(details):
                    details_table.setItem(i, 0, QTableWidgetItem(str(detail['receipt_number'])))
                    details_table.setItem(i, 1, QTableWidgetItem(str(detail['order_number'])))
                    details_table.setItem(i, 2, QTableWidgetItem(detail['customer_name']))
                    details_table.setItem(i, 3, QTableWidgetItem(f"{detail['amount']:,.2f}"))
                    
                    # Парсим дату-время если есть
                    receipt_time = 'не указано'
                    try:
                        if ' ' in detail['receipt_date']:
                            receipt_time = detail['receipt_date'].split(' ')[1]
                    except:
                        pass
                    details_table.setItem(i, 4, QTableWidgetItem(receipt_time))
                
                details_table.resizeColumnsToContents()
                details_layout.addWidget(details_table)
                details_group.setLayout(details_layout)
                layout.addWidget(details_group)
            
            # Кнопки
            btn_layout = QHBoxLayout()
            print_btn = QPushButton('Печать')
            export_btn = QPushButton('Экспорт в Excel')
            close_btn = QPushButton('Закрыть')
            
            btn_layout.addWidget(print_btn)
            btn_layout.addWidget(export_btn)
            btn_layout.addWidget(close_btn)
            
            layout.addLayout(btn_layout)
            
            # Обработчики кнопок
            print_btn.clicked.connect(lambda: self.print_report(details, today))
            export_btn.clicked.connect(lambda: self.export_daily_report(details, today, stats))
            close_btn.clicked.connect(dialog.close)
            
            dialog.exec_()
            
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Ошибка генерации отчета: {str(e)}')
    
    def print_report(self, details, date):
        QMessageBox.information(self, 'Печать', 
            'Для печати используйте экспорт в Excel.')
    
    def export_daily_report(self, details, date, stats):
        try:
            import pandas as pd
            from datetime import datetime
            
            # Создаем DataFrame с деталями
            if details:
                df_details = pd.DataFrame(details)
                
                # Создаем DataFrame со статистикой
                stats_data = {
                    'Дата': [date],
                    'Количество оплат': [stats['payments_count'] or 0],
                    'Общая сумма': [stats['total_amount'] or 0],
                    'Минимальный чек': [stats['min_amount'] or 0],
                    'Максимальный чек': [stats['max_amount'] or 0],
                    'Средний чек': [stats['avg_amount'] or 0]
                }
                df_stats = pd.DataFrame(stats_data)
                
                # Сохраняем в Excel с двумя листами
                filename = f"reports/cash_report_{date}.xlsx"
                
                with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                    df_stats.to_excel(writer, sheet_name='Статистика', index=False)
                    df_details.to_excel(writer, sheet_name='Детали оплат', index=False)
                
                QMessageBox.information(self, 'Успех', f'Отчет сохранен: {filename}')
            else:
                QMessageBox.information(self, 'Информация', 'Нет данных для экспорта')
                
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Ошибка экспорта: {str(e)}')