// main.cpp - Windows-ready telemetry backend
// Build (MinGW): g++ main.cpp sqlite3.lib -o telemetry_backend.exe -std=c++17 -lws2_32
// Build (MSVC): cl /EHsc main.cpp sqlite3.lib ws2_32.lib

#ifndef _WIN32_WINNT
  #define _WIN32_WINNT 0x0A00   // target Windows 10 or later
#endif

// winsock2 must come before windows.h
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>

#include <iostream>
#include <string>
#include <vector>
#include <thread>
#include <mutex>
#include <atomic>
#include <sstream>
#include <chrono>

#include "httplib.h"   // download from https://github.com/yhirose/cpp-httplib
#include "sqlite3.h"   // sqlite header

// ----- Config -----
static std::string COM_PORT = "COM11";       // COM port (change to your COM#)
static const DWORD BAUD_RATE = CBR_115200;   // change if needed
static const char* DB_FILE = "telemetry.db";
static const int HTTP_PORT = 8080;

// ----- Globals -----
sqlite3* db = nullptr;
std::mutex db_mutex;
std::atomic<bool> keep_running(true);
std::unique_ptr<httplib::Server> http_server; // to call stop() later

// ----- Utilities -----
static void trim(std::string &s) {
    size_t a = s.find_first_not_of(" \t\r\n");
    size_t b = s.find_last_not_of(" \t\r\n");
    if (a == std::string::npos) { s.clear(); return; }
    s = s.substr(a, b - a + 1);
}

static std::vector<std::string> split_csv(const std::string &line) {
    std::vector<std::string> out;
    std::string cur;
    bool in_quote = false;
    for (size_t i = 0; i < line.size(); ++i) {
        char c = line[i];
        if (c == '"') {
            in_quote = !in_quote;
        } else if (c == ',' && !in_quote) {
            trim(cur);
            out.push_back(cur);
            cur.clear();
        } else {
            cur.push_back(c);
        }
    }
    trim(cur);
    if (!cur.empty() || line.back()==',') out.push_back(cur);
    return out;
}

static double to_double_or_zero(const std::string &s) {
    if (s.empty()) return 0.0;
    try { return std::stod(s); } catch(...) { return 0.0; }
}
static int to_int_or_zero(const std::string &s) {
    if (s.empty()) return 0;
    try { return std::stoi(s); } catch(...) { return 0; }
}

// ----- Database -----
bool init_db() {
    if (sqlite3_open(DB_FILE, &db) != SQLITE_OK) {
        std::cerr << "Cannot open DB: " << sqlite3_errmsg(db) << std::endl;
        return false;
    }
    const char* create_sql =
        "CREATE TABLE IF NOT EXISTS telemetry ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "received_at TEXT DEFAULT CURRENT_TIMESTAMP,"
        "team_id TEXT,"
        "time_stamping TEXT,"
        "packet_count INTEGER,"
        "altitude REAL,"
        "pressure REAL,"
        "temp REAL,"
        "voltage TEXT,"
        "gnss_time TEXT,"
        "gnss_latitude REAL,"
        "gnss_longitude REAL,"
        "gnss_altitude REAL,"
        "gnss_sats INTEGER,"
        "accelerometer_data TEXT,"
        "gyro_spin_rate TEXT,"
        "flight_software_state TEXT,"
        "optional_data TEXT"
        ");";
    char* err = nullptr;
    if (sqlite3_exec(db, create_sql, nullptr, nullptr, &err) != SQLITE_OK) {
        std::cerr << "Create table error: " << err << std::endl;
        sqlite3_free(err);
        return false;
    }
    return true;
}

bool insert_telemetry_vec(const std::vector<std::string>& f) {
    std::lock_guard<std::mutex> lock(db_mutex);
    const char* insert_sql =
        "INSERT INTO telemetry (team_id, time_stamping, packet_count, altitude, pressure, temp, voltage, gnss_time, gnss_latitude, gnss_longitude, gnss_altitude, gnss_sats, accelerometer_data, gyro_spin_rate, flight_software_state, optional_data) "
        "VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14,?15,?16);";
    sqlite3_stmt* stmt = nullptr;
    if (sqlite3_prepare_v2(db, insert_sql, -1, &stmt, nullptr) != SQLITE_OK) {
        std::cerr << "Prepare failed: " << sqlite3_errmsg(db) << std::endl;
        return false;
    }

    auto get = [&](size_t i)->std::string { return (i < f.size() ? f[i] : std::string()); };

    sqlite3_bind_text(stmt, 1, get(0).c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 2, get(1).c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_int(stmt, 3, to_int_or_zero(get(2)));
    sqlite3_bind_double(stmt, 4, to_double_or_zero(get(3)));
    sqlite3_bind_double(stmt, 5, to_double_or_zero(get(4)));
    sqlite3_bind_double(stmt, 6, to_double_or_zero(get(5)));
    sqlite3_bind_text(stmt, 7, get(6).c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 8, get(7).c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_double(stmt, 9, to_double_or_zero(get(8)));
    sqlite3_bind_double(stmt, 10, to_double_or_zero(get(9)));
    sqlite3_bind_double(stmt, 11, to_double_or_zero(get(10)));
    sqlite3_bind_int(stmt, 12, to_int_or_zero(get(11)));
    sqlite3_bind_text(stmt, 13, get(12).c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 14, get(13).c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 15, get(14).c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 16, get(15).c_str(), -1, SQLITE_TRANSIENT);

    bool ok = (sqlite3_step(stmt) == SQLITE_DONE);
    if (!ok) std::cerr << "Insert failed: " << sqlite3_errmsg(db) << std::endl;
    sqlite3_finalize(stmt);
    return ok;
}

// ----- Serial (COM) reading -----
HANDLE open_serial_port(const std::string &port) {
    // On Windows, COM10+ require "\\.\COM10" style
    std::string winport = port;
    if (port.size() > 4 && port.rfind("COM",0)==0) {
        // if COM10+ (two digits), use \\.\ prefix to be safe; but CreateFile accepts COMx too
        if (port.size() > 4) winport = "\\\\.\\" + port;
    }
    HANDLE h = CreateFileA(winport.c_str(), GENERIC_READ, 0, NULL, OPEN_EXISTING, 0, NULL);
    if (h == INVALID_HANDLE_VALUE) {
        std::cerr << "Failed to open serial " << winport << " (err " << GetLastError() << ")\n";
        return INVALID_HANDLE_VALUE;
    }

    DCB dcb = {0};
    dcb.DCBlength = sizeof(DCB);
    if (!GetCommState(h, &dcb)) {
        std::cerr << "GetCommState failed\n";
        CloseHandle(h);
        return INVALID_HANDLE_VALUE;
    }
    dcb.BaudRate = BAUD_RATE;
    dcb.ByteSize = 8;
    dcb.Parity = NOPARITY;
    dcb.StopBits = ONESTOPBIT;
    if (!SetCommState(h, &dcb)) {
        std::cerr << "SetCommState failed\n";
        CloseHandle(h);
        return INVALID_HANDLE_VALUE;
    }

    COMMTIMEOUTS timeouts = {0};
    timeouts.ReadIntervalTimeout = 50;
    timeouts.ReadTotalTimeoutConstant = 50;
    timeouts.ReadTotalTimeoutMultiplier = 10;
    SetCommTimeouts(h, &timeouts);

    return h;
}

void serial_reader_thread() {
    HANDLE h = open_serial_port(COM_PORT);
    if (h == INVALID_HANDLE_VALUE) return;
    std::string buffer;
    char ch;
    DWORD readBytes;
    while (keep_running) {
        BOOL ok = ReadFile(h, &ch, 1, &readBytes, NULL);
        if (!ok) {
            DWORD err = GetLastError();
            // if timeout, ReadFile may return FALSE with ERROR_OPERATION_ABORTED on shutdown; handle gracefully
            if (err == ERROR_OPERATION_ABORTED) break;
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
            continue;
        }
        if (readBytes == 0) {
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
            continue;
        }
        if (ch == '\n' || ch == '\r') {
            if (!buffer.empty()) {
                auto fields = split_csv(buffer);
                if (!fields.empty()) {
                    if (insert_telemetry_vec(fields)) {
                        std::cout << "[DB] saved packet: " << buffer << "\n";
                    } else {
                        std::cout << "[DB] failed to save: " << buffer << "\n";
                    }
                }
                buffer.clear();
            }
        } else {
            buffer.push_back(ch);
        }
    }
    CloseHandle(h);
}

// ----- HTTP server -----
void start_http_server_thread() {
    http_server = std::make_unique<httplib::Server>();

    http_server->Get("/latest", [](const httplib::Request&, httplib::Response& res) {
        std::lock_guard<std::mutex> lock(db_mutex);
        const char* sql = "SELECT id, received_at, team_id, time_stamping, packet_count, altitude FROM telemetry ORDER BY id DESC LIMIT 1;";
        sqlite3_stmt* stmt = nullptr;
        if (sqlite3_prepare_v2(db, sql, -1, &stmt, nullptr) != SQLITE_OK) {
            res.status = 500;
            res.set_content("{\"error\":\"db prepare failed\"}", "application/json");
            return;
        }
        std::string json = "{}";
        if (sqlite3_step(stmt) == SQLITE_ROW) {
            int id = sqlite3_column_int(stmt, 0);
            const unsigned char* received_at = sqlite3_column_text(stmt, 1);
            const unsigned char* team_id = sqlite3_column_text(stmt, 2);
            const unsigned char* time_stamp = sqlite3_column_text(stmt, 3);
            int pkt = sqlite3_column_int(stmt, 4);
            double alt = sqlite3_column_double(stmt, 5);

            std::ostringstream oss;
            oss << "{";
            oss << "\"id\":" << id << ",";
            oss << "\"received_at\":\"" << (received_at ? (const char*)received_at : "") << "\",";
            oss << "\"team_id\":\"" << (team_id ? (const char*)team_id : "") << "\",";
            oss << "\"time_stamping\":\"" << (time_stamp ? (const char*)time_stamp : "") << "\",";
            oss << "\"packet_count\":" << pkt << ",";
            oss << "\"altitude\":" << alt;
            oss << "}";
            json = oss.str();
        }
        sqlite3_finalize(stmt);
        res.set_content(json, "application/json");
    });

    http_server->Get("/count", [](const httplib::Request&, httplib::Response& res) {
        std::lock_guard<std::mutex> lock(db_mutex);
        const char* sql = "SELECT COUNT(*) FROM telemetry;";
        sqlite3_stmt* stmt = nullptr;
        int count = 0;
        if (sqlite3_prepare_v2(db, sql, -1, &stmt, nullptr) == SQLITE_OK) {
            if (sqlite3_step(stmt) == SQLITE_ROW) count = sqlite3_column_int(stmt,0);
        }
        sqlite3_finalize(stmt);
        res.set_content(std::string("{\"count\":") + std::to_string(count) + "}", "application/json");
    });

    std::cout << "[HTTP] Listening on port " << HTTP_PORT << " ...\n";
    http_server->listen("0.0.0.0", HTTP_PORT); // blocking call (runs until stop() is called)
}

// ----- Main -----
int main(int argc, char** argv) {
    if (argc >= 2) {
        COM_PORT = argv[1]; // allow COM port override from command line
        std::cout << "Using COM port: " << COM_PORT << "\n";
    } else {
        std::cout << "Default COM port: " << COM_PORT << " (override: telemetry_backend.exe COM4)\n";
    }

    if (!init_db()) {
        std::cerr << "DB init failed. Exiting.\n";
        return 1;
    }

    // WSAStartup (required for winsock / cpp-httplib)
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2,2), &wsaData) != 0) {
        std::cerr << "WSAStartup failed\n";
        return 1;
    }

    // start serial reader thread
    std::thread t_serial(serial_reader_thread);

    // start HTTP server in separate thread
    std::thread t_http(start_http_server_thread);

    std::cout << "Backend running. Press ENTER to stop...\n";
    std::cin.get();

    // Stop everything
    keep_running = false;

    // Stop http server gracefully
    if (http_server) {
        http_server->stop(); // stop() will cause listen() to return
    }

    // wait for threads
    if (t_serial.joinable()) t_serial.join();
    if (t_http.joinable()) t_http.join();

    sqlite3_close(db);
    WSACleanup();

    std::cout << "Stopped.\n";
    return 0;
}
