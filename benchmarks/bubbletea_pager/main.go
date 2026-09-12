package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"runtime"
	"strings"
	"time"
)

type session struct {
	step  func(int)
	view  func() string
	close func()
}

type sample struct {
	Kind   string `json:"kind"`
	NS     int64  `json:"ns"`
	Bytes  uint64 `json:"go_bytes"`
	Allocs uint64 `json:"go_allocations"`
	GC     uint32 `json:"gc_cycles"`
	Hash   string `json:"frame_sha256,omitempty"`
}

func canonical(value string) string {
	rows := strings.Split(strings.TrimSuffix(value, "\n"), "\n")
	if len(rows) != 24 {
		panic(fmt.Sprintf("expected 24 rows, got %d", len(rows)))
	}
	for i, row := range rows {
		if len(row) > 80 {
			panic(fmt.Sprintf("row %d exceeds viewport: %d", i, len(row)))
		}
		rows[i] = row + strings.Repeat(" ", 80-len(row))
	}
	return strings.Join(rows, "\n")
}

func expected(lines []string, offset int) string {
	rows := make([]string, 24)
	for i := range rows {
		row := lines[offset+i]
		if len(row) > 80 {
			row = row[:80]
		}
		rows[i] = row + strings.Repeat(" ", 80-len(row))
	}
	return strings.Join(rows, "\n")
}

func main() {
	verify := flag.Bool("verify", false, "verify every frame in a separate, untimed process")
	flag.Parse()
	lines := make([]string, 10000)
	for i := range lines {
		lines[i] = fmt.Sprintf("%05d | %s", i, strings.Repeat("abcdefghij", 1+(i*37)%14))
	}
	start := time.Now()
	model := prepare(lines)
	startup := time.Since(start).Nanoseconds()
	defer model.close()
	if *verify && canonical(model.view()) != expected(lines, 0) {
		panic("initial frame mismatch")
	}
	samples := make([]sample, 0, 240)
	offset := 0
	var capture string
	for i := 0; i < 240; i++ {
		direction, kind := 1, "down"
		if i >= 100 && i < 200 {
			direction, kind = -1, "up"
		}
		if i >= 200 {
			direction, kind = 0, "unchanged"
		}
		offset += direction
		if *verify {
			model.step(direction)
			frame := canonical(model.view())
			if frame != expected(lines, offset) {
				panic(fmt.Sprintf("frame mismatch at step %d offset %d", i, offset))
			}
			hash := sha256.Sum256([]byte(frame))
			samples = append(samples, sample{Kind: kind, Hash: hex.EncodeToString(hash[:])})
			if i == 99 {
				capture = frame
			}
			continue
		}
		var before, after runtime.MemStats
		runtime.ReadMemStats(&before)
		start = time.Now()
		model.step(direction)
		elapsed := time.Since(start).Nanoseconds()
		runtime.ReadMemStats(&after)
		samples = append(samples, sample{kind, elapsed, after.TotalAlloc - before.TotalAlloc,
			after.Mallocs - before.Mallocs, after.NumGC - before.NumGC, ""})
	}
	final := canonical(model.view())
	if final != expected(lines, offset) {
		panic("final frame mismatch")
	}
	hash := sha256.Sum256([]byte(final))
	json.NewEncoder(os.Stdout).Encode(map[string]any{"verify": *verify, "startup_ns": startup, "samples": samples, "capture": capture, "final_frame_sha256": hex.EncodeToString(hash[:])})
}
