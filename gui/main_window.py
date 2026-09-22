import sys
import webbrowser
from pathlib import Path
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QIcon, QFont
from database.db_connection import DatabaseConnection
from config import Config

class MainWindow(QMainWindow):
    def __init__(self, current_user=None):
        super().__init__()
        self.db = DatabaseConnection()
        self.current_user = current_user
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle(f'{Config.APP_NAME} v{Config.APP_VERSION}')
        self.setGeometry(100, 100, 1200, 700)
        
        # Создаем меню
        self.create_menu()
        
        # Центральный виджет с вкладками
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)
        
        # Дашборд
        self.create_dashboard()
        
        # Статус бар
        status_text = 'Готово'
        if self.current_user:
            status_text += f'  |  Пользователь: {self.current_user}'
        self.statusBar().showMessage(status_text)
        
    def create_menu(self):
        menubar = self.menuBar()
        
        # Меню Справочники
        ref_menu = menubar.addMenu('Справочники')
        
        cutters_action = QAction('Закройщики', self)
        cutters_action.triggered.connect(self.show_cutters)
        ref_menu.addAction(cutters_action)
        
        categories_action = QAction('Категории', self)
        categories_action.triggered.connect(self.show_categories)
        ref_menu.addAction(categories_action)
        
        products_action = QAction('Изделия', self)
        products_action.triggered.connect(self.show_products)
        ref_menu.addAction(products_action)
        
        fabrics_action = QAction('Ткани', self)
        fabrics_action.triggered.connect(self.show_fabrics)
        ref_menu.addAction(fabrics_action)
        
        fabric_types_action = QAction('Типы ткани', self)
        fabric_types_action.triggered.connect(self.show_fabric_types)
        ref_menu.addAction(fabric_types_action)
        
        complications_action = QAction('Усложнения', self)
        complications_action.triggered.connect(self.show_complications)
        ref_menu.addAction(complications_action)
        
        ref_menu.addSeparator()
        
        # Меню Заказы
        orders_menu = menubar.addMenu('Заказы')
        
        new_order_action = QAction('Новый заказ', self)
        new_order_action.triggered.connect(self.create_new_order)
        orders_menu.addAction(new_order_action)
        
        view_orders_action = QAction('Просмотр заказов', self)
        view_orders_action.triggered.connect(self.show_orders)
        orders_menu.addAction(view_orders_action)
        
        # Меню Финансы
        finance_menu = menubar.addMenu('Финансы')
        
        cash_action = QAction('Касса', self)
        cash_action.triggered.connect(self.show_cash_register)
        finance_menu.addAction(cash_action)
        
        # Меню Отчеты
        reports_menu = menubar.addMenu('Отчеты')
        
        daily_report = QAction('Дневной отчет', self)
        daily_report.triggered.connect(self.generate_daily_report)
        reports_menu.addAction(daily_report)
        
        orders_report = QAction('Отчет по заказам', self)
        orders_report.triggered.connect(self.generate_orders_report)
        reports_menu.addAction(orders_report)
        
        finance_report = QAction('Финансовый отчет', self)
        finance_report.triggered.connect(self.generate_finance_report)
        reports_menu.addAction(finance_report)
        
    def create_dashboard(self):
        dashboard = QWidget()
        layout = QVBoxLayout(dashboard)
        
        # Заголовок
        title = QLabel(f'<h1>{Config.APP_NAME}</h1>')
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Быстрые кнопки
        button_layout = QGridLayout()
        
        buttons = [
            ('Новый заказ', self.create_new_order, '#4CAF50'),
            ('Закройщики', self.show_cutters, '#2196F3'),
            ('Изделия', self.show_products, '#FF9800'),
            ('Ткани', self.show_fabrics, '#9C27B0'),
            ('Заказы', self.show_orders, '#F44336'),
            ('Касса', self.show_cash_register, '#009688'),
            ('Отчеты', self.generate_daily_report, '#607D8B'),
            ('Справка', self.show_help, '#795548')
        ]
        
        for i, (text, handler, color) in enumerate(buttons):
            btn = QPushButton(text)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    padding: 15px;
                    font-size: 14px;
                    font-weight: bold;
                    border-radius: 5px;
                }}
                QPushButton:hover {{ background-color: {color}80; }}
            """)
            btn.clicked.connect(handler)
            button_layout.addWidget(btn, i // 4, i % 4)
        
        layout.addLayout(button_layout)
        
        # Статистика
        stats_group = QGroupBox('Статистика за сегодня')
        stats_layout = QGridLayout()
        
        try:
            today = QDate.currentDate().toString('yyyy-MM-dd')
            
            # Количество заказов
            orders_count = self.db.fetch_one(
                "SELECT COUNT(*) as count FROM orders WHERE order_date = ?", 
                (today,)
            )['count']
            stats_layout.addWidget(QLabel(f'Заказов сегодня: {orders_count}'), 0, 0)
            
            # Выручка
            revenue = self.db.fetch_one("""
                SELECT COALESCE(SUM(amount), 0) as total 
                FROM cash_register 
                WHERE receipt_date = ?
            """, (today,))['total']
            stats_layout.addWidget(QLabel(f'Выручка: {revenue:,.2f} руб'), 0, 1)
            
            # Активные закройщики
            active_cutters = self.db.fetch_all("""
                SELECT COUNT(DISTINCT cutter_id) as count 
                FROM orders WHERE order_date = ?
            """, (today,))[0]['count']
            stats_layout.addWidget(QLabel(f'Работают закройщиков: {active_cutters}'), 1, 0)
            
            # Невыполненные заказы
            pending_orders = self.db.fetch_one("""
                SELECT COUNT(*) as count FROM orders 
                WHERE completion_date < date('now') 
                  AND order_number NOT IN (SELECT order_number FROM cash_register)
            """)['count']
            stats_layout.addWidget(QLabel(f'Просрочено заказов: {pending_orders}'), 1, 1)
            
        except Exception as e:
            print(f"Ошибка загрузки статистики: {e}")
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        self.tab_widget.addTab(dashboard, "Главная")
    
    # Методы для отображения форм (будут реализованы далее)
    def show_cutters(self):
        from gui.cutters_manager import CuttersManager
        dialog = CuttersManager(self)
        dialog.exec_()
    
    def show_categories(self):
        from gui.categories_manager import CategoriesManager
        dialog = CategoriesManager(self)
        dialog.exec_()
    
    def show_products(self):
        from gui.products_manager import ProductsManager
        dialog = ProductsManager(self)
        dialog.exec_()
    
    def show_fabrics(self):
        from gui.fabrics_manager import FabricsManager
        dialog = FabricsManager(self)
        dialog.exec_()
    
    def show_fabric_types(self):
        from gui.fabric_types_manager import FabricTypesManager
        dialog = FabricTypesManager(self)
        dialog.exec_()
    
    def show_complications(self):
        from gui.complications_manager import ComplicationsManager
        dialog = ComplicationsManager(self)
        dialog.exec_()
    
    def create_new_order(self):
        from gui.orders_manager import OrdersManager
        dialog = OrdersManager(self)
        dialog.exec_()
    
    def show_orders(self):
        from gui.orders_manager import OrdersManager
        dialog = OrdersManager(self, view_mode=True)
        dialog.exec_()
    
    def show_cash_register(self):
        from gui.cash_register import CashRegisterManager
        dialog = CashRegisterManager(self)
        dialog.exec_()
    
    def generate_daily_report(self):
        self.generate_report('daily')
    
    def generate_orders_report(self):
        self.generate_report('orders')
    
    def generate_finance_report(self):
        self.generate_report('finance')
    
    def generate_report(self, report_type):
        try:
            if report_type == 'daily':
                query = """
                SELECT 
                    o.order_number,
                    o.order_date,
                    c.full_name as cutter,
                    p.product_name,
                    o.customer_name,
                    o.completion_date,
                    oc.total_amount,
                    CASE WHEN cr.order_number IS NULL THEN 'Не оплачен' ELSE 'Оплачен' END as status
                FROM orders o
                JOIN cutters c ON o.cutter_id = c.cutter_id
                JOIN products p ON o.product_id = p.product_id
                LEFT JOIN order_costs oc ON o.order_number = oc.order_number
                LEFT JOIN cash_register cr ON o.order_number = cr.order_number
                WHERE o.order_date = date('now')
                ORDER BY o.order_number
                """
                title = 'Дневной отчет'
                
            elif report_type == 'orders':
                query = """
                SELECT 
                    o.order_number,
                    o.order_date,
                    o.completion_date,
                    c.full_name as cutter,
                    cat.category_name,
                    p.product_name,
                    o.customer_name,
                    o.customer_phone,
                    oc.total_amount,
                    CASE 
                        WHEN cr.order_number IS NULL AND o.completion_date < date('now') 
                        THEN 'Просрочен'
                        WHEN cr.order_number IS NULL 
                        THEN 'В работе'
                        ELSE 'Завершен'
                    END as status
                FROM orders o
                JOIN cutters c ON o.cutter_id = c.cutter_id
                JOIN products p ON o.product_id = p.product_id
                JOIN categories cat ON p.category_id = cat.category_id
                LEFT JOIN order_costs oc ON o.order_number = oc.order_number
                LEFT JOIN cash_register cr ON o.order_number = cr.order_number
                ORDER BY o.order_date DESC
                """
                title = 'Отчет по заказам'
                
            elif report_type == 'finance':
                query = """
                SELECT 
                    strftime('%Y-%m', cr.receipt_date) as month,
                    COUNT(cr.receipt_number) as orders_count,
                    SUM(cr.amount) as total_income,
                    AVG(cr.amount) as avg_order_amount
                FROM cash_register cr
                GROUP BY strftime('%Y-%m', cr.receipt_date)
                ORDER BY month DESC
                """
                title = 'Финансовый отчет'
            else:
                return
            
            results = self.db.fetch_all(query)
            
            if not results:
                QMessageBox.information(self, 'Информация', 'Нет данных для отчета')
                return
            
            # Создаем диалог отчета
            dialog = QDialog(self)
            dialog.setWindowTitle(title)
            dialog.setMinimumSize(900, 500)
            
            layout = QVBoxLayout(dialog)
            
            # Заголовок
            title_label = QLabel(f'<h2>{title}</h2>')
            title_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(title_label)
            
            # Таблица
            table = QTableWidget()
            table.setRowCount(len(results))
            
            if results:
                headers = list(results[0].keys())
                table.setColumnCount(len(headers))
                table.setHorizontalHeaderLabels(headers)
                
                for i, row in enumerate(results):
                    for j, header in enumerate(headers):
                        value = row[header]
                        if isinstance(value, (int, float)) and header not in ['month', 'status', 'cutter', 'product_name']:
                            if value == int(value):
                                display_value = f"{int(value):,}"
                            else:
                                display_value = f"{value:,.2f}"
                        else:
                            display_value = str(value) if value is not None else ''
                        
                        item = QTableWidgetItem(display_value)
                        
                        # Подсветка статусов
                        if header == 'status':
                            if display_value == 'Просрочен':
                                item.setBackground(Qt.red)
                                item.setForeground(Qt.white)
                            elif display_value == 'В работе':
                                item.setBackground(Qt.yellow)
                            elif display_value == 'Завершен':
                                item.setBackground(Qt.green)
                                item.setForeground(Qt.white)
                        
                        table.setItem(i, j, item)
                
                table.resizeColumnsToContents()
            
            layout.addWidget(table)
            
            # Кнопки
            btn_layout = QHBoxLayout()
            export_btn = QPushButton('Экспорт в Excel')
            print_btn = QPushButton('Печать')
            close_btn = QPushButton('Закрыть')
            
            btn_layout.addWidget(export_btn)
            btn_layout.addWidget(print_btn)
            btn_layout.addWidget(close_btn)
            
            layout.addLayout(btn_layout)
            
            # Обработчики
            export_btn.clicked.connect(lambda: self.export_to_excel(results, title))
            print_btn.clicked.connect(lambda: self.print_report(table, title))
            close_btn.clicked.connect(dialog.close)
            
            dialog.exec_()
            
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Ошибка генерации отчета: {str(e)}')
    
    def export_to_excel(self, data, report_name):
        try:
            import pandas as pd
            from datetime import datetime
            
            df = pd.DataFrame(data)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"reports/{report_name}_{timestamp}.xlsx"
            
            df.to_excel(filename, index=False)
            
            QMessageBox.information(
                self, 'Успешный экспорт',
                f'Отчет сохранен: {filename}'
            )
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Ошибка экспорта: {str(e)}')
    
    def print_report(self, table, title):
        QMessageBox.information(self, 'Печать', 
            'Для печати используйте экспорт в Excel')
    
    def show_help(self):
        help_text = """
        <h2>Справка по системе "Ателье"</h2>
        
        <h3>Основные модули:</h3>
        <ul>
            <li><b>Справочники</b> - базовые данные (закройщики, изделия, ткани)</li>
            <li><b>Заказы</b> - создание и управление заказами</li>
            <li><b>Касса</b> - учет финансовых операций</li>
            <li><b>Отчеты</b> - анализ деятельности ателье</li>
        </ul>
        
        <h3>Рабочий процесс:</h3>
        <ol>
            <li>Добавьте закройщиков и изделия в справочники</li>
            <li>Создайте новый заказ для клиента</li>
            <li>Укажите ткань и усложнения для заказа</li>
            <li>После выполнения заказа внесите оплату в кассу</li>
            <li>Анализируйте работу через отчеты</li>
        </ol>
        
        <h3>Важные особенности:</h3>
        <ul>
            <li>Стоимость заказа рассчитывается автоматически</li>
            <li>Учитывается срочность изготовления (% надбавки)</li>
            <li>Контроль остатков ткани на складе</li>
            <li>Отслеживание статуса заказов</li>
        </ul>
        """
        
        dialog = QDialog(self)
        dialog.setWindowTitle('Справка')
        dialog.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(dialog)
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml(help_text)
        layout.addWidget(text_edit)
        
        btn = QPushButton('Закрыть')
        btn.clicked.connect(dialog.close)
        layout.addWidget(btn)
        
        dialog.exec_()

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()