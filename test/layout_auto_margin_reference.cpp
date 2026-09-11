#include <yoga/Yoga.h>
#include <cstdio>
// Native reference for the accepted per-line auto-margin adaptation.
int main() {
  auto config = YGConfigNew();
  YGConfigSetUseWebDefaults(config, true);
  auto root = YGNodeNewWithConfig(config);
  YGNodeStyleSetWidth(root, 10);
  YGNodeStyleSetHeight(root, 2);
  YGNodeStyleSetFlexDirection(root, YGFlexDirectionRow);
  YGNodeStyleSetFlexWrap(root, YGWrapWrap);
  YGNodeStyleSetAlignContent(root, YGAlignFlexStart);
  for (int i = 0; i < 2; ++i) {
    auto child = YGNodeNewWithConfig(config);
    YGNodeStyleSetWidth(child, 6);
    YGNodeStyleSetHeight(child, 1);
    YGNodeStyleSetFlexShrink(child, 0);
    YGNodeStyleSetMarginAuto(child, YGEdgeLeft);
    YGNodeInsertChild(root, child, i);
  }
  YGNodeCalculateLayout(root, 10, 2, YGDirectionLTR);
  for (int i = 0; i < 2; ++i) {
    auto child = YGNodeGetChild(root, i);
    std::printf("child%d x=%.0f y=%.0f width=%.0f\n", i, YGNodeLayoutGetLeft(child), YGNodeLayoutGetTop(child), YGNodeLayoutGetWidth(child));
  }
  YGNodeFreeRecursive(root);
  YGConfigFree(config);
}
