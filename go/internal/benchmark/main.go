package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"runtime"
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
func main() {
	n := iterations()
	var sink any
	for _, file := range os.Args[1:] {
		source, err := os.ReadFile(file)
		if err != nil {
			panic(err)
		}
		measure := func(fn func() []byte) (float64, []byte) {
			start := time.Now()
			var out []byte
			for i := 0; i < n; i++ {
				out = fn()
			}
			return float64(time.Since(start).Nanoseconds()) / float64(n), out
		}
		parseOrdered := func() *orderedjson.Value {
			v, err := orderedjson.ParseBytes(source)
			if err != nil {
				panic(err)
			}
			return v
		}
		parseNs, _ := measure(func() []byte { sink = parseOrdered(); runtime.KeepAlive(sink); return nil })
		value := parseOrdered()
		stringifyNs, output := measure(func() []byte {
			out, err := value.Compact()
			if err != nil {
				panic(err)
			}
			return []byte(out)
		})
		roundtripNs, _ := measure(func() []byte {
			out, err := parseOrdered().Compact()
			if err != nil {
				panic(err)
			}
			return []byte(out)
		})
		var nativeValue any
		nativeParseNs, _ := measure(func() []byte {
			if err := json.Unmarshal(source, &nativeValue); err != nil {
				panic(err)
			}
			runtime.KeepAlive(nativeValue)
			return nil
		})
		nativeValue, err = func() (any, error) { var value any; err := json.Unmarshal(source, &value); return value, err }()
		if err != nil {
			panic(err)
		}
		nativeStringifyNs, nativeOutput := measure(func() []byte {
			out, err := json.Marshal(nativeValue)
			if err != nil {
				panic(err)
			}
			return out
		})
		nativeRoundtripNs, _ := measure(func() []byte {
			var value any
			if err := json.Unmarshal(source, &value); err != nil {
				panic(err)
			}
			out, err := json.Marshal(value)
			if err != nil {
				panic(err)
			}
			return out
		})
		fmt.Printf("%s\tordered-json\t%f\t%f\t%f\t%s\t%d\t%d\n", file, parseNs, stringifyNs, roundtripNs, digest(output), len(source), len(output))
		fmt.Printf("%s\tnative-json\t%f\t%f\t%f\t%s\t%d\t%d\n", file, nativeParseNs, nativeStringifyNs, nativeRoundtripNs, digest(nativeOutput), len(source), len(nativeOutput))
	}
}
