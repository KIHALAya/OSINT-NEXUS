# Contributing to OSINT-SENTINEL

Thank you for contributing to OSINT-SENTINEL. We are building a system that helps real-world investigators find missing persons using AI-native OSINT.

---

## 🗺 Workflow

1.  **Branching:** Always create a feature branch from `main`.
    *   `feature/your-feature-name`
    *   `bugfix/issue-description`
2.  **Pull Requests:** Submit a PR with a clear description of the change and any relevant screenshots (for frontend) or logs (for backend).
3.  **Review:** All code must be reviewed by at least one maintainer.

---

## 🛠 Quality Standards

### Backend (Python)
- **Linting:** Use `ruff` for linting and formatting.
- **Type Hints:** All new functions must include Python type hints.
- **Tests:** Add unit tests in `backend/tests/` for any new tools or nodes.

### Frontend (React)
- **CSS:** Prefer Vanilla CSS or CSS Modules.
- **Components:** Keep components atomic and reusable.
- **Documentation:** Add JSDoc comments to complex hooks or utility functions.

---

## 🧪 Running Tests

### Backend
```bash
cd backend
pytest
```

### Frontend
```bash
cd osint-system
npm test  # if vitest is configured
```

---

## 📖 Documentation
When adding features, update the relevant files in the `docs/` directory to ensure the modular documentation remains accurate.
