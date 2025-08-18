# Contributing to PostOp PDF Collector

First off, thank you for considering contributing to PostOp PDF Collector! It's people like you that make this tool better for everyone.

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible using our bug report template.

**Great Bug Reports** tend to have:
- A quick summary and/or background
- Steps to reproduce
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please use the feature request template and include:
- A clear and descriptive title
- A detailed description of the proposed enhancement
- Explain why this enhancement would be useful
- List any alternative solutions you've considered

### Pull Requests

1. Fork the repo and create your branch from `main`.
2. If you've added code that should be tested, add tests.
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes.
5. Make sure your code lints.
6. Issue that pull request!

## Development Setup

1. **Clone your fork:**
```bash
git clone https://github.com/YOUR_USERNAME/postop-pdf-collector.git
cd postop-pdf-collector
```

2. **Create a virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
pip install -e ".[dev]"
```

4. **Set up pre-commit hooks:**
```bash
pip install pre-commit
pre-commit install
```

5. **Create a branch:**
```bash
git checkout -b feature/your-feature-name
```

## Development Guidelines

### Code Style

We use:
- **Black** for code formatting
- **isort** for import sorting
- **Flake8** for linting
- **MyPy** for type checking

Run formatting and checks:
```bash
black postop_collector tests
isort postop_collector tests
flake8 postop_collector tests
mypy postop_collector
```

### Testing

Write tests for any new functionality:
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=postop_collector

# Run specific test file
pytest tests/test_specific.py

# Run tests in parallel
pytest -n auto
```

### Documentation

- Update README.md if needed
- Add docstrings to all functions/classes
- Update API_DOCUMENTATION.md for API changes
- Include inline comments for complex logic

### Commit Messages

We follow conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `test:` Adding or updating tests
- `chore:` Maintenance tasks
- `perf:` Performance improvements

Examples:
```
feat: add support for OCR in PDF extraction
fix: resolve memory leak in timeline parser
docs: update API documentation for new endpoints
```

### Branch Naming

- `feature/` for new features
- `fix/` for bug fixes
- `docs/` for documentation
- `refactor/` for code refactoring
- `test/` for test improvements

## Testing Your Changes

Before submitting:

1. **Run the test suite:**
```bash
pytest tests/
```

2. **Check code style:**
```bash
black --check postop_collector tests
flake8 postop_collector tests
```

3. **Test the API:**
```bash
python run_api.py
# In another terminal:
curl http://localhost:8000/health
```

4. **Test Docker build:**
```bash
docker build -t postop-test .
docker run -p 8000:8000 postop-test
```

## Submitting Changes

1. **Ensure all tests pass**
2. **Update documentation** if needed
3. **Write clear commit messages**
4. **Push to your fork**
5. **Submit a Pull Request**

In your PR description:
- Reference any related issues
- Describe what the PR does
- Include screenshots if relevant
- List any breaking changes

## Release Process

Releases are automated through GitHub Actions:

1. Maintainers merge PRs to `main`
2. When ready for release, create a tag:
```bash
git tag -a v1.0.1 -m "Release version 1.0.1"
git push origin v1.0.1
```
3. GitHub Actions will:
   - Run all tests
   - Build Docker images
   - Publish to PyPI
   - Create GitHub release

## Getting Help

- Check the [documentation](README.md)
- Search [existing issues](https://github.com/michaelevans/postop-pdf-collector/issues)
- Join our discussions
- Ask questions in issues with the `question` label

## Recognition

Contributors will be recognized in:
- The project README
- Release notes
- Our contributors page

Thank you for contributing! 🎉