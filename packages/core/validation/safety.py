"""
Code Safety Inspector - AST-Based Static Analysis
==================================================

Static Analysis tool to ensure AI-generated strategies are safe.
Blocks: System calls, File I/O, Network (except via approved clients).
"""

import ast
import logging

logger = logging.getLogger("sg1_safety")


class CodeSafetyInspector:
    """
    Static Analysis tool to ensure AI-generated strategies are safe.
    
    Blocks: System calls, File I/O, Network (except via approved clients).
    """

    FORBIDDEN_IMPORTS = {'os', 'sys', 'subprocess', 'shutil', 'requests', 'urllib', 'socket'}
    ALLOWED_IMPORTS = {'pandas', 'numpy', 'pandas_ta', 'datetime', 'asyncio', 'logging', 'math'}

    def inspect_code(self, code_str: str) -> bool:
        """
        Inspect code for security violations.
        
        Args:
            code_str: Python code as string
            
        Returns:
            True if code is safe, False otherwise
        """
        try:
            tree = ast.parse(code_str)
        except SyntaxError as e:
            logger.error(f"❌ Generated code has syntax errors: {e}")
            return False

        for node in ast.walk(tree):
            # Check Imports
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module_names = []
                if isinstance(node, ast.Import):
                    module_names = [n.name.split('.')[0] for n in node.names]
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module_names = [node.module.split('.')[0]]

                for mod in module_names:
                    if mod in self.FORBIDDEN_IMPORTS:
                        logger.error(f"❌ Security Violation: Forbidden import '{mod}' detected.")
                        return False

            # Check for dangerous built-ins (exec, eval)
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in {'exec', 'eval', 'open'}:
                        logger.error(f"❌ Security Violation: Forbidden function '{node.func.id}' call.")
                        return False

        logger.info("✅ Code passed Static Safety Analysis.")
        return True

