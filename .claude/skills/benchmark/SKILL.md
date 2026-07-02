---
name: benchmark
description: Run benchmark tests for the type_enforced package. Use when asked to evaluate performance changes or compare different implementations.
---

# Benchmarking

Take note of current benchmark results in `benchmark.md`. Assume this is the current state of the codebase.


Run:

```
uv run utils/benchmark.py
```

Consider the new content in `benchmark.md` and compare it to the previous results. If the new results are worse, consider optimizing the code or reverting changes. If noticibly different, when you report to the user include this information and provide relevant details.