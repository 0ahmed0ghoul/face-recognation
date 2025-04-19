from PyQt5.QtWidgets import QWidget
from PyQt5.uic import loadUi
from PyQt5.QtWidgets import  QWidget, QHeaderView 

class parameters(QWidget):  # Corrected class name
    def __init__(self):
        super().__init__()
        loadUi("ui/dailyAttendence.ui", self)  
        