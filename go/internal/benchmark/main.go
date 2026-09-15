package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"runtime"
	"sort"
	"strconv"
	"time"

	orderedjson "github.com/polyspec/ordered-json/go"
)

func digest(value []byte) string { sum := sha256.Sum256(value); return hex.EncodeToString(sum[:]) }
func iterations() int {
	n, _ := strconv.Atoi(os.Getenv("OJ_BENCH_ITERATIONS"))
	if n < 1 {
		return 1000
	}
	return n
}
func setting(name string, fallback int) int {
	n, _ := strconv.Atoi(os.Getenv(name))
	if n < 1 {
		return fallback
	}
	return n
}

type stats struct {
	Median  float64   `json:"median"`
	P95     float64   `json:"p95"`
	Samples []float64 `json:"samples"`
}

func measure(fn func() []byte, iterations, warmup, samples int) (stats, []byte) {
	for i := 0; i < warmup; i++ {
		fn()
	}
	values := make([]float64, 0, samples)
	var out []byte
	for sample := 0; sample < samples; sample++ {
		start := time.Now()
		for i := 0; i < iterations; i++ {
			out = fn()
		}
		values = append(values, float64(time.Since(start).Nanoseconds())/float64(iterations))
	}
	sort.Float64s(values)
	return stats{values[len(values)/2], values[minInt(len(values)-1, int((float64(len(values))*0.95+0.999999))-1)], values}, out
}
func minInt(a, b int) int {
	if a < b {
		return a
	}
	return b
}
func main() {
	n := iterations()
	warmup, samples := setting("OJ_BENCH_WARMUP", 1000), setting("OJ_BENCH_SAMPLES", 9)
	var sink any
	for _, file := range os.Args[1:] {
		source, err := os.ReadFile(file)
		if err != nil {
			panic(err)
		}
		parseOrdered := func() *orderedjson.Value {
			v, err := orderedjson.ParseBytesBorrowed(source)
			if err != nil {
				panic(err)
			}
			return v
		}
		parseStats, _ := measure(func() []byte { sink = parseOrdered(); runtime.KeepAlive(sink); return nil }, n, warmup, samples)
		value := parseOrdered()
		stringifyStats, output := measure(func() []byte {
			out, err := value.Compact()
			if err != nil {
				panic(err)
			}
			return []byte(out)
		}, n, warmup, samples)
		roundtripStats, _ := measure(func() []byte {
			out, err := parseOrdered().Compact()
			if err != nil {
				panic(err)
			}
			return []byte(out)
		}, n, warmup, samples)
		var nativeValue any
		nativeParseStats, _ := measure(func() []byte {
			if err := json.Unmarshal(source, &nativeValue); err != nil {
				panic(err)
			}
			runtime.KeepAlive(nativeValue)
			return nil
		}, n, warmup, samples)
		nativeValue, err = func() (any, error) { var value any; err := json.Unmarshal(source, &value); return value, err }()
		if err != nil {
			panic(err)
		}
		nativeStringifyStats, nativeOutput := measure(func() []byte {
			out, err := json.Marshal(nativeValue)
			if err != nil {
				panic(err)
			}
			return out
		}, n, warmup, samples)
		nativeRoundtripStats, _ := measure(func() []byte {
			var value any
			if err := json.Unmarshal(source, &value); err != nil {
				panic(err)
			}
			out, err := json.Marshal(value)
			if err != nil {
				panic(err)
			}
			return out
		}, n, warmup, samples)
		statsJSON := func(p, s, r stats) string {
			b, _ := json.Marshal(map[string]any{"parse": p.Samples, "stringify": s.Samples, "roundtrip": r.Samples})
			return string(b)
		}
		fmt.Printf("%s\tordered-json\t%f\t%f\t%f\t%f\t%f\t%f\t%s\t%s\t%d\t%d\n", file, parseStats.Median, stringifyStats.Median, roundtripStats.Median, parseStats.P95, stringifyStats.P95, roundtripStats.P95, statsJSON(parseStats, stringifyStats, roundtripStats), digest(output), len(source), len(output))
		fmt.Printf("%s\tnative-json\t%f\t%f\t%f\t%f\t%f\t%f\t%s\t%s\t%d\t%d\n", file, nativeParseStats.Median, nativeStringifyStats.Median, nativeRoundtripStats.Median, nativeParseStats.P95, nativeStringifyStats.P95, nativeRoundtripStats.P95, statsJSON(nativeParseStats, nativeStringifyStats, nativeRoundtripStats), digest(nativeOutput), len(source), len(nativeOutput))
	}
}
