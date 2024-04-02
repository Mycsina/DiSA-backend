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
  "password": "$2b$12$efjMKEXXiPswWSo0vQVRHO/9uAUUWg.B5XuFPODFUnxzC.lnR/2yq",
  "mobile_key": null,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxY2Q4NzEzNC01NTljLTQzZTMtOGE5OS1lY2I1MTM0MzY5ODkiLCJleHAiOjE3MTIwOTM3ODB9.kKPTWaRsQ0X-Wrs4se9Yedn99QoNIsxOO5RHlt1NHPw",
  "id": "1cd87134559c43e38a99ecb513436989",
  "email": "text@example.com",
  "role": "USER"
}
```

- A simple collection:
```json
{
  "name": "README.md",
  "submission_date": "2024-04-02 22:01:26.453626",
  "last_update": null,
  "share_state": "private",
  "access_from_date": null,
  "id": "f52a45e7926f4a69b20c00205c114e94",
  "owner_id": "1cd87134559c43e38a99ecb513436989"
}
```

- A complex collection:
```json
{
  "name": "c2023-adv-06.tar.gz",
  "submission_date": "2024-04-02 22:01:26.453626",
  "last_update": null,
  "share_state": "private",
  "access_from_date": null,
  "id": "85726967a1154a46828cd1099282bd2d",
  "owner_id": "1cd87134559c43e38a99ecb513436989"
}
```

# Need help?
@mycsina on most platforms online