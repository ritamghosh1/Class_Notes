#ifndef ERROR_DETECTION_H
#define ERROR_DETECTION_H

#include <vector>
#include <cstdint>
#include <string>

struct CRC{
    uint32_t polynomial;
    int degree;
};

class ErrorDetection {
public:
    static uint16_t computeInternetChecksum(std::vector<uint8_t>& payload);
    static uint32_t computeCyclicRedundancy(std::vector<uint8_t>& payload, uint32_t poly, int bitLen);
};

#endif