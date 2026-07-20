import re

FUNCTION_DECLARATION_RE = re.compile(r"^\s*(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s*\*?\s+(\w+)\s*\(")
ARROW_ASSIGNMENT_RE = re.compile(r"^\s*(?:export\s+(?:default\s+)?)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(?[^=]*\)?\s*=>")
METHOD_RE = re.compile(r"^\s*(?:public|private|protected|static|async|\*|\s)*(\w+)\s*\([^)]*\)\s*\{")
CLASS_RE = re.compile(r"^\s*(?:export\s+(?:default\s+)?)?class\s+(\w+)")

RESERVED_METHOD_NAMES = {"if", "for", "while", "switch", "catch", "function", "return"}

FROM_RE = re.compile(r"""from\s+['"]([^'"]+)['"]""")
REQUIRE_RE = re.compile(r"""\brequire\(\s*['"]([^'"]+)['"]\s*\)""")
BARE_IMPORT_RE = re.compile(r"""^\s*import\s+['"]([^'"]+)['"]""")

MAX_FUNCTION_CHARS = 4000


def _extract_block(source, start_index):
    """Given the index of a signature match, find the following {...} block
    via brace counting and return the full snippet (signature + body)."""
    brace_index = source.find("{", start_index)
    if brace_index == -1:
        return source[start_index:start_index + 200]

    depth = 0
    for i in range(brace_index, min(len(source), brace_index + MAX_FUNCTION_CHARS)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start_index:i + 1]

    return source[start_index:brace_index + MAX_FUNCTION_CHARS]


def get_functions(source):
    functions = []
    lines = source.split("\n")
    offsets = []
    offset = 0
    for line in lines:
        offsets.append(offset)
        offset += len(line) + 1

    in_class = False
    class_depth = 0

    for i, line in enumerate(lines):
        stripped = line.strip()

        class_match = CLASS_RE.match(line)
        if class_match:
            in_class = True
            class_depth = line.count("{") - line.count("}")
            continue

        if in_class:
            class_depth += line.count("{") - line.count("}")
            if class_depth <= 0:
                in_class = False

        func_match = FUNCTION_DECLARATION_RE.match(line) or ARROW_ASSIGNMENT_RE.match(line)
        if func_match:
            name = func_match.group(1)
            code = _extract_block(source, offsets[i])
            functions.append({"name": name, "code": code})
            continue

        if in_class:
            method_match = METHOD_RE.match(line)
            if method_match:
                name = method_match.group(1)
                if name not in RESERVED_METHOD_NAMES and not stripped.startswith("//"):
                    code = _extract_block(source, offsets[i])
                    functions.append({"name": name, "code": code})

    return functions


def get_classes(source):
    return [m.group(1) for m in CLASS_RE.finditer(source)]


def get_imports(source):
    imports = set()
    imports.update(FROM_RE.findall(source))
    imports.update(REQUIRE_RE.findall(source))
    for line in source.split("\n"):
        bare = BARE_IMPORT_RE.match(line)
        if bare:
            imports.add(bare.group(1))
    return sorted(imports)


def analyze_file(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        source = f.read()

    return {
        "functions": get_functions(source),
        "classes": get_classes(source),
        "imports": get_imports(source),
        # Building an accurate JS call graph needs a real parser; a regex
        # pass would be too noisy to be useful, so this stays empty.
        "graph": {},
    }


if __name__ == "__main__":
    import sys
    result = analyze_file(sys.argv[1] if len(sys.argv) > 1 else "app/js_parser.py")
    print(result)
