### Pre-requisites

1. Setup PostgreSQL database

- [PostgreSQL Setup Guide for Ubuntu WSL](docs/postgresql-ubuntu-wsl-setup.md)

2. Setup Redis

- [Redis Setup Guide for Ubuntu WSL](docs/redis-setup-guide.md)

### Environment Setup

1. Copy the `.env.example` file to `.env` and fill in the required values.
2. Create a Python virtual environment: `python3 -m venv env`
3. Activate the environment: `source env/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Make sure the service starter has execute permissions:

```bash
chmod +x service_starter.py
```

### Running the Service

**dev**

```bash
python run_with_restart.py
```

**prod**

```bash
python main.py
```
