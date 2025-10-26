#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <string>
#include <ctime>
#include <termios.h>
#include <fcntl.h>
#include <unistd.h>
#include <nlohmann/json.hpp>

using namespace std;
using json = nlohmann::json;

// ===========================================================
//  FUNCTION: sendTelemetry
// ===========================================================
void sendTelemetry(
    float altitude,
    float temperature,
    float velocity,
    float latitude,
    float longitude,
    float pressure = 0.0f,
    float battery = 0.0f
) {
    try {
        json telemetry;
        telemetry["source"]      = "cansat";
        telemetry["timestamp"]   = static_cast<long>(std::time(nullptr));  // Unix timestamp
        telemetry["altitude"]    = altitude;
        telemetry["temperature"] = temperature;
        telemetry["velocity"]    = velocity;
        telemetry["latitude"]    = latitude;
        telemetry["longitude"]   = longitude;
        telemetry["pressure"]    = pressure;
        telemetry["battery"]     = battery;
        telemetry["status"]      = "OK";

        // Send JSON to stdout (frontend reads this)
        std::cout << telemetry.dump() << std::endl;
    }
    catch (const std::exception &e) {
        std::cerr << "Telemetry JSON error: " << e.what() << std::endl;
    }
}

// ---------- Configuration ----------
const char* SERIAL_PORT = "/dev/ttyUSB0";  // change if needed
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

// ---------- Telemetry Processor ----------
void processLine(const string &line, ofstream &logFile) {
    auto fields = split(line, ',');
    if (!validateFields(fields))
        return;

    // Debug info to stderr (not read by Python)
    cerr << "\n[" << getCurrentTime() << "] Telemetry Packet Received:\n";
    cerr << "-------------------------------------------\n";
    cerr << "TEAM ID: " << fields[0] << endl;
    cerr << "Time since power (s): " << fields[1] << endl;
    cerr << "Packet Count: " << fields[2] << endl;
    cerr << "Altitude (m): " << fields[3] << endl;
    cerr << "Pressure (Pa): " << fields[4] << endl;
    cerr << "Temperature (°C): " << fields[5] << endl;
    cerr << "Voltage (V): " << fields[6] << endl;
    cerr << "GNSS Latitude: " << fields[8] << endl;
    cerr << "GNSS Longitude: " << fields[9] << endl;
    cerr << "Gyro Spin Rate (deg/s): " << fields[13] << endl;

    // Save to CSV log
    logFile << line << endl;
    logFile.flush();

    // Convert relevant values to float for JSON telemetry
    float altitude    = stof(fields[3]);
    float pressure    = stof(fields[4]);
    float temperature = stof(fields[5]);
    float voltage     = stof(fields[6]);
    float latitude    = stof(fields[8]);
    float longitude   = stof(fields[9]);
    float velocity    = stof(fields[13]); // using gyro rate as velocity example

    // Send structured JSON telemetry to frontend
    sendTelemetry(altitude, temperature, velocity, latitude, longitude, pressure, voltage);
}

// ---------- Serial Port Setup ----------
int openSerial(const char* port, int baud) {
    int fd = open(port, O_RDONLY | O_NOCTTY);
    if (fd == -1) {
        cerr << "[" << getCurrentTime() << "] Error: Failed to open serial port " << port << endl;
        cerr << "Check permissions: ls -l " << port << endl;
        cerr << "If needed, run: sudo usermod -aG dialout $USER\n";
        return -1;
    }

    struct termios tty{};
    if (tcgetattr(fd, &tty) != 0) {
        cerr << "[" << getCurrentTime() << "] Error: Unable to get port attributes\n";
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
            cerr << "Unsupported baud rate, using 115200\n";
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
        cerr << "[" << getCurrentTime() << "] Error: Failed to configure serial port\n";
        close(fd);
        return -1;
    }

    return fd;
}

// ---------- Main ----------
int main() {
    // Disable buffering on stdout so Python reads immediately
    std::cout << std::unitbuf;

    cerr << "[" << getCurrentTime() << "] Starting 433 MHz Telemetry Reader (baud: " << BAUDRATE << ")...\n";

    int fd = openSerial(SERIAL_PORT, BAUDRATE);
    if (fd < 0) return 1;

    cerr << "[" << getCurrentTime() << "] Listening on " << SERIAL_PORT << " ...\n";

    ofstream logFile("telemetry_433.csv", ios::app);
    if (!logFile.is_open()) {
        cerr << "[" << getCurrentTime() << "] Error: Unable to open telemetry_433.csv\n";
        close(fd);
        return 1;
    }

    // Read incoming data line-by-line
    string line;
    char c;
    while (true) {
        ssize_t n = read(fd, &c, 1);
        if (n > 0) {
            if (c == '\n' || c == '\r') {
                if (!line.empty()) {
                    processLine(line, logFile);
                    line.clear();
                }
            } else {
                line += c;
            }
        } else {
            usleep(1000);
        }
    }

    close(fd);
    logFile.close();
    return 0;
}
