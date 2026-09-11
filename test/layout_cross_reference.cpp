#include <yoga/Yoga.h>
#include <cassert>
#include <cstdio>

// Independent native reference for the corresponding visitor regression.
static YGSize measure(YGNodeConstRef, float, YGMeasureMode, float, YGMeasureMode) {
  return {6, 2};
}

int main() {
  auto config = YGConfigNew();
  YGConfigSetUseWebDefaults(config, true);
  for (int scenario = 0; scenario < 3; ++scenario) {
    auto root = YGNodeNewWithConfig(config);
    YGNodeStyleSetWidth(root, 10);
    YGNodeStyleSetHeight(root, 12);
    YGNodeStyleSetAlignItems(root, YGAlignStretch);
    YGNodeStyleSetAlignContent(root, YGAlignFlexStart);
    YGNodeStyleSetFlexWrap(root, scenario == 0 ? YGWrapWrap : YGWrapNoWrap);
    const int count = scenario == 0 ? 2 : 1;
    for (int i = 0; i < count; ++i) {
      auto child = YGNodeNewWithConfig(config);
      YGNodeStyleSetWidth(child, 6);
      YGNodeSetMeasureFunc(child, measure);
      if (scenario == 1) {
        YGNodeStyleSetMarginAuto(child, YGEdgeTop);
        YGNodeStyleSetMargin(child, YGEdgeBottom, 1);
      }
      YGNodeInsertChild(root, child, i);
    }
    YGNodeCalculateLayout(root, 10, 12, YGDirectionLTR);
    for (int i = 0; i < count; ++i) {
      const float height = YGNodeLayoutGetHeight(YGNodeGetChild(root, i));
      assert(height == (scenario == 2 ? 12 : 2));
      std::printf("scenario%d child%d height=%.0f\n", scenario, i, height);
    }
    YGNodeFreeRecursive(root);
  }
  YGConfigFree(config);
}
