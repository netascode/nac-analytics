"""Product-agnostic building blocks shared by every product package.

Nothing in ``core`` may import from ``nac_analytics.products``; the dependency
only ever points the other way (products build on core).
"""
