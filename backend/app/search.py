def find_function(index, name):
    return index["functions"].get(name)  
#we use get here to return None if the function is not found,
# instead of raising a KeyError jo ki api ke liye troublesome ho sakta hai


def find_class(index, name):
    return index["classes"].get(name)


def find_import(index, module):
    return index["imports"].get(module)


def find_calls(index, function):
    return index["call_graph"].get(function)


