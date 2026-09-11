// Test driver only: calls the pinned upstream header, not a copied algorithm.
#include <yoga/numeric/Comparison.h>
#include <yoga/algorithm/Cache.h>
#include <yoga/algorithm/PixelGrid.h>
#include <yoga/algorithm/CalculateLayout.h>

#include <bit>
#include <cstdint>
#include <cstdio>
#include <limits>

static void cache_reference();
static void leaf_reference();

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
  leaf_reference();
}

static int leaf_calls = 0;
static float leaf_content_width = 7.0f;

static YGSize leaf_measure(YGNodeConstRef, float, YGMeasureMode, float, YGMeasureMode) {
  ++leaf_calls;
  return {leaf_content_width, 2.0f};
}

static void leaf_reference() {
  using namespace facebook::yoga;
  auto config = YGConfigNew();
  YGConfigSetUseWebDefaults(config, true);
  auto leaf = YGNodeNewWithConfig(config);
  YGNodeStyleSetPadding(leaf, YGEdgeLeft, 1.0f);
  YGNodeStyleSetPadding(leaf, YGEdgeRight, 3.0f);
  YGNodeStyleSetPadding(leaf, YGEdgeTop, 1.0f);
  YGNodeStyleSetPadding(leaf, YGEdgeBottom, 2.0f);
  YGNodeStyleSetMargin(leaf, YGEdgeLeft, 2.0f);
  YGNodeSetMeasureFunc(leaf, leaf_measure);
  LayoutData data{};
  for (int step = 0; step < 5; ++step) {
    if (step == 4) {
      leaf_content_width = 13.0f;
      YGNodeMarkDirty(leaf);
    }
    bool visited = calculateLayoutInternal(resolveRef(leaf), 20.0f, 10.0f,
        Direction::LTR, SizingMode::FitContent, SizingMode::MaxContent,
        40.0f, 20.0f, step >= 2, LayoutPassReason::kInitial, data, 0,
        step < 3 ? 1 : step - 1);
    std::printf("leaf %s %s %d", visited ? "true" : "false",
        YGNodeIsDirty(leaf) ? "true" : "false", leaf_calls);
    emit(resolveRef(leaf)->getLayout().measuredDimension(Dimension::Width));
    emit(resolveRef(leaf)->getLayout().measuredDimension(Dimension::Height));
    std::printf("\n");
  }
  YGNodeFree(leaf);
  YGConfigFree(config);
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
