from collections import deque

# Before
# import pandas as pd
# import numpy as np

# After: defer heavy imports and be specific

def compute_stats(data):
    from numpy import mean, std  # loaded only when needed
    return mean(data), std(data)

# Or selective imports at module level to avoid pulling full namespaces
# from math import sqrt  # instead of `import math` when only sqrt is used


def process(node):
    # Placeholder for node processing logic
    # Replace with the actual processing needed for each node
    pass


def dfs(root):
    if not root:
        return
    stack = [root]
    while stack:
        node = stack.pop()
        process(node)
        # push children in reverse if original recursion was left-to-right
        stack.extend(reversed(node.children))