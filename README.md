# Installation

## Prerequisites
- Python 3.11 or higher
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

# Testing
The postman collection used to test the API is available [here](https://api.postman.com/collections/27354467-c0c20ae1-68da-4f77-a2b1-0871ee31cb5c?access_key=PMAT-01HTGBCH99JB2KC1EJGCGMJ01G)

To facilitate testing, there is a toy database included in the test folder. To use it, add the following environment variable:
```bash
  export TEST=1
```

It comes with:

- A user:
```json
{
  "name": "test",
  "password": "$2b$12$iFMxI.xziyqiG7lS8jBnB.NLhU7aNTwlizXR8KrRil.zVrMncrwpi",
  "cmd_token": null,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5MTBkYzBjMC1jMGNhLTQ5NjctODkzMS05MmVkNmM5OGE0OGUiLCJleHAiOjE3MTI3OTQ1Njh9.B1edr-57h9LbID6BZvL5gCpM8GrANQRU1jT6K0CVZ2M",
  "id": "910dc0c0c0ca4967893192ed6c98a48e",
  "email": "text@example.com",
  "nic": "237583734",
  "role": "USER"
}
```

- A simple collection:
```json
{
  "name": "README.md",
  "submission_date": "2024-04-11 00:47:45.466539",
  "last_update": null,
  "share_state": "private",
  "access_from_date": null,
  "id": "61e665d97f904e6f9d898069b7c641a8",
  "owner_id": "910dc0c0c0ca4967893192ed6c98a48e"
}
```

- A complex collection:
```json
{
  "name": "c2023-adv-06.tar.gz",
  "submission_date": "2024-04-11 00:48:28.782808",
  "last_update": null,
  "share_state": "private",
  "access_from_date": null,
  "id": "0c8589364f934efeaca79824d5237289",
  "owner_id": "910dc0c0c0ca4967893192ed6c98a48e"
}
```

# Development
## Migrations
To create a migration, run the following command:
```bash
  poetry run alembic revision --autogenerate -m "migration message"
```

To apply the migration, run the following command:
```bash
  poetry run alembic upgrade head
```

To downgrade the migration, run the following command:
```bash
  poetry run alembic downgrade -1
```

# Need help?
@mycsina on most platforms online