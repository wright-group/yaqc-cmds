import sympy


def const_order(**expressions):
    expressions = {sympy.Symbol(k): sympy.sympify(v) for k, v in expressions.items()}
    while expressions:
        cycle = True
        for symb, expr in list(expressions.items()):
            if all(x.is_constant() or x not in expressions for x in expr.atoms()):
                yield str(symb)
                expressions.pop(symb)
                cycle = False
                break
        if cycle:
            raise ValueError("Cycle detected in set of expressions")
