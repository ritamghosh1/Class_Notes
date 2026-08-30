#include "ErrorInjection.h"
#include <random>
#include <chrono>
#include <unordered_set>

void ErrorInjection::introduceRandomBitFlip(std::vector<uint8_t>& packet) {
    if (packet.empty()) return;
    int numBits = packet.size() * 8;
    if (numBits < 3) return;
    std::default_random_engine engine(static_cast<unsigned int>(std::chrono::system_clock::now().time_since_epoch().count()));
    std::uniform_int_distribution<int> dist(0, numBits - 1);
    int target = dist(engine);
    packet[target / 8] ^= (1 << (target % 8));
}

void ErrorInjection::introduceDoubleBitFlip(std::vector<uint8_t>& packet) {
    if (packet.empty()) return;
    int numBits = packet.size() * 8;
    if (numBits < 3) return;
    std::default_random_engine engine(static_cast<unsigned int>(std::chrono::system_clock::now().time_since_epoch().count()));
    std::uniform_int_distribution<int> dist(0, numBits - 1);
    int firstTarget = dist(engine);
    int secondTarget;
    bool found = false;
    while (!found) {
        secondTarget = dist(engine);
        if (std::abs(firstTarget - secondTarget) > 1) {
            found = true;
        }
    }
    packet[firstTarget / 8] ^= (1 << (firstTarget % 8));
    packet[secondTarget / 8] ^= (1 << (secondTarget % 8));
}

void ErrorInjection::introduceOddAnomalies(std::vector<uint8_t>& packet) {
    if (packet.empty()) return;
    int numBits = packet.size() * 8;
    std::default_random_engine engine(static_cast<unsigned int>(std::chrono::system_clock::now().time_since_epoch().count()));
    std::uniform_int_distribution<int> distOdd(0, 2);
    int anomalyCount = 3 + (distOdd(engine) * 2);
    if (anomalyCount > numBits) {
        anomalyCount = (numBits % 2 != 0) ? numBits : numBits - 1;
        if (anomalyCount <= 0) return;
    }
    std::unordered_set<int> mutatedBits;
    std::uniform_int_distribution<int> bitDist(0, numBits - 1);
    while (mutatedBits.size() < static_cast<size_t>(anomalyCount)) {
        mutatedBits.insert(bitDist(engine));
    }
    for (auto it = mutatedBits.begin(); it != mutatedBits.end(); ++it) {
        int target = *it;
        packet[target / 8] ^= (1 << (target % 8));
    }
}

void ErrorInjection::introduceBurstNoise(std::vector<uint8_t>& packet, int noiseLength) {
    if (packet.empty() || noiseLength <= 1) return;
    int numBits = packet.size() * 8;
    if (noiseLength > numBits) {
        noiseLength = numBits; 
    }
    std::default_random_engine engine(static_cast<unsigned int>(std::chrono::system_clock::now().time_since_epoch().count()));
    std::uniform_int_distribution<int> startDist(0, numBits - noiseLength);
    int startPos = startDist(engine);
    int k = 0;
    while (k < noiseLength) {
        int target = startPos + k;
        packet[target / 8] ^= (1 << (target % 8));
        k++;
    }
}

void ErrorInjection::introduceChecksumCollision(std::vector<uint8_t>& packet) {
    if (packet.size() <= 2) return;

    size_t dataSize = packet.size() - 2;
    if (dataSize < 4) return;

    size_t numWords = dataSize / 2;
    std::default_random_engine engine(static_cast<unsigned int>(std::chrono::system_clock::now().time_since_epoch().count()));
    std::uniform_int_distribution<size_t> wordDist(0, numWords - 1);
    std::uniform_int_distribution<int> bitDist(0, 15);

    auto flipWordBit = [&](size_t wordIndex, int bitPosition) {
        size_t byteBase = wordIndex * 2;
        if (bitPosition >= 8) {
            packet[byteBase] ^= static_cast<uint8_t>(1 << (bitPosition - 8));
        } else {
            packet[byteBase + 1] ^= static_cast<uint8_t>(1 << bitPosition);
        }
    };

    for (int attempt = 0; attempt < 200; ++attempt) {
        size_t firstWord = wordDist(engine);
        size_t secondWord = wordDist(engine);
        if (firstWord == secondWord) continue;

        int bitPos = bitDist(engine);
        uint16_t wordA = (static_cast<uint16_t>(packet[firstWord * 2]) << 8) | packet[firstWord * 2 + 1];
        uint16_t wordB = (static_cast<uint16_t>(packet[secondWord * 2]) << 8) | packet[secondWord * 2 + 1];
        bool bitA = (wordA >> bitPos) & 1;
        bool bitB = (wordB >> bitPos) & 1;

        if (bitA != bitB) {
            flipWordBit(firstWord, bitPos);
            flipWordBit(secondWord, bitPos);
            return;
        }
    }

    introduceRandomBitFlip(packet);
}

void ErrorInjection::introduceWordSwap(std::vector<uint8_t>& packet) {
    if (packet.size() < 4) return;
    
    // Swap two 16-bit words in the payload (excluding header to not break parsing)
    // We'll operate on the payload area. NetworkFrameHeader is 16 bytes.
    size_t headerSize = 16;
    if (packet.size() <= headerSize + 4) return;
    
    size_t dataSize = packet.size() - headerSize - 4; // exclude header and trailer
    if (dataSize < 4) return;
    
    size_t numWords = dataSize / 2;
    std::default_random_engine engine(static_cast<unsigned int>(std::chrono::system_clock::now().time_since_epoch().count()));
    std::uniform_int_distribution<size_t> wordDist(0, numWords - 1);
    
    size_t w1 = wordDist(engine);
    size_t w2 = wordDist(engine);
    while (w1 == w2) {
        w2 = wordDist(engine);
    }
    
    size_t idx1 = headerSize + w1 * 2;
    size_t idx2 = headerSize + w2 * 2;
    
    std::swap(packet[idx1], packet[idx2]);
    std::swap(packet[idx1+1], packet[idx2+1]);
}

void ErrorInjection::introduceCRC8Collision(std::vector<uint8_t>& packet) {
    if (packet.size() < 18) return;
    size_t headerSize = 16;
    
    std::default_random_engine engine(static_cast<unsigned int>(std::chrono::system_clock::now().time_since_epoch().count()));
    std::uniform_int_distribution<size_t> posDist(headerSize, packet.size() - 3);
    size_t pos = posDist(engine);
    
    // CRC-8 polynomial is 0x1D5 (1 1101 0101).
    // To cause a collision, the error polynomial must be a multiple of the generator polynomial.
    // The generator itself is 9 bits: 111010101.
    // If we XOR this into the bitstream starting at a byte boundary (MSB), we flip:
    // Byte 0: 1 1 1 0 1 0 1 0 = 0xEA
    // Byte 1: 1 0 0 0 0 0 0 0 = 0x80
    packet[pos] ^= 0xEA;
    packet[pos+1] ^= 0x80;
}