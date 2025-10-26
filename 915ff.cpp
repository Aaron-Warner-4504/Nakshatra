// 915f_updated.cpp - Updated backend for Rocket (915 MHz)
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
#include <algorithm>

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
        cout << telemetry.dump() << endl;
    } catch (const std::exception &e) {
        cerr << "[" << std::time(nullptr) << "] Telemetry JSON error: " << e.what() << endl;
    }
}

// ---------- Configuration ----------
const char* SERIAL_PORT = "/dev/ttyUSB1";  // Change according to your rocket dongle
const int BAUDRATE = 57600;

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
    if (fields.size() < 15) {
        cerr << "[" << getCurrentTime() << "] Warning: Incomplete packet (" << fields.size() << " fields)" << endl;
        return false;
    }
    return true;
}

// Safe conversion helpers
float safe_stof(const string &s, float def = 0.0f) {
    try { return stof(s); } catch (...) { return def; }
}
int safe_stoi(const string &s, int def = 0) {
    try { return stoi(s); } catch (...) { return def; }
}

// Remove non-ASCII characters from a string
string sanitize(const string &s) {
    string result;
    for (char c : s) {
        if (c >= 32 && c <= 126)  // printable ASCII
            result += c;
        else
            result += ' ';        // replace non-ASCII with space
    }
    return result;
}

// ---------- Telemetry Processor ----------
void processLine(const string &rawline) {
    string line = rawline;
    line.erase(remove(line.begin(), line.end(), '\r'), line.end());
    line = sanitize(line);

    auto fields = split(line, ',');
    if (!validateFields(fields)) return;

    string team_id = fields[0];
    int time_since_power = safe_stoi(fields[1]);
    int packet_count = safe_stoi(fields[2]);
    float altitude = safe_stof(fields[3]);
    float pressure = safe_stof(fields[4]);
    float temperature = safe_stof(fields[5]);
    float voltage = safe_stof(fields[6]);
    string gnss_time = fields[7];
    float latitude = safe_stof(fields[8]);
    float longitude = safe_stof(fields[9]);
    float gnss_alt = safe_stof(fields[10]);
    int gnss_sats = safe_stoi(fields[11]);
    string accelerometer = fields[12];
    float gyro = safe_stof(fields[13]);
    string flight_state = fields[14];

    // Debug logs
    cerr << "\n[" << getCurrentTime() << "] Rocket Telemetry Packet Received:" << endl;
    cerr << "TEAM ID: " << team_id << ", Altitude: " << altitude << " m, Temperature: " << temperature << " °C" << endl;

    if (logFile.is_open()) {
        logFile << line << endl;
        logFile.flush();
    }

    // Build JSON for frontend
    json telemetry;
    telemetry["source"] = "rocket";
    telemetry["timestamp"] = static_cast<long>(time(nullptr));
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

    sendTelemetry(telemetry);
}

// ---------- Serial Port Setup ----------
int openSerial(const char* port, int baud) {
    int fd = open(port, O_RDONLY | O_NOCTTY);
    if (fd == -1) {
        cerr << "[" << getCurrentTime() << "] Error: Failed to open serial port " << port << endl;
        return -1;
    }

    struct termios tty{};
    if (tcgetattr(fd, &tty) != 0) {
        cerr << "[" << getCurrentTime() << "] Error: Unable to get port attributes" << endl;
        close(fd);
        return -1;
    }

    speed_t speed;
    switch(baud) {
        case 9600: speed = B9600; break;
        case 19200: speed = B19200; break;
        case 38400: speed = B38400; break;
        case 57600: speed = B57600; break;
        case 115200: speed = B115200; break;
        default: speed = B115200;
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
}

// ---------- Main ----------
int main() {
    cout << std::unitbuf;

    signal(SIGINT, handle_signal);
    signal(SIGTERM, handle_signal);

    cerr << "[" << getCurrentTime() << "] Starting 915 MHz Rocket Telemetry Reader..." << endl;

    serial_fd = openSerial(SERIAL_PORT, BAUDRATE);
    if (serial_fd < 0) return 1;

    logFile.open("telemetry_915.csv", ios::app);
    if (!logFile.is_open()) {
        cerr << "[" << getCurrentTime() << "] Error: Unable to open telemetry_915.csv" << endl;
        close(serial_fd);
        return 1;
    }

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
            usleep(1000);
        }
    }

    if (serial_fd != -1) close(serial_fd);
    if (logFile.is_open()) logFile.close();
    cerr << "[" << getCurrentTime() << "] Exiting." << endl;
    return 0;
}
