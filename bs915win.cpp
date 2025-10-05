#include <windows.h>
#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <string>
#include <ctime>

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

bool validateFields(vector<string> &fields) {
    if (fields.size() < 14) {  // accept 14 or more fields
        cerr << "[" << getCurrentTime() << "] Warning: Incomplete packet (" << fields.size() << " fields)" << endl;
        return false;
    }
    // fill missing fields if less than 15
    while (fields.size() < 15)
        fields.push_back("");  // add empty string for missing 15th field
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

    string portName = "\\\\.\\COM11"; // <-- Change to your telemetry COM port
    DWORD baudRate = CBR_57600;

    // Open serial port
    HANDLE hSerial = CreateFileA(portName.c_str(),
                                 GENERIC_READ | GENERIC_WRITE,
                                 0, 0, OPEN_EXISTING,
                                 FILE_ATTRIBUTE_NORMAL, 0);

    if (hSerial == INVALID_HANDLE_VALUE) {
        cerr << "[" << getCurrentTime() << "] Error: Could not open " << portName << endl;
        return 1;
    }

    // Configure serial port
    DCB dcbSerialParams = {0};
    dcbSerialParams.DCBlength = sizeof(dcbSerialParams);
    if (!GetCommState(hSerial, &dcbSerialParams)) {
        cerr << "[" << getCurrentTime() << "] Error: Could not get COM state" << endl;
        CloseHandle(hSerial);
        return 1;
    }

    dcbSerialParams.BaudRate = baudRate;
    dcbSerialParams.ByteSize = 8;
    dcbSerialParams.StopBits = ONESTOPBIT;
    dcbSerialParams.Parity   = NOPARITY;

    if (!SetCommState(hSerial, &dcbSerialParams)) {
        cerr << "[" << getCurrentTime() << "] Error: Could not set COM parameters" << endl;
        CloseHandle(hSerial);
        return 1;
    }

    // Set timeouts
    COMMTIMEOUTS timeouts = {0};
    timeouts.ReadIntervalTimeout         = 50;
    timeouts.ReadTotalTimeoutConstant    = 50;
    timeouts.ReadTotalTimeoutMultiplier  = 10;
    SetCommTimeouts(hSerial, &timeouts);

    cout << "[" << getCurrentTime() << "] Listening on " << portName << " ...\n";

    // Open log file
    ofstream logFile("telemetry_log.csv", ios::app);
    if (!logFile.is_open()) {
        cerr << "[" << getCurrentTime() << "] Error: Unable to open telemetry_log.csv\n";
        CloseHandle(hSerial);
        return 1;
    }

    // Read incoming data
    string line;
    char c;
    DWORD bytesRead;
    while (true) {
        if (ReadFile(hSerial, &c, 1, &bytesRead, NULL) && bytesRead > 0) {
            if (c == '\n' || c == '\r') {
                if (!line.empty()) {
                    processLine(line, logFile);
                    line.clear();
                }
            } else {
                line += c;
            }
        } else {
            Sleep(1);  // small delay (ms)
        }
    }

    CloseHandle(hSerial);
    logFile.close();
    return 0;
}

// 2024 ASI-011,20,50,722,25,9,20,18.2765,7.5623,50,11,0,0,idle
// 2024 ASI-011,20,50,722,25,9,20,18.2765,7.5623,50,11,0,0,idle
