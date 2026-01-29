import sys, cv2, numpy as np, os, time
from datetime import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QLineEdit, 
    QMessageBox, QTabWidget, QGroupBox, QInputDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap

from database import DatabaseManager
from plate_detector import PlateDetector
import warnings
warnings.filterwarnings("ignore")

ENTRY_camera='http://10.35.201.160:8080/video' #'http://192.168.1.10:8080/video'
EXIT_camera='http://10.35.201.160:8080/video'

class CameraThread(QThread):
    frame_signal = pyqtSignal(np.ndarray)
    plate_signal = pyqtSignal(str, float, np.ndarray)
    
    def __init__(self, source, detector, direction):
        super().__init__()
        self.source = source
        self.detector = detector
        self.direction = direction
        self.running = True
        self.skip_frames = 10
    
    def run(self):
        cap = cv2.VideoCapture(self.source)
        if not cap.isOpened():
            return
        
        frame_counter = 0
        while self.running:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.resize(frame, (640, 480))
            self.frame_signal.emit(frame)

            if self.skip_frames == -1 or frame_counter <= self.skip_frames:
                if self.skip_frames != -1:
                    frame_counter += 1
                continue
            
            frame_counter = 0
            
            result = self.detector.detect(frame)
            if result:
                self.plate_signal.emit(result[0], result[1], frame.copy())
                self.skip_frames = -1
        
        cap.release()
    
    def stop(self):
        self.running = False
        self.wait()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Система парковки - Въезд/Выезд")
        self.setGeometry(50, 50, 1800, 1000)
        
        self.db = DatabaseManager()
        self.detector = PlateDetector()
        
        self.entry_req = None
        self.exit_req = None
        
        self.setup_ui()
        
        self.entry_thread = CameraThread(ENTRY_camera, self.detector, "ВЪЕЗД")
        self.entry_thread.frame_signal.connect(self.update_entry_video)
        self.entry_thread.plate_signal.connect(self.on_entry_plate)
        self.entry_thread.start()
        
        self.exit_thread = CameraThread(EXIT_camera, self.detector, "ВЫЕЗД")
        self.exit_thread.frame_signal.connect(self.update_exit_video)
        self.exit_thread.plate_signal.connect(self.on_exit_plate)
        self.exit_thread.start()
    
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout()
        
        video_layout = QHBoxLayout()
        
        entry_group = QGroupBox("ВЪЕЗД")
        entry_layout = QVBoxLayout()
        self.entry_video = QLabel()
        self.entry_video.setStyleSheet("border: 3px solid green; background-color: black;")
        self.entry_video.setMinimumSize(640, 480)
        entry_layout.addWidget(self.entry_video)
        self.entry_status = QLabel("Ожидание...")
        self.entry_status.setStyleSheet("background-color: #e8e8e8; padding: 8px;")
        entry_layout.addWidget(self.entry_status)
        entry_group.setLayout(entry_layout)
        video_layout.addWidget(entry_group)
        
        exit_group = QGroupBox("ВЫЕЗД")
        exit_layout = QVBoxLayout()
        self.exit_video = QLabel()
        self.exit_video.setStyleSheet("border: 3px solid orange; background-color: black;")
        self.exit_video.setMinimumSize(640, 480)
        exit_layout.addWidget(self.exit_video)
        self.exit_status = QLabel("Ожидание...")
        self.exit_status.setStyleSheet("background-color: #e8e8e8; padding: 8px;")
        exit_layout.addWidget(self.exit_status)
        exit_group.setLayout(exit_layout)
        video_layout.addWidget(exit_group)
        
        main_layout.addLayout(video_layout)
        
        bottom_layout = QHBoxLayout()
        
        req_layout = QVBoxLayout()
        req_layout.addWidget(QLabel("ЗАПРОСЫ:"))
        
        req_layout.addWidget(QLabel("Въезд:"))
        self.entry_req_label = QLabel("Нет запроса")
        self.entry_req_label.setStyleSheet("background-color: #c8e6c9; padding: 10px;")
        req_layout.addWidget(self.entry_req_label)
        
        entry_btn_layout = QHBoxLayout()
        
        entry_ok = QPushButton("ПОДТВЕРДИТЬ")
        entry_ok.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        entry_ok.clicked.connect(lambda: self.confirm_entry(False))
        entry_btn_layout.addWidget(entry_ok)
        
        entry_err = QPushButton("ПОДТВЕРДИТЬ С ОШИБКОЙ")
        entry_err.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")
        entry_err.clicked.connect(lambda: self.confirm_entry(True))
        entry_btn_layout.addWidget(entry_err)
        
        entry_rescan = QPushButton("ПЕРЕСКАНИРОВАТЬ")
        entry_rescan.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        entry_rescan.clicked.connect(self.rescan_entry)
        entry_btn_layout.addWidget(entry_rescan)
        
        req_layout.addLayout(entry_btn_layout)
        
        req_layout.addWidget(QLabel("\nВыезд:"))
        self.exit_req_label = QLabel("Нет запроса")
        self.exit_req_label.setStyleSheet("background-color: #ffe0b2; padding: 10px;")
        req_layout.addWidget(self.exit_req_label)
        
        exit_btn_layout = QHBoxLayout()
        
        exit_ok = QPushButton("ПОДТВЕРДИТЬ")
        exit_ok.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        exit_ok.clicked.connect(lambda: self.confirm_exit(False))
        exit_btn_layout.addWidget(exit_ok)
        
        exit_err = QPushButton("ПОДТВЕРДИТЬ С ОШИБКОЙ")
        exit_err.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")
        exit_err.clicked.connect(lambda: self.confirm_exit(True))
        exit_btn_layout.addWidget(exit_err)
        
        exit_rescan = QPushButton("ПЕРЕСКАНИРОВАТЬ")
        exit_rescan.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        exit_rescan.clicked.connect(self.rescan_exit)
        exit_btn_layout.addWidget(exit_rescan)
        
        req_layout.addLayout(exit_btn_layout)
        req_layout.addStretch()
        
        bottom_layout.addLayout(req_layout, 1)

        restart_btn = QPushButton("ПЕРЕЗАПУСТИТЬ КАМЕРЫ")
        restart_btn.setStyleSheet("background-color: #9C27B0; color: white;")
        restart_btn.clicked.connect(self.restart_cameras)
        req_layout.addWidget(restart_btn)
        
        tabs = QTabWidget()
        
        entry_tab = QWidget()
        entry_tab_layout = QVBoxLayout()
        self.entry_table = QTableWidget()
        self.entry_table.setColumnCount(5)
        self.entry_table.setHorizontalHeaderLabels(["Номер", "Время", "Тип", "Фото", "ID"])
        entry_tab_layout.addWidget(self.entry_table)
        refresh_entry_btn = QPushButton("Обновить логи въезда")
        refresh_entry_btn.clicked.connect(self.refresh_entry_logs)
        entry_tab_layout.addWidget(refresh_entry_btn)
        entry_tab.setLayout(entry_tab_layout)
        tabs.addTab(entry_tab, "Логи въезда")
        
        exit_tab = QWidget()
        exit_tab_layout = QVBoxLayout()
        self.exit_table = QTableWidget()
        self.exit_table.setColumnCount(5)
        self.exit_table.setHorizontalHeaderLabels(["Номер", "Время", "Тип", "Фото", "ID"])
        exit_tab_layout.addWidget(self.exit_table)
        refresh_exit_btn = QPushButton("Обновить логи выезда")
        refresh_exit_btn.clicked.connect(self.refresh_exit_logs)
        exit_tab_layout.addWidget(refresh_exit_btn)
        exit_tab.setLayout(exit_tab_layout)
        tabs.addTab(exit_tab, "Логи выезда")
        
        tenant_tab = QWidget()
        tenant_layout = QVBoxLayout()
        add_layout = QHBoxLayout()
        
        self.plate_input = QLineEdit()
        self.plate_input.setPlaceholderText("Номер")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Имя")
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Телефон")
        
        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(self.add_tenant)
        
        add_layout.addWidget(self.plate_input)
        add_layout.addWidget(self.name_input)
        add_layout.addWidget(self.phone_input)
        add_layout.addWidget(add_btn)
        tenant_layout.addLayout(add_layout)
        
        self.tenant_table = QTableWidget()
        self.tenant_table.setColumnCount(3)
        self.tenant_table.setHorizontalHeaderLabels(["Номер", "Имя", "Телефон"])
        tenant_layout.addWidget(self.tenant_table)
        
        refresh_tenant_btn = QPushButton("Обновить список арендаторов")
        refresh_tenant_btn.clicked.connect(self.refresh_tenants)
        tenant_layout.addWidget(refresh_tenant_btn)
        
        tenant_tab.setLayout(tenant_layout)
        tabs.addTab(tenant_tab, "Арендаторы")
        
        bottom_layout.addWidget(tabs, 2)
        main_layout.addLayout(bottom_layout)
        central.setLayout(main_layout)
    
    def display_frame(self, frame, label):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        q_img = QImage(rgb.data, w, h, 3*w, QImage.Format_RGB888)
        label.setPixmap(QPixmap.fromImage(q_img).scaledToWidth(label.width(), Qt.SmoothTransformation))
    
    def update_entry_video(self, frame):
        self.display_frame(frame, self.entry_video)
    
    def update_exit_video(self, frame):
        self.display_frame(frame, self.exit_video)
    
    def on_entry_plate(self, plate, conf, frame):
        if self.entry_req:
            return
        self.entry_req = {'plate': plate, 'frame': frame, 'time': datetime.now()}
        tenant = self.db.get_tenant(plate)
        tenant_info = f"Найден: {tenant['full_name']}" if tenant else "Не в БД"
        time_str = self.entry_req['time'].strftime('%H:%M:%S')
        self.entry_req_label.setText(f"<div style='font-size: 16px; font-weight: bold;'>Номер: <span style='font-size: 20px;'>{plate}</span></div><div>{tenant_info}</div><div>Время: {time_str}</div>")
        self.entry_status.setText(f"Обнаружен: {plate}")
        
    def on_exit_plate(self, plate, conf, frame):
        if self.exit_req:
            return
        self.exit_req = {'plate': plate, 'frame': frame, 'time': datetime.now()}
        tenant = self.db.get_tenant(plate)
        tenant_info = f"Найден: {tenant['full_name']}" if tenant else "Не в БД"
        time_str = self.exit_req['time'].strftime('%H:%M:%S')
        self.exit_req_label.setText(f"<div style='font-size: 16px; font-weight: bold;'>Номер: <span style='font-size: 20px;'>{plate}</span></div><div>{tenant_info}</div><div>Время: {time_str}</div>")
        self.exit_status.setText(f"Обнаружен: {plate}")
    
    def rescan_entry(self):
        self.entry_req = None
        self.entry_req_label.setText("Нет запроса")
        self.entry_status.setText("Ожидание...")
        self.entry_thread.skip_frames = 10
    
    def rescan_exit(self):
        self.exit_req = None
        self.exit_req_label.setText("Нет запроса")
        self.exit_status.setText("Ожидание...")
        self.exit_thread.skip_frames = 10
    
    def confirm_entry(self, has_error):
        if not self.entry_req:
            QMessageBox.warning(self, "Ошибка", "Нет запроса на въезд")
            return
        
        plate = self.entry_req['plate']
        frame = self.entry_req['frame']
        
        photo_path = PlateDetector.save(frame, 'entry', plate)
        conf_type = "ОШИБКА" if has_error else "ОК"
        self.db.add_entry(plate, photo_path, conf_type)
        
        self.entry_req = None
        self.entry_req_label.setText("Нет запроса")
        self.entry_status.setText("Въезд подтвержден")
        self.entry_thread.skip_frames = 10
        self.refresh_entry_logs()
    
    def confirm_exit(self, has_error):
        if not self.exit_req:
            QMessageBox.warning(self, "Ошибка", "Нет запроса на выезд")
            return
        
        plate = self.exit_req['plate']
        frame = self.exit_req['frame']
        
        if not self.db.get_tenant(plate):
            name, ok = QInputDialog.getText(self, "Регистрация", f"Имя для {plate}:")
            if not ok or not name:
                return
            phone, ok = QInputDialog.getText(self, "Регистрация", f"Телефон для {plate}:")
            if not ok or not phone:
                return
            self.db.add_tenant(plate, name, phone)
        
        photo_path = PlateDetector.save(frame, 'exit', plate)
        conf_type = "ОШИБКА" if has_error else "ОК"
        self.db.add_exit(plate, photo_path, conf_type)
        
        self.exit_req = None
        self.exit_req_label.setText("Нет запроса")
        self.exit_status.setText("Выезд подтвержден")
        self.exit_thread.skip_frames = 10
        self.refresh_exit_logs()
        self.refresh_tenants()
    
    def refresh_entry_logs(self):
        logs = self.db.get_entry_logs()
        self.entry_table.setRowCount(len(logs))
        for i, log in enumerate(logs):
            self.entry_table.setItem(i, 0, QTableWidgetItem(str(log['plate'] or '')))
            self.entry_table.setItem(i, 1, QTableWidgetItem(str(log['confirm_time'].strftime('%d.%m.%Y %H:%M:%S') if log['confirm_time'] else '')))
            self.entry_table.setItem(i, 2, QTableWidgetItem(str(log['confirm_type'] or '')))
            self.entry_table.setItem(i, 3, QTableWidgetItem(str(log['photo_path'] or '')))
            self.entry_table.setItem(i, 4, QTableWidgetItem(str(log['id'])))
    
    def refresh_exit_logs(self):
        logs = self.db.get_exit_logs()
        self.exit_table.setRowCount(len(logs))
        for i, log in enumerate(logs):
            self.exit_table.setItem(i, 0, QTableWidgetItem(str(log['plate'] or '')))
            self.exit_table.setItem(i, 1, QTableWidgetItem(str(log['confirm_time'].strftime('%d.%m.%Y %H:%M:%S') if log['confirm_time'] else '')))
            self.exit_table.setItem(i, 2, QTableWidgetItem(str(log['confirm_type'] or '')))
            self.exit_table.setItem(i, 3, QTableWidgetItem(str(log['photo_path'] or '')))
            self.exit_table.setItem(i, 4, QTableWidgetItem(str(log['id'])))
    
    def refresh_tenants(self):
        tenants = self.db.get_all_tenants()
        self.tenant_table.setRowCount(len(tenants))
        for i, t in enumerate(tenants):
            self.tenant_table.setItem(i, 0, QTableWidgetItem(t['plate']))
            self.tenant_table.setItem(i, 1, QTableWidgetItem(t['full_name']))
            self.tenant_table.setItem(i, 2, QTableWidgetItem(t['phone']))
    
    def add_tenant(self):
        plate = self.plate_input.text().strip()
        name = self.name_input.text().strip()
        phone = self.phone_input.text().strip()
        
        if not all([plate, name, phone]):
            QMessageBox.warning(self, "Ошибка", "Заполните все поля")
            return
        
        if self.db.add_tenant(plate, name, phone):
            self.plate_input.clear()
            self.name_input.clear()
            self.phone_input.clear()
            self.refresh_tenants()
        else:
            QMessageBox.warning(self, "Ошибка", f"Не удалось добавить {plate}")
    
    def restart_cameras(self):
        if not self.entry_thread.isRunning():
            self.entry_thread.start()
        if not self.exit_thread.isRunning():
            self.exit_thread.start()

    def closeEvent(self, event):
        self.entry_thread.stop()
        self.exit_thread.stop()
        self.db.close()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()