from testcode.core.operations import add, subtract


class Calculator:
    def __init__(self):
        self.history = []

    def compute(self, op: str, a: float, b: float) -> float:
        res = 0.0
        if op == "add":
            res = add(a, b)
        elif op == "sub":
            res = subtract(a, b)
        else:
            raise ValueError(f"Unknown operation: {op}")

        self.history.append((op, a, b, res))
        return res
