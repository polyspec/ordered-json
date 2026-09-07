// Adapter only. The common verifier supplies every example and expectation.
package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"github.com/ordered-json/ordered-json/go"
	"strings"
)

func quote(s string) string {
	out, err := json.Marshal(s)
	if err != nil {
		panic(err)
	}
	return string(out)
}
func text(v *orderedjson.Value) string {
	units, err := v.StringUnits()
	if err != nil {
		panic(err)
	}
	return orderedjson.StringFromUnits(units).Raw()
}
func tree(v *orderedjson.Value) string {
	switch v.Kind() {
	case orderedjson.ObjectKind:
		members, err := v.Members()
		if err != nil {
			panic(err)
		}
		parts := []string{}
		for _, m := range members {
			parts = append(parts, "["+text(m.Key)+","+tree(m.Value)+"]")
		}
		return `["object",[` + strings.Join(parts, ",") + `]]`
	case orderedjson.ArrayKind:
		items, err := v.Items()
		if err != nil {
			panic(err)
		}
		parts := []string{}
		for _, item := range items {
			parts = append(parts, tree(item))
		}
		return `["array",[` + strings.Join(parts, ",") + `]]`
	case orderedjson.StringKind:
		return `["string",` + text(v) + `]`
	case orderedjson.NumberKind:
		raw, err := v.NumberLiteral()
		if err != nil {
			panic(err)
		}
		return `["number",` + quote(raw) + `]`
	case orderedjson.BooleanKind:
		value, err := v.BooleanValue()
		if err != nil {
			panic(err)
		}
		return fmt.Sprintf(`["boolean",%t]`, value)
	default:
		return `["null"]`
	}
}
func rebuild(v *orderedjson.Value) *orderedjson.Value {
	switch v.Kind() {
	case orderedjson.ObjectKind:
		members, err := v.Members()
		if err != nil {
			panic(err)
		}
		for i, m := range members {
			members[i].Value = rebuild(m.Value)
		}
		out, err := orderedjson.Object(members)
		if err != nil {
			panic(err)
		}
		return out
	case orderedjson.ArrayKind:
		items, err := v.Items()
		if err != nil {
			panic(err)
		}
		for i, item := range items {
			items[i] = rebuild(item)
		}
		out, err := orderedjson.Array(items)
		if err != nil {
			panic(err)
		}
		return out
	default:
		return v
	}
}
func main() {
	scanner := bufio.NewScanner(os.Stdin)
	for scanner.Scan() {
		source, err := os.ReadFile(scanner.Text())
		if err != nil {
			panic(err)
		}
		value, err := orderedjson.ParseBytes(source)
		if err != nil {
			fmt.Println(`{"ok":false}`)
			continue
		}
		compact, err := value.Compact()
		if err != nil {
			panic(err)
		}
		rebuilt, err := rebuild(value).Compact()
		if err != nil {
			panic(err)
		}
		fmt.Printf("{\"ok\":true,\"raw\":%s,\"compact\":%s,\"tree\":%s,\"rebuilt\":%s}\n",
			quote(value.Raw()), quote(compact), tree(value), quote(rebuilt))
	}
	if err := scanner.Err(); err != nil {
		panic(err)
	}
}
