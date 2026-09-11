// Test driver only: calls the pinned upstream header, not a copied algorithm.
#include <yoga/numeric/Comparison.h>
#include <yoga/algorithm/Cache.h>
#include <yoga/algorithm/PixelGrid.h>

#include <bit>
#include <cstdint>
#include <cstdio>
#include <limits>

static void cache_reference();

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
  cache_reference();
}

static void cache_reference() {
  using namespace facebook::yoga;
  const float values[] = {std::numeric_limits<float>::quiet_NaN(), -0.5f,
      -0.50005f, 0.0f, 4.49f, 4.49995f, 4.5f, 5.0f, 7.0f, 10.0f,
      8388608.0f, 3.0e30f};
  const SizingMode modes[] = {SizingMode::MaxContent, SizingMode::FitContent,
      SizingMode::StretchFit};
  for (float value : values) {
    std::printf("round");
    emit(value);
    emit(roundValueToPixelGrid(value, 1.0, false, false));
    std::printf("\n");
  }
  for (bool round : {false, true}) {
    Config config(nullptr);
    config.setPointScaleFactor(round ? 1.0f : 0.0f);
    for (auto mode : modes) {
      for (auto old_mode : modes) {
        for (float available : values) {
          for (float old_available : values) {
            for (float computed : {-1.0f, 5.0f}) {
              bool hit = canUseCachedMeasurement(mode, available,
                  SizingMode::StretchFit, 3.0f, old_mode, old_available,
                  SizingMode::StretchFit, 3.0f, computed, 3.0f, 2.0f, 0.0f,
                  &config);
              std::printf("cache %s\n", hit ? "true" : "false");
            }
          }
        }
      }
    }
  }
}
