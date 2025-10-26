import sys
import json
import subprocess
import threading
import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QGroupBox, QGridLayout
)
from PyQt5.QtCore import Qt, QTimer, QObject, pyqtSignal
import pyqtgraph as pg


# ===========================================================
#   THREAD-SAFE SIGNAL EMITTER
# ===========================================================
class TelemetryEmitter(QObject):
    data_received = pyqtSignal(str, dict)  # source, data


# ===========================================================
#   GCS FRONTEND CLASS
# ===========================================================
class TelemetryGCS(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ground Control Station - Rocket & CanSat")
        self.setGeometry(100, 100, 1400, 800)

        # Latest telemetry
        self.cansat_data = {}
        self.rocket_data = {}

        # Plot data
        self.cansat_alt_data = []
        self.rocket_alt_data = []

        # Thread-safe emitter
        self.emitter = TelemetryEmitter()
        self.emitter.data_received.connect(self.handle_packet)

        # Build GUI
        self.init_ui()

        # Launch telemetry processes
        self.start_listeners()

        # Refresh plots every 1 second
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plots)
        self.timer.start(1000)

    # ---------------------------------------------------
    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # ----- CAN-SAT TELEMETRY -----
        cansat_group = QGroupBox("CanSat Telemetry (433 MHz)")
        cansat_layout = QGridLayout()
        self.c_alt = QLabel("Altitude: -")
        self.c_temp = QLabel("Temperature: -")
        self.c_vel = QLabel("Velocity: -")
        self.c_lat = QLabel("Latitude: -")
        self.c_lon = QLabel("Longitude: -")
        for lbl in [self.c_alt, self.c_temp, self.c_vel, self.c_lat, self.c_lon]:
            lbl.setStyleSheet("font-size: 14px; color: #222; font-weight: bold;")
        cansat_layout.addWidget(self.c_alt, 0, 0)
        cansat_layout.addWidget(self.c_temp, 0, 1)
        cansat_layout.addWidget(self.c_vel, 1, 0)
        cansat_layout.addWidget(self.c_lat, 1, 1)
        cansat_layout.addWidget(self.c_lon, 2, 0)
        cansat_group.setLayout(cansat_layout)

        # ----- ROCKET TELEMETRY -----
        rocket_group = QGroupBox("Rocket Telemetry (915 MHz)")
        rocket_layout = QGridLayout()
        self.r_alt = QLabel("Altitude: -")
        self.r_temp = QLabel("Temperature: -")
        self.r_vel = QLabel("Velocity: -")
        self.r_lat = QLabel("Latitude: -")
        self.r_lon = QLabel("Longitude: -")
        for lbl in [self.r_alt, self.r_temp, self.r_vel, self.r_lat, self.r_lon]:
            lbl.setStyleSheet("font-size: 14px; color: #222; font-weight: bold;")
        rocket_layout.addWidget(self.r_alt, 0, 0)
        rocket_layout.addWidget(self.r_temp, 0, 1)
        rocket_layout.addWidget(self.r_vel, 1, 0)
        rocket_layout.addWidget(self.r_lat, 1, 1)
        rocket_layout.addWidget(self.r_lon, 2, 0)
        rocket_group.setLayout(rocket_layout)

        # ----- Graphs -----
        pg.setConfigOption("background", "w")
        pg.setConfigOption("foreground", "k")
        self.cansat_alt_curve = pg.PlotWidget(title="CanSat Altitude (m)")
        self.cansat_alt_curve.plotItem.showGrid(True, True)
        self.rocket_alt_curve = pg.PlotWidget(title="Rocket Altitude (m)")
        self.rocket_alt_curve.plotItem.showGrid(True, True)

        graphs_layout = QHBoxLayout()
        graphs_layout.addWidget(self.cansat_alt_curve)
        graphs_layout.addWidget(self.rocket_alt_curve)

        # ----- Logs -----
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet(
            "background-color:#fafafa; color:#111; font-family:Consolas; font-size:12px;"
        )

        # Add to main layout
        main_layout.addWidget(cansat_group)
        main_layout.addWidget(rocket_group)
        main_layout.addLayout(graphs_layout)
        main_layout.addWidget(QLabel("System Logs:"))
        main_layout.addWidget(self.log_box)

    # ---------------------------------------------------
    def start_listeners(self):
        # Launch backends
        self.cansat_proc = subprocess.Popen(
            ["./433ff"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=0
        )
        self.rocket_proc = subprocess.Popen(
            ["./915ff"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1
        )

        # Start threads to read stdout safely
        threading.Thread(target=self.read_stream_text, args=("cansat", self.cansat_proc.stdout), daemon=True).start()
        threading.Thread(target=self.read_stream_bytes, args=("rocket", self.rocket_proc.stdout), daemon=True).start()

        # Optional: read stderr for debugging
        threading.Thread(target=self.read_stream_text, args=("cansat_err", self.cansat_proc.stderr), daemon=True).start()
        threading.Thread(target=self.read_stream_bytes, args=("rocket_err", self.rocket_proc.stderr), daemon=True).start()

    # ---------------------------------------------------
    def read_stream_text(self, source, stream):
        """For UTF-8 clean streams like 433"""
        for line in iter(stream.readline, ''):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                self.emitter.data_received.emit(source, data)
            except json.JSONDecodeError:
                continue

    def read_stream_bytes(self, source, stream):
        """For streams with potential invalid UTF-8 (915)"""
        for rawline in iter(stream.readline, b''):
            try:
                line = rawline.decode('utf-8', errors='ignore').strip()
                if not line:
                    continue
                data = json.loads(line)
                self.emitter.data_received.emit(source, data)
            except json.JSONDecodeError:
                continue
            except Exception as e:
                self.log_box.append(f"Error reading {source}: {e}")

    # ---------------------------------------------------
    def handle_packet(self, source, data):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        if source == "cansat":
            self.cansat_data = data
            self.log_box.append(f"[{timestamp}] 🛰️ CANSAT: {data}")
        elif source == "rocket":
            self.rocket_data = data
            self.log_box.append(f"[{timestamp}] 🚀 ROCKET: {data}")

        # Limit log size
        if self.log_box.document().blockCount() > 500:
            self.log_box.clear()

    # ---------------------------------------------------
    def update_plots(self):
        # Update CAN-SAT telemetry
        if self.cansat_data:
            d = self.cansat_data
            self.c_alt.setText(f"Altitude: {d.get('altitude',0):.2f} m")
            self.c_temp.setText(f"Temperature: {d.get('temperature',0):.2f} °C")
            self.c_vel.setText(f"Velocity: {d.get('velocity',0):.2f} m/s")
            self.c_lat.setText(f"Latitude: {d.get('latitude',0):.5f}")
            self.c_lon.setText(f"Longitude: {d.get('longitude',0):.5f}")
            self.cansat_alt_data.append(d.get("altitude", 0))
            self.cansat_alt_curve.plot(list(range(len(self.cansat_alt_data))),
                                       self.cansat_alt_data,
                                       pen=pg.mkPen(color=(0, 100, 0), width=2),
                                       clear=True)

        # Update ROCKET telemetry
        if self.rocket_data:
            d = self.rocket_data
            self.r_alt.setText(f"Altitude: {d.get('altitude',0):.2f} m")
            self.r_temp.setText(f"Temperature: {d.get('temperature',0):.2f} °C")
            self.r_vel.setText(f"Velocity: {d.get('velocity',0):.2f} m/s")
            self.r_lat.setText(f"Latitude: {d.get('latitude',0):.5f}")
            self.r_lon.setText(f"Longitude: {d.get('longitude',0):.5f}")
            self.rocket_alt_data.append(d.get("altitude", 0))
            self.rocket_alt_curve.plot(list(range(len(self.rocket_alt_data))),
                                       self.rocket_alt_data,
                                       pen=pg.mkPen(color=(150, 0, 0), width=2),
                                       clear=True)


# ===========================================================
#   MAIN ENTRY
# ===========================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TelemetryGCS()
    win.show()
    sys.exit(app.exec_())
