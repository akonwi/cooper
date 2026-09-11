// Test driver only: calls the pinned upstream header, not a copied algorithm.
#include <yoga/numeric/Comparison.h>
#include <yoga/algorithm/Cache.h>
#include <yoga/algorithm/PixelGrid.h>
// Include the pinned translation unit to exercise its private axis helpers,
// rather than duplicate their algorithms in this reference driver.
#include <yoga/algorithm/CalculateLayout.cpp>

#include <bit>
#include <cstdint>
#include <cstdio>
#include <limits>

static void cache_reference();
static void leaf_reference();
static void axis_reference();
static void length_reference();
static void basis_reference();
static void fallback_reference();
static void flex_reference();

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
  axis_reference();
  length_reference();
  basis_reference();
  fallback_reference();
  flex_reference();
}

static void flex_reference() {
  using namespace facebook::yoga;
  auto config = YGConfigNew();
  YGConfigSetUseWebDefaults(config, true);
  for (bool minimum : {false, true}) for (bool maximum : {false, true})
  for (bool fractional : {false, true}) for (float space : {-20.0f, 0.0f, 6.0f, 40.0f}) {
    auto parent = YGNodeNewWithConfig(config);
    YGNodeStyleSetFlexDirection(parent, YGFlexDirectionRow);
    YGNodeStyleSetAlignItems(parent, YGAlignFlexStart);
    const float bases[] = {8, 13, 5}, mins[] = {6, 4, 0}, maxes[] = {10, 14, 7};
    const float grows[] = {0.25f, 1, 3}, shrinks[] = {1, 2, 0.5f};
    for (int i = 0; i < 3; ++i) {
      auto child = YGNodeNewWithConfig(config);
      YGNodeStyleSetHeight(child, 1);
      YGNodeStyleSetFlexGrow(child, fractional ? grows[i] : 1);
      YGNodeStyleSetFlexShrink(child, fractional ? shrinks[i] : 1);
      if (minimum) YGNodeStyleSetMinWidth(child, mins[i]);
      if (maximum) YGNodeStyleSetMaxWidth(child, maxes[i]);
      YGNodeInsertChild(parent, child, i);
      resolveRef(child)->processDimensions();
      resolveRef(child)->setLayoutComputedFlexBasis(FloatOptional(bases[i]));
    }
    auto iterator = resolveRef(parent)->getLayoutChildren().begin();
    auto line = calculateFlexLine(resolveRef(parent), Direction::LTR, 100, 100, 100, 100, iterator, 0);
    line.layout.remainingFreeSpace = space;
    distributeFreeSpaceFirstPass(line, Direction::LTR, FlexDirection::Row, 100, 100, 100, 100);
    std::printf("flex");
    emit(line.sizeConsumed);
    emit(line.layout.remainingFreeSpace);
    emit(line.layout.totalFlexGrowFactors);
    emit(line.layout.totalFlexShrinkScaledFactors);
    LayoutData data{};
    const float delta = distributeFreeSpaceSecondPass(line, resolveRef(parent), FlexDirection::Row,
        FlexDirection::Column, Direction::LTR, 100, 100, 100, 10, 100, 10, false,
        SizingMode::StretchFit, false, data, 0, 1);
    for (int i = 0; i < 3; ++i)
      emit(resolveRef(YGNodeGetChild(parent, i))->getLayout().measuredDimension(Dimension::Width));
    emit(delta);
    emit(space - delta);
    std::printf("\n");
    YGNodeFreeRecursive(parent);
  }
  YGConfigFree(config);
}

static float fallback_width, fallback_height;
static YGMeasureMode fallback_wm, fallback_hm;
static int fallback_calls;
static YGSize fallback_measure(YGNodeConstRef, float w, YGMeasureMode wm, float h, YGMeasureMode hm) {
  ++fallback_calls;
  fallback_width = w; fallback_height = h; fallback_wm = wm; fallback_hm = hm;
  return {wm == YGMeasureModeUndefined ? 31.0f : std::min(31.0f, w),
          hm == YGMeasureModeUndefined ? 17.0f : std::min(17.0f, h)};
}

static void fallback_reference() {
  using namespace facebook::yoga;
  auto config = YGConfigNew();
  YGConfigSetUseWebDefaults(config, true);
  for (bool row : {true, false}) for (bool scroll : {false, true})
  for (bool stretch : {false, true}) for (bool bounded : {false, true}) {
    auto parent = YGNodeNewWithConfig(config);
    auto child = YGNodeNewWithConfig(config);
    YGNodeStyleSetFlexDirection(parent, row ? YGFlexDirectionRow : YGFlexDirectionColumn);
    YGNodeStyleSetOverflow(parent, scroll ? YGOverflowScroll : YGOverflowVisible);
    YGNodeStyleSetAlignItems(parent, stretch ? YGAlignStretch : YGAlignFlexStart);
    YGNodeStyleSetMargin(child, YGEdgeLeft, 3);
    YGNodeStyleSetMargin(child, YGEdgeTop, 2);
    YGNodeStyleSetPadding(child, YGEdgeLeft, 4);
    YGNodeStyleSetPadding(child, YGEdgeTop, 1);
    if (bounded) { YGNodeStyleSetMaxWidth(child, 10); YGNodeStyleSetMaxHeight(child, 6); }
    YGNodeSetMeasureFunc(child, fallback_measure);
    resolveRef(child)->processDimensions();
    fallback_calls = 0;
    LayoutData data{};
    for (int visit = 0; visit < 2; ++visit) {
      computeFlexBasisForChild(resolveRef(parent), resolveRef(child), 20, SizingMode::StretchFit,
          12, 40, 30, SizingMode::StretchFit, Direction::LTR, data, 0, 1);
      std::printf("fallback %d %d %d", fallback_calls, fallback_wm, fallback_hm);
      emit(fallback_width); emit(fallback_height);
      emit(resolveRef(child)->getLayout().measuredDimension(Dimension::Width));
      emit(resolveRef(child)->getLayout().measuredDimension(Dimension::Height));
      emit(resolveRef(child)->getLayout().computedFlexBasis.unwrap());
      std::printf(" %d\n", resolveRef(child)->getLayout().computedFlexBasisGeneration);
    }
    YGNodeFree(child); YGNodeFree(parent);
  }
  YGConfigFree(config);
}

static int basis_calls;
static YGSize basis_measure(YGNodeConstRef, float, YGMeasureMode, float, YGMeasureMode) {
  ++basis_calls;
  return {11.0f, 3.0f};
}

static void basis_reference() {
  using namespace facebook::yoga;
  auto config = YGConfigNew();
  YGConfigSetUseWebDefaults(config, true);
  const StyleSizeLength bases[] = {StyleSizeLength::points(0), StyleSizeLength::points(5),
      StyleSizeLength::percent(25), StyleSizeLength::ofAuto(), StyleSizeLength::ofMaxContent()};
  for (bool row : {true, false}) for (auto basis : bases)
  for (float available : {YGUndefined, 0.0f, 20.0f}) for (float owner : {YGUndefined, 40.0f})
  for (auto dimension : {StyleSizeLength::points(7), StyleSizeLength::percent(50), StyleSizeLength::ofAuto()})
  for (float padding : {0.0f, 9.0f}) for (float previous : {YGUndefined, 17.0f}) {
    auto parent = YGNodeNewWithConfig(config);
    auto child = YGNodeNewWithConfig(config);
    YGNodeStyleSetFlexDirection(parent, row ? YGFlexDirectionRow : YGFlexDirectionColumn);
    YGNodeStyleSetAlignItems(parent, YGAlignFlexStart);
    resolveRef(child)->style().setFlexBasis(basis);
    resolveRef(child)->style().setDimension(row ? Dimension::Width : Dimension::Height, dimension);
    YGNodeStyleSetPadding(child, row ? YGEdgeLeft : YGEdgeTop, padding);
    YGNodeSetMeasureFunc(child, basis_measure);
    resolveRef(child)->processDimensions();
    resolveRef(child)->setLayoutComputedFlexBasis(FloatOptional(previous));
    resolveRef(child)->setLayoutComputedFlexBasisGeneration(4);
    basis_calls = 0;
    LayoutData data{};
    computeFlexBasisForChild(resolveRef(parent), resolveRef(child), row ? available : 73.0f,
        SizingMode::FitContent, row ? 73.0f : available, row ? owner : 73.0f,
        row ? 73.0f : owner, SizingMode::FitContent, Direction::LTR, data, 0, 9);
    const bool selected = basis_calls == 0;
    std::printf("basis %s", selected ? "true" : "false");
    // The untranslated measurement branch is tested only as a required fallback.
    emit(selected ? resolveRef(child)->getLayout().computedFlexBasis.unwrap() : previous);
    std::printf(" %d\n", selected ? resolveRef(child)->getLayout().computedFlexBasisGeneration : 4);
    YGNodeFree(child);
    YGNodeFree(parent);
  }
  YGConfigFree(config);
}

static void length_reference() {
  using namespace facebook::yoga;
  const StyleSizeLength lengths[] = {
      StyleSizeLength::undefined(), StyleSizeLength::ofAuto(),
      StyleSizeLength::points(0), StyleSizeLength::points(7),
      StyleSizeLength::points(7.00005f), StyleSizeLength::points(7.0002f),
      StyleSizeLength::percent(0), StyleSizeLength::percent(33.3f),
      StyleSizeLength::percent(100), StyleSizeLength::ofMaxContent(),
      StyleSizeLength::ofFitContent(), StyleSizeLength::ofStretch()};
  for (auto value : lengths) {
    Node node;
    node.style().setDimension(Dimension::Width, value);
    node.processDimensions();
    for (float reference : {YGUndefined, 0.0f, 38.0f, 113.7f, 1000000.0f}) {
      std::printf("length %d", static_cast<int>(static_cast<YGValue>(value).unit));
      emit(reference);
      emit(value.resolve(reference).unwrap());
      std::printf(" %s\n", node.hasDefiniteLength(Dimension::Width, reference) ? "true" : "false");
    }
  }
  for (auto preferred : lengths) {
    for (auto minimum : lengths) {
      for (auto maximum : lengths) {
        // Independent cases: avoid the pinned pool's indexed-value to keyword
        // mutation bug. Cooper uses value structs, not Yoga's packed storage.
        Node node;
        node.style().setDimension(Dimension::Width, preferred);
        node.style().setMinDimension(Dimension::Width, minimum);
        node.style().setMaxDimension(Dimension::Width, maximum);
        node.processDimensions();
        auto processed = node.getProcessedDimension(Dimension::Width);
        std::printf("processed %d", static_cast<int>(static_cast<YGValue>(processed).unit));
        emit(processed.resolve(40.0f).unwrap());
        std::printf("\n");
      }
    }
  }
}

static void axis_reference() {
  using namespace facebook::yoga;
  const float nan = std::numeric_limits<float>::quiet_NaN();
  const float values[] = {nan, -2.0f, 0.0f, 2.0f, 11.0f,
      std::numeric_limits<float>::infinity(), 3.0e30f};
  auto leaf = YGNodeNew();
  for (auto mode : {SizingMode::MaxContent, SizingMode::FitContent, SizingMode::StretchFit}) {
    for (float available : values) {
      for (float padding : {0.0f, 4.0f, 9.0f}) {
        for (float minimum : {nan, 0.0f, 5.0f, 13.0f}) {
          for (float maximum : {nan, 0.0f, 5.0f, 13.0f}) {
            for (float margin : {0.0f, 3.0f}) {
              YGNodeStyleSetMinWidth(leaf, minimum);
              YGNodeStyleSetMaxWidth(leaf, maximum);
              YGNodeStyleSetMargin(leaf, YGEdgeLeft, margin);
              auto constrained_mode = mode;
              float constrained = available;
              constrainMaxSizeForMode(resolveRef(leaf), Direction::LTR,
                  FlexDirection::Row, 40.0f, 40.0f, &constrained_mode, &constrained);
              std::printf("axis");
              emit(available); emit(padding); emit(minimum); emit(maximum); emit(margin);
              std::printf(" %d %d", static_cast<int>(mode), static_cast<int>(constrained_mode));
              emit(constrained);
              emit(calculateAvailableInnerDimension(resolveRef(leaf), Direction::LTR,
                  Dimension::Width, available - margin, padding, 40.0f, 40.0f));
              std::printf("\n");
            }
          }
        }
      }
    }
  }
  YGNodeFree(leaf);
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
