def add(a: float, b: float) -> float:
    return a + b


def subtract(a: float, b: float) -> float:
    return a - b


def mul(a: float, b: float) -> float:
    return round(a * b, 10)


def div(a: float, b: float) -> float | str:
    if abs(b) < 1e-9:
        return "除数不能为0"
    return round(a / b, 10)
