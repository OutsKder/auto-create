import datetime
from .operations import add, subtract, mul, div
from utils.storage import load_history, save_history


class Calculator:
    def __init__(self):
        self.history = load_history()

    def compute(self, op: str, a: float, b: float) -> float | str:
        res = 0.0
        if op == "add":
            res = add(a, b)
        elif op == "sub":
            res = subtract(a, b)
        elif op == "mul":
            res = mul(a, b)
        elif op == "div":
            res = div(a, b)
        else:
            raise ValueError(f"Unknown operation: {op}")

        self.history.append({
            "expression": f"{a} {op} {b}",
            "result": res,
            "timestamp": datetime.datetime.now().isoformat()
        })
        save_history(self.history)
        return res

    def get_history(self) -> list[dict]:
        return self.history

    def clear_history(self) -> None:
        self.history = []
        save_history(self.history)
