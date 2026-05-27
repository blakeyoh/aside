import time
import re
from aside.dictionary.replacements import apply_replacements
from aside.dictionary.hotwords import DictionaryData

# Wait, we know `isinstance` check and the loop takes time.
# Let's ensure the `apply_replacements` receives the exact default dictionary from config to mirror real world.
from aside.config import DEFAULT_CONFIG

class OldTranscriber:
    def __init__(self):
        self._replacements = DEFAULT_CONFIG["replacements"]
        self._dict_data = DictionaryData()
        self._dict_data.replacements = {f"user{i}": f"urep{i}" for i in range(10)}
        self._dict_data.compiled_replacements = [
            (re.compile(rf"(?<!\w)user{i}(?!\w)", re.IGNORECASE), f"urep{i}") for i in range(10)
        ]

    def process(self, text):
        combined_rules = self._dict_data.replacements.copy()
        for k, v in self._replacements.items():
            if k not in combined_rules:
                combined_rules[k] = v
        return apply_replacements(text, combined_rules)

class NewTranscriber:
    def __init__(self):
        from aside.dictionary.replacements import _get_compiled_pattern
        self._replacements = DEFAULT_CONFIG["replacements"]
        self._compiled_replacements = [
            (_get_compiled_pattern(k), v, k) for k, v in self._replacements.items()
        ]
        self._dict_data = DictionaryData()
        self._dict_data.replacements = {f"user{i}": f"urep{i}" for i in range(10)}
        self._dict_data.compiled_replacements = [
            (re.compile(rf"(?<!\w)user{i}(?!\w)", re.IGNORECASE), f"urep{i}") for i in range(10)
        ]
        self._combined_compiled = None
        self._last_dict_data = None

    def process(self, text):
        if self._last_dict_data is not self._dict_data:
            self._combined_compiled = list(self._dict_data.compiled_replacements)
            for pattern, replacement, key in self._compiled_replacements:
                if key not in self._dict_data.replacements:
                    self._combined_compiled.append((pattern, replacement))
            self._last_dict_data = self._dict_data

        return apply_replacements(text, self._combined_compiled)

if __name__ == "__main__":
    o = OldTranscriber()
    n = NewTranscriber()
    text = "This is alright, nevermind."

    print("Benchmarking Default Overhead...")

    start = time.perf_counter()
    for _ in range(100000):
        o.process(text)
    old_time = time.perf_counter() - start
    print(f"Baseline Approach: {old_time:.4f} seconds")

    start = time.perf_counter()
    for _ in range(100000):
        n.process(text)
    new_time = time.perf_counter() - start
    print(f"Optimized Approach: {new_time:.4f} seconds")

    improvement = ((old_time - new_time) / old_time) * 100
    print(f"Improvement: {improvement:.2f}% faster")
