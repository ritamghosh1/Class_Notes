#include "ErrorDetection.h"

uint16_t ErrorDetection::computeInternetChecksum(std::vector<uint8_t>& payload) {
    uint32_t acc = 0;
    size_t length = payload.size();
    size_t index = 0;
    
    while (length > 1) {
        uint16_t chunk = (payload[index] << 8) | payload[index + 1];
        acc += chunk;
        index += 2;
        length -= 2;
    }
    
    if (length > 0) {
        uint16_t chunk = (payload.back() << 8) | 0x00;
        acc += chunk;
    }
    
    while (acc >> 16) {
        acc = (acc & 0xFFFF) + (acc >> 16);
    }
    
    return static_cast<uint16_t>(~acc);
}

uint32_t ErrorDetection::computeCyclicRedundancy(std::vector<uint8_t>& payload, uint32_t poly, int bitLen){
    uint32_t registerVal = 0;
    uint32_t boundary = (bitLen == 32) ? 0xFFFFFFFF : (1ULL << bitLen) - 1;
    
    for (size_t k = 0; k < payload.size(); ++k) {
        uint8_t currentByte = payload[k];
        for (int b = 7; b >= 0; --b) {
            uint8_t extractedBit = (currentByte >> b) & 1;
            uint8_t topBit = (registerVal >> (bitLen - 1)) & 1;
            registerVal = (registerVal << 1) | extractedBit;
            if (topBit) {
                registerVal ^= poly;
            }
        }
    }
    
    int padCount = bitLen;
    while(padCount > 0) {
        uint8_t topBit = (registerVal >> (bitLen - 1)) & 1;
        registerVal = (registerVal << 1);
        if (topBit) {
            registerVal ^= poly;
        }
        padCount--;
    }

    return registerVal & boundary;
}