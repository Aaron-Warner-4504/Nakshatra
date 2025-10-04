#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <string>
#include <ctime>
#include <termios.h>
#include <fcntl.h>
#include <unistd.h>

using namespace std;

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
    if (fields.size() < 15) {  // expecting 15 fields exactly
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

    cout << "\n[" << getCurrentTime() << "] Telemetry Packet Received:\n";
    cout << "-------------------------------------------\n";
    cout << "TEAM ID: " << fields[0] << endl;
    cout << "Time since power (s): " << fields[1] << endl;
    cout << "Packet Count: " << fields[2] << endl;
    cout << "Altitude (m): " << fields[3] << endl;
    cout << "Pressure (Pa): " << fields[4] << endl;
    cout << "Temperature (°C): " << fields[5] << endl;
    cout << "Voltage (V): " << fields[6] << endl;
    cout << "GNSS Time (s): " << fields[7] << endl;
    cout << "GNSS Latitude: " << fields[8] << endl;
    cout << "GNSS Longitude: " << fields[9] << endl;
    cout << "GNSS Altitude (m): " << fields[10] << endl;
    cout << "GNSS SATS: " << fields[11] << endl;
    cout << "Accelerometer: " << fields[12] << endl;
    cout << "Gyro Spin Rate (deg/s): " << fields[13] << endl; 
    cout << "Flight Software State: " << fields[14] << endl;

    // Save to CSV log
    logFile << line << endl;
    logFile.flush();
}

// ---------- Main ----------
int main() {
    cout << "[" << getCurrentTime() << "] Starting Telemetry Reader (57600 baud)...\n";

    const char *port = "/dev/ttyUSB0"; // Change to /dev/ttyUSB1 if needed
    int fd = open(port, O_RDONLY | O_NOCTTY);
    if (fd == -1) {
        cerr << "[" << getCurrentTime() << "] Error: Failed to open serial port " << port << endl;
        cerr << "Check permissions using: ls -l /dev/ttyUSB*\n";
        cerr << "If needed, run: sudo usermod -aG dialout $USER\n";
        return 1;
    }

    // Configure serial port
    struct termios tty;
    if (tcgetattr(fd, &tty) != 0) {
        cerr << "[" << getCurrentTime() << "] Error: Unable to get port attributes\n";
        close(fd);
        return 1;
    }

    cfsetispeed(&tty, B57600);
    cfsetospeed(&tty, B57600);
    tty.c_cflag = (tty.c_cflag & ~CSIZE) | CS8;  // 8-bit chars
    tty.c_iflag = IGNPAR;
    tty.c_lflag = 0;  // Raw input mode
    tty.c_oflag = 0;
    tty.c_cc[VMIN] = 1;
    tty.c_cc[VTIME] = 1;

    tcflush(fd, TCIFLUSH);
    if (tcsetattr(fd, TCSANOW, &tty) != 0) {
        cerr << "[" << getCurrentTime() << "] Error: Failed to configure serial port\n";
        close(fd);
        return 1;
    }

    cout << "[" << getCurrentTime() << "] Listening on " << port << " ...\n";

    // Open log file
    ofstream logFile("telemetry_log.csv", ios::app);
    if (!logFile.is_open()) {
        cerr << "[" << getCurrentTime() << "] Error: Unable to open telemetry_log.csv\n";
        close(fd);
        return 1;
    }

    // Read incoming data
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
            usleep(1000);  // small delay
        }
    }

    close(fd);
    logFile.close();
    return 0;
}
