# 🗄️ Database Migration Manager - Quick Start

## 5-Minute Setup

### 1. **Make it Executable**
```bash
chmod +x server/Config/DB/migrate.sh
```

### 2. **Run Full Migration**
```bash
cd server/Config/DB
./migrate.sh full
```

That's it! 🎉

---

## Common Commands

### Check for Model Changes
```bash
./migrate.sh check
```
Detects new or modified models without running migration.

**Example Output:**
```
🔍 DETECTING MODEL CHANGES
⚠️  MODEL CHANGE DETECTED: User_model.py
⚠️  Changes detected in models:
    • MODIFIED: User_model.py
```

### Run Migration Only
```bash
./migrate.sh migrate
```
Creates/updates database tables based on models.

### Validate Schema
```bash
./migrate.sh validate
```
Shows all tables, columns, and their types.

**Example Output:**
```
📋 Database Schema Validation:
   Tables in database: 2
   
   📊 Table: users
      Primary Key: ['id']
      Columns (8):
         • id: UUID (NOT NULL)
         • username: VARCHAR (NOT NULL)
         • email: VARCHAR (NOT NULL)
         ...
```

### Get Status
```bash
./migrate.sh status
```
Shows model changes and recent logs.

### Generate Report
```bash
./migrate.sh report
```
Creates detailed migration report in `migrations/migration_report.txt`

### Backup Database
```bash
./migrate.sh backup
```
Creates backup file in `backups/` directory.

---

## How It Works

### Model Change Detection
The script tracks model files using MD5 checksums:

1. **First Run**: Creates baseline checksums
2. **Subsequent Runs**: Compares current vs. stored checksums
3. **Detects**:
   - 🆕 NEW models
   - 🔄 MODIFIED models
   - ✅ UNCHANGED models

### Migration Process
```
Check Changes → Backup DB → Run Migrations → Validate Schema
```

### Directory Structure Created
```
Config/DB/
├── migrate.sh                      ← Main script
├── migrations/
│   ├── .model_checksums            ← Change tracking
│   ├── migration.log               ← Activity logs
│   └── migration_report.txt        ← Reports
└── backups/
    └── db_backup_*.sql             ← Database backups
```

---

## Typical Workflow

### Adding a New Model
```bash
# 1. Create new model
vim App/models/MyNewModel.py

# 2. Check what changed
./migrate.sh check
# Output: ⚠️  NEW MODEL DETECTED: MyNewModel.py

# 3. Backup and migrate
./migrate.sh migrate

# 4. Verify
./migrate.sh validate
```

### Modifying Existing Model
```bash
# 1. Edit model
vim App/models/User_model.py

# 2. Check changes
./migrate.sh check
# Output: ⚠️  MODEL CHANGE DETECTED: User_model.py

# 3. Backup first
./migrate.sh backup

# 4. Migrate
./migrate.sh migrate

# 5. Validate
./migrate.sh validate
```

### Before Deployment
```bash
# 1. Ensure no pending changes
./migrate.sh check
# Should show: ✅ No model changes detected

# 2. Create backup
./migrate.sh backup

# 3. Run complete migration
./migrate.sh full

# 4. Generate documentation
./migrate.sh report

# 5. Verify everything
./migrate.sh validate
```

---

## Troubleshooting

### Error: "Python not found"
```bash
# Check Python is installed
python3 --version

# Install if needed (macOS)
brew install python3
```

### Error: "DATABASE_URL not found"
```bash
# Check .env file exists in project root
cat ../.env

# Should contain:
# DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```

### Error: "Permission denied"
```bash
# Make script executable
chmod +x migrate.sh

# Verify
ls -la migrate.sh
# Should show: -rwxr-xr-x
```

### Error: "Connection refused"
```bash
# Check database is running
pg_isready -h localhost

# For PostgreSQL on macOS:
brew services start postgresql

# For PostgreSQL on Ubuntu:
sudo systemctl start postgresql
```

---

## Understanding the Output

### Success
```
✅ Migrations completed successfully
✅ Schema validation passed
```

### Changes Detected
```
⚠️  MODEL CHANGE DETECTED: User_model.py
⚠️  Changes detected in models:
    • MODIFIED: User_model.py
```

### New Model
```
⚠️  NEW MODEL DETECTED: CustomAudit_model.py
⚠️  Changes detected in models:
    • NEW: CustomAudit_model.py
```

### No Changes
```
✅ No model changes detected
```

---

## Important Notes

1. **Always backup before production migrations**
   ```bash
   ./migrate.sh backup
   ```

2. **Test in development first**
   - Run on local database
   - Validate schema
   - Test application

3. **Keep old backups**
   - Don't delete backup files
   - Keep at least 2-3 recent versions

4. **Monitor logs**
   ```bash
   tail -f Config/DB/migrations/migration.log
   ```

5. **Regular checks**
   ```bash
   ./migrate.sh check  # Check for pending changes
   ./migrate.sh status # Get status overview
   ```

---

## Full Help
```bash
./migrate.sh help
```

---

**Version**: 1.0.0  
**Created**: December 26, 2025  
**Status**: ✅ Ready to use
