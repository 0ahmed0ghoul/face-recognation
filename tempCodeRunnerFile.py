from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QTabWidget, QWidget
from PyQt5.QtCore import Qt, QTimer
from PyQt5.uic import loadUi
import subprocess
import threading
import os
from utils.workers import Workers
from utils.attendence import attendence  
from utils.dailyAttend import dailyAttendence 
from utils.parameters import parameters  
from db.db import session ,Worker, Log
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        loadUi('ui/main.ui', self) 
        self.prepare()
        self.setWindowTitle("Attendance System")
        self.setGeometry(100, 100, 800, 600)

        
    def prepare(self):
        screen = QApplication.primaryScreen() 
        screen_geometry = screen.geometry()
        width, height = screen_geometry.width(), screen_geometry.height()
        self.resize(width, height)


        # Attendance Tab
        layout1 = QVBoxLayout()
        layout1.addWidget(dailyAttendence())  # Add the dailyAttendence widget

        self.tabWidget.widget(0).setLayout(layout1)

        # Another Attendance Tab (or whichever widget you want)
        layout2 = QVBoxLayout()
        layout2.addWidget(attendence())  # Add the attendence widget
        self.tabWidget.widget(1).setLayout(layout2)# Add third tab

        # Workers Tab
        layout3 = QVBoxLayout()
        layout3.addWidget(Workers())  # Add the Workers widget
        self.tabWidget.widget(2).setLayout(layout3)# Ad # Add Workers tab

        # Now you can safely access each tab like this:
        self.tabWidget.widget(0).setLayout(layout1)
        self.tabWidget.widget(1).setLayout(layout2)
        self.tabWidget.widget(2).setLayout(layout3)

        # Connect button
        self.startVideoBtn.clicked.connect(self.start)
    def reset_button(self):
        self.startVideoBtn.setEnabled(True)
        self.startVideoBtn.setText("Start Detecting")
        self.startVideoBtn.setStyleSheet("")
        self.startVideoBtn.setCursor(Qt.ArrowCursor)
    
    def start(self):
        self.startVideoBtn.setEnabled(False)
        self.startVideoBtn.setText("Processing...")
        self.startVideoBtn.setStyleSheet("background-color: lightgray; color: black;")
        self.startVideoBtn.setCursor(Qt.WaitCursor)
        
        def run_script():
            recognizer_path = r"recognizer.py"
            if os.path.exists(recognizer_path):
                subprocess.run(["python", recognizer_path])
            else:
                print(f"Error: {recognizer_path} not found!")

            # Call GUI update on the main thread
            QTimer.singleShot(0, self.reset_button)

        thread = threading.Thread(target=run_script)
        thread.start()


        

if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec_()
