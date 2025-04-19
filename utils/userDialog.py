import PIL.ImageShow
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import (QApplication,  QFileDialog, QMessageBox)
from PyQt5.QtCore import QSize
from PyQt5.uic import loadUi
import sys
from db.db import session, Worker
import os
import shutil
from PIL import Image

class UserDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, name=None):
        super().__init__(parent)
        loadUi("ui/userDialog.ui", self)
        
        # Set fixed width and height for the dialog
        self.setFixedSize(QSize(800, 600))  # Adjust these values as needed
        
        self.image_files = []
        self.prepare()
        self.parent = parent

        
        
        self.save_images = []
        self.name = name
        if name:
            self.nameInput.setText(name)
            path = "known_faces/" + name
            for file in os.listdir(path):
                self.save_images.append(os.path.join(path, file))
            self.update_list()

    def prepare(self):
        self.add_images_button.clicked.connect(self.add_images)
        self.delete_image_button.clicked.connect(self.delete_image)
        self.save_button.clicked.connect(self.save)
        self.listWidget.itemDoubleClicked.connect(self.show_image)

    def show_image(self, item):
        name = item.text()
        if name in self.save_images:
            path = name
            try:
                image = Image.open(path)
                image.show()
            except:
                pass

    def add_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Images",
            "",
            "Images (*.png *.xpm *.jpg *.jpeg *.bmp);;All Files (*)"
        )
        if files:
            self.image_files = files
            self.update_list()

    def delete_image(self):
        item = self.listWidget.currentItem()
        if item:
            name = item.text()
            if name in self.image_files:
                self.image_files.remove(name)
            else:
                self.save_images.remove(name)
                os.remove(name)
            self.update_list()

    def update_list(self):
        self.listWidget.clear()
        for path in self.save_images + self.image_files:
            self.listWidget.addItem(path)

    def save(self):
        name = self.nameInput.text().strip()
        if not name:
            QMessageBox.warning(self, "Input Required", "Please enter a name.")
            return

        if self.name and self.name != name:
            # Update existing worker if name has changed
            worker = session.query(Worker).filter(Worker.name == self.name).first()
            worker.name = name
            session.commit()
            os.rename('known_faces/' + self.name, 'known_faces/' + name)
            self.parent.update_list()

        if not self.image_files and self.name == name:
            QMessageBox.warning(self, "No Images", "Please select at least one image.")
            return

        # If name is new, add it to the database
        if not self.name:
            worker = Worker(name=name)
            session.add(worker)
            session.commit()

        folder = "known_faces/" + name
        if not os.path.exists(folder):
            os.makedirs(folder)

        # Save the images
        for file in self.image_files:
            shutil.copy(file, os.path.join(folder, os.path.basename(file)))

        QMessageBox.information(self, "Saved", f"Saved {len(self.image_files)} image(s) for {name}.")

        # Clear the dialog input fields and reset images list
        self.clear_dialog()

        # Update the workers list in the parent (Workers class)
        self.parent.update_list()

        self.accept()

    def clear_dialog(self):
        self.nameInput.clear()  # Clear name input
        self.image_files = []   # Clear added images
        self.save_images = []   # Clear saved images
        self.listWidget.clear()  # Clear the list widget
    
    

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = UserDialog()
    dialog.show()
    sys.exit(app.exec())
