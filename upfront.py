# gcs_full_integration.py
import sys
import json
import subprocess
import threading
import datetime
import random
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTextEdit, QGridLayout, QGroupBox, QListWidget, QListWidgetItem, QStackedWidget
)
from PyQt5.QtGui import QColor, QPalette, QFont, QFontDatabase
from PyQt5.QtCore import Qt, QTimer, QObject, pyqtSignal
import pyqtgraph as pg

# -------------------------
# Thread-safe emitter
# -------------------------
class TelemetryEmitter(QObject):
    data_received = pyqtSignal(str, dict)  # source, data

# -------------------------
# Preflight page (unchanged)
# -------------------------
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

# -------------------------
# CANSAT Mission Page (demo style)
# -------------------------
class CANSATMissionWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: #f5f5f5; color: #333;")
        self.altitude_data = []
        self.speed_data = []
        self.time_data = []

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Section 1: CANSAT GPS Location
        gps_group = QGroupBox("CANSAT LOCATION")
        gps_group.setStyleSheet("color: #333; font-weight: bold;")
        gps_layout = QGridLayout()

        self.lat_label = QLabel("Latitude: -")
        self.lon_label = QLabel("Longitude: -")
        self.speed_label = QLabel("Speed: - m/s")
        self.gps_lock_label = QLabel("GPS Lock: Unknown")

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

        self.altitude_label = QLabel("Altitude: - m")
        self.vert_speed_label = QLabel("Vertical Speed: - m/s")
        self.temp_label = QLabel("Temperature: - °C")

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

        self.altitude_plot = pg.PlotWidget()
        self.altitude_plot.setTitle("Altitude vs Time", color="k")
        self.altitude_plot.setLabel('left', 'Altitude (m)', color="k")
        self.altitude_plot.setLabel('bottom', 'Time (s)', color="k")
        self.altitude_curve = self.altitude_plot.plot(pen=pg.mkPen('g', width=2))

        self.speed_plot = pg.PlotWidget()
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
        self.log_box.setPlaceholderText("Mission logs will appear here...")

        main_layout.addWidget(gps_group)
        main_layout.addWidget(telemetry_group)
        main_layout.addLayout(graph_layout)
        main_layout.addWidget(QLabel("MISSION LOGS:"))
        main_layout.addWidget(self.log_box)

        self.setLayout(main_layout)

    def update_from_cansat(self, data):
        """Called from main thread (via TelemetryEmitter)"""
        alt = data.get("altitude")
        spd = data.get("velocity") or data.get("speed")
        lat = data.get("latitude")
        lon = data.get("longitude")
        temp = data.get("temperature")

        if alt is not None:
            self.altitude_label.setText(f"Altitude: {alt:.2f} m")
            self.altitude_data.append(alt)
            self.altitude_curve.setData(list(range(len(self.altitude_data))), self.altitude_data)

        if spd is not None:
            self.vert_speed_label.setText(f"Vertical Speed: {spd:.2f} m/s")
            self.speed_data.append(spd)
            self.speed_curve.setData(list(range(len(self.speed_data))), self.speed_data)
            self.speed_label.setText(f"Speed: {spd:.2f} m/s")

        if temp is not None:
            self.temp_label.setText(f"Temperature: {temp:.2f} °C")

        if lat is not None:
            self.lat_label.setText(f"Latitude: {lat:.6f}")
        if lon is not None:
            self.lon_label.setText(f"Longitude: {lon:.6f}")

        # Update logs
        now = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_box.append(f"{now} [CANSAT] Alt:{alt} Spd:{spd} Temp:{temp}")


# -------------------------
# Data Page (cards + graphs + logs) - adapted to accept real telemetry
# -------------------------
class DataWindow(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()

        # keep rolling data arrays for graphs
        self.altitude_data = []
        self.velocity_data = []
        self.temp_data = []
        self.pressure_data = []

    def _init_ui(self):
        self.layout = QVBoxLayout(self)
        self.value_labels = {}

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

        # GPS cards
        gps_layout = QHBoxLayout()

        lat_frame = QFrame()
        lat_frame.setStyleSheet("background-color: #fff; border: 1px solid #ddd; border-radius: 12px; padding: 20px;")
        lat_vbox = QVBoxLayout(lat_frame)
        self.lat_label = QLabel("Latitude\n 0°")
        self.lat_label.setStyleSheet("color: #333; font-size: 18px;")
        lat_vbox.addWidget(self.lat_label)

        lon_frame = QFrame()
        lon_frame.setStyleSheet("background-color: #fff; border: 1px solid #ddd; border-radius: 12px; padding: 20px;")
        lon_vbox = QVBoxLayout(lon_frame)
        self.lon_label = QLabel("Longitude\n7 0°")
        self.lon_label.setStyleSheet("color: #333; font-size: 18px;")
        lon_vbox.addWidget(self.lon_label)

        gps_status_frame = QFrame()
        gps_status_frame.setStyleSheet("background-color: #fff; border: 1px solid #ddd; border-radius: 12px; padding: 20px;")
        gps_status_vbox = QVBoxLayout(gps_status_frame)
        self.gps_status_label = QLabel("GPS Status\nUNKNOWN")
        self.gps_status_label.setStyleSheet("color: #333; font-size: 18px;")
        gps_status_vbox.addWidget(self.gps_status_label)

        gps_layout.addWidget(lat_frame)
        gps_layout.addWidget(lon_frame)
        gps_layout.addWidget(gps_status_frame)
        gps_layout.addStretch()
        self.layout.addLayout(gps_layout)

    def _create_graphs_and_logs(self):
        content_layout = QHBoxLayout()
        graph_grid = QGridLayout()

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

    # Methods to be called from TelemetryGCS.handle_packet
    def apply_cansat_data(self, data):
        # Update cards and graphs with CANSAT data
        alt = data.get("altitude")
        vel = data.get("velocity") or data.get("speed")
        temp = data.get("temperature")
        pres = data.get("pressure")
        lat = data.get("latitude")
        lon = data.get("longitude")
        status = data.get("status")

        if alt is not None:
            self.altitude_data.append(alt)
            self.alt_curve.setData(range(len(self.altitude_data)), self.altitude_data)
            self.value_labels["Altitude"].setText(f"Altitude\n{alt:.2f}")

        if vel is not None:
            self.velocity_data.append(vel)
            self.vel_curve.setData(range(len(self.velocity_data)), self.velocity_data)
            self.value_labels["Velocity"].setText(f"Velocity\n{vel:.2f}")

        if temp is not None:
            self.temp_data.append(temp)
            self.temp_curve.setData(range(len(self.temp_data)), self.temp_data)
            self.value_labels["Temperature"].setText(f"Temperature\n{temp:.2f}")

        if pres is not None:
            self.pressure_data.append(pres)
            self.pres_curve.setData(range(len(self.pressure_data)), self.pressure_data)
            self.value_labels["Pressure"].setText(f"Pressure\n{pres:.2f}")

        if lat is not None:
            self.lat_label.setText(f"Latitude\n{lat:.6f}")
        if lon is not None:
            self.lon_label.setText(f"Longitude\n{lon:.6f}")
        if status:
            color = "green" if status == "OK" else ("orange" if status == "WARN" else "red")
            self.gps_status_label.setText(f"GPS Status\n{status}")
            self.gps_status_label.setStyleSheet(f"color: {color}; font-size: 18px;")

        # Log it
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_area.append(f"{ts} [CANSAT] Alt:{alt} Vel:{vel} Temp:{temp} Pres:{pres}")

    def apply_rocket_data(self, data):
        # Same as above but for rocket data
        alt = data.get("altitude")
        vel = data.get("velocity") or data.get("speed")
        temp = data.get("temperature")
        pres = data.get("pressure")
        lat = data.get("latitude")
        lon = data.get("longitude")
        status = data.get("status")

        if alt is not None:
            self.altitude_data.append(alt)
            self.alt_curve.setData(range(len(self.altitude_data)), self.altitude_data)
            self.value_labels["Altitude"].setText(f"Altitude\n{alt:.2f}")

        if vel is not None:
            self.velocity_data.append(vel)
            self.vel_curve.setData(range(len(self.velocity_data)), self.velocity_data)
            self.value_labels["Velocity"].setText(f"Velocity\n{vel:.2f}")

        if temp is not None:
            self.temp_data.append(temp)
            self.temp_curve.setData(range(len(self.temp_data)), self.temp_data)
            self.value_labels["Temperature"].setText(f"Temperature\n{temp:.2f}")

        if pres is not None:
            self.pressure_data.append(pres)
            self.pres_curve.setData(range(len(self.pressure_data)), self.pressure_data)
            self.value_labels["Pressure"].setText(f"Pressure\n{pres:.2f}")

        if lat is not None:
            self.lat_label.setText(f"Latitude\n{lat:.6f}")
        if lon is not None:
            self.lon_label.setText(f"Longitude\n{lon:.6f}")

        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_area.append(f"{ts} [ROCKET] Alt:{alt} Vel:{vel} Temp:{temp} Pres:{pres}")

# -------------------------
# Main Window that wires backends -> pages
# -------------------------
class TelemetryGCS(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GCS - Nakshatra (Integrated)")
        self.setGeometry(100, 100, 1400, 800)
        self.setStyleSheet("background-color: #f5f5f5; color: #333;")

        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(245, 245, 245))
        palette.setColor(QPalette.WindowText, QColor(51, 51, 51))
        self.setPalette(palette)

        # Telemetry holders
        self.cansat_data = {}
        self.rocket_data = {}

        # Plot arrays
        self.cansat_alt_data = []
        self.rocket_alt_data = []

        # Thread-safe emitter
        self.emitter = TelemetryEmitter()
        self.emitter.data_received.connect(self.handle_packet)

        # Build UI pages
        central_widget = QWidget()
        layout = QHBoxLayout(central_widget)
        self.setCentralWidget(central_widget)

        sidebar = QVBoxLayout()
        sidebar.setAlignment(Qt.AlignTop)
        self.stack = QStackedWidget()

        # Pages
        self.preflight_page = PreflightCheckWindow()
        self.data_page = DataWindow()
        self.cansat_page = CANSATMissionWindow()

        self.stack.addWidget(self.preflight_page)
        self.stack.addWidget(self.data_page)
        self.stack.addWidget(self.cansat_page)

        # Sidebar buttons
        for name, page in [("Preflight Checks", self.preflight_page), ("Live Data", self.data_page)]:
            btn = QPushButton(name)
            btn.clicked.connect(lambda _, p=page: self.stack.setCurrentWidget(p))
            btn.setStyleSheet("background-color: #007acc; color: white; padding: 12px; border: none; border-radius: 8px; margin: 2px;")
            sidebar.addWidget(btn)

        cansat_btn = QPushButton("CANSAT Mission")
        cansat_btn.setStyleSheet("background-color: #007acc; color: white; padding: 12px; border: none; border-radius: 8px; margin: 2px;")
        cansat_btn.clicked.connect(lambda: self.stack.setCurrentWidget(self.cansat_page))
        sidebar.addWidget(cansat_btn)

        sidebar_frame = QFrame()
        sidebar_frame.setLayout(sidebar)
        sidebar_frame.setStyleSheet("background-color: #e0e0e0; min-width: 200px; border-right: 1px solid #ccc;")

        layout.addWidget(sidebar_frame)
        layout.addWidget(self.stack)

        # Central log area at main window level
        self.global_log = QTextEdit()
        self.global_log.setReadOnly(True)
        self.global_log.setFixedHeight(120)
        self.global_log.setStyleSheet("background-color:#fff; color:#111; font-family:Consolas; font-size:12px; padding:8px; border:1px solid #ccc;")
        layout.addWidget(self.global_log)

        # Start backends/listeners
        self.start_listeners()

        # Timer for periodic UI housekeeping (optional)
        self.housekeeping_timer = QTimer()
        self.housekeeping_timer.timeout.connect(self.housekeeping)
        self.housekeeping_timer.start(1000)

    def housekeeping(self):
        # Resize log to keep memory in check
        if self.global_log.document().blockCount() > 2000:
            self.global_log.clear()

    # -----------------------------
    # Backend launch & reading
    # -----------------------------
    def start_listeners(self):
        try:
            self.cansat_proc = subprocess.Popen(
                ["./433ff"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1
            )
        except Exception as e:
            self.global_log.append(f"[ERROR] launching ./433ff: {e}")
            self.cansat_proc = None

        try:
            # rocket process might output raw bytes; keep it as bytes mode
            self.rocket_proc = subprocess.Popen(
                ["./915ff"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0
            )
        except Exception as e:
            self.global_log.append(f"[ERROR] launching ./915ff: {e}")
            self.rocket_proc = None

        # Start threads to read streams
        if self.cansat_proc and self.cansat_proc.stdout:
            threading.Thread(target=self.read_stream_text, args=("cansat", self.cansat_proc.stdout), daemon=True).start()
        if self.cansat_proc and self.cansat_proc.stderr:
            threading.Thread(target=self.read_stream_text, args=("cansat_err", self.cansat_proc.stderr), daemon=True).start()

        if self.rocket_proc and self.rocket_proc.stdout:
            threading.Thread(target=self.read_stream_bytes, args=("rocket", self.rocket_proc.stdout), daemon=True).start()
        if self.rocket_proc and self.rocket_proc.stderr:
            threading.Thread(target=self.read_stream_bytes, args=("rocket_err", self.rocket_proc.stderr), daemon=True).start()

    def read_stream_text(self, source, stream):
        """Read a text stream line by line (text mode)."""
        for line in iter(stream.readline, ''):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                # emit to UI thread
                self.emitter.data_received.emit(source, data)
            except json.JSONDecodeError:
                # if it's not JSON, still log raw
                ts = datetime.datetime.now().strftime("%H:%M:%S")
                self.global_log.append(f"{ts} [RAW-{source}] {line}")

    def read_stream_bytes(self, source, stream):
        """Read a byte stream and decode safely line by line."""
        # In Python, iter(stream.readline, b'') returns bytes on each read
        for rawline in iter(stream.readline, b''):
            try:
                line = rawline.decode('utf-8', errors='ignore').strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    self.emitter.data_received.emit(source, data)
                except json.JSONDecodeError:
                    ts = datetime.datetime.now().strftime("%H:%M:%S")
                    self.global_log.append(f"{ts} [RAW-{source}] {line}")
            except Exception as e:
                ts = datetime.datetime.now().strftime("%H:%M:%S")
                self.global_log.append(f"{ts} Error decoding {source} line: {e}")

    # -----------------------------
    # Handle incoming packets on UI thread
    # -----------------------------
    def handle_packet(self, source, data):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        # Normalize names for easier handling
        key = source.lower()
        if key.startswith("cansat"):
            self.cansat_data = data
            self.global_log.append(f"[{timestamp}] 🛰️ CANSAT: {data}")
            # Update pages that care
            try:
                self.data_page.apply_cansat_data(data)
            except Exception as e:
                self.global_log.append(f"[ERROR] updating data_page with cansat: {e}")
            try:
                self.cansat_page.update_from_cansat(data)
            except Exception as e:
                self.global_log.append(f"[ERROR] updating cansat_page: {e}")

        elif key.startswith("rocket"):
            self.rocket_data = data
            self.global_log.append(f"[{timestamp}] 🚀 ROCKET: {data}")
            # Update Data page with rocket data as well (merge/append)
            try:
                self.data_page.apply_rocket_data(data)
            except Exception as e:
                self.global_log.append(f"[ERROR] updating data_page with rocket: {e}")

        else:
            # generic
            self.global_log.append(f"[{timestamp}] {source}: {data}")

        # Keep global log size bounded
        if self.global_log.document().blockCount() > 4000:
            self.global_log.clear()

# -------------------------
# MAIN
# -------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Optional: try to load a custom font (from original demo)
    font_db = QFontDatabase()
    try:
        font_id = font_db.addApplicationFont("EUDC.TTE")
        if font_id != -1:
            font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
            app_font = QFont(font_family, 9)
            app.setFont(app_font)
    except Exception:
        pass

    # Ensure pyqtgraph uses light theme
    pg.setConfigOption('background', 'w')
    pg.setConfigOption('foreground', 'k')

    win = TelemetryGCS()
    win.show()
    sys.exit(app.exec_())
