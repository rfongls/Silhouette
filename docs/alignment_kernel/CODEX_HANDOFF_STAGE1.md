# Stage 1 Codex Handoff

This document contains the seed examples for the reasoning module along with the prompt used to expand the dataset. It also describes how to run the Codex controller and validate the outputs.

## Seed Entries (stage1_sample.jsonl)
```jsonl
{"prompt": "Explain the Pythagorean theorem", "completion": "The Pythagorean theorem states that for any right triangle, the square of the hypotenuse equals the sum of the squares of the other two sides."}
{"prompt": "List the first five prime numbers", "completion": "2, 3, 5, 7, 11"}
{"prompt": "Convert 37 degrees Celsius to Fahrenheit", "completion": "98.6"}
{"prompt": "What is the factorial of 5?", "completion": "120"}
{"prompt": "Simplify the expression (x^2 - 9)/(x - 3)", "completion": "x + 3"}
```

## Expansion Prompt
Here is the exact multi-line prompt you can copy-and-paste (or feed via `--prompt`) into Codex to expand your 5 seeds to 500 entries:

````
The following are 5 sample entries in JSONL format. Each entry has a "prompt" (an algorithmic task) and a "completion" consisting of a step-by-step reasoning explanation followed by a Python code block. Continue this list until you have 500 unique examples total, one JSON object per line, following exactly the same structure and quoting. Cover classic algorithms (sorting, searching, dynamic programming, graph, greedy, backtracking, etc.) with non-trivial chain-of-thought and correct Python code.

```jsonl
{"prompt":"Implement merge sort for a list of integers.","completion":"First, I will explain my approach step by step:\n1. If the list has 0 or 1 elements, it's already sorted.\n2. Otherwise, split the list in half.\n3. Recursively sort each half.\n4. Merge the two sorted halves by repeatedly taking the smaller head element.\n\nNow the Python code:\n```python\ndef merge_sort(arr):\n    if len(arr) <= 1:\n        return arr\n    mid = len(arr) // 2\n    left = merge_sort(arr[:mid])\n    right = merge_sort(arr[mid:])\n    merged = []\n    i = j = 0\n    while i < len(left) and j < len(right):\n        if left[i] < right[j]:\n            merged.append(left[i])\n            i += 1\n        else:\n            merged.append(right[j])\n            j += 1\n    merged.extend(left[i:])\n    merged.extend(right[j:])\n    return merged\n```"}
{"prompt":"Implement binary search to find a target in a sorted list. Return its index or -1 if not found.","completion":"First, I will outline my plan:\n1. Initialize low = 0 and high = len(arr) - 1.\n2. While low <= high:\n   a. Compute mid = (low + high) // 2.\n   b. If arr[mid] == target, return mid.\n   c. If arr[mid] < target, set low = mid + 1.\n   d. Otherwise, set high = mid - 1.\n3. Return -1 if not found.\n\nNow the code:\n```python\ndef binary_search(arr, target):\n    low, high = 0, len(arr) - 1\n    while low <= high:\n        mid = (low + high) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            low = mid + 1\n        else:\n            high = mid - 1\n    return -1\n```"}
{"prompt":"Implement a function to compute the nth Fibonacci number using dynamic programming.","completion":"Here's my reasoning:\n1. Use an array `fib` of size n+1.\n2. Set fib[0]=0 and fib[1]=1.\n3. For i from 2 to n, set fib[i] = fib[i-1] + fib[i-2].\n4. Return fib[n].\n\nImplementation:\n```python\ndef fib(n):\n    if n < 2:\n        return n\n    fib = [0] * (n+1)\n    fib[0], fib[1] = 0, 1\n    for i in range(2, n+1):\n        fib[i] = fib[i-1] + fib[i-2]\n    return fib[n]\n```"}
{"prompt":"Implement breadth-first search (BFS) on a graph represented as an adjacency list. Return nodes in BFS order from a given start node.","completion":"Approach:\n1. Use a queue initialized with the start node.\n2. Maintain a visited set.\n3. While queue is not empty, pop front, record it, enqueue unvisited neighbors.\n4. Return the recorded order.\n\nCode:\n```python\ndef bfs(graph, start):\n    visited = set([start])\n    queue = [start]\n    order = []\n    while queue:\n        node = queue.pop(0)\n        order.append(node)\n        for nbr in graph.get(node, []):\n            if nbr not in visited:\n                visited.add(nbr)\n                queue.append(nbr)\n    return order\n```"}
{"prompt":"Implement depth-first search (DFS) on a graph represented as an adjacency list. Return nodes in DFS order from a given start node.","completion":"Plan:\n1. Use recursion with a visited set.\n2. On visiting a node, mark visited and append to order.\n3. Recurse on each unvisited neighbor.\n4. Return the order list.\n\nCode:\n```python\ndef dfs(graph, start):\n    visited = set()\n    order = []\n    def visit(node):\n        visited.add(node)\n        order.append(node)\n        for nbr in graph.get(node, []):\n            if nbr not in visited:\n                visit(nbr)\n    visit(start)\n    return order\n```"}
````

Now run Codex with:

```bash
openai api completions.create \
  --model code-davinci-002 \
  --prompt "$(cat training_data/reasoner/stage1_sample.jsonl)

The following are 5 sample entries in JSONL format...<as above>" \
  --max_tokens 25000 \
  --temperature 0.0 \
  > training_data/reasoner/stage1_full.jsonl
```

## CLI Example
```bash
python -m silhouette_core.codex_controller --input training_data/reasoner/stage1_sample.jsonl --output training_data/reasoner/stage1_full.jsonl --count 500
```

## Post-processing
1. Remove any duplicate prompts.
2. Ensure JSONL formatting is valid.
3. Run the tests:
   ```bash
   pytest tests
   ```
