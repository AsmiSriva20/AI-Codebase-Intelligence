"""Generic, grammar-driven parser: given a language name, uses that language's
tree-sitter grammar package plus a small query set (below) to extract
functions/classes/imports. Adding a language means adding one entry to
_LANGUAGE_MODULES and one entry to _QUERIES — not a new parser class.

Python and JS/TS/TSX are handled here too (not separate hand-rolled parsers) —
see _HAS_CALL_GRAPH below for the one place Python still gets special treatment.
"""
import importlib

from tree_sitter import Language, Parser, Query, QueryCursor

_LANGUAGE_MODULES = {
    "python": "tree_sitter_python",
    "javascript": "tree_sitter_javascript",
    "typescript": "tree_sitter_typescript",
    "tsx": "tree_sitter_typescript",
    "go": "tree_sitter_go",
    "rust": "tree_sitter_rust",
    "java": "tree_sitter_java",
    "cpp": "tree_sitter_cpp",
    "c": "tree_sitter_c",
    "ruby": "tree_sitter_ruby",
    "php": "tree_sitter_php",
    "csharp": "tree_sitter_c_sharp",
}

# Most grammar modules expose a plain `language()` function; a few package
# multiple grammar variants behind different names in the same module.
_LANGUAGE_FUNC_OVERRIDES = {
    "php": "language_php",
    "typescript": "language_typescript",
    "tsx": "language_tsx",
}

_JS_LIKE_FUNCTION_QUERY = (
    "[(function_declaration name: (identifier) @name) "
    "(generator_function_declaration name: (identifier) @name) "
    "(method_definition name: (property_identifier) @name) "
    "(variable_declarator name: (identifier) @name value: (arrow_function)) "
    "(variable_declarator name: (identifier) @name value: (function_expression))] @definition.function"
)
_JS_LIKE_IMPORT_QUERY = (
    '[(import_statement) '
    '(call_expression function: (identifier) @_fn (#eq? @_fn "require")) '
    '(call_expression function: (import))] @import'
)

# C/C++ function_definition nodes don't expose a `name` field directly (the
# identifier is nested inside a chain of pointer/function/qualified
# declarators), so those two languages resolve the name in Python instead of
# via a `@name` capture — see _extract_declarator_name.
_QUERIES = {
    "python": {
        "function": "(function_definition name: (identifier) @name) @definition.function",
        "class": "(class_definition name: (identifier) @name) @definition.class",
        "import": "[(import_statement) (import_from_statement)] @import",
    },
    "javascript": {
        "function": _JS_LIKE_FUNCTION_QUERY,
        "class": "(class_declaration name: (identifier) @name) @definition.class",
        "import": _JS_LIKE_IMPORT_QUERY,
    },
    "typescript": {
        "function": _JS_LIKE_FUNCTION_QUERY,
        "class": "[(class_declaration name: (type_identifier) @name) "
                  "(interface_declaration name: (type_identifier) @name)] @definition.class",
        "import": _JS_LIKE_IMPORT_QUERY,
    },
    "tsx": {
        "function": _JS_LIKE_FUNCTION_QUERY,
        "class": "[(class_declaration name: (type_identifier) @name) "
                  "(interface_declaration name: (type_identifier) @name)] @definition.class",
        "import": _JS_LIKE_IMPORT_QUERY,
    },
    "go": {
        "function": "[(function_declaration name: (identifier) @name) "
                     "(method_declaration name: (field_identifier) @name)] @definition.function",
        "class": "(type_spec name: (type_identifier) @name type: (struct_type)) @definition.class",
        "import": "(import_spec) @import",
    },
    "rust": {
        "function": "(function_item name: (identifier) @name) @definition.function",
        "class": "[(struct_item name: (type_identifier) @name) "
                  "(enum_item name: (type_identifier) @name) "
                  "(trait_item name: (type_identifier) @name)] @definition.class",
        "import": "(use_declaration) @import",
    },
    "java": {
        "function": "[(method_declaration name: (identifier) @name) "
                     "(constructor_declaration name: (identifier) @name)] @definition.function",
        "class": "[(class_declaration name: (identifier) @name) "
                  "(interface_declaration name: (identifier) @name) "
                  "(enum_declaration name: (identifier) @name)] @definition.class",
        "import": "(import_declaration) @import",
    },
    "c": {
        "function": "(function_definition) @definition.function",
        "class": "(struct_specifier name: (type_identifier) @name) @definition.class",
        "import": "(preproc_include) @import",
    },
    "cpp": {
        "function": "(function_definition) @definition.function",
        "class": "[(class_specifier name: (type_identifier) @name) "
                  "(struct_specifier name: (type_identifier) @name)] @definition.class",
        "import": "(preproc_include) @import",
    },
    "ruby": {
        "function": "[(method name: (identifier) @name) "
                     "(singleton_method name: (identifier) @name)] @definition.function",
        "class": "[(class name: (constant) @name) (module name: (constant) @name)] @definition.class",
        "import": '(call method: (identifier) @method-name '
                  '(#any-of? @method-name "require" "require_relative")) @import',
    },
    "php": {
        "function": "[(function_definition name: (name) @name) "
                     "(method_declaration name: (name) @name)] @definition.function",
        "class": "[(class_declaration name: (name) @name) "
                  "(interface_declaration name: (name) @name) "
                  "(trait_declaration name: (name) @name)] @definition.class",
        "import": "(namespace_use_declaration) @import",
    },
    "csharp": {
        "function": "[(method_declaration name: (identifier) @name) "
                     "(constructor_declaration name: (identifier) @name)] @definition.function",
        "class": "[(class_declaration name: (identifier) @name) "
                  "(interface_declaration name: (identifier) @name) "
                  "(struct_declaration name: (identifier) @name) "
                  "(record_declaration name: (identifier) @name)] @definition.class",
        "import": "(using_directive) @import",
    },
}

_NEEDS_DECLARATOR_WALK = {"c", "cpp"}

# Cross-file call resolution lives in analysis/callgraph.py — this is just a
# per-file, unresolved "function name -> called names" map, matching what the
# hand-rolled python_parser.py used to build (indexer.py feeds it into
# /calls/{name}). No other language attempted this before the parsers were
# merged into this generic engine, so none of them start attempting it now.
_HAS_CALL_GRAPH = {"python"}
_CALL_GRAPH_NODE_TYPES = {
    "python": {"function_node": "function_definition", "call_node": "call"},
}

_cache = {}  # lang_name -> (Parser, {query_key: Query})


def _load(lang_name):
    if lang_name not in _cache:
        module = importlib.import_module(_LANGUAGE_MODULES[lang_name])
        func_name = _LANGUAGE_FUNC_OVERRIDES.get(lang_name, "language")
        ts_language = Language(getattr(module, func_name)())
        parser = Parser(ts_language)
        compiled = {key: Query(ts_language, qstr) for key, qstr in _QUERIES[lang_name].items()}
        _cache[lang_name] = (parser, compiled)
    return _cache[lang_name]


def _extract_declarator_name(node):
    """Walk a C/C++ declarator chain (pointer/function/qualified) to find the identifier."""
    declarator = node.child_by_field_name("declarator")
    while declarator is not None:
        if declarator.type in ("identifier", "field_identifier", "qualified_identifier",
                                "destructor_name", "operator_name"):
            return declarator.text.decode()
        nxt = declarator.child_by_field_name("declarator")
        if nxt is None:
            for child in declarator.children:
                if child.type in ("identifier", "field_identifier", "qualified_identifier"):
                    return child.text.decode()
            return ""
        declarator = nxt
    return ""


def _match_pairs(query, root):
    """Yield each match's capture dict (name -> [nodes]) for a query, one per match."""
    cursor = QueryCursor(query)
    for _pattern_index, captures in cursor.matches(root):
        yield captures


def _get_functions(lang_name, compiled, root):
    query = compiled.get("function")
    if query is None:
        return []

    functions = []
    for captures in _match_pairs(query, root):
        def_nodes = captures.get("definition.function")
        if not def_nodes:
            continue
        def_node = def_nodes[0]

        if lang_name in _NEEDS_DECLARATOR_WALK:
            name = _extract_declarator_name(def_node)
        else:
            name_nodes = captures.get("name")
            name = name_nodes[0].text.decode() if name_nodes else ""

        functions.append({"name": name, "code": def_node.text.decode(errors="ignore")})

    return functions


def _get_classes(compiled, root):
    query = compiled.get("class")
    if query is None:
        return []

    classes = []
    for captures in _match_pairs(query, root):
        name_nodes = captures.get("name")
        if name_nodes:
            classes.append(name_nodes[0].text.decode())

    return classes


def _get_imports(compiled, root):
    query = compiled.get("import")
    if query is None:
        return []

    cursor = QueryCursor(query)
    captures = cursor.captures(root)
    return [n.text.decode() for n in captures.get("import", [])]


def _build_call_graph(lang_name, root):
    """Per-file (not cross-file resolved — see callgraph.py for that) map of
    function name -> called names, tracking the innermost enclosing function
    as we walk. Mirrors the original python_parser.py's build_dependency_graph
    exactly (same recursive, parameter-scoped algorithm), just relocated here."""
    node_types = _CALL_GRAPH_NODE_TYPES.get(lang_name)
    if node_types is None:
        return {}

    function_node_type = node_types["function_node"]
    call_node_type = node_types["call_node"]
    graph = {}

    def walk(node, current_function):
        if node.type == function_node_type:
            name_node = node.child_by_field_name("name")
            if name_node is not None:
                current_function = name_node.text.decode()
                graph.setdefault(current_function, [])

        if node.type == call_node_type and current_function:
            func = node.child_by_field_name("function")
            if func is not None:
                graph[current_function].append(func.text.decode())

        for child in node.children:
            walk(child, current_function)

    walk(root, None)
    return graph


class _LanguageParser:
    def __init__(self, lang_name):
        self.lang_name = lang_name

    def analyze_file(self, path):
        parser, compiled = _load(self.lang_name)

        with open(path, "rb") as f:
            source = f.read()
        tree = parser.parse(source)
        root = tree.root_node

        return {
            "functions": _get_functions(self.lang_name, compiled, root),
            "classes": _get_classes(compiled, root),
            "imports": _get_imports(compiled, root),
            "graph": _build_call_graph(self.lang_name, root) if self.lang_name in _HAS_CALL_GRAPH else {},
        }


_instances = {}


def for_language(lang_name):
    if lang_name not in _LANGUAGE_MODULES:
        raise ValueError(f"No tree-sitter grammar configured for language '{lang_name}'")
    if lang_name not in _instances:
        _instances[lang_name] = _LanguageParser(lang_name)
    return _instances[lang_name]
