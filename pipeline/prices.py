"""List prices in USD per million tokens, for reference on the page.

Cost figures in the metrics come from each call's measured `usage.cost`, not from these.
"""
PRICES = {
    "typesafe/jev-1.14": {"input": 0.042, "output": 0.0},
    "anthropic/claude-sonnet-5.5": {"input": 2.0, "output": 10.0},
}
