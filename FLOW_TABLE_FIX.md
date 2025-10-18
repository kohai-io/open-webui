# Fix: Flow Table Not Created

The error `no such table: flow` means the database migration hasn't been applied yet.

## Quick Fix Options

### Option 1: Run SQL Directly (Easiest)

1. **Find your database file**:
   - Usually at `backend/data/webui.db` (SQLite)
   - Or check your `DATABASE_URL` environment variable

2. **Run the SQL script**:
   ```bash
   # For SQLite
   sqlite3 backend/data/webui.db < backend/create_flow_table.sql
   
   # Or using Python
   python -c "
   import sqlite3
   conn = sqlite3.connect('backend/data/webui.db')
   with open('backend/create_flow_table.sql', 'r') as f:
       conn.executescript(f.read())
   conn.close()
   print('✅ Flow table created!')
   "
   ```

### Option 2: Manual SQL (Copy-Paste)

Connect to your database and run:

```sql
CREATE TABLE IF NOT EXISTS flow (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    nodes JSON NOT NULL,
    edges JSON NOT NULL,
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL,
    meta JSON DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS flow_user_id_idx ON flow(user_id);
CREATE INDEX IF NOT EXISTS flow_updated_at_idx ON flow(updated_at);
CREATE INDEX IF NOT EXISTS flow_user_id_updated_at_idx ON flow(user_id, updated_at);
```

### Option 3: Restart Backend (Automatic Migration)

If you're using the standard setup:

```bash
cd backend
# Stop the backend if running
# Then start it again
./start.sh  # or however you start the backend
```

The Alembic migration should run automatically on startup.

### Option 4: Run Alembic Migration

If alembic is installed in your environment:

```bash
cd backend
alembic upgrade head
```

Or with Python module:

```bash
cd backend
python -m alembic upgrade head
```

## Verify Table Creation

After running any of the above, verify with:

```sql
SELECT name FROM sqlite_master WHERE type='table' AND name='flow';
```

Should return: `flow`

Or check from Python:

```python
from open_webui.models.flows import Flows
flows = Flows.get_flows()
print(f"✅ Flow table working! Found {len(flows)} flows")
```

## For PostgreSQL Users

If you're using PostgreSQL instead of SQLite, use this instead:

```sql
CREATE TABLE IF NOT EXISTS flow (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    nodes JSONB NOT NULL,
    edges JSONB NOT NULL,
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL,
    meta JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS flow_user_id_idx ON flow(user_id);
CREATE INDEX IF NOT EXISTS flow_updated_at_idx ON flow(updated_at);
CREATE INDEX IF NOT EXISTS flow_user_id_updated_at_idx ON flow(user_id, updated_at);
```

Note: PostgreSQL uses `JSONB` instead of `JSON` for better performance.

## Still Having Issues?

1. **Check database location**:
   ```bash
   # Look for DATABASE_URL in your environment
   echo $DATABASE_URL
   # Or check the backend logs for database path
   ```

2. **Check permissions**:
   Make sure the backend has write permissions to the database file

3. **Check backend logs**:
   Look for migration errors when the backend starts

4. **Verify migration file exists**:
   ```bash
   ls backend/open_webui/migrations/versions/e1f4a2b6c3d7_add_flow_table.py
   ```

## After Creating the Table

1. Restart your browser to clear any cached errors
2. Navigate to `/workspace/flows`
3. Click "Create Flow" to test
4. You should now be able to create and save flows!

---

**Need Help?** Check the main `FLOWS_README.md` for complete documentation.
