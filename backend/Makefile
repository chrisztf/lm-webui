.PHONY: test test-cov lint format clean install-dev

# Install development dependencies
install-dev:
	pip install -r requirements-test.txt

# Run all tests
test:
	pytest tests/ -v

# Run tests with coverage
test-cov:
	pytest tests/ --cov=app --cov-report=html --cov-report=term

# Run specific test file
test-file:
	pytest $(FILE) -v

# Run linting
lint:
	flake8 app/ tests/
	black --check app/ tests/
	isort --check-only app/ tests/

# Format code
format:
	black app/ tests/
	isort app/ tests/

# Clean up cache and coverage files
clean:
	rm -rf .coverage htmlcov .pytest_cache __pycache__ */__pycache__ */*/__pycache__

# Run all checks
check: lint test