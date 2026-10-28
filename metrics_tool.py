import ast
from collections import defaultdict

filename = input("Enter the filename: ")

try:
    with open(filename, "r") as file:
        tree = ast.parse(file.read())
except FileNotFoundError:
    print(f"File '{filename}' not found.")
except SyntaxError:
    print(f"File '{filename}' contains invalid Python syntax.")
# else:
#     print(f"File '{filename}' is valid.")

class weightedMethodsAnalyzer (ast.NodeVisitor):
    def visit_ClassDef(self, node):
        # Filter the class body for function definitions
        # This counts standard methods, classmethods, staticmethods, and __init__
        counter = 0
        for n in node.body:
            if isinstance(n, ast.FunctionDef):
                counter += 1
        
        print(f"Class '{node.name}' WMC = {counter}")
            
        # Continue traversing the tree in case there are nested classes
        self.generic_visit(node)


class ClassCohesionAnalyzer:
    def __init__(self, tree):
        self.tree = tree
        self.results = {}
        
    def analyze(self):
        """Finds and analyzes all classes in the source code."""
        class_nodes = [n for n in ast.walk(self.tree) if isinstance(n, ast.ClassDef)]
        
        results = {}
        for class_node in class_nodes:
            results[class_node.name] = self._calculate_lcom4(class_node)
            
        return results

    def _calculate_lcom4(self, class_node: ast.ClassDef) -> dict:
        # 1. Identify all valid methods (ignoring __init__ by default as it touches everything)
        methods = [
            n.name for n in class_node.body 
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name != '__init__'
        ]
        
        if not methods:
            return {"lcom4": 0, "components": []}

        # 2. Track variable usage and method calls per method
        method_vars = defaultdict(set)
        method_calls = defaultdict(set)
        
        for node in class_node.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name != '__init__':
                # Find instance variables (self.attribute)
                for sub_node in ast.walk(node):
                    if isinstance(sub_node, ast.Attribute) and isinstance(sub_node.value, ast.Name) and sub_node.value.id == 'self':
                        method_vars[node.name].add(sub_node.attr)
                    
                    # Find internal method calls (self.other_method())
                    if isinstance(sub_node, ast.Call) and isinstance(sub_node.func, ast.Attribute):
                        if isinstance(sub_node.func.value, ast.Name) and sub_node.func.value.id == 'self':
                            if sub_node.func.attr in methods:
                                method_calls[node.name].add(sub_node.func.attr)

        # 3. Build an adjacency list (Graph) connecting methods that share states or call each other
        graph = defaultdict(set)
        for m in methods:
            graph[m] = set()

        for i in range(len(methods)):
            for j in range(i + 1, len(methods)):
                m1, m2 = methods[i], methods[j]
                
                # Check shared variables
                shared_vars = method_vars[m1].intersection(method_vars[m2])
                # Check direct calls
                is_called = m2 in method_calls[m1] or m1 in method_calls[m2]
                
                if shared_vars or is_called:
                    graph[m1].add(m2)
                    graph[m2].add(m1)

        # 4. Find Connected Components using Breadth-First Search (BFS)
        visited = set()
        components = []
        
        for method in methods:
            if method not in visited:
                component = []
                queue = [method]
                visited.add(method)
                
                while queue:
                    current = queue.pop(0)
                    component.append(current)
                    
                    for neighbor in graph[current]:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)
                            
                components.append(component)
                
        return {
            "lcom4": len(components),
            "components": components
        }


class ClassCouplingAnalyzer(ast.NodeVisitor):
    def __init__(self):
        # Maps ClassName -> Set of other classes it depends on
        self.dependencies = defaultdict(set)
        self.current_class = None
        self.all_classes = set()

    def visit_ClassDef(self, node):
        old_class = self.current_class
        self.current_class = node.name
        self.all_classes.add(node.name)
        
        # Track Inheritance coupling
        for base in node.bases:
            if isinstance(base, ast.Name):
                self.dependencies[self.current_class].add(base.id)
            elif isinstance(base, ast.Attribute):
                # Handles module names like module.ClassName
                self.dependencies[self.current_class].add(base.attr)

        # Traverse inside the class body to check for other couplings
        self.generic_visit(node)
        self.current_class = old_class

    def visit_Name(self, node):
        # Catches instantiations, type hints, or static references
        if self.current_class and node.id != self.current_class:
            self.dependencies[self.current_class].add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node):
        # Handles external calls or namespaced references
        if self.current_class and isinstance(node.value, ast.Name):
            self.dependencies[self.current_class].add(node.attr)
        self.generic_visit(node)



class RFCCalculator(ast.NodeVisitor):
    def __init__(self):
        # Maps ClassName -> Set of defined methods (M)
        self.defined_methods = defaultdict(set)
        # Maps ClassName -> Set of external methods called (R)
        self.called_methods = defaultdict(set)
        
        self.current_class = None
        self.current_method = None
        self.all_classes = set()

    def visit_ClassDef(self, node):
        old_class = self.current_class
        self.current_class = node.name
        self.all_classes.add(node.name)
        
        # 1. Collect all methods defined inside this class
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.defined_methods[self.current_class].add(item.name)
                
        # 2. Traverse the contents of the class to capture method calls
        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node):
        old_method = self.current_method
        self.current_method = node.name
        self.generic_visit(node)
        self.current_method = old_method

    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)

    def visit_Call(self, node):
        # We only look for method calls inside a class's method context
        if self.current_class and self.current_method:
            func = node.func
            
            # Case 1: Standard object calls like: obj.method()
            if isinstance(func, ast.Attribute):
                # If it's calling another method on self (self.other_method())
                if isinstance(func.value, ast.Name) and func.value.id == 'self':
                    # We only log it as an external dependency if it wasn't defined locally
                    # (Though LCOM tracks internal calls, RFC definition focuses on outward reach)
                    self.called_methods[self.current_class].add(func.attr)
                else:
                    # External method invocation
                    self.called_methods[self.current_class].add(func.attr)
                    
            # Case 2: Global/Direct function calls like: print(), len(), or local_func()
            elif isinstance(func, ast.Name):
                self.called_methods[self.current_class].add(func.id)
                
        self.generic_visit(node)
    








print("Weighted Methods Analysis:")
print("==================================")
weightedMethodsAnalyzer().visit(tree)
print("--------------------------------------")
print("Class Cohesion Analysis:")
print("==================================")
analyzer = ClassCohesionAnalyzer(tree)
analysis_results = analyzer.analyze()

for class_name, metrics in analysis_results.items():
    print(f"Class '{class_name}' LOCM = {metrics['lcom4']}")

print("--------------------------------------")
analyzer = ClassCouplingAnalyzer()
analyzer.visit(tree)

# Filter dependencies so we only report coupling between internal classes
# (This prevents noise like 'print', 'str', 'list' from flooding results)
print("Class Coupling Analysis:")
print("=========================")

for source_class in analyzer.all_classes:
    # Find which *defined classes* this specific class couples with
    coupled_targets = analyzer.dependencies[source_class].intersection(analyzer.all_classes)
    
    if coupled_targets:
        print(f"Class '{source_class}' CBO = {len(coupled_targets)}")
    else:
        print(f"Class '{source_class}' CBO = 0")

print("--------------------------------------")
calculator = RFCCalculator()
calculator.visit(tree)

print("Response for Class (RFC) Analysis:")
print("==================================")

for class_name in calculator.all_classes:
    m_set = calculator.defined_methods[class_name]
    r_set = calculator.called_methods[class_name]
    
    # Avoid double-counting internal self-calls (RFC = |M| + unique external calls)
    external_only_calls = r_set - m_set
    rfc_score = len(m_set) + len(external_only_calls)

    print(f"Class '{class_name}': RFC = {rfc_score}")

