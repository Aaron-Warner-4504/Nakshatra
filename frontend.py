# gcs_main_light.py

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTextEdit, QGridLayout, QGroupBox, QListWidget, QListWidgetItem, QStackedWidget
)
from PyQt5.QtGui import QColor, QPalette, QFont, QFontDatabase
from PyQt5.QtCore import Qt, QTimer
import pyqtgraph as pg
import sys
import random
import time
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QTextEdit, QGroupBox, QGridLayout
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
from PyQt5.QtCore import QTimer
import random
import datetime


class CANSATMissionWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: #f5f5f5; color: #333;")
        self.altitude_data = []
        self.speed_data = []
        self.time_data = []

        self.init_ui()
        self.start_dummy_updates()

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Section 1: CANSAT GPS Location
        gps_group = QGroupBox("CANSAT LOCATION")
        gps_group.setStyleSheet("color: #333; font-weight: bold;")
        gps_layout = QGridLayout()

        self.lat_label = QLabel("Latitude: 19.0760")
        self.lon_label = QLabel("Longitude: 72.8777")
        self.speed_label = QLabel("Speed: 2.5 m/s")
        self.gps_lock_label = QLabel("GPS Lock: Locked")

        for lbl in [self.lat_label, self.lon_label, self.speed_label, self.gps_lock_label]:
            lbl.setStyleSheet("font-size: 14px; color: #555;")

        gps_layout.addWidget(self.lat_label, 0, 0)
        gps_layout.addWidget(self.lon_label, 0, 1)
        gps_layout.addWidget(self.speed_label, 1, 0)
        gps_layout.addWidget(self.gps_lock_label, 1, 1)
        gps_group.setLayout(gps_layout)

        # Section 2: Primary Telemetry (Altitude, Speed, Temp)
        telemetry_group = QGroupBox("PRIMARY TELEMETRY")
        telemetry_group.setStyleSheet("color: #333; font-weight: bold;")
        telemetry_layout = QGridLayout()

        self.altitude_label = QLabel("Altitude: 100 m")
        self.vert_speed_label = QLabel("Vertical Speed: 1.2 m/s")
        self.temp_label = QLabel("Temperature: 25 °C")

        for lbl in [self.altitude_label, self.vert_speed_label, self.temp_label]:
            lbl.setStyleSheet("font-size: 14px; color: #555;")

        telemetry_layout.addWidget(self.altitude_label, 0, 0)
        telemetry_layout.addWidget(self.vert_speed_label, 0, 1)
        telemetry_layout.addWidget(self.temp_label, 1, 0)
        telemetry_group.setLayout(telemetry_layout)

        # Section 3: Live Graphs
        graph_layout = QHBoxLayout()

        # Configure PyQtGraph for light theme
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')

        self.altitude_plot = PlotWidget()
        self.altitude_plot.setTitle("Altitude vs Time", color="k")
        self.altitude_plot.setLabel('left', 'Altitude (m)', color="k")
        self.altitude_plot.setLabel('bottom', 'Time (s)', color="k")
        self.altitude_curve = self.altitude_plot.plot(pen=pg.mkPen('g', width=2))

        self.speed_plot = PlotWidget()
        self.speed_plot.setTitle("Speed vs Time", color="k")
        self.speed_plot.setLabel('left', 'Speed (m/s)', color="k")
        self.speed_plot.setLabel('bottom', 'Time (s)', color="k")
        self.speed_curve = self.speed_plot.plot(pen=pg.mkPen('r', width=2))

        graph_layout.addWidget(self.altitude_plot)
        graph_layout.addWidget(self.speed_plot)

        # Section 4: Telemetry Logs
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet("background-color: #fff; color: #333; font-family: Consolas; font-size: 12px; border: 1px solid #ccc;")
        self.log_box.setPlaceholderText("System logs will appear here...")

        # Add everything to the main layout
        main_layout.addWidget(gps_group)
        main_layout.addWidget(telemetry_group)
        main_layout.addLayout(graph_layout)
        main_layout.addWidget(QLabel("SYSTEM LOGS:"))
        main_layout.addWidget(self.log_box)

        self.setLayout(main_layout)

    def start_dummy_updates(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_dummy_data)
        self.timer.start(1000)  # update every second

    def update_dummy_data(self):
        # Update telemetry values
        altitude = random.randint(95, 105)
        speed = round(random.uniform(1.0, 3.0), 2)
        temperature = random.randint(22, 28)

        self.altitude_label.setText(f"Altitude: {altitude} m")
        self.vert_speed_label.setText(f"Vertical Speed: {speed} m/s")
        self.temp_label.setText(f"Temperature: {temperature} °C")

        # Update GPS values
        lat = round(19.076 + random.uniform(-0.0005, 0.0005), 6)
        lon = round(72.877 + random.uniform(-0.0005, 0.0005), 6)
        self.lat_label.setText(f"Latitude: {lat}")
        self.lon_label.setText(f"Longitude: {lon}")
        self.speed_label.setText(f"Speed: {speed} m/s")

        # Update graph
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.time_data.append(timestamp)
        self.altitude_data.append(altitude)
        self.speed_data.append(speed)

        self.altitude_curve.setData(list(range(len(self.altitude_data))), self.altitude_data)
        self.speed_curve.setData(list(range(len(self.speed_data))), self.speed_data)

        # Update logs
        log_type = random.choice(["[INFO]", "[GPS]", "[SENSOR]", "[FAILURE]"])
        if log_type == "[FAILURE]":
            msg = f"{log_type} Sensor 2 failed to initialize"
        else:
            msg = f"{log_type} Altitude: {altitude}, Speed: {speed}, Temp: {temperature}"

        now = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_box.append(f"{now} {msg}")



class TelemetrySimulator:
    """Simulates telemetry data and potential failures."""
    def __init__(self):
        self.time = 0

    def generate_data(self):
        self.time += 1
        return {
            'time': self.time,
            'altitude': random.uniform(100, 300),
            'velocity': random.uniform(20, 60),
            'temperature': random.uniform(25, 45),
            'pressure': random.uniform(980, 1020),
            'status': random.choices(["OK", "WARN", "FAIL"], weights=[0.7, 0.2, 0.1])[0],
            'failed_sensor': random.choice([None, "Altitude", "Velocity", "Temperature", "Pressure", None])
        }


class DataWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.simulator = TelemetrySimulator()
        self._init_ui()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(1000)

    def _init_ui(self):
        self.layout = QVBoxLayout(self)
        self.value_labels = {}
        self.altitude_data = []
        self.velocity_data = []
        self.temp_data = []
        self.pressure_data = []

        self._create_cards()
        self._create_graphs_and_logs()

    def _create_cards(self):
        card_layout = QHBoxLayout()
        for label in ["Altitude", "Velocity", "Temperature", "Pressure"]:
            frame = QFrame()
            frame.setStyleSheet("background-color: #fff; border: 1px solid #ddd; border-radius: 12px; padding: 20px;")
            vbox = QVBoxLayout(frame)
            lbl = QLabel(f"{label}\n0.00")
            lbl.setStyleSheet("color: #333; font-size: 18px;")
            self.value_labels[label] = lbl
            vbox.addWidget(lbl)
            card_layout.addWidget(frame)
        self.layout.addLayout(card_layout)

        # Add GPS cards section
        gps_layout = QHBoxLayout()
        
        # Latitude card
        lat_frame = QFrame()
        lat_frame.setStyleSheet("background-color: #fff; border: 1px solid #ddd; border-radius: 12px; padding: 20px;")
        lat_vbox = QVBoxLayout(lat_frame)
        self.lat_label = QLabel("Latitude\n19.0760°")
        self.lat_label.setStyleSheet("color: #333; font-size: 18px;")
        lat_vbox.addWidget(self.lat_label)
        
        # Longitude card
        lon_frame = QFrame()
        lon_frame.setStyleSheet("background-color: #fff; border: 1px solid #ddd; border-radius: 12px; padding: 20px;")
        lon_vbox = QVBoxLayout(lon_frame)
        self.lon_label = QLabel("Longitude\n72.8777°")
        self.lon_label.setStyleSheet("color: #333; font-size: 18px;")
        lon_vbox.addWidget(self.lon_label)
        
        # GPS Status card
        gps_status_frame = QFrame()
        gps_status_frame.setStyleSheet("background-color: #fff; border: 1px solid #ddd; border-radius: 12px; padding: 20px;")
        gps_status_vbox = QVBoxLayout(gps_status_frame)
        self.gps_status_label = QLabel("GPS Status\nLOCKED")
        self.gps_status_label.setStyleSheet("color: #333; font-size: 18px;")
        gps_status_vbox.addWidget(self.gps_status_label)
        
        gps_layout.addWidget(lat_frame)
        gps_layout.addWidget(lon_frame)
        gps_layout.addWidget(gps_status_frame)
        gps_layout.addStretch()  # Add stretch to push GPS cards to the left
        
        self.layout.addLayout(gps_layout)

    def _create_graphs_and_logs(self):
        content_layout = QHBoxLayout()
        graph_grid = QGridLayout()

        # Configure PyQtGraph for light theme
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')

        self.alt_plot = self._create_plot("Altitude (m)", "Time (s)")
        self.vel_plot = self._create_plot("Velocity (m/s)", "Time (s)")
        self.temp_plot = self._create_plot("Temperature (°C)", "Time (s)")
        self.pres_plot = self._create_plot("Pressure (Pa)", "Time (s)")

        self.alt_curve = self.alt_plot.plot(pen=pg.mkPen('g', width=3))
        self.vel_curve = self.vel_plot.plot(pen=pg.mkPen('b', width=3))
        self.temp_curve = self.temp_plot.plot(pen=pg.mkPen('r', width=3))
        self.pres_curve = self.pres_plot.plot(pen=pg.mkPen('#FF8C00', width=3))

        graph_grid.addWidget(self.alt_plot, 0, 0)
        graph_grid.addWidget(self.vel_plot, 0, 1)
        graph_grid.addWidget(self.temp_plot, 1, 0)
        graph_grid.addWidget(self.pres_plot, 1, 1)

        graph_container = QWidget()
        graph_container.setLayout(graph_grid)
        content_layout.addWidget(graph_container, 3)

        # Logs
        log_container = QWidget()
        log_layout = QVBoxLayout()

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("background-color: #fff; color: #333; font-family: Consolas; padding: 10px; border: 1px solid #ccc;")

        log_layout.addWidget(QLabel("Telemetry Logs:", self))
        log_layout.addWidget(self.log_area)
        log_container.setLayout(log_layout)

        content_layout.addWidget(log_container, 1)
        self.layout.addLayout(content_layout)

    def _create_plot(self, y_label, x_label):
        plot = pg.PlotWidget()
        plot.setBackground("w")
        plot.setLabel("left", y_label, color="k")
        plot.setLabel("bottom", x_label, color="k")
        plot.showGrid(x=True, y=True)
        return plot

    def update_data(self):
        data = self.simulator.generate_data()

        self.altitude_data.append(data['altitude'])
        self.velocity_data.append(data['velocity'])
        self.temp_data.append(data['temperature'])
        self.pressure_data.append(data['pressure'])

        self.alt_curve.setData(range(len(self.altitude_data)), self.altitude_data)
        self.vel_curve.setData(range(len(self.velocity_data)), self.velocity_data)
        self.temp_curve.setData(range(len(self.temp_data)), self.temp_data)
        self.pres_curve.setData(range(len(self.pressure_data)), self.pressure_data)

        self.value_labels["Altitude"].setText(f"Altitude\n{data['altitude']:.2f}")
        self.value_labels["Velocity"].setText(f"Velocity\n{data['velocity']:.2f}")
        self.value_labels["Temperature"].setText(f"Temperature\n{data['temperature']:.2f}")
        self.value_labels["Pressure"].setText(f"Pressure\n{data['pressure']:.2f}")

        # Update GPS data
        lat = round(19.076 + random.uniform(-0.0005, 0.0005), 6)
        lon = round(72.877 + random.uniform(-0.0005, 0.0005), 6)
        gps_status = random.choice(["LOCKED", "LOCKED", "LOCKED", "SEARCHING"])  # Mostly locked
        
        self.lat_label.setText(f"Latitude\n{lat}°")
        self.lon_label.setText(f"Longitude\n{lon}°")
        self.gps_status_label.setText(f"GPS Status\n{gps_status}")
        
        # Change GPS status color based on status
        if gps_status == "LOCKED":
            self.gps_status_label.setStyleSheet("color: green; font-size: 18px;")
        else:
            self.gps_status_label.setStyleSheet("color: orange; font-size: 18px;")

        self._log_data(data)

    def _log_data(self, data):
        log = f"[{data['time']}s] Temp: {data['temperature']:.1f}°C | Alt: {data['altitude']:.1f} m | Vel: {data['velocity']:.1f} m/s | Pres: {data['pressure']:.1f} Pa"
        status_color = {
            "OK": "#0a0",
            "WARN": "orange",
            "FAIL": "red"
        }
        self.log_area.append(f"<span style='color:{status_color[data['status']]}'>{data['status']}: {log}</span>")

        if data['failed_sensor']:
            self.log_area.append(f"<span style='color:red;'>[ERROR] {data['failed_sensor']} Sensor Failure!</span>")


class PreflightCheckWindow(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.status_labels = {}

        layout.addWidget(QLabel("Preflight System Check", self))
        self.modules = ["IMU", "GPS", "Barometer", "Telemetry Link", "SD Card", "Battery Monitor"]

        for module in self.modules:
            hbox = QHBoxLayout()
            label = QLabel(module)
            label.setStyleSheet("color: #333;")
            status = QLabel(" Not Checked")
            status.setStyleSheet("color: orange;")
            hbox.addWidget(label)
            hbox.addStretch()
            hbox.addWidget(status)
            layout.addLayout(hbox)
            self.status_labels[module] = status

        check_btn = QPushButton("Run Checks")
        check_btn.clicked.connect(self.run_checks)
        check_btn.setStyleSheet("background-color: #007acc; color: white; padding: 10px; border: none; border-radius: 5px;")
        layout.addWidget(check_btn)

    def run_checks(self):
        for mod in self.modules:
            passed = random.choice([True, True, False])
            self.status_labels[mod].setText(" OK" if passed else " FAIL")
            self.status_labels[mod].setStyleSheet("color: green;" if passed else "color: red;")


class GCSWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GCS - Nakshatra")
        self.setGeometry(100, 100, 1400, 800)
        self.setStyleSheet("background-color: #f5f5f5; color: #333;")

        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(245, 245, 245))
        palette.setColor(QPalette.WindowText, QColor(51, 51, 51))
        self.setPalette(palette)

        central_widget = QWidget()
        layout = QHBoxLayout(central_widget)
        self.setCentralWidget(central_widget)

        sidebar = QVBoxLayout()
        sidebar.setAlignment(Qt.AlignTop)
        self.stack = QStackedWidget()

        self.preflight_page = PreflightCheckWindow()
        self.data_page = DataWindow()
        self.cansat_page = CANSATMissionWindow()

        self.stack.addWidget(self.preflight_page)
        self.stack.addWidget(self.data_page)
        self.stack.addWidget(self.cansat_page)

        for name, page in [("Preflight Checks", self.preflight_page), ("Live Data", self.data_page)]:
            btn = QPushButton(name)
            btn.clicked.connect(lambda _, p=page: self.stack.setCurrentWidget(p))
            btn.setStyleSheet("background-color: #007acc; color: white; padding: 12px; border: none; border-radius: 8px; margin: 2px;")
            sidebar.addWidget(btn)

        sidebar_frame = QFrame()
        sidebar_frame.setLayout(sidebar)
        sidebar_frame.setStyleSheet("background-color: #e0e0e0; min-width: 200px; border-right: 1px solid #ccc;")
        
        cansat_btn = QPushButton("CANSAT Mission")
        cansat_btn.setStyleSheet("background-color: #007acc; color: white; padding: 12px; border: none; border-radius: 8px; margin: 2px;")
        cansat_btn.clicked.connect(lambda: self.stack.setCurrentWidget(self.cansat_page))
        sidebar.addWidget(cansat_btn)

        layout.addWidget(sidebar_frame)
        layout.addWidget(self.stack)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Add EUDC font support
    font_db = QFontDatabase()
    font_id = font_db.addApplicationFont("EUDC.TTE")
    if font_id != -1:
        font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        app_font = QFont(font_family, 9)  # 9 is the default font size
        app.setFont(app_font)
    
    win = GCSWindow()
    win.show()
    sys.exit(app.exec_())