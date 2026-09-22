from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from database.db_connection import DatabaseConnection
from config import Config

class CategoriesManager(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseConnection()
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        self.setWindowTitle('Категории закройщиков/изделий')
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Информация
        info_label = QLabel(
            "Категории определяют специализацию закройщиков и тип изделий.\n"
            "Доступные значения фиксированы: верхняя одежда, легкое платье,\n"
            "мужская одежда, шляпы, меховые изделия."
        )
        info_label.setStyleSheet("background-color: #f0f8ff; padding: 10px; border-radius: 5px;")
        layout.addWidget(info_label)
        
        # Панель инструментов
        toolbar = QHBoxLayout()
        refresh_btn = QPushButton('Обновить')
        refresh_btn.clicked.connect(self.load_data)
        toolbar.addWidget(refresh_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(['Код', 'Наименование', 'Описание'])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        layout.addWidget(self.table)
    
    def load_data(self):
        try:
            # Сначала проверяем, что все категории существуют
            self.ensure_categories_exist()
            
            query = "SELECT * FROM categories ORDER BY category_name"
            results = self.db.fetch_all(query)
            
            self.table.setRowCount(len(results))
            
            descriptions = {
                'верхняя одежда': 'Пальто, куртки, плащи, шубы',
                'легкое платье': 'Платья, юбки, блузки, сарафаны',
                'мужская одежда': 'Костюмы, пиджаки, брюки, рубашки',
                'шляпы': 'Головные уборы всех видов',
                'меховые изделия': 'Шубы, меховые жилеты, манто'
            }
            
            for i, row in enumerate(results):
                self.table.setItem(i, 0, QTableWidgetItem(str(row['category_id'])))
                self.table.setItem(i, 1, QTableWidgetItem(row['category_name']))
                self.table.setItem(i, 2, QTableWidgetItem(
                    descriptions.get(row['category_name'], 'Общая категория')
                ))
            
            self.table.resizeColumnsToContents()
            
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Ошибка загрузки: {str(e)}')
    
    def ensure_categories_exist(self):
        for category in Config.CUTTER_CATEGORIES:
            self.db.execute_query(
                "INSERT OR IGNORE INTO categories (category_name) VALUES (?)",
                (category,)
            )