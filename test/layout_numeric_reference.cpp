// Test driver only: calls the pinned upstream header, not a copied algorithm.
#include <yoga/numeric/Comparison.h>

#include <bit>
#include <cstdint>
#include <cstdio>
#include <limits>

static void emit(float value) {
  if (value != value) {
    std::printf(" nan");
  } else {
    std::printf(" %08x", std::bit_cast<std::uint32_t>(value));
  }
}

int main() {
  const float values[] = {
      std::numeric_limits<float>::quiet_NaN(),
      std::numeric_limits<float>::infinity(),
      -std::numeric_limits<float>::infinity(),
      0.0f, -0.0f, -7.0f, 2.0f,
      0.000099f, 0.0001f, 0.000101f,
      -0.000099f, -0.0001f, -0.000101f,
  };
  for (float a : values) {
    for (float b : values) {
      emit(a);
      emit(b);
      std::printf(" %s %s %s",
                  facebook::yoga::isUndefined(a) ? "true" : "false",
                  facebook::yoga::isDefined(a) ? "true" : "false",
                  facebook::yoga::inexactEquals(a, b) ? "true" : "false");
      emit(facebook::yoga::maxOrDefined(a, b));
      emit(facebook::yoga::minOrDefined(a, b));
      std::printf("\n");
    }
  }
}
