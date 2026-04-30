import sys
from core.calculator import Calculator
from utils.logger import setup_logger

def run_app():
    logger = setup_logger()
    calc = Calculator()
    logger.info('Starting calculator app...')
    result = calc.compute('add', 10.5, 5.0)
    logger.info(f'Result: {result}')

if __name__ == '__main__':
    run_app()
