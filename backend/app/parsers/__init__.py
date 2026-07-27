from app.parsers import treesitter_parser

# Used elsewhere (e.g. architecture.py's import-graph scoping) as "every
# JS/TS-family extension", regardless of which specific tree-sitter grammar
# ends up parsing a given file's functions/classes below.
JS_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}

# extension -> tree-sitter language name, for the JS/TS family specifically —
# split out from JS_EXTENSIONS because .ts/.tsx need a different grammar
# (and .tsx a third) than plain .js/.jsx/.mjs/.cjs.
JS_TS_LANGUAGES = {
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
}

# extension -> tree-sitter language name (treesitter_parser._LANGUAGE_MODULES key)
TREESITTER_LANGUAGES = {
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".cpp": "cpp",
    ".c": "c",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
}


# extension -> tree-sitter language name, across every supported language —
# the single canonical mapping other modules (file_info.py, dependency.py)
# should use instead of hand-rolling their own partial copy.
LANGUAGE_BY_EXT = {".py": "python", **JS_TS_LANGUAGES, **TREESITTER_LANGUAGES}


def build_registry():
    """extension -> parser instance, each exposing analyze_file(path)."""
    return {ext: treesitter_parser.for_language(lang) for ext, lang in LANGUAGE_BY_EXT.items()}
