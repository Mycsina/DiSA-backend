# Installation

## Prerequisites
- Python 3.8 or higher
- [poetry](https://python-poetry.org/docs/)

## Installing dependencies
You can install the dependencies by running the following command:
```bash
  poetry install
```

# Running the server
You can start the server by running the following command:
```bash
  poetry run hypercorn start:app --reload
```