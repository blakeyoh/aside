import timeit

setup = """
from src.aside.punctuation.formatter import _ensure_trailing_space, _apply_smart_quotes

text = "Hello world!This is a test. Wait,what? Yes;this is it.  Multiple   spaces here."
text_quotes = 'He said "hello" to me. I said "hi".'
"""

stmt1 = "_ensure_trailing_space(text)"
stmt2 = "_apply_smart_quotes(text_quotes)"

n = 100000
t1 = timeit.timeit(stmt1, setup=setup, number=n)
t2 = timeit.timeit(stmt2, setup=setup, number=n)

print(f"Original _ensure_trailing_space: {t1:.4f} seconds for {n} iterations")
print(f"Original _apply_smart_quotes: {t2:.4f} seconds for {n} iterations")
