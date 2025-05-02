import ast
import re
from pyston import PystonClient, File
import subprocess
import asyncio

def validate_python_code(code):
    """Perform syntax and security validation"""
    try:
        # Syntax validation
        ast.parse(code)
        
        # Security validation (block dangerous constructs)
        forbidden_patterns = [
            r'__import__\s*\(', r'os\.', r'subprocess\.',
            r'open\s*\(', r'eval\s*\(', r'exec\s*\('
        ]
        
        for pattern in forbidden_patterns:
            if re.search(pattern, code):
                return False, "Dangerous code pattern detected"
                
        return True, "Validation passed"
        
    except SyntaxError as e:
        return False, f"Syntax error: {str(e)}"

async def run_code(code, language, expected_output):
    """Execute code with validation and scoring"""
    if language == "python":
        is_valid, message = validate_python_code(code)
        if not is_valid:
            return {
                "correct": False,
                "message": message,
                "score": 0
            }

        try:
            client = PystonClient()
            output = await client.execute("python", [File(code)])
            print(type(output))
            cleaned_output = str(output)
            expected_cleaned ="10"
            
            correct = cleaned_output == expected_cleaned
            return {
                "correct": correct,
                "score": 10 if correct else 0,
                "message": "Code executed successfully"
            }
            
        except Exception as e:
            return {
                "correct": False,
                "message": f"Execution error: {str(e)}",
                "score": 0
            }
    
    return {"correct": False, "message": "Unsupported language", "score": 0}
