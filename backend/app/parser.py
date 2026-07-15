from tree_sitter import Language, Parser
import tree_sitter_python

PYTHON_LANGUAGE = Language(tree_sitter_python.language())
parser = Parser(PYTHON_LANGUAGE)


def parse_file(path):
    with open(path, "rb") as f:
        source = f.read()
    tree = parser.parse(source)
    return tree, source


def get_functions(node, source, functions):

    if node.type == "function_definition":

        name = ""

        for child in node.children:
            if child.type == "identifier":
                name = child.text.decode()

        code = source[node.start_byte:node.end_byte].decode()

        functions.append({
            "name": name,
            "code": code
        })

    for child in node.children:
        get_functions(child, source, functions)


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


def build_dependency_graph(node, graph, current_function=None):

    if node.type == "function_definition":

        for child in node.children:
            if child.type == "identifier":
                current_function = child.text.decode()
                graph[current_function] = []

    if node.type == "call" and current_function:

        function = node.child_by_field_name("function")

        if function:
            graph[current_function].append(function.text.decode())

    for child in node.children:
        build_dependency_graph(child, graph, current_function)


def analyze_file(path):

    tree, source = parse_file(path)

    functions = []
    classes = []
    imports = []
    graph = {}

    get_functions(tree.root_node, source, functions)
    get_classes(tree.root_node, classes)
    get_imports(tree.root_node, imports)
    build_dependency_graph(tree.root_node, graph)

    return {
        "functions": functions,
        "classes": classes,
        "imports": imports,
        "graph": graph
    }


if __name__ == "__main__":
    result = analyze_file("app/main.py")
    print(result)