from PyQt5.QtWidgets import QWidget, QHeaderView, QPushButton, QTableWidgetItem
from PyQt5.QtGui import QColor
from PyQt5.uic import loadUi
from PyQt5.QtCore import QTimer
import cv2
from db.db import session, Worker, Log
from datetime import datetime, timedelta

class dailyAttendence(QWidget):
    def __init__(self):
        super().__init__()
        loadUi("ui/dailyAttendence.ui", self)
        self.prepare()

        # ⏱️ تحديث الجدول كل 5 ثواني
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_table)
        self.timer.start(5000)  # 5000 ملي ثانية = 5 ثواني

    def prepare(self):
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.update_table()

    def get_attendance_data(self):
        workers = session.query(Worker).all()

        for worker in workers:
            logs_today = []

            for log in worker.logs:
                in_dt = log.in_date
                out_dt = log.out_date

                if isinstance(in_dt, int):
                    in_dt = datetime.fromtimestamp(in_dt)
                if isinstance(out_dt, int):
                    out_dt = datetime.fromtimestamp(out_dt)

                if in_dt.date() == datetime.now().date():
                    logs_today.append((in_dt, out_dt))

            if not logs_today:
                yield {
                    "name": worker.name,
                    "first_in": '/',
                    "last_out": '/',
                    "duration": '/',
                    "late_by": '/'
                }
                continue

            first_in = min(log[0] for log in logs_today)
            last_out = max(log[1] for log in logs_today)

            work_duration = sum((out - inn for inn, out in logs_today), timedelta())
            work_duration = round(work_duration.total_seconds() / 60 / 60, 2)

            expected_start = datetime.combine(datetime.now().date(), datetime.strptime("05:00", "%H:%M").time())
            late_minutes = max(0, int((first_in - expected_start).total_seconds() / 60))

            yield {
                "name": worker.name,
                "first_in": first_in.strftime("%H:%M"),
                "last_out": last_out.strftime("%H:%M"),
                "late_by": str(late_minutes),
                "duration": str(work_duration),
            }

    def update_table(self):
        self.table.setRowCount(0)

        for row, entry in enumerate(self.get_attendance_data()):
            color = QColor(255, 0, 0, 50) if entry["first_in"] == '/' else QColor(0, 128, 0, 100)

            self.table.insertRow(row)
            for col, value in enumerate(entry.values()):
                item = QTableWidgetItem(value)
                item.setBackground(color)
                self.table.setItem(row, col, item)
