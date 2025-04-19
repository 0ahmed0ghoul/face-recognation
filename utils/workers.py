from PyQt5.QtWidgets import (QWidget, QListWidgetItem, 
                            QLineEdit, QMessageBox, QGraphicsOpacityEffect)
from PyQt5.QtCore import (QPropertyAnimation, QEasingCurve, QEvent, 
                         QPoint, Qt, QSize)
from PyQt5.QtGui import QColor, QFont
from PyQt5.uic import loadUi
from functools import partial
from utils.userDialog import UserDialog
from db.db import session, Worker
import shutil
import os

    
        

class Workers(QWidget):
    def __init__(self):
        super().__init__()
        loadUi("ui/workers.ui", self)
        self.prepare()
        self.search_input.textChanged.connect(self.search_worker)


        

    def prepare(self):
        self.add_worker_button.clicked.connect(self.add_worker)
        self.delete_worker_button.clicked.connect(self.delete_worker)
        self.listWorkers_2.itemDoubleClicked.connect(self.edit_worker)
        
        self.update_list()
        self.customize_list_style()


    def edit_worker(self, item):
        name = item.text()
        dialog = UserDialog(self, name)
        
        # Add fade animation for dialog
        opacity_effect = QGraphicsOpacityEffect(dialog)
        dialog.setGraphicsEffect(opacity_effect)
        
        opacity_animation = QPropertyAnimation(opacity_effect, b"opacity")
        opacity_animation.setDuration(300)
        opacity_animation.setStartValue(0)
        opacity_animation.setEndValue(1)
        
        dialog.exec_()
        self.update_list()

    def customize_list_style(self):
        self.listWorkers_2.setStyleSheet("""
            /* Glass Panel with Frosted Background */
            QListWidget {
                padding: 10px;
                background-color: transparent;
                border-radius: 14px;
                border: 1px solid rgba(255, 255, 255, 0.25);
                backdrop-filter: blur(12px);
            }

            /* List Items */
            QListWidget::item {
                height: 44px;
                margin: 6px 0;
                padding: 10px 14px;
                color: #fff;
                border: 1px solid #333;
            }

            /* Hover Effect */
            QListWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.35);
            }

            /* Selected Item */
            QListWidget::item:selected {
                color: white;
                font-weight: bold;
            }

            /* Scrollbar Track */
            QScrollBar:vertical {
                background: transparent;
                width: 10px;
                margin: 4px;
            }

            /* Scrollbar Handle */
            QScrollBar::handle:vertical {
                background: rgba(180, 180, 180, 0.4);
                min-height: 30px;
                border-radius: 5px;
            }

            /* Optional: Scrollbar on hover for better UX */
            QScrollBar::handle:vertical:hover {
                background: rgba(150, 150, 150, 0.6);
            }
        """)


    def add_worker(self):
        dialog = UserDialog(self)
        
        # Add animation
        opacity_effect = QGraphicsOpacityEffect(dialog)
        dialog.setGraphicsEffect(opacity_effect)
        
        opacity_animation = QPropertyAnimation(opacity_effect, b"opacity")
        opacity_animation.setDuration(300)
        opacity_animation.setStartValue(0)
        opacity_animation.setEndValue(1)
        
        dialog.exec_()
        self.update_list()

    def delete_worker(self):
        item = self.listWorkers_2.currentItem()
        if not item:
            return
            
        name = item.text()
        
        # Create a custom message box
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Delete Worker")
        msg_box.setText(f'Are you sure you want to delete "{name}"?')
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        
        # Style the message box
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #FFFFFF;
                font-size: 14px;
            }
            QMessageBox QLabel {
                color: #424242;
            }
            QMessageBox QPushButton {
                min-width: 80px;
                padding: 8px;
                border-radius: 6px;
            }
        """)
        
        reply = msg_box.exec_()
        
        if reply == QMessageBox.Yes:
            worker = session.query(Worker).filter(Worker.name == name).first()
            if worker:
                session.delete(worker)
                session.commit()
                
                # Delete face data if exists
                face_dir = os.path.join("known_faces", name)
                if os.path.exists(face_dir):
                    try:
                        shutil.rmtree(face_dir)
                    except Exception as e:
                        error_box = QMessageBox()
                        error_box.setWindowTitle("Warning")
                        error_box.setText(f"Could not delete face data: {str(e)}")
                        error_box.setIcon(QMessageBox.Warning)
                        error_box.exec_()
                
                # Add item removal animation
                for i in range(self.listWorkers_2.count()):
                    if self.listWorkers_2.item(i).text() == name:
                        break
                self.update_list()

    def update_list(self, search_query=""):
        self.listWorkers_2.clear()
        workers = session.query(Worker).filter(Worker.name.ilike(f"%{search_query}%")).all()

        for worker in workers:
            item = QListWidgetItem(worker.name)
            font = QFont()
            font.setPointSize(14)
            font.setWeight(500)
            item.setFont(font)
            self.listWorkers_2.addItem(item)

    def search_worker(self):
        search_query = self.search_input.text().strip()
        self.update_list(search_query)