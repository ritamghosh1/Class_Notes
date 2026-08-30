#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <cstring>
#include <chrono>
#include <algorithm>
#include <mutex>
#include <sstream>
#include <thread>
#include <signal.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <cstdlib>
#include "ErrorDetection.h"
using namespace std;

#define PORT 8080
#define WEB_PORT 8081
#define MAX_FRAME_SIZE 1500
#define MIN_PAYLOAD_SIZE 46

struct NetworkFrameHeader
{
    uint32_t packetId;
    uint16_t payloadSize;
    uint8_t protocolId; // 0: Checksum, 1: CRC8, 2: CRC10, 3: CRC16, 4: CRC32
    uint8_t reserved;
    uint8_t sourceAddress[6];
    uint8_t targetAddress[6];
};

struct Scheme { int type; uint32_t poly; int degree; string name; };
Scheme schemes[5] = {
    {1, 0, 0, "Checksum"},          
    {2, 0xD5, 8, "CRC-8"},               
    {2, 0x233, 10, "CRC-10"},             
    {2, 0x8005, 16, "CRC-16"},            
    {2, 0x04C11DB7, 32, "CRC-32"}         
};

mutex webMutex;
vector<int> webClients;
vector<string> webHistory;

string escapeHtml(const string &text)
{
    string escaped;
    for (char ch : text) {
        switch (ch) {
            case '&': escaped += "&amp;"; break;
            case '<': escaped += "&lt;"; break;
            case '>': escaped += "&gt;"; break;
            case '"': escaped += "&quot;"; break;
            default: escaped += ch; break;
        }
    }
    return escaped;
}

string escapeSse(const string &text)
{
    string escaped;
    for (char ch : text) {
        if (ch == '\n') escaped += "\\n";
        else escaped += ch;
    }
    return escaped;
}

bool sendAll(int sock, const string &data)
{
    size_t sent = 0;
    while (sent < data.size()) {
        ssize_t result = send(sock, data.data() + sent, data.size() - sent, 0);
        if (result <= 0) return false;
        sent += static_cast<size_t>(result);
    }
    return true;
}

static bool isValidProtocolId(uint8_t protocolId)
{
    return protocolId < 5;
}

static bool computeFrameSize(const NetworkFrameHeader &header, size_t &frameSize)
{
    uint8_t protocolId = header.protocolId;
    if (!isValidProtocolId(protocolId)) return false;

    size_t payloadSize = max<size_t>(ntohs(header.payloadSize), MIN_PAYLOAD_SIZE);
    if (payloadSize > MAX_FRAME_SIZE) return false;

    size_t trailerSize = (protocolId == 0) ? 2 :
                         (protocolId == 1 ? 1 : (protocolId == 4 ? 4 : 2));
    frameSize = sizeof(NetworkFrameHeader) + payloadSize + trailerSize;
    if (frameSize > MAX_FRAME_SIZE) return false;
    return true;
}

static bool hasValidHeader(const vector<uint8_t> &pending, size_t &validFrameSize)
{
    if (pending.size() < sizeof(NetworkFrameHeader)) return false;
    NetworkFrameHeader candidate;
    memcpy(&candidate, pending.data(), sizeof(NetworkFrameHeader));
    return computeFrameSize(candidate, validFrameSize);
}

void logLine(const string &line)
{
    cout << line << "\n";

    lock_guard<mutex> lock(webMutex);
    webHistory.push_back(line);
    if (webHistory.size() > 200) {
        webHistory.erase(webHistory.begin());
    }

    string event = "data: " + escapeSse(line) + "\n\n";
    for (auto it = webClients.begin(); it != webClients.end();) {
        if (sendAll(*it, event)) {
            ++it;
        } else {
            close(*it);
            it = webClients.erase(it);
        }
    }
}

void runWebServer(int webPort)
{
    int webFd;
    struct sockaddr_in webAddress;
    int opt = 1;

    if ((webFd = socket(AF_INET, SOCK_STREAM, 0)) == 0) {
        cerr << "Web socket creation failed\n";
        return;
    }

    if (setsockopt(webFd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt))) {
        cerr << "Web setsockopt failed\n";
        close(webFd);
        return;
    }

    webAddress.sin_family = AF_INET;
    webAddress.sin_addr.s_addr = INADDR_ANY;
    webAddress.sin_port = htons(static_cast<uint16_t>(webPort));

    if (::bind(webFd, (struct sockaddr *)&webAddress, sizeof(webAddress)) < 0) {
        cerr << "Web bind failed\n";
        close(webFd);
        return;
    }

    if (listen(webFd, 8) < 0) {
        cerr << "Web listen failed\n";
        close(webFd);
        return;
    }

    while (true) {
        int client = accept(webFd, nullptr, nullptr);
        if (client < 0) continue;

        char reqBuffer[1024] = {0};
        ssize_t reqSize = recv(client, reqBuffer, sizeof(reqBuffer) - 1, 0);
        if (reqSize <= 0) {
            close(client);
            continue;
        }

        string request(reqBuffer, reqSize);
        if (request.rfind("GET /events", 0) == 0) {
            string headers =
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/event-stream\r\n"
                "Cache-Control: no-cache\r\n"
                "Connection: keep-alive\r\n"
                "Access-Control-Allow-Origin: *\r\n\r\n";
            if (!sendAll(client, headers)) {
                close(client);
                continue;
            }

            {
                lock_guard<mutex> lock(webMutex);
                for (const string &line : webHistory) {
                    if (!sendAll(client, "data: " + escapeSse(line) + "\n\n")) {
                        close(client);
                        client = -1;
                        break;
                    }
                }
                if (client >= 0) webClients.push_back(client);
            }
        } else {
            string page =
                "<!doctype html><html><head><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
                "<title>Receiver</title><style>"
                "body{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;margin:0;background:#111;color:#eee}"
                "header{position:sticky;top:0;background:#1b1b1b;padding:14px 16px;border-bottom:1px solid #333}"
                "h1{font-size:18px;margin:0}.status{font-size:13px;color:#9ee493;margin-top:4px}"
                "#log{white-space:pre-wrap;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px;padding:16px;line-height:1.45}"
                "</style></head><body><header><h1>Receiver Output</h1><div class=\"status\" id=\"status\">Connecting...</div></header>"
                "<main id=\"log\"></main><script>"
                "const log=document.getElementById('log');const status=document.getElementById('status');"
                "const es=new EventSource('/events');"
                "es.onopen=()=>status.textContent='Connected to receiver on Mac';"
                "es.onerror=()=>status.textContent='Disconnected. Refresh after restarting receiver.';"
                "es.onmessage=e=>{log.textContent+=e.data+'\\n';window.scrollTo(0,document.body.scrollHeight);};"
                "</script></body></html>";
            string response =
                "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: " +
                to_string(page.size()) + "\r\nConnection: close\r\n\r\n" + page;
            sendAll(client, response);
            close(client);
        }
    }
}

int main(int argc, char *argv[])
{
    string bindAddress = "0.0.0.0";
    int port = PORT;
    int webPort = WEB_PORT;

    if (argc >= 2) {
        string arg1 = argv[1];
        bool isNumeric = !arg1.empty() && all_of(arg1.begin(), arg1.end(), ::isdigit);
        if (!isNumeric || arg1.find('.') != string::npos || arg1 == "localhost") {
            bindAddress = arg1;
            if (argc >= 3) port = atoi(argv[2]);
            if (argc >= 4) webPort = atoi(argv[3]);
        } else {
            port = atoi(argv[1]);
            if (argc >= 3) webPort = atoi(argv[2]);
            if (argc >= 4) bindAddress = argv[3];
        }
    }

    if (port < 1 || port > 65535) {
        cerr << "Invalid port. Use a value between 1 and 65535.\n";
        return -1;
    }
    if (webPort < 1 || webPort > 65535) {
        cerr << "Invalid web port. Use a value between 1 and 65535.\n";
        return -1;
    }

    signal(SIGPIPE, SIG_IGN);
    thread(runWebServer, webPort).detach();

    int server_fd, new_socket;
    struct sockaddr_in address;
    int opt = 1;
    int addrlen = sizeof(address);

    if ((server_fd = socket(AF_INET, SOCK_STREAM, 0)) == 0) {
        cerr << "Socket creation failed\n";
        return -1;
    }

    if (setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt))) {
        cerr << "Setsockopt failed\n";
        return -1;
    }

    address.sin_family = AF_INET;
    if (inet_pton(AF_INET, bindAddress.c_str(), &address.sin_addr) != 1) {
        cerr << "Invalid bind address: " << bindAddress << "\n";
        return -1;
    }
    address.sin_port = htons(static_cast<uint16_t>(port));

    if (::bind(server_fd, (struct sockaddr *)&address, sizeof(address)) < 0) {
        cerr << "Bind failed\n";
        return -1;
    }

    if (listen(server_fd, 3) < 0) {
        cerr << "Listen failed\n";
        return -1;
    }

    logLine("Receiver is listening for sender frames on " + bindAddress + ", port " + to_string(port) + "...");
    logLine("Open the receiver web UI from another device at http://<receiver-ip>:" + to_string(webPort) + " to view receiver output.");

    if ((new_socket = accept(server_fd, (struct sockaddr *)&address, (socklen_t *)&addrlen)) < 0) {
        cerr << "Accept failed\n";
        return -1;
    }

    logLine("Sender connected. Entering Packet Parsing mode...");
    logLine("--------------------------------------------");

    vector<uint8_t> buffer(4096);
    int bytesRead;
    vector<uint8_t> pending;
    
    bool detectedErrors[5] = {false};
    long executionTimes[5] = {0};
    uint32_t currentSeqNo = 0;
    uint32_t completedCycles = 0;
    
    // To keep track of when we've received all 5 schemes for a sequence number
    int schemesReceivedForSeq = 0;

    while ((bytesRead = recv(new_socket, buffer.data(), buffer.size(), 0)) > 0)
    {
        pending.insert(pending.end(), buffer.begin(), buffer.begin() + bytesRead);

        // TCP is a byte stream: extract complete frames instead of assuming
        // one recv() call equals one send() call.
        while (pending.size() >= sizeof(NetworkFrameHeader))
        {
            NetworkFrameHeader peekHeader;
            memcpy(&peekHeader, pending.data(), sizeof(NetworkFrameHeader));
            size_t frameSize;

            if (!computeFrameSize(peekHeader, frameSize)) {
                // Search for the next valid header alignment.
                size_t syncPos = 1;
                bool found = false;
                while (syncPos + sizeof(NetworkFrameHeader) <= pending.size()) {
                    NetworkFrameHeader candidate;
                    memcpy(&candidate, pending.data() + syncPos, sizeof(NetworkFrameHeader));
                    size_t candidateFrameSize;
                    if (computeFrameSize(candidate, candidateFrameSize)) {
                        found = true;
                        break;
                    }
                    syncPos++;
                }

                if (found) {
                    pending.erase(pending.begin(), pending.begin() + syncPos);
                    continue;
                }

                if (pending.size() > MAX_FRAME_SIZE) {
                    pending.erase(pending.begin());
                }
                break;
            }

            if (pending.size() < frameSize) break;

            vector<uint8_t> frame(pending.begin(), pending.begin() + frameSize);
            pending.erase(pending.begin(), pending.begin() + frameSize);

            NetworkFrameHeader rxHeader;
            memcpy(&rxHeader, frame.data(), sizeof(NetworkFrameHeader));

            // Initialize a new cycle if sequence number changes
            if (ntohl(rxHeader.packetId) != currentSeqNo && schemesReceivedForSeq > 0) {
                currentSeqNo = ntohl(rxHeader.packetId);
                schemesReceivedForSeq = 0;
                for (int i = 0; i < 5; i++) {
                    detectedErrors[i] = false;
                    executionTimes[i] = 0;
                }
            } else {
                currentSeqNo = ntohl(rxHeader.packetId);
            }

            uint8_t protocolId = rxHeader.protocolId;
            Scheme currentScheme = schemes[protocolId];

            if (currentScheme.type == 1) {
                uint8_t chkLow = frame.back(); frame.pop_back();
                uint8_t chkHigh = frame.back(); frame.pop_back();
                uint16_t rxChecksum = (chkHigh << 8) | chkLow;

                auto start = chrono::high_resolution_clock::now();
                uint16_t calcChecksum = ErrorDetection::computeInternetChecksum(frame);
                auto end = chrono::high_resolution_clock::now();

                executionTimes[protocolId] = chrono::duration_cast<chrono::microseconds>(end - start).count();
                detectedErrors[protocolId] = (rxChecksum != calcChecksum);
            } else {
                int deg = currentScheme.degree;
                size_t crcSize = (deg == 8) ? 1 : ((deg == 32) ? 4 : 2);
                uint32_t rxCrc = 0;

                if (crcSize == 1) {
                    rxCrc = frame.back(); frame.pop_back();
                } else if (crcSize == 2) {
                    uint8_t low = frame.back(); frame.pop_back();
                    uint8_t high = frame.back(); frame.pop_back();
                    rxCrc = (high << 8) | low;
                } else if (crcSize == 4) {
                    uint8_t b0 = frame.back(); frame.pop_back();
                    uint8_t b1 = frame.back(); frame.pop_back();
                    uint8_t b2 = frame.back(); frame.pop_back();
                    uint8_t b3 = frame.back(); frame.pop_back();
                    rxCrc = (b3 << 24) | (b2 << 16) | (b1 << 8) | b0;
                }

                auto start = chrono::high_resolution_clock::now();
                uint32_t calcCrc = ErrorDetection::computeCyclicRedundancy(frame, currentScheme.poly, currentScheme.degree);
                auto end = chrono::high_resolution_clock::now();

                executionTimes[protocolId] = chrono::duration_cast<chrono::microseconds>(end - start).count();
                detectedErrors[protocolId] = (rxCrc != calcCrc);
            }

            if (detectedErrors[protocolId]) {
                logLine("[REJECTED] SeqNo: " + to_string(currentSeqNo) + " | Scheme: " + currentScheme.name + " caught an error!");
            } else {
                logLine("[ACCEPTED] SeqNo: " + to_string(currentSeqNo) + " | Scheme: " + currentScheme.name + " received clean (or missed error)." );
            }

            ofstream csvFile("results.csv", ios::app);
            if (csvFile.is_open()) {
                string errorTypeStr = "Clean";
                bool errorInjected = (rxHeader.reserved > 0);
                if (errorInjected) {
                    switch (rxHeader.reserved - 1) {
                        case 0: errorTypeStr = "SingleBit"; break;
                        case 1: errorTypeStr = "DoubleBit"; break;
                        case 2: errorTypeStr = "OddErrors"; break;
                        case 3: errorTypeStr = "Burst"; break;
                        case 4: errorTypeStr = "ChecksumCollision"; break;
                        case 5: errorTypeStr = "WordSwap"; break;
                        case 6: errorTypeStr = "CRC8Collision"; break;
                        default: errorTypeStr = "Unknown"; break;
                    }
                }
                
                csvFile << currentSeqNo << ","
                        << currentScheme.name << ","
                        << errorTypeStr << ","
                        << (errorInjected ? "True" : "False") << ","
                        << (detectedErrors[protocolId] ? "True" : "False") << ","
                        << executionTimes[protocolId] << "\n";
                csvFile.close();
            }

            schemesReceivedForSeq++;

            // Once we have received all 5 schemes for the current packetId
            if (schemesReceivedForSeq == 5) {
                completedCycles++;
                logLine("--------------------------------------------");
                schemesReceivedForSeq = 0; // Reset for the next sequence
            }
        }
    }

    if (bytesRead == 0) {
        logLine("Evaluation complete. " + to_string(completedCycles) + " datawords evaluated across all schemes.");
    } else if (bytesRead < 0) {
        cerr << "Error occurred during reception.\n";
    }


    close(new_socket);
    close(server_fd);
    return 0;
}
