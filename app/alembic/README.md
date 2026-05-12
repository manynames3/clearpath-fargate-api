# Alembic Migrations

This folder provides the production-style migration path for future schema changes.

The current deployment still includes `sql/schema.sql` and `scripts/migrate.sh` as the simple bootstrap path used during short-lived AWS validation. The initial Alembic revision mirrors that schema so the project has a clean upgrade path when the database starts evolving beyond the demo schema.

Run migrations from the `app/` directory with either `DATABASE_URL` for local/dev databases or the deployed `DB_SECRET_ARN` and `DB_PROXY_ENDPOINT` environment variables for RDS Proxy IAM authentication.

```bash
cd app
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/clearpath alembic upgrade head
```
