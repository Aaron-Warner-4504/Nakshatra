// 433f.cpp - Updated backend for CanSat (433 MHz)
// Sends one JSON object per line on stdout and debug/logs on stderr.

#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <string>
#include <ctime>
#include <termios.h>
#include <fcntl.h>
#include <unistd.h>
#include <signal.h>
#include <nlohmann/json.hpp>

using namespace std;
using json = nlohmann::json;

static volatile bool keep_running = true;
static int serial_fd = -1;
static ofstream logFile;

// ===========================================================
//  FUNCTION: sendTelemetry
//  Sends single-line JSON to stdout (frontend reads this)
// ===========================================================
void sendTelemetry(const json &telemetry) {
    try {
        // Ensure telemetry is printed as a single line JSON and flushed immediately
        std::cout << telemetry.dump() << std::endl;
    }
    catch (const std::exception &e) {
        std::cerr << "[" << std::time(nullptr) << "] Telemetry JSON error: " << e.what() << std::endl;
    }
}

// ---------- Configuration ----------
const char* SERIAL_PORT = "/dev/ttyUSB0";  // <--- change if needed
const int BAUDRATE = 57600;               // match your transmitter

// ---------- Utility Functions ----------
vector<string> split(const string &s, char delimiter) {
    vector<string> tokens;
    string token;
    istringstream tokenStream(s);
    while (getline(tokenStream, token, delimiter))
        tokens.push_back(token);
    return tokens;
}

string getCurrentTime() {
    time_t now = time(0);
    char buf[80];
    strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", localtime(&now));
    return string(buf);
}

bool validateFields(const vector<string> &fields) {
    if (fields.size() < 15) {  // expecting 15 fields
        cerr << "[" << getCurrentTime() << "] Warning: Incomplete packet (" << fields.size() << " fields)" << endl;
        return false;
    }
    return true;
}

// Safe conversion helpers
float safe_stof(const string &s, float def = 0.0f) {
    try {
        return stof(s);
    } catch (...) { return def; }
}
int safe_stoi(const string &s, int def = 0) {
    try {
        return stoi(s);
    } catch (...) { return def; }
}

// ---------- Telemetry Processor ----------
void processLine(const string &rawline) {
    // Normalize line endings & trim spaces
    string line = rawline;
    // remove possible '\r' characters
    line.erase(remove(line.begin(), line.end(), '\r'), line.end());

    auto fields = split(line, ',');
    if (!validateFields(fields)) return;

    // Map fields (based on your provided format)
    // 0: TEAM ID
    // 1: Time since power (s)
    // 2: Packet Count
    // 3: Altitude (m)
    // 4: Pressure (Pa)
    // 5: Temperature (°C)
    // 6: Voltage (V)
    // 7: GNSS Time (s)
    // 8: GNSS Latitude
    // 9: GNSS Longitude
    // 10: GNSS Altitude (m)
    // 11: GNSS SATS
    // 12: Accelerometer
    // 13: Gyro Spin Rate (deg/s)
    // 14: Flight Software State

    string team_id = fields[0];
    int time_since_power = safe_stoi(fields[1], 0);
    int packet_count = safe_stoi(fields[2], 0);
    float altitude = safe_stof(fields[3], 0.0f);
    float pressure = safe_stof(fields[4], 0.0f);
    float temperature = safe_stof(fields[5], 0.0f);
    float voltage = safe_stof(fields[6], 0.0f);
    string gnss_time = fields[7];
    float latitude = safe_stof(fields[8], 0.0f);
    float longitude = safe_stof(fields[9], 0.0f);
    float gnss_alt = safe_stof(fields[10], 0.0f);
    int gnss_sats = safe_stoi(fields[11], 0);
    string accelerometer = fields[12];
    float gyro = safe_stof(fields[13], 0.0f);
    string flight_state = fields[14];

    // Debug info to stderr only (frontend won't parse this)
    cerr << "\n[" << getCurrentTime() << "] Telemetry Packet Received:" << endl;
    cerr << "-------------------------------------------" << endl;
    cerr << "TEAM ID: " << team_id << endl;
    cerr << "Time since power (s): " << time_since_power << endl;
    cerr << "Packet Count: " << packet_count << endl;
    cerr << "Altitude (m): " << altitude << endl;
    cerr << "Pressure (Pa): " << pressure << endl;
    cerr << "Temperature (°C): " << temperature << endl;
    cerr << "Voltage (V): " << voltage << endl;
    cerr << "GNSS Time (s): " << gnss_time << endl;
    cerr << "GNSS Latitude: " << latitude << endl;
    cerr << "GNSS Longitude: " << longitude << endl;
    cerr << "GNSS Altitude (m): " << gnss_alt << endl;
    cerr << "GNSS SATS: " << gnss_sats << endl;
    cerr << "Accelerometer: " << accelerometer << endl;
    cerr << "Gyro Spin Rate (deg/s): " << gyro << endl;
    cerr << "Flight Software State: " << flight_state << endl;

    // Save to CSV log
    if (logFile.is_open()) {
        logFile << line << endl;
        logFile.flush();
    }

    // Build JSON telemetry with more fields for frontend
    json telemetry;
    telemetry["source"] = "cansat";
    telemetry["timestamp"] = static_cast<long>(std::time(nullptr));
    telemetry["team_id"] = team_id;
    telemetry["time_since_power"] = time_since_power;
    telemetry["packet_count"] = packet_count;
    telemetry["altitude"] = altitude;
    telemetry["pressure"] = pressure;
    telemetry["temperature"] = temperature;
    telemetry["voltage"] = voltage;
    telemetry["gnss_time"] = gnss_time;
    telemetry["latitude"] = latitude;
    telemetry["longitude"] = longitude;
    telemetry["gnss_altitude"] = gnss_alt;
    telemetry["gnss_sats"] = gnss_sats;
    telemetry["accelerometer"] = accelerometer;
    telemetry["gyro"] = gyro;
    telemetry["state"] = flight_state;
    telemetry["status"] = "OK";

    // Send structured JSON telemetry to frontend (stdout)
    sendTelemetry(telemetry);
}

// ---------- Serial Port Setup ----------
int openSerial(const char* port, int baud) {
    int fd = open(port, O_RDONLY | O_NOCTTY);
    if (fd == -1) {
        cerr << "[" << getCurrentTime() << "] Error: Failed to open serial port " << port << endl;
        cerr << "Check permissions: ls -l " << port << endl;
        cerr << "If needed, run: sudo usermod -aG dialout $USER" << endl;
        return -1;
    }

    struct termios tty{};
    if (tcgetattr(fd, &tty) != 0) {
        cerr << "[" << getCurrentTime() << "] Error: Unable to get port attributes" << endl;
        close(fd);
        return -1;
    }

    // Set baud rate
    speed_t speed;
    switch(baud) {
        case 9600: speed = B9600; break;
        case 19200: speed = B19200; break;
        case 38400: speed = B38400; break;
        case 57600: speed = B57600; break;
        case 115200: speed = B115200; break;
        default:
            cerr << "[" << getCurrentTime() << "] Unsupported baud rate, using 115200" << endl;
            speed = B115200;
    }

    cfsetospeed(&tty, speed);
    cfsetispeed(&tty, speed);

    tty.c_cflag = (tty.c_cflag & ~CSIZE) | CS8;
    tty.c_iflag = IGNPAR;
    tty.c_lflag = 0;
    tty.c_oflag = 0;
    tty.c_cc[VMIN] = 1;
    tty.c_cc[VTIME] = 1;

    tcflush(fd, TCIFLUSH);
    if (tcsetattr(fd, TCSANOW, &tty) != 0) {
        cerr << "[" << getCurrentTime() << "] Error: Failed to configure serial port" << endl;
        close(fd);
        return -1;
    }

    return fd;
}

// ---------- Signal handler ----------
void handle_signal(int signum) {
    keep_running = false;
    cerr << "[" << getCurrentTime() << "] Received signal, shutting down..." << endl;
    if (serial_fd != -1) close(serial_fd);
    if (logFile.is_open()) logFile.close();
    // Allow main to exit gracefully
}

// ---------- Main ----------
int main() {
    // Unbuffered stdout so python can read each JSON line immediately
    std::cout << std::unitbuf;

    // Register SIGINT/SIGTERM to cleanup
    signal(SIGINT, handle_signal);
    signal(SIGTERM, handle_signal);

    cerr << "[" << getCurrentTime() << "] Starting 433 MHz Telemetry Reader (baud: " << BAUDRATE << ")..." << endl;

    serial_fd = openSerial(SERIAL_PORT, BAUDRATE);
    if (serial_fd < 0) return 1;

    cerr << "[" << getCurrentTime() << "] Listening on " << SERIAL_PORT << " ..." << endl;

    logFile.open("telemetry_433.csv", ios::app);
    if (!logFile.is_open()) {
        cerr << "[" << getCurrentTime() << "] Error: Unable to open telemetry_433.csv" << endl;
        close(serial_fd);
        return 1;
    }

    // Read incoming data line-by-line from serial
    string line;
    char c;
    while (keep_running) {
        ssize_t n = read(serial_fd, &c, 1);
        if (n > 0) {
            if (c == '\n' || c == '\r') {
                if (!line.empty()) {
                    processLine(line);
                    line.clear();
                }
            } else {
                line += c;
            }
        } else {
            // nothing read; small sleep to avoid busy loop
            usleep(1000);
        }
    }

    // cleanup
    if (serial_fd != -1) close(serial_fd);
    if (logFile.is_open()) logFile.close();
    cerr << "[" << getCurrentTime() << "] Exiting." << endl;
    return 0;
}
