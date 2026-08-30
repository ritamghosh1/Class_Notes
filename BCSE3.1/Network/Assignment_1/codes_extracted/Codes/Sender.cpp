#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <cstring>
#include <ctime>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <unistd.h>

#include <algorithm>
#include <random>
#include "ErrorDetection.h"
#include "ErrorInjection.h"
using namespace std;

#define PORT 8080
#define MAX_PAYLOAD_SIZE 1024
#define MIN_PAYLOAD_SIZE 46

static bool sendAll(int sock, const uint8_t *data, size_t size)
{
    size_t sent = 0;
    while (sent < size) {
        ssize_t result = send(sock, data + sent, size - sent, 0);
        if (result <= 0) return false;
        sent += static_cast<size_t>(result);
    }
    return true;
}

struct NetworkFrameHeader
{
    uint32_t packetId;
    uint16_t payloadSize;
    uint8_t protocolId; // 0: Checksum, 1: CRC8, 2: CRC10, 3: CRC16, 4: CRC32
    uint8_t reserved;
    uint8_t sourceAddress[6];
    uint8_t targetAddress[6];
};

struct Scheme
{
    int type;
    uint32_t poly;
    int degree;
    string name;
};
Scheme schemes[5] = {
    {1, 0, 0, "Checksum"},
    {2, 0xD5, 8, "CRC-8"},
    {2, 0x233, 10, "CRC-10"},
    {2, 0x8005, 16, "CRC-16"},
    {2, 0x04C11DB7, 32, "CRC-32"}};

int main(int argc, char const *argv[])
{
    srand(time(0));

    if (argc < 2)
    {
        cerr << "Usage: ./sender <filename> [receiver-ip] [port] [errorChoice]\n";
        return -1;
    }
    string filename = argv[1];
    const char *receiverIp = (argc >= 3) ? argv[2] : "127.0.0.1";
    int port = (argc >= 4) ? atoi(argv[3]) : PORT;
    if (port < 1 || port > 65535) {
        cerr << "Usage: ./sender <filename> [receiver-ip] [port] [errorChoice]\n";
        return -1;
    }

    int errorChoice = 0;
    if (argc >= 5) {
        errorChoice = atoi(argv[4]);
    } else {
        cout << "\nSelect the type of error to inject:\n"
             << "0: Single-bit error\n"
             << "1: Two isolated single-bit errors\n"
             << "2: Odd number of errors\n"
             << "3: Burst errors\n"
             << "4: Checksum collision error (may evade Internet checksum)\n"
             << "5: Word Swap (evades Internet Checksum)\n"
             << "6: CRC-8 Collision (evades CRC-8)\n"
             << "Enter your choice (0-6): ";
        cin >> errorChoice;
    }

    if (errorChoice < 0 || errorChoice > 6)
    {
        cout << "Invalid error choice! Defaulting to Single-bit error (0).\n";
        errorChoice = 0;
    }

    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0)
    {
        cerr << "Socket creation error\n";
        return -1;
    }

    struct sockaddr_in serv_addr;
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port = htons(static_cast<uint16_t>(port));

    if (inet_pton(AF_INET, receiverIp, &serv_addr.sin_addr) <= 0)
    {
        cerr << "Invalid address / Address not supported\n";
        close(sock);
        return -1;
    }

    if (connect(sock, (struct sockaddr *)&serv_addr, sizeof(serv_addr)) < 0)
    {
        cerr << "Connection Failed. Is the receiver running?\n";
        close(sock);
        return -1;
    }
    cout << "Connected to receiver.\n";

    ifstream file(filename, ios::binary);
    if (!file.is_open())
    {
        cerr << "Error: Could not open file " << filename << "\n";
        close(sock);
        return -1;
    }

    cout << "--------------------------------------------\n";
    cout << "Starting Transmission...\n";
    cout << "--------------------------------------------\n";

    vector<uint8_t> buffer(MAX_PAYLOAD_SIZE);
    uint32_t sequenceCounter = 0;

    uint8_t sourceMac[6] = {0x00, 0x1A, 0x2B, 0x3C, 0x4D, 0x5E};
    uint8_t destinationMac[6] = {0xFF, 0xEE, 0xDD, 0xCC, 0xBB, 0xAA};




    while (file.read(reinterpret_cast<char *>(buffer.data()), MAX_PAYLOAD_SIZE) || file.gcount() > 0)
    {
        size_t bytesRead = file.gcount();
        vector<uint8_t> payload(buffer.begin(), buffer.begin() + bytesRead);

        if (payload.size() < MIN_PAYLOAD_SIZE)
        {
            payload.resize(MIN_PAYLOAD_SIZE, 0x00);
        }

        std::vector<int> protocolOrder = {0, 1, 2, 3, 4};
        std::random_device rd;
        std::mt19937 g(rd());
        std::shuffle(protocolOrder.begin(), protocolOrder.end(), g);

        bool injectErrorThisChunk = (rand() % 2 == 1);

        for (int i : protocolOrder)
        {


            NetworkFrameHeader header;
            memcpy(header.sourceAddress, sourceMac, 6);
            memcpy(header.targetAddress, destinationMac, 6);
            header.payloadSize = htons(static_cast<uint16_t>(bytesRead));
            header.packetId = htonl(sequenceCounter);
            header.protocolId = i;
            header.reserved = injectErrorThisChunk ? (errorChoice + 1) : 0;

            vector<uint8_t> frame;
            const uint8_t *hdrBytes = reinterpret_cast<const uint8_t *>(&header);
            frame.insert(frame.end(), hdrBytes, hdrBytes + sizeof(NetworkFrameHeader));
            frame.insert(frame.end(), payload.begin(), payload.end());

            if (schemes[i].type == 1)
            {
                uint16_t checksum = ErrorDetection::computeInternetChecksum(frame);
                frame.push_back((checksum >> 8) & 0xFF);
                frame.push_back(checksum & 0xFF);
            }
            else
            {
                uint32_t crc = ErrorDetection::computeCyclicRedundancy(frame, schemes[i].poly, schemes[i].degree);
                int deg = schemes[i].degree;

                if (deg == 8)
                {
                    frame.push_back(crc & 0xFF);
                }
                else if (deg == 10 || deg == 16)
                {
                    frame.push_back((crc >> 8) & 0xFF);
                    frame.push_back(crc & 0xFF);
                }
                else if (deg == 32)
                {
                    frame.push_back((crc >> 24) & 0xFF);
                    frame.push_back((crc >> 16) & 0xFF);
                    frame.push_back((crc >> 8) & 0xFF);
                    frame.push_back(crc & 0xFF);
                }
            }

            if (injectErrorThisChunk)
            {
                switch (errorChoice)
                {
                case 0:
                    ErrorInjection::introduceRandomBitFlip(frame);
                    break;
                case 1:
                    ErrorInjection::introduceDoubleBitFlip(frame);
                    break;
                case 2:
                    ErrorInjection::introduceOddAnomalies(frame);
                    break;
                case 3:
                    ErrorInjection::introduceBurstNoise(frame, 3 + (rand() % 6));
                    break;
                case 4:
                    ErrorInjection::introduceChecksumCollision(frame);
                    break;
                case 5:
                    ErrorInjection::introduceWordSwap(frame);
                    break;
                case 6:
                    ErrorInjection::introduceCRC8Collision(frame);
                    break;
                }
            }
            if (!sendAll(sock, frame.data(), frame.size())) {
                cerr << "Transmission failed.\n";
                close(sock);
                return -1;
            }
            cout << "[SENT] SeqNo: " << sequenceCounter
                 << " | Scheme: " << schemes[i].name << " (ID: " << i << ")"
                 << " | Size: " << frame.size() << " bytes | "
                 << (injectErrorThisChunk ? "[CORRUPTED]" : "[CLEAN]") << "\n";

            usleep(50000);
        }
        sequenceCounter++;
        cout << "--------------------------------------------\n";
    }

    cout << "Transmission Complete. " << sequenceCounter << " datawords sent (" << sequenceCounter * 5 << " total frames).\n";


    file.close();
    close(sock);
    return 0;
}
