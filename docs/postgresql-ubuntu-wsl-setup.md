# PostgreSQL Setup Guide for Ubuntu WSL

## 1. Update your system

First, make sure your system is up to date:

```bash
sudo apt update
sudo apt upgrade
```

## 2. Install PostgreSQL

Install PostgreSQL and its contrib package:

```bash
sudo apt install postgresql postgresql-contrib
```

## 3. Start PostgreSQL service

Start the PostgreSQL service:

```bash
sudo service postgresql start
```

## 4. Switch to PostgreSQL account

Switch to the postgres account:

```bash
sudo -i -u postgres
```

## 5. Access PostgreSQL prompt

You can now access the PostgreSQL prompt by typing:

```bash
psql
```

## 6. Create a new user and database

While in the PostgreSQL prompt:

```sql
CREATE USER yourusername WITH PASSWORD 'yourpassword';
CREATE DATABASE yourdatabase;
GRANT ALL PRIVILEGES ON DATABASE yourdatabase TO yourusername;
```

Replace 'yourusername', 'yourpassword', and 'yourdatabase' with your preferred values.

## 7. Exit PostgreSQL prompt

Exit the PostgreSQL prompt:

```
\q
```

## 8. Exit postgres user account

Exit the postgres user account:

```bash
exit
```

## 9. Configure PostgreSQL to allow connections

Edit the PostgreSQL configuration file:

```bash
sudo nano /etc/postgresql/[version]/main/postgresql.conf
```

Make sure to replace [version] your actual PostgreSQL version eg: 12.\
You can find this by running psql --version.\
Find the line that says `listen_addresses` and change it to:

```
listen_addresses = '*'
```

Find the line that says `password_encryption` and change it to:

```
password_encryption = md5
```

## 10. Allow user authentication

Edit the client authentication configuration file:

```bash
sudo nano /etc/postgresql/[version]/main/pg_hba.conf
```

Add this line at the end of the file:

```
host    all    all    0.0.0.0/0    md5
```

## 11. Restart PostgreSQL

Restart the PostgreSQL service to apply changes:

```bash
sudo service postgresql restart
```

## 12. Install psycopg2

Install psycopg2, the PostgreSQL adapter for Python:

```bash
pip install psycopg2-binary
```

Make sure to start the PostgreSQL service every time you start your WSL instance:

```bash
sudo service postgresql start
```

13. Login database to Create tables in the database

```bash
 psql -U postgres -h localhost -d postgres
```

- Run the query found in [alpha_calls_table.sql](../sql/alpha_calls_table.sql) to create the table.
