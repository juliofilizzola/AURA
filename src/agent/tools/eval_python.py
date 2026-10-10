"""Ferramenta: avaliação segura de expressões Python.

Usa ast.parse para validar que a expressão é composta apenas por literais
e operações matemáticas seguras. Não permite import, chamadas de função
arbitrárias, acesso a atributos ou qualquer operação perigosa.
"""

from __future__ import annotations

import ast
import math
import operator as op
from typing import Any

from src.agent.tools.registry import Tool

# Operações binárias permitidas
_BINOPS: dict[type, Any] = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
}

# Operações unárias permitidas
_UNOPS: dict[type, Any] = {
    ast.USub: op.neg,
    ast.UAdd: op.pos,
}

# Constantes matemáticas permitidas
_CONSTANTS: dict[str, float] = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
    "inf": math.inf,
}

# Funções matemáticas permitidas
_FUNCTIONS: dict[str, Any] = {
    "sqrt": math.sqrt,
    "abs": abs,
    "round": round,
    "floor": math.floor,
    "ceil": math.ceil,
    "log": math.log,
    "log2": math.log2,
    "log10": math.log10,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "pow": math.pow,
}


def _eval_node(node: ast.AST) -> float | int:
    match node:
        case ast.Constant(value=v) if isinstance(v, (int, float)):
            return v
        case ast.Name(id=name) if name in _CONSTANTS:
            return _CONSTANTS[name]
        case ast.BinOp(left=left, op=op_node, right=right):
            op_fn = _BINOPS.get(type(op_node))
            if op_fn is None:
                raise ValueError(f"Operador não suportado: {type(op_node).__name__}")
            return op_fn(_eval_node(left), _eval_node(right))
        case ast.UnaryOp(op=op_node, operand=operand):
            op_fn = _UNOPS.get(type(op_node))
            if op_fn is None:
                raise ValueError(f"Operador unário não suportado: {type(op_node).__name__}")
            return op_fn(_eval_node(operand))
        case ast.Call(func=ast.Name(id=name), args=args, keywords=[]):
            fn = _FUNCTIONS.get(name)
            if fn is None:
                raise ValueError(f"Função não permitida: {name}")
            evaluated_args = [_eval_node(a) for a in args]
            return fn(*evaluated_args)
        case _:
            raise ValueError(f"Construção não permitida: {ast.dump(node)}")


async def _eval_python(expression: str) -> str:
    if len(expression) > 200:
        return "Erro: expressão muito longa (máximo 200 caracteres)."
    try:
        tree = ast.parse(expression, mode="eval")
        result = _eval_node(tree.body)
        # Evita exibir floats com muitas casas desnecessárias
        if isinstance(result, float) and result == int(result) and not math.isinf(result):
            return str(int(result))
        return str(result)
    except ZeroDivisionError:
        return "Erro: divisão por zero."
    except (ValueError, TypeError, SyntaxError) as exc:
        return f"Erro ao avaliar expressão: {exc}"


def make_eval_python_tool() -> Tool:
    return Tool(
        name="eval_python",
        description=(
            "Avalia expressões matemáticas Python de forma segura. "
            "Suporta operações (+, -, *, /, //, %, **), funções (sqrt, abs, round, "
            "floor, ceil, log, sin, cos, tan) e constantes (pi, e, tau). "
            "Não suporta imports, variáveis ou código arbitrário."
        ),
        parameters={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Expressão matemática a avaliar (ex: '2 ** 10', 'sqrt(144)').",
                }
            },
            "required": ["expression"],
        },
        fn=_eval_python,
    )
