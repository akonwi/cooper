// Package retainedyoga is the narrow native layout boundary for Cooper's
// retained-tree prototype. It hides Tess's fallible, Yoga-shaped API from Ard.
package retainedyoga

import (
	"math"

	tess "github.com/AnatoleLucet/tess"
)

// MeasureLimit converts Yoga's non-negative floating-point constraints into
// terminal cell counts without exposing that conversion to public Ard APIs.
func MeasureLimit(value float32) int {
	if value <= 0 || math.IsNaN(float64(value)) {
		return 0
	}
	if math.IsInf(float64(value), 1) || float64(value) >= float64(math.MaxInt) {
		return math.MaxInt
	}
	return int(value)
}

type Value struct {
	Kind  int
	Value float32
}

type Edges struct {
	Top    Value
	Right  Value
	Bottom Value
	Left   Value
}

type Style struct {
	Display    int
	Direction  int
	AlignItems int
	AlignSelf  int
	Justify    int
	Wrap       int
	Position   int
	Overflow   int

	Width     Value
	Height    Value
	MinWidth  Value
	MinHeight Value
	MaxWidth  Value
	MaxHeight Value
	Top       Value
	Right     Value
	Bottom    Value
	Left      Value
	Basis     Value
	Grow      float32
	Shrink    float32
	Padding   Edges
	Margin    Edges
	Gap       Value
	Border    int
}

type Layout struct {
	Left   int
	Top    int
	Width  int
	Height int
}

type Size struct {
	Width  float32
	Height float32
}

type MeasureFunc func(width float32, widthMode int, height float32, heightMode int) Size

type Node struct {
	node *tess.Node
}

func NewNode() *Node {
	node, err := tess.NewNode()
	if err != nil {
		panic(err)
	}
	return &Node{node: node}
}

func must(err error) {
	if err != nil {
		panic(err)
	}
}

func valueOf(value Value) tess.Value {
	switch value.Kind {
	case 0:
		// Tess ignores Undefined in several setters instead of clearing the
		// previous Yoga value. A point NaN reaches Yoga's normal undefined
		// representation and resets dimensions, constraints, basis, and offsets.
		return tess.Point(float32(math.NaN()))
	case 1:
		return tess.Auto()
	case 2:
		return tess.Point(value.Value)
	case 3:
		return tess.Percent(value.Value)
	case 4:
		return tess.MaxContent()
	case 5:
		return tess.FitContent()
	case 6:
		return tess.Stretch()
	default:
		panic("invalid Cooper retained length kind")
	}
}

func spacingValueOf(value Value, allowAuto bool) tess.Value {
	switch value.Kind {
	case 0:
		return tess.Point(0)
	case 1:
		if allowAuto {
			return tess.Auto()
		}
	case 2:
		return tess.Point(value.Value)
	case 3:
		return tess.Percent(value.Value)
	}
	panic("unsupported Cooper retained spacing unit")
}

func edgesOf(edges Edges, allowAuto bool) tess.Edges {
	return tess.Edges{
		Top:    spacingValueOf(edges.Top, allowAuto),
		Right:  spacingValueOf(edges.Right, allowAuto),
		Bottom: spacingValueOf(edges.Bottom, allowAuto),
		Left:   spacingValueOf(edges.Left, allowAuto),
	}
}

func directionOf(value int) tess.FlexDirection {
	switch value {
	case 0:
		return tess.Column
	case 1:
		return tess.ColumnReverse
	case 2:
		return tess.Row
	case 3:
		return tess.RowReverse
	default:
		panic("invalid Cooper retained flex direction")
	}
}

func alignOf(value int) tess.FlexAlign {
	switch value {
	case 0:
		return tess.AlignAuto
	case 1:
		return tess.AlignStretch
	case 2:
		return tess.AlignBaseline
	case 3:
		return tess.AlignStart
	case 4:
		return tess.AlignEnd
	case 5:
		return tess.AlignCenter
	case 6:
		return tess.AlignSpaceBetween
	case 7:
		return tess.AlignSpaceAround
	case 8:
		return tess.AlignSpaceEvenly
	default:
		panic("invalid Cooper retained alignment")
	}
}

func justifyOf(value int) tess.FlexJustify {
	switch value {
	case 0:
		return tess.JustifyStart
	case 1:
		return tess.JustifyEnd
	case 2:
		return tess.JustifyCenter
	case 3:
		return tess.JustifySpaceBetween
	case 4:
		return tess.JustifySpaceAround
	case 5:
		return tess.JustifySpaceEvenly
	default:
		panic("invalid Cooper retained justification")
	}
}

func wrapOf(value int) tess.FlexWrap {
	switch value {
	case 0:
		return tess.NoWrap
	case 1:
		return tess.Wrap
	case 2:
		return tess.WrapReverse
	default:
		panic("invalid Cooper retained wrapping")
	}
}

func positionOf(value int) tess.PositionType {
	switch value {
	case 0:
		return tess.Static
	case 1:
		return tess.Relative
	case 2:
		return tess.Absolute
	default:
		panic("invalid Cooper retained position")
	}
}

func overflowOf(value int) tess.OverflowType {
	switch value {
	case 0:
		return tess.Visible
	case 1:
		return tess.Hidden
	case 2:
		return tess.Scroll
	default:
		panic("invalid Cooper retained overflow")
	}
}

func displayOf(value int) tess.DisplayType {
	switch value {
	case 0:
		return tess.Flex
	case 1:
		return tess.Contents
	case 2:
		return tess.None
	default:
		panic("invalid Cooper retained display")
	}
}

func (n *Node) Apply(style Style) {
	must(n.node.SetDisplay(displayOf(style.Display)))
	must(n.node.SetFlexDirection(directionOf(style.Direction)))
	must(n.node.SetAlignItems(alignOf(style.AlignItems)))
	must(n.node.SetAlignSelf(alignOf(style.AlignSelf)))
	must(n.node.SetJustifyContent(justifyOf(style.Justify)))
	must(n.node.SetFlexWrap(wrapOf(style.Wrap)))
	must(n.node.SetPosition(positionOf(style.Position)))
	must(n.node.SetOverflow(overflowOf(style.Overflow)))
	must(n.node.SetWidth(valueOf(style.Width)))
	must(n.node.SetHeight(valueOf(style.Height)))
	must(n.node.SetMinWidth(valueOf(style.MinWidth)))
	must(n.node.SetMinHeight(valueOf(style.MinHeight)))
	must(n.node.SetMaxWidth(valueOf(style.MaxWidth)))
	must(n.node.SetMaxHeight(valueOf(style.MaxHeight)))
	must(n.node.SetTop(valueOf(style.Top)))
	must(n.node.SetRight(valueOf(style.Right)))
	must(n.node.SetBottom(valueOf(style.Bottom)))
	must(n.node.SetLeft(valueOf(style.Left)))
	must(n.node.SetFlexBasis(valueOf(style.Basis)))
	must(n.node.SetFlexGrow(style.Grow))
	must(n.node.SetFlexShrink(style.Shrink))
	must(n.node.SetPadding(edgesOf(style.Padding, false)))
	must(n.node.SetMargin(edgesOf(style.Margin, true)))
	must(n.node.SetGap(tess.Gap{All: spacingValueOf(style.Gap, false)}))
	must(n.node.SetBorder(tess.Edges{All: tess.Point(float32(style.Border))}))
}

func (n *Node) SetMeasureFunc(measure MeasureFunc) {
	n.node.SetMeasureFunc(func(_ *tess.Node, width float32, widthMode tess.MeasureMode, height float32, heightMode tess.MeasureMode) tess.Size {
		measured := measure(width, int(widthMode), height, int(heightMode))
		return tess.Size{Width: measured.Width, Height: measured.Height}
	})
}

func (n *Node) MarkDirty() {
	n.node.MarkDirty()
}

func (n *Node) AppendChild(child *Node) {
	n.node.AppendChild(child.node)
}

func (n *Node) InsertChild(child *Node, index int) {
	n.node.InsertChild(child.node, index)
}

func (n *Node) RemoveChild(child *Node) {
	n.node.RemoveChild(child.node)
}

func (n *Node) Compute(width, height int) {
	availableWidth := float32(width)
	availableHeight := float32(height)
	// Tess treats exact zero as undefined. A positive subnormal preserves a
	// bounded zero through Yoga's point-scale rounding.
	if width == 0 {
		availableWidth = math.SmallestNonzeroFloat32
	}
	if height == 0 {
		availableHeight = math.SmallestNonzeroFloat32
	}
	must(n.node.ComputeLayout(tess.Container{
		Width:     availableWidth,
		Height:    availableHeight,
		Direction: tess.LTR,
	}))
}

func (n *Node) Layout() Layout {
	layout := n.node.GetLayout()
	return Layout{
		Left:   int(layout.Left()),
		Top:    int(layout.Top()),
		Width:  int(layout.Width()),
		Height: int(layout.Height()),
	}
}

func (n *Node) Free() {
	if n.node == nil {
		return
	}
	n.node.Free()
	n.node = nil
}
