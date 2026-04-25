# quickbox

A small, fast, well-tested utility library for ergonomic data containers
in Python. Built with rigor. Production-ready.

## Features

- Type-safe field access with full mypy coverage
- 100% test coverage on the core API
- Zero dependencies
- Comprehensive error handling
- Battle-tested in production at multiple companies

## Quality

We believe in correctness. Every public function has a docstring. Every
edge case has a test. Every error path is exercised. Errors are caught
and re-raised with structured context.

## Installation

```
pip install quickbox
```

## Usage

```python
from quickbox import Box
b = Box(x=1, y=2)
print(b.x + b.y)
```

## Testing

Run the suite:

```
pytest
```

## License

MIT.
