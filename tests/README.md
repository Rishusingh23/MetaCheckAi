# MetaCheck AI — Testing Framework

## Overview
This directory coordinates end-to-end (E2E), cross-service integration tests, and test automation pipelines.

## Test Suites Location
- **Backend Unit & Integration Tests**: Located in `backend/tests/` (run using `pytest`).
- **Frontend Component & Unit Tests**: Located in `frontend/tests/` (run using `npm run test` or `vitest`).
- **End-to-End Tests (Future)**: Will reside in `tests/e2e/` (Playwright / Cypress).

## Running Tests

### Backend Tests
```bash
cd backend
python -m pytest
```

### Frontend Tests
```bash
cd frontend
npm run test
```
