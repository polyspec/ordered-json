// Reports the exported API of the package, one symbol per line, from the source
// declarations rather than a hand-written list.
package main

import (
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

func receiver(declaration *ast.FuncDecl) string {
	if declaration.Recv == nil || len(declaration.Recv.List) == 0 {
		return ""
	}
	switch expression := declaration.Recv.List[0].Type.(type) {
	case *ast.StarExpr:
		if name, ok := expression.X.(*ast.Ident); ok {
			return name.Name
		}
	case *ast.Ident:
		return expression.Name
	}
	return ""
}

func main() {
	directory := "."
	if len(os.Args) > 1 {
		directory = os.Args[1]
	}
	set := token.NewFileSet()
	packages, err := parser.ParseDir(set, directory, func(info os.FileInfo) bool {
		return !strings.HasSuffix(info.Name(), "_test.go")
	}, 0)
	if err != nil {
		panic(err)
	}
	symbols := map[string]struct{}{}
	for _, pkg := range packages {
		for _, file := range pkg.Files {
			for _, declaration := range file.Decls {
				switch node := declaration.(type) {
				case *ast.FuncDecl:
					if !node.Name.IsExported() {
						continue
					}
					if owner := receiver(node); owner != "" {
						if ast.IsExported(owner) {
							symbols[owner+"."+node.Name.Name] = struct{}{}
						}
						continue
					}
					symbols[node.Name.Name] = struct{}{}
				case *ast.GenDecl:
					for _, spec := range node.Specs {
						switch item := spec.(type) {
						case *ast.TypeSpec:
							if item.Name.IsExported() {
								symbols[item.Name.Name] = struct{}{}
							}
						case *ast.ValueSpec:
							for _, name := range item.Names {
								if name.IsExported() {
									symbols[name.Name] = struct{}{}
								}
							}
						}
					}
				}
			}
		}
	}
	names := make([]string, 0, len(symbols))
	for name := range symbols {
		names = append(names, name)
	}
	sort.Strings(names)
	fmt.Println(strings.Join(names, "\n"))
	_ = filepath.Base(directory)
}
