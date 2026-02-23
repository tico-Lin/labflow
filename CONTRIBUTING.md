# Contributing to LabFlow

Thank you for your interest in contributing to LabFlow! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

Please read and follow our [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) to ensure a welcoming community for all participants.

---

## How to Contribute

### 1. Report Bugs

- Check if the bug has already been reported in [Issues](https://github.com/tico-Lin/labflow/issues)
- Use the [Bug Report Template](.github/ISSUE_TEMPLATE/bug_report.md) to provide detailed information
- Include: Steps to reproduce, expected behavior, actual behavior, environment details

### 2. Request Features

- Check if the feature has already been requested in [Issues](https://github.com/tico-Lin/labflow/issues)
- Use the [Feature Request Template](.github/ISSUE_TEMPLATE/feature_request.md)
- Include: Use case, proposed solution, alternatives considered

### 3. Submit Code Changes

#### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/tico-Lin/labflow.git
cd labflow

# Create a virtual environment (Python)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r dev-requirements.txt

# Install Node.js dependencies (for frontend)
npm install
```

#### Make Changes

1. **Create a branch** from `main`:

   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix-name
   ```

2. **Follow code style**:
   - Python: Follow PEP 8 (checked with Ruff)
   - JavaScript/React: Use Prettier formatter
   - Documentation: Use Markdown best practices

3. **Write/update tests**:

   ```bash
   # Run tests
   pytest -v --cov=app --cov-report=html

   # For frontend
   npm test
   ```

4. **Commit with clear messages**:

   ```bash
   git commit -m "fix: brief description"
   git commit -m "feat: brief description"
   git commit -m "docs: brief description"
   ```

5. **Push to your fork**:

   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request**:
   - Use the [PR Template](.github/PULL_REQUEST_TEMPLATE.md)
   - Link related issues
   - Describe changes and testing performed

## Pull Request Guidelines

- ✅ Tests pass and coverage doesn't decrease
- ✅ Code follows project style conventions
- ✅ Documentation is updated (docstrings, README, etc.)
- ✅ Commit history is clean and descriptive
- ✅ Changes address a single concern or feature

## Development Workflow

### Project Structure

```
LabFlow/
├── app/                    # Python backend (FastAPI)
├── frontend/              # React frontend (Vite)
├── electron/              # Desktop application (Electron)
├── labflow/               # Core library
├── docs/                  # Documentation
├── tests/                 # Test suite
└── pyproject.toml         # Python project config
```

### Running Locally

**Backend:**

```bash
cd labflow
python -m uvicorn app.main:app --reload
```

**Frontend:**

```bash
cd frontend
npm run dev
```

### Building

**Desktop (Electron):**

```bash
npm run build
npm run electron
```

**Docker:**

```bash
docker-compose up --build
```

## Documentation

- Keep README.md and docs updated
- Add docstrings to all public functions/classes
- Use both English and Chinese for primary documentation
- Reference related design documents in docs/

## Commit Message Conventions

Use conventional commits format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types:

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation change
- **style**: Code style (no logic change)
- **refactor**: Code refactoring
- **test**: Test changes
- **chore**: Build, dependencies, tooling
- **perf**: Performance improvement

### Example:

```
fix(reasoning-engine): resolve infinite loop in DAG execution

- Added circular dependency detection
- Fixed node completion callback timing
- Added integration test for cycle detection

Fixes #123
```

## Review Process

1. Automated checks must pass (tests, lint, coverage)
2. At least one maintainer review required
3. Address review feedback and request re-review
4. Squash commits if needed before merge
5. Merge to `main` branch

## Licensing

By contributing to LabFlow, you agree that your contributions will be licensed under the [GPL v3 License](LICENSE).

## Attribution

All contributors will be credited in:

- Git commit history (automatic)
- CONTRIBUTORS file (upon request)
- Release notes (for major contributions)

## Questions or Need Help?

- 📖 Check [docs/README.md](docs/README.md) for architecture and design
- 💬 Start a discussion in GitHub Discussions
- 📧 Contact: [@tico-Lin](https://github.com/tico-Lin)

---

**Thank you for making LabFlow better!** 🚀
