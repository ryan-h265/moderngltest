#!/usr/bin/env python3
"""
Python Project Overview Generator - Compact Format
Generates a token-optimized overview (~15K tokens) for LLM context pre-seeding.
"""

import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class FunctionInfo:
    """Represents a function or method."""
    name: str
    full_namespace: str
    signature: str
    return_type: str
    description: str


@dataclass
class ClassInfo:
    """Represents a class."""
    name: str
    full_namespace: str
    bases: List[str]
    methods: List[FunctionInfo]
    description: str


class ProjectAnalyzer:
    """Analyzes Python project structure."""
    
    EXCLUDED_DIRS = {
        'venv', 'env', '.venv', '.env', '__pycache__', '.git', '.github',
        'node_modules', '.pytest_cache', '.mypy_cache', '.tox', 'dist',
        'build', '*.egg-info', '.eggs', 'tests', 'test'
    }
    
    # Boilerplate dunder methods to exclude
    BOILERPLATE_DUNDERS = {
        '__repr__', '__str__', '__eq__', '__ne__', '__lt__', '__le__',
        '__gt__', '__ge__', '__hash__', '__bool__', '__len__', '__iter__',
        '__next__', '__contains__', '__getitem__', '__setitem__', '__delitem__',
        '__enter__', '__exit__', '__del__', '__new__'
    }
    
    MAX_DESC_LENGTH = 50  # Shorter for COMPACT format
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path).resolve()
        self.classes: Dict[str, ClassInfo] = {}
        self.functions: Dict[str, FunctionInfo] = {}
    
    def should_exclude_path(self, path: Path) -> bool:
        """Check if path should be excluded."""
        name = path.name
        # Exclude test files
        if name.startswith('test_') or name.endswith('_test.py'):
            return True
        # Exclude directories
        return any(
            name.startswith(pattern.rstrip('*')) if pattern.endswith('*') else name == pattern
            for pattern in self.EXCLUDED_DIRS
        )
    
    def truncate_description(self, text: str) -> str:
        """Truncate description to max length."""
        if not text:
            return ""
        text = text.strip()
        if len(text) <= self.MAX_DESC_LENGTH:
            return text
        return text[:self.MAX_DESC_LENGTH - 3] + "..."
    
    def extract_docstring_summary(self, node: ast.AST) -> str:
        """Extract and truncate first line of docstring."""
        docstring = ast.get_docstring(node)
        if docstring:
            lines = [line.strip() for line in docstring.split('\n') if line.strip()]
            if lines:
                return self.truncate_description(lines[0])
        return ""
    
    def get_type_annotation(self, annotation: Optional[ast.AST]) -> str:
        """Convert AST annotation to string."""
        if annotation is None:
            return ""
        try:
            return ast.unparse(annotation)
        except:
            return ""
    
    def extract_function_signature(self, node: ast.FunctionDef) -> tuple:
        """Extract compact function signature and return type."""
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
        return_type = self.get_type_annotation(node.returns) if node.returns else ""
        
        return signature, return_type
    
    def should_include_method(self, method_name: str) -> bool:
        """Check if method should be included (filter boilerplate)."""
        # Always include __init__
        if method_name == '__init__':
            return True
        # Exclude common boilerplate dunders
        if method_name in self.BOILERPLATE_DUNDERS:
            return False
        return True
    
    def analyze_file(self, file_path: Path):
        """Analyze a single Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=str(file_path))
            module_name = self.get_module_name(file_path)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    self.process_class(node, module_name, file_path)
                elif isinstance(node, ast.FunctionDef) and self.is_module_level(node, tree):
                    self.process_function(node, module_name, file_path)
                    
        except Exception as e:
            print(f"Error parsing {file_path}: {e}", file=sys.stderr)
    
    def is_module_level(self, node: ast.FunctionDef, tree: ast.Module) -> bool:
        """Check if function is at module level."""
        return node in tree.body
    
    def get_module_name(self, file_path: Path) -> str:
        """Convert file path to module name."""
        rel_path = file_path.relative_to(self.project_path)
        parts = list(rel_path.parts[:-1]) + [rel_path.stem]
        
        if parts and parts[-1] == '__init__':
            parts = parts[:-1]
        
        return '.'.join(parts) if parts else '__main__'
    
    def process_class(self, node: ast.ClassDef, module_name: str, file_path: Path):
        """Process a class definition."""
        full_namespace = f"{module_name}.{node.name}"
        bases = [self.get_type_annotation(base) for base in node.bases]
        
        methods = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                if self.should_include_method(item.name):
                    method_info = self.process_method(item, full_namespace, file_path)
                    methods.append(method_info)
        
        class_info = ClassInfo(
            name=node.name,
            full_namespace=full_namespace,
            bases=bases,
            methods=methods,
            description=self.extract_docstring_summary(node)
        )
        
        self.classes[full_namespace] = class_info
    
    def process_method(self, node: ast.FunctionDef, class_namespace: str, file_path: Path) -> FunctionInfo:
        """Process a method definition."""
        signature, return_type = self.extract_function_signature(node)
        full_namespace = f"{class_namespace}.{node.name}"
        
        return FunctionInfo(
            name=node.name,
            full_namespace=full_namespace,
            signature=signature,
            return_type=return_type,
            description=self.extract_docstring_summary(node)
        )
    
    def process_function(self, node: ast.FunctionDef, module_name: str, file_path: Path):
        """Process a module-level function."""
        signature, return_type = self.extract_function_signature(node)
        full_namespace = f"{module_name}.{node.name}"
        
        func_info = FunctionInfo(
            name=node.name,
            full_namespace=full_namespace,
            signature=signature,
            return_type=return_type,
            description=self.extract_docstring_summary(node)
        )
        
        self.functions[full_namespace] = func_info
    
    def scan_project(self):
        """Scan the entire project."""
        for root, dirs, files in os.walk(self.project_path):
            root_path = Path(root)
            
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if not self.should_exclude_path(root_path / d)]
            
            # Process Python files
            for file in files:
                if file.endswith('.py'):
                    file_path = root_path / file
                    if not self.should_exclude_path(file_path):
                        self.analyze_file(file_path)
    
    def generate_overview(self) -> str:
        """Generate compact overview."""
        lines = []
        
        # Header
        lines.append(f"# PROJECT: {self.project_path.name}")
        lines.append("")
        
        # Functions
        if self.functions:
            lines.append("## FUNCTIONS")
            for ns in sorted(self.functions.keys()):
                f = self.functions[ns]
                lines.append(self.format_function(f))
            lines.append("")
        
        # Classes
        if self.classes:
            lines.append("## CLASSES")
            for ns in sorted(self.classes.keys()):
                c = self.classes[ns]
                lines.extend(self.format_class(c))
            lines.append("")
        
        # Summary
        total_methods = sum(len(c.methods) for c in self.classes.values())
        lines.append(f"# TOTAL: {len(self.classes)} classes, {total_methods} methods, {len(self.functions)} functions")
        
        return '\n'.join(lines)
    
    def format_function(self, f: FunctionInfo) -> str:
        """Format function in compact single line."""
        ret = f" -> {f.return_type}" if f.return_type else ""
        desc = f" | {f.description}" if f.description else ""
        return f"{f.full_namespace}: {f.signature}{ret}{desc}"
    
    def format_class(self, c: ClassInfo) -> List[str]:
        """Format class in compact format."""
        lines = []
        
        # Class line
        bases = f"({', '.join(c.bases)})" if c.bases else ""
        desc = f" | {c.description}" if c.description else ""
        lines.append(f"{c.full_namespace}{bases}{desc}")
        
        # Methods (indented with single space)
        for m in c.methods:
            ret = f" -> {m.return_type}" if m.return_type else ""
            desc = f" | {m.description}" if m.description else ""
            lines.append(f"  {m.signature}{ret}{desc}")
        
        return lines


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate compact overview of Python project for LLM context'
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
    
    args = parser.parse_args()
    
    # Analyze project
    analyzer = ProjectAnalyzer(args.project_path)
    
    print(f"Scanning: {analyzer.project_path}", file=sys.stderr)
    analyzer.scan_project()
    print(f"Found: {len(analyzer.classes)} classes, {len(analyzer.functions)} functions", 
          file=sys.stderr)
    
    # Generate overview
    overview = analyzer.generate_overview()
    
    # Output
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(overview)
        print(f"Written to: {args.output}", file=sys.stderr)
    else:
        print(overview)


if __name__ == '__main__':
    main()
