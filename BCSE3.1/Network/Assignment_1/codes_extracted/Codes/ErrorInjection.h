#ifndef ERROR_INJECTION_H
#define ERROR_INJECTION_H

#include <vector>
#include <cstdint>

class ErrorInjection {
public:
    static void introduceRandomBitFlip(std::vector<uint8_t>& packet);
    static void introduceDoubleBitFlip(std::vector<uint8_t>& packet);
    static void introduceOddAnomalies(std::vector<uint8_t>& packet);
    static void introduceBurstNoise(std::vector<uint8_t>& packet, int noiseLength);
    static void introduceChecksumCollision(std::vector<uint8_t>& packet);
    static void introduceWordSwap(std::vector<uint8_t>& packet);
    static void introduceCRC8Collision(std::vector<uint8_t>& packet);
};

#endif