# Insights database migrations

Run migrations from this directory:

```bash
alembic upgrade head
```

Set `INSIGHTS_DB_URL` to control the database connection string. Defaults to `sqlite:///data/insights.db`.
