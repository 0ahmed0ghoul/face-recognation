from PyQt5.QtWidgets import QWidget, QHeaderView, QFileDialog, QMessageBox, QTableWidgetItem, QPlainTextEdit, QVBoxLayout, QDialog, QPushButton
from PyQt5.uic import loadUi
from PyQt5.QtCore import QDateTime
import csv
from datetime import datetime, timedelta
from db.db import session ,Worker  # Assuming you have a session and Worker model defined in db.db
class attendence(QWidget):  # Corrected class name
    def __init__(self):
        super().__init__()
        loadUi("ui/attendence.ui", self) 
        self.prepare()
    def prepare(self):
        
        current_datetime = QDateTime.currentDateTime()
        self.dateEditFrom.setMinimumDateTime(current_datetime)
        self.dateEditTo.setMinimumDateTime(current_datetime)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
   # Connect the button to the export function
        self.export_csv_btn.clicked.connect(self.export_table_to_csv)
        self.table.cellDoubleClicked.connect(self.show_worker_logs_dialog) 
        self.update_table()

    def update_table(self):
        from_date = self.dateEditFrom.date().toPyDate()
        to_date = self.dateEditTo.date().toPyDate()

        from_date = datetime.combine(from_date, datetime.min.time())
        to_date = datetime.combine(to_date, datetime.min.time())

        workers = session.query(Worker).all()
        total_days = (to_date - from_date).days + 1

        data = self.get_worker_data(workers, from_date, to_date, total_days)
        self.populate_table(data)

    def get_worker_data(self, workers, from_date, to_date, total_days):
        worker_data = []

        for worker in workers:
            logs_in_range = self.get_logs_in_range(worker, from_date, to_date)
            logs_by_day = self.group_logs_by_day(logs_in_range)

            present_days = len(logs_by_day)
            absent_days = total_days - present_days

            total_duration, total_exits = self.calculate_duration_and_exits(logs_by_day)

            total_duration_hours = total_duration.total_seconds() / 3600

            avg_hours = total_duration / present_days if present_days else timedelta()
            avg_hours_decimal = avg_hours.total_seconds() / 3600 if present_days else 0

            exit_rate = total_exits / present_days if present_days else 0

            worker_data.append({
                "name": worker.name,
                "present_days": present_days,
                "absent_days": absent_days,
                "total_duration": total_duration_hours,
                "avg_hours": avg_hours_decimal,
                "exit_rate": exit_rate
            })

        return worker_data

    def get_logs_in_range(self, worker, from_date, to_date):
        from_date = from_date.date() if isinstance(from_date, datetime) else from_date
        to_date = to_date.date() if isinstance(to_date, datetime) else to_date

        logs_in_range = []

        for log in worker.logs:
            in_dt = log.in_date
            out_dt = log.out_date

            if isinstance(in_dt, int):
                in_dt = datetime.fromtimestamp(in_dt)
            if isinstance(out_dt, int):
                out_dt = datetime.fromtimestamp(out_dt)

            if from_date <= in_dt.date() <= to_date:
                logs_in_range.append((in_dt.date(), in_dt, out_dt))

        return logs_in_range


    def group_logs_by_day(self, logs_in_range):
        logs_by_day = {}
        for day, in_time, out_time in logs_in_range:
            if day not in logs_by_day:
                logs_by_day[day] = []
            logs_by_day[day].append((in_time, out_time))
        return logs_by_day

    def calculate_duration_and_exits(self, logs_by_day):
        total_duration = timedelta()
        total_exits = 0

        for day_logs in logs_by_day.values():
            total_exits += len(day_logs)
            for in_time, out_time in day_logs:
                total_duration += (out_time - in_time)

        return total_duration, total_exits

    def populate_table(self, data):
        self.table.setRowCount(0)

        for row, entry in enumerate(data):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(entry["name"]))
            self.table.setItem(row, 1, QTableWidgetItem(str(entry["present_days"])))
            self.table.setItem(row, 2, QTableWidgetItem(str(entry["absent_days"])))
            self.table.setItem(row, 3, QTableWidgetItem(f"{entry['total_duration']:.2f}"))
            self.table.setItem(row, 4, QTableWidgetItem(f"{entry['avg_hours']:.2f}"))
            self.table.setItem(row, 5, QTableWidgetItem(f"{entry['exit_rate']:.2f}"))

    def show_worker_logs_dialog(self, row, column):
        # Get the worker name from the clicked row
        worker_name = self.table.item(row, 0).text()

        # Get the worker object
        worker = session.query(Worker).filter(Worker.name == worker_name).first()
        
        # Collect logs for the worker
        logs_in_range = self.get_logs_in_range(worker, self.dateEditFrom.date().toPyDate(), self.dateEditTo.date().toPyDate())
        logs_by_day = self.group_logs_by_day(logs_in_range)

        # Create a QDialog to show the logs
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Logs for {worker_name}")
        layout = QVBoxLayout(dialog)

        # Create QPlainTextEdit to display logs
        log_text = QPlainTextEdit(dialog)
        log_text.setReadOnly(True)  # Make it read-only
        log_content = ""

        for day, logs in logs_by_day.items():
            log_content += f"{day.strftime('%d/%m/%Y')}\n"
            for in_time, out_time in logs:
                log_content += f"           in:{in_time.strftime('%H:%M')}   | out:{out_time.strftime('%H:%M')}\n"
            log_content += "\n"
        
        log_text.setPlainText(log_content)
        layout.addWidget(log_text)

        # Add a Close button
        close_button = QPushButton("Close", dialog)
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)

        dialog.setLayout(layout)
        dialog.exec_()

    def export_table_to_csv(self):
        # Open a file dialog to choose where to save
        path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "", "CSV Files (*.csv)")
        if path:
            with open(path, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)

                # Write headers
                headers = []
                for column in range(self.table.columnCount()):
                    header_item = self.table.horizontalHeaderItem(column)
                    headers.append(header_item.text() if header_item else '')
                writer.writerow(headers)

                # Write table rows
                for row in range(self.table.rowCount()):
                    row_data = []
                    for column in range(self.table.columnCount()):
                        item = self.table.item(row, column)
                        row_data.append(item.text() if item else '')
                    writer.writerow(row_data)

            # Show success popup
            QMessageBox.information(self, "Success", "CSV file has been exported successfully!")


    def export_table_to_csv(self):
    # Open file dialog to choose where to save the CSV file
        path, _ = QFileDialog.getSaveFileName(self, "Save CSV File", "", "CSV Files (*.csv)")

        if path:
            try:
                with open(path, mode='w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)

                    # Write the table headers
                    headers = [
                        self.table.horizontalHeaderItem(column).text() if self.table.horizontalHeaderItem(column) else ''
                        for column in range(self.table.columnCount())
                    ]
                    writer.writerow(headers)

                    # Write the table rows
                    for row in range(self.table.rowCount()):
                        row_data = [
                            self.table.item(row, column).text() if self.table.item(row, column) else ''
                            for column in range(self.table.columnCount())
                        ]
                        writer.writerow(row_data)

                # Show success message
                QMessageBox.information(self, "Success", "CSV file has been exported successfully!")
            
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred while exporting:\n{str(e)}")

