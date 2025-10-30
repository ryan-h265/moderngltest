#!/usr/bin/env env python3
"""
Python Project Overview Generator
Generates a compact, token-optimized overview of all functions, classes, and methods
in a Python project for LLM context pre-seeding.
"""

import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class FunctionInfo:
    """Represents a function or method."""
    name: str
    full_namespace: str
    signature: str
    return_type: str
    description: str
    line_number: int
    file_path: str
    related_objects: Set[str] = field(default_factory=set)


@dataclass
class ClassInfo:
    """Represents a class."""
    name: str
    full_namespace: str
    bases: List[str]
    methods: List[FunctionInfo]
    line_number: int
    file_path: str
    description: str
    siblings: Set[str] = field(default_factory=set)


class ProjectAnalyzer:
    """Analyzes Python project structure."""
    
    EXCLUDED_DIRS = {
        'venv', 'env', '.venv', '.env',
        '__pycache__', '.git', '.github',
        'node_modules', '.pytest_cache',
        '.mypy_cache', '.tox', 'dist',
        'build', '*.egg-info', '.eggs'
    }
    
    def __init__(self, project_path: str, include_line_numbers: bool = True):
        self.project_path = Path(project_path).resolve()
        self.include_line_numbers = include_line_numbers
        self.classes: Dict[str, ClassInfo] = {}
        self.functions: Dict[str, FunctionInfo] = {}
        self.module_classes: Dict[str, List[str]] = {}  # module -> list of class names
        
    def should_exclude_dir(self, dir_path: Path) -> bool:
        """Check if directory should be excluded."""
        dir_name = dir_path.name
        return any(
            dir_name.startswith(pattern.rstrip('*')) if pattern.endswith('*') else dir_name == pattern
            for pattern in self.EXCLUDED_DIRS
        )
    
    def extract_docstring_summary(self, node: ast.AST) -> str:
        """Extract first line of docstring."""
        docstring = ast.get_docstring(node)
        if docstring:
            # Get first non-empty line
            lines = [line.strip() for line in docstring.split('\n') if line.strip()]
            return lines[0] if lines else ""
        return ""
    
    def get_type_annotation(self, annotation: Optional[ast.AST]) -> str:
        """Convert AST annotation to string."""
        if annotation is None:
            return ""
        return ast.unparse(annotation)
    
    def extract_function_signature(self, node: ast.FunctionDef, class_name: str = "") -> Tuple[str, str]:
        """Extract function signature and return type."""
        args = []
        
        # Regular arguments
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {self.get_type_annotation(arg.annotation)}"
            args.append(arg_str)
        
        # *args
        if node.args.vararg:
            vararg_str = f"*{node.args.vararg.arg}"
            if node.args.vararg.annotation:
                vararg_str += f": {self.get_type_annotation(node.args.vararg.annotation)}"
            args.append(vararg_str)
        
        # **kwargs
        if node.args.kwarg:
            kwarg_str = f"**{node.args.kwarg.arg}"
            if node.args.kwarg.annotation:
                kwarg_str += f": {self.get_type_annotation(node.args.kwarg.annotation)}"
            args.append(kwarg_str)
        
        signature = f"{node.name}({', '.join(args)})"
        return_type = self.get_type_annotation(node.returns) if node.returns else "None"
        
        return signature, return_type
    
    def extract_related_objects(self, node: ast.AST) -> Set[str]:
        """Extract names of classes/functions referenced in the code."""
        related = set()
        
        for child in ast.walk(node):
            # Function calls
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    related.add(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    # Get the full attribute chain
                    related.add(ast.unparse(child.func))
            
            # Name references (variables, classes)
            elif isinstance(child, ast.Name):
                if isinstance(child.ctx, ast.Load):  # Only loading, not storing
                    related.add(child.id)
            
            # Attribute access
            elif isinstance(child, ast.Attribute):
                if isinstance(child.ctx, ast.Load):
                    related.add(ast.unparse(child))
        
        # Remove common built-ins and noise
        builtins = {'self', 'cls', 'True', 'False', 'None', 'str', 'int', 'float', 
                   'list', 'dict', 'set', 'tuple', 'bool', 'type', 'len', 'range',
                   'print', 'super', 'property'}
        related = {r for r in related if r not in builtins and not r.startswith('_')}
        
        return related
    
    def analyze_file(self, file_path: Path):
        """Analyze a single Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=str(file_path))
            module_name = self.get_module_name(file_path)
            
            # Track classes in this module for sibling detection
            module_class_names = []
            
            for node in ast.walk(tree):
                # Handle classes
                if isinstance(node, ast.ClassDef):
                    self.process_class(node, module_name, file_path)
                    module_class_names.append(node.name)
                
                # Handle module-level functions
                elif isinstance(node, ast.FunctionDef) and self.is_module_level(node, tree):
                    self.process_function(node, module_name, file_path)
            
            # Store module classes for sibling detection
            if module_class_names:
                self.module_classes[module_name] = module_class_names
                
        except Exception as e:
            print(f"Error parsing {file_path}: {e}", file=sys.stderr)
    
    def is_module_level(self, node: ast.FunctionDef, tree: ast.Module) -> bool:
        """Check if function is at module level (not inside a class)."""
        return node in tree.body
    
    def get_module_name(self, file_path: Path) -> str:
        """Convert file path to module name."""
        rel_path = file_path.relative_to(self.project_path)
        parts = list(rel_path.parts[:-1]) + [rel_path.stem]
        
        # Remove __init__ from module name
        if parts[-1] == '__init__':
            parts = parts[:-1]
        
        return '.'.join(parts) if parts else '__main__'
    
    def process_class(self, node: ast.ClassDef, module_name: str, file_path: Path):
        """Process a class definition."""
        full_namespace = f"{module_name}.{node.name}"
        
        # Extract base classes
        bases = [self.get_type_annotation(base) for base in node.bases]
        
        # Extract methods
        methods = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                method_info = self.process_method(item, full_namespace, file_path)
                methods.append(method_info)
        
        class_info = ClassInfo(
            name=node.name,
            full_namespace=full_namespace,
            bases=bases,
            methods=methods,
            line_number=node.lineno,
            file_path=str(file_path.relative_to(self.project_path)),
            description=self.extract_docstring_summary(node)
        )
        
        self.classes[full_namespace] = class_info
    
    def process_method(self, node: ast.FunctionDef, class_namespace: str, 
                       file_path: Path) -> FunctionInfo:
        """Process a method definition."""
        signature, return_type = self.extract_function_signature(node)
        full_namespace = f"{class_namespace}.{node.name}"
        related = self.extract_related_objects(node)
        
        return FunctionInfo(
            name=node.name,
            full_namespace=full_namespace,
            signature=signature,
            return_type=return_type,
            description=self.extract_docstring_summary(node),
            line_number=node.lineno,
            file_path=str(file_path.relative_to(self.project_path)),
            related_objects=related
        )
    
    def process_function(self, node: ast.FunctionDef, module_name: str, file_path: Path):
        """Process a module-level function."""
        signature, return_type = self.extract_function_signature(node)
        full_namespace = f"{module_name}.{node.name}"
        related = self.extract_related_objects(node)
        
        func_info = FunctionInfo(
            name=node.name,
            full_namespace=full_namespace,
            signature=signature,
            return_type=return_type,
            description=self.extract_docstring_summary(node),
            line_number=node.lineno,
            file_path=str(file_path.relative_to(self.project_path)),
            related_objects=related
        )
        
        self.functions[full_namespace] = func_info
    
    def add_sibling_info(self):
        """Add sibling class information."""
        for module_name, class_names in self.module_classes.items():
            for class_name in class_names:
                full_namespace = f"{module_name}.{class_name}"
                if full_namespace in self.classes:
                    # Add all other classes in same module as siblings
                    siblings = {f"{module_name}.{cn}" for cn in class_names if cn != class_name}
                    self.classes[full_namespace].siblings = siblings
    
    def scan_project(self):
        """Scan the entire project."""
        for root, dirs, files in os.walk(self.project_path):
            root_path = Path(root)
            
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if not self.should_exclude_dir(root_path / d)]
            
            # Process Python files
            for file in files:
                if file.endswith('.py'):
                    file_path = root_path / file
                    self.analyze_file(file_path)
        
        # Add sibling information after all files are processed
        self.add_sibling_info()
    
    def generate_compact_overview(self) -> str:
        """Generate compact overview in tree format."""
        output = []
        output.append("=" * 80)
        output.append("PYTHON PROJECT STRUCTURE OVERVIEW")
        output.append(f"Project: {self.project_path.name}")
        output.append("=" * 80)
        output.append("")
        
        # Module-level functions
        if self.functions:
            output.append("MODULE-LEVEL FUNCTIONS:")
            output.append("-" * 80)
            for namespace in sorted(self.functions.keys()):
                func = self.functions[namespace]
                output.extend(self.format_function(func, indent=0))
            output.append("")
        
        # Classes
        if self.classes:
            output.append("CLASSES:")
            output.append("-" * 80)
            for namespace in sorted(self.classes.keys()):
                cls = self.classes[namespace]
                output.extend(self.format_class(cls))
            output.append("")
        
        # Summary
        output.append("=" * 80)
        output.append(f"SUMMARY: {len(self.classes)} classes, "
                     f"{sum(len(c.methods) for c in self.classes.values())} methods, "
                     f"{len(self.functions)} functions")
        output.append("=" * 80)
        
        return '\n'.join(output)
    
    def format_function(self, func: FunctionInfo, indent: int = 2) -> List[str]:
        """Format a function for output."""
        lines = []
        prefix = "  " * indent
        
        # Main signature line
        line_info = f" [L{func.line_number}]" if self.include_line_numbers else ""
        location = f" @ {func.file_path}{line_info}" if self.include_line_numbers else ""
        lines.append(f"{prefix}├─ {func.signature} -> {func.return_type}{location}")
        
        # Description
        if func.description:
            lines.append(f"{prefix}│  ⮕ {func.description}")
        
        # Related objects (limit to most relevant)
        if func.related_objects:
            related = sorted(func.related_objects)[:5]  # Limit to 5 for compactness
            related_str = ', '.join(related)
            if len(func.related_objects) > 5:
                related_str += f" (+{len(func.related_objects) - 5} more)"
            lines.append(f"{prefix}│  ⤷ Uses: {related_str}")
        
        return lines
    
    def format_class(self, cls: ClassInfo) -> List[str]:
        """Format a class for output."""
        lines = []
        
        # Class header
        bases_str = f"({', '.join(cls.bases)})" if cls.bases else ""
        line_info = f" [L{cls.line_number}]" if self.include_line_numbers else ""
        location = f" @ {cls.file_path}{line_info}" if self.include_line_numbers else ""
        lines.append(f"\n{cls.full_namespace}{bases_str}{location}")
        
        if cls.description:
            lines.append(f"  ⮕ {cls.description}")
        
        # Siblings
        if cls.siblings:
            siblings = sorted(cls.siblings)[:3]  # Show up to 3 siblings
            siblings_str = ', '.join([s.split('.')[-1] for s in siblings])
            if len(cls.siblings) > 3:
                siblings_str += f" (+{len(cls.siblings) - 3} more)"
            lines.append(f"  ⤖ Siblings: {siblings_str}")
        
        # Methods
        if cls.methods:
            for method in cls.methods:
                lines.extend(self.format_function(method, indent=1))
        
        return lines


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate compact overview of Python project structure for LLM context'
    )
    parser.add_argument(
        'project_path',
        nargs='?',
        default='.',
        help='Path to Python project (default: current directory)'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output file path (default: stdout)'
    )
    parser.add_argument(
        '--no-line-numbers',
        action='store_true',
        help='Exclude line numbers from output'
    )
    
    args = parser.parse_args()
    
    # Analyze project
    analyzer = ProjectAnalyzer(
        args.project_path,
        include_line_numbers=not args.no_line_numbers
    )
    
    print(f"Scanning project: {analyzer.project_path}", file=sys.stderr)
    analyzer.scan_project()
    
    # Generate overview
    overview = analyzer.generate_compact_overview()
    
    # Output
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(overview)
        print(f"Overview written to: {args.output}", file=sys.stderr)
    else:
        print(overview)


if __name__ == '__main__':
    main()
