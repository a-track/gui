import ast
import operator

def safe_eval_math(expression):
    """
    Safely evaluate a mathematical expression from a string.
    Supported operators: +, -, *, /
    """
    if not isinstance(expression, str):
        return float(expression)
    
    # Remove whitespace
    expression = expression.replace(' ', '')
    if not expression:
        return 0.0
        
    # Standardize decimal separator if needed (assuming . for now, but could handle ,)
    expression = expression.replace(',', '.')

    # Whitelist of allowed characters
    allowed_chars = set('0123456789+-*/.()')
    if not set(expression).issubset(allowed_chars):
        raise ValueError("Invalid characters in expression")

    try:
        # Parse into an AST
        node = ast.parse(expression, mode='eval')
        
        def eval_node(n):
            if isinstance(n, ast.Expression):
                return eval_node(n.body)
            elif isinstance(n, ast.Constant):  # number
                return n.value
            elif isinstance(n, ast.BinOp):
                left = eval_node(n.left)
                right = eval_node(n.right)
                if isinstance(n.op, ast.Add):
                    return operator.add(left, right)
                elif isinstance(n.op, ast.Sub):
                    return operator.sub(left, right)
                elif isinstance(n.op, ast.Mult):
                    return operator.mul(left, right)
                elif isinstance(n.op, ast.Div):
                    return operator.truediv(left, right)
            elif isinstance(n, ast.UnaryOp):
                 if isinstance(n.op, ast.USub):
                     return -eval_node(n.operand)
                 elif isinstance(n.op, ast.UAdd):
                     return eval_node(n.operand)
            
            raise ValueError(f"Unsupported operation: {n}")

        return float(eval_node(node))
    except (SyntaxError, ValueError, ZeroDivisionError) as e:
        raise ValueError(f"Invalid expression: {e}")
