# GitHub API Quality Monitor

A Python-based API monitoring project that checks the availability, response time, response structure, and rate-limit information of a public GitHub REST API endpoint.

The project demonstrates API testing, automated test design, error handling, test reporting, and continuous integration using GitHub Actions.

## Features

- **API availability monitoring:** Checks the HTTP status code.
- **Response-time measurement:** Records how long the API request takes.
- **Schema validation:** Verifies that required JSON fields exist and have the expected types.
- **Rate-limit tracking:** Captures the remaining GitHub API request allowance.
- **Error handling:** Handles HTTP errors, invalid JSON, request failures, and unexpected response structures.
- **Historical logging:** Stores timestamped monitoring results in JSON Lines format.
- **Historical analysis:** Reports total checks, successful and failed checks, success rate, and response-time statistics.
- **Automated testing:** Uses pytest and mocked API responses to test different scenarios.
- **Continuous integration:** Runs automated tests through GitHub Actions.
- **Performance thresholds:** Flags successful API responses that exceed a configurable response-time limit (currently 500 ms).
- **Separate performance status:** Distinguishes API availability and schema validation from response-time performance.
- **Performance testing:** Includes automated tests for responses below and above the configured threshold.

## Technology Stack

- Python 3.12
- Requests
- pytest
- GitHub REST API
- GitHub Actions
- JSON / JSONL

## Project Structure

```text
github-api-quality-monitor/
├── .github/
│   └── workflows/
│       └── tests.yml
├── results/
│   └── history.jsonl
├── tests/
│   └── test_monitor.py
├── analyze_history.py
├── monitor.py
├── requirements.txt
├── .gitignore
└── README.md
```

The `results/history.jsonl` file is generated locally when the monitor runs. It may not exist in a fresh checkout until the first monitoring run.

## Setup

Clone the repository:

```bash
git clone https://github.com/sritejaswiniraj-commits/github-api-quality-monitor.git
cd github-api-quality-monitor
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Usage

Run an API check and save the result to the history file:

```bash
python monitor.py
```

Analyze the recorded monitoring history:

```bash
python analyze_history.py
```

Run the automated test suite:

```bash
python -m pytest -v
```

## Automated Testing

The test suite covers:

- Successful API responses
- Unexpected HTTP status codes
- Missing required fields
- Invalid JSON responses
- Request timeouts
- Incorrect field types
- Invalid owner structures

The tests use mocked HTTP responses to exercise different scenarios without depending on a live API response for every test.

**Latest local test result:** 7 tests passed.

## Continuous Integration

GitHub Actions automatically runs the pytest suite when code is pushed or a pull request is opened. The workflow can also be triggered manually.

## Learning Outcomes

This project demonstrates practical skills in API testing, Python automation, response validation, exception handling, test isolation, JSON-based reporting, and CI/CD fundamentals.

## Future Improvements

- Configurable API endpoints
- Response-time thresholds and performance alerts
- Historical trend visualization
- Scheduled monitoring
- Exportable monitoring reports

## Author

Tejaswini Raj