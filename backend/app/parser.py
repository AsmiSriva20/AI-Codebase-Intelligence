from tree_sitter import Language, Parser
import tree_sitter_python

PYTHON_LANGUAGE = Language(tree_sitter_python.language())

parser = Parser(PYTHON_LANGUAGE)

def parse_file(path):
    with open(path, "rb") as f:
        return parser.parse(f.read())


def get_functions(node, functions):

    if node.type == "function_definition":
        for child in node.children:
            if child.type == "identifier":
                functions.append(child.text.decode())

    for child in node.children:
        get_functions(child, functions)


def get_classes(node, classes):
    if node.type == "class_definition":
        for child in node.children:
            if child.type == "identifier":
                classes.append(child.text.decode())

    for child in node.children:
        get_classes(child, classes)

def get_imports(node, imports):
    if node.type in ["import_statement", "import_from_statement"]:
        imports.append(node.text.decode())

    for child in node.children:
        get_imports(child, imports)

if __name__ == "__main__":
    tree = parse_file("app/main.py")

    functions = []
    classes = []
    imports = []

    tree = parse_file("app/main.py")

    get_functions(tree.root_node, functions)
    get_classes(tree.root_node, classes)
    get_imports(tree.root_node, imports)

    print("Functions:", functions)
    print("Classes:", classes)
    print("Imports:", imports)