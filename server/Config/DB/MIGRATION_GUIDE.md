#!/bin/bash
#
# Database Migration Manager - Installation & Setup Guide
#
# This file provides instructions for using the migrate.sh script

cat << 'EOF'

╔════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║              📦 DATABASE MIGRATION MANAGER - SETUP GUIDE                    ║
║                                                                              ║
║              Nela Multi-Tenant AI Agent API - Model Migration Tool          ║
║                                                                              ║
╚════════════════════════════════════════════════════════════════════════════╝


🎯 PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The migrate.sh script provides automated database migrations for your SQLAlchemy
models with the following features:

  ✓ Automatic table creation from models
  ✓ Model change detection using checksums
  ✓ Database backups before migration
  ✓ Schema validation
  ✓ Migration logging
  ✓ Change tracking


📋 PREREQUISITES
═══════════════════════════════════════════════════════════════════════════════

Before using the migration script, ensure you have:

  ✓ Python 3.8+ installed
  ✓ PostgreSQL running (if using PostgreSQL)
  ✓ .env file configured with DATABASE_URL
  ✓ All dependencies installed (pip install -r requirements.txt)

Example .env file:
  DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/analyst_db
  ALGORITHM=HS256
  SECRET_KEY=your-secret-key-here


🚀 QUICK START
═══════════════════════════════════════════════════════════════════════════════

1. Navigate to the database config directory:
   cd server/Config/DB

2. Run the full migration:
   ./migrate.sh full

3. Or check for model changes first:
   ./migrate.sh check

4. Then run migration:
   ./migrate.sh migrate


📊 AVAILABLE COMMANDS
═══════════════════════════════════════════════════════════════════════════════

full                Run complete migration (detect changes + backup + migrate + validate)
  Usage: ./migrate.sh full
  Steps:
    1. Detect model changes
    2. Backup database
    3. Run migrations
    4. Validate schema
    5. Generate report
  
  Example:
    ./migrate.sh full
    ✅ Output shows all changes and migrations


status              Show migration status and model changes
  Usage: ./migrate.sh status
  Shows:
    • Model files present
    • What changed since last migration
    • Recent migration logs
    • Full schema validation report
  
  Example:
    ./migrate.sh status


check               Check for model changes only (don't migrate)
  Usage: ./migrate.sh check
  Shows:
    • List of new models
    • List of modified models
    • File hashes for tracking
  
  Example:
    ./migrate.sh check
    ⚠️  Model changes detected:
        • NEW: CustomUser_model.py
        • MODIFIED: Document_model.py


migrate             Run migrations without other checks
  Usage: ./migrate.sh migrate
  Steps:
    1. Backup database
    2. Create/update tables
  
  Example:
    ./migrate.sh migrate


validate            Validate database schema
  Usage: ./migrate.sh validate
  Shows:
    • Tables in database
    • Columns per table
    • Column types and constraints
    • Primary keys
  
  Example:
    ./migrate.sh validate
    ✅ Schema validation passed
       Total tables: 2
       • users: 8 columns
       • documents: 6 columns


backup              Create database backup only
  Usage: ./migrate.sh backup
  Creates:
    • Backup file in Config/DB/backups/
    • Named: db_backup_YYYYMMDD_HHMMSS.sql
  
  Example:
    ./migrate.sh backup
    ✅ Backup created: db_backup_20251226_143025.sql


report              Generate migration report
  Usage: ./migrate.sh report
  Creates:
    • Report file: Config/DB/migrations/migration_report.txt
    • Shows model files, checksums, recent logs
  
  Example:
    ./migrate.sh report
    ✅ Report saved to: Config/DB/migrations/migration_report.txt


clean               Clear migration cache and checksums
  Usage: ./migrate.sh clean
  Removes:
    • Stored model checksums
    • Migration cache
  
  Example:
    ./migrate.sh clean
    ✅ Cache cleaned


help                Show help message
  Usage: ./migrate.sh help
       ./migrate.sh --help
       ./migrate.sh -h


═════════════════════════════════════════════════════════════════════════════════


🔄 TYPICAL WORKFLOW
═══════════════════════════════════════════════════════════════════════════════

1. DEVELOPMENT: Check for changes
   ────────────────────────────────
   $ ./migrate.sh check
   
   ⚠️  Model changes detected:
       • MODIFIED: User_model.py


2. BEFORE MIGRATION: Create backup
   ──────────────────────────────
   $ ./migrate.sh backup
   
   ✅ Backup created: db_backup_20251226_143025.sql


3. MIGRATE: Apply changes
   ──────────────────────
   $ ./migrate.sh migrate
   
   ✅ Migrations completed successfully


4. VALIDATE: Check schema
   ──────────────────────
   $ ./migrate.sh validate
   
   📋 Database Schema Validation:
      Tables in database: 2
      • users: 8 columns
      • documents: 6 columns
   ✅ Schema validation passed!


5. REPORT: Generate documentation
   ─────────────────────────────────
   $ ./migrate.sh report
   
   ✅ Report saved to: Config/DB/migrations/migration_report.txt


═════════════════════════════════════════════════════════════════════════════════


📁 DIRECTORY STRUCTURE
═══════════════════════════════════════════════════════════════════════════════

Config/DB/
├── migrate.sh                    ← Main migration script
├── MIGRATION_README.sh           ← This file
├── db.py                         ← Database configuration
├── init_db.py                    ← Initial DB setup
├── migrations/
│   ├── run_migration.py          ← Generated: Python migration script
│   ├── validate_schema.py        ← Generated: Schema validator
│   ├── .model_checksums          ← Model change tracking
│   ├── migration.log             ← Migration logs
│   └── migration_report.txt      ← Generated: Migration report
└── backups/
    ├── db_backup_20251226_143025.sql
    ├── db_backup_20251226_142015.sql
    └── ...


═════════════════════════════════════════════════════════════════════════════════


🔍 MODEL CHANGE DETECTION
═══════════════════════════════════════════════════════════════════════════════

The script tracks model changes using MD5 checksums:

1. On first run:
   - Calculates hash of all model files in App/models/
   - Stores checksums in Config/DB/migrations/.model_checksums
   - Creates baseline for comparison

2. On subsequent runs:
   - Compares current model hashes with stored checksums
   - Identifies:
     • NEW models (not in previous checksums)
     • MODIFIED models (hash changed)
     • UNCHANGED models (hash matches)

3. Change detection types:
   ┌─────────────────────────────────────────────────────┐
   │ NEW MODEL                                           │
   │ File not seen before                                │
   │ Action: Table will be created                       │
   │ Example: CustomAudit_model.py                       │
   ├─────────────────────────────────────────────────────┤
   │ MODIFIED MODEL                                      │
   │ File content changed (hash differs)                 │
   │ Action: Table columns may be added/modified         │
   │ Example: User_model.py (new field added)            │
   ├─────────────────────────────────────────────────────┤
   │ UNCHANGED MODEL                                     │
   │ File not changed (hash matches)                     │
   │ Action: No changes needed                           │
   │ Example: Document_model.py                          │
   └─────────────────────────────────────────────────────┘

How to understand the output:

   $ ./migrate.sh check
   
   🔍 DETECTING MODEL CHANGES
   
   ℹ️  Comparing model files...
   
   ✅ No model changes detected    ← All models unchanged
   
   OR
   
   ⚠️  NEW MODEL DETECTED: CustomAudit_model.py
   ⚠️  MODEL CHANGE DETECTED: User_model.py
   
   ⚠️  Changes detected in models:
       • NEW: CustomAudit_model.py
       • MODIFIED: User_model.py


═════════════════════════════════════════════════════════════════════════════════


💾 DATABASE BACKUPS
═══════════════════════════════════════════════════════════════════════════════

The script automatically backs up your database before migrations:

Location:
  Config/DB/backups/db_backup_YYYYMMDD_HHMMSS.sql

Naming Format:
  db_backup_20251226_143025.sql
  ├─ Date: 2025-12-26
  └─ Time: 14:30:25

When backups are created:
  ✓ Before running 'full' migration
  ✓ When running 'migrate' command
  ✓ When running 'backup' command explicitly

Backup management:
  • Backups are kept indefinitely (you can manually delete old ones)
  • Create backup before making schema changes
  • Test migrations on backup first in development

Manual backup:
  $ ./migrate.sh backup


═════════════════════════════════════════════════════════════════════════════════


📝 MIGRATION LOGS
═══════════════════════════════════════════════════════════════════════════════

All migration activity is logged to: Config/DB/migrations/migration.log

Log entries include:
  • Timestamp
  • Action taken
  • Model changes detected
  • Backup locations
  • Migration status
  • Validation results

Example log:
  [2025-12-26 14:30:25] New model: /path/to/App/models/CustomAudit_model.py
  [2025-12-26 14:30:26] Model modified: /path/to/App/models/User_model.py
  [2025-12-26 14:30:27] Database backup created: db_backup_20251226_143025.sql
  [2025-12-26 14:30:30] Migrations completed successfully
  [2025-12-26 14:30:33] Schema validation passed


═════════════════════════════════════════════════════════════════════════════════


🛠️  TROUBLESHOOTING
═══════════════════════════════════════════════════════════════════════════════

Problem: "Python not found"
Solution:
  • Ensure Python 3.8+ is installed
  • On macOS: brew install python3
  • On Ubuntu: sudo apt install python3
  • On Windows: Download from python.org

Problem: "DATABASE_URL not found"
Solution:
  • Create/update .env file in project root
  • Add: DATABASE_URL=postgresql://...
  • Restart terminal
  • Run: echo $DATABASE_URL (to verify)

Problem: "Connection refused" error
Solution:
  • Ensure database server is running
  • For PostgreSQL: pg_isready -h localhost
  • Check DATABASE_URL credentials
  • Verify database exists

Problem: "Tables already exist" warning
Solution:
  • This is normal if tables already exist
  • SQLAlchemy handles existing tables gracefully
  • No data is lost

Problem: "Permission denied" error
Solution:
  • Make script executable: chmod +x migrate.sh
  • Check file permissions: ls -la migrate.sh
  • Run from correct directory: cd server/Config/DB

Problem: "Import error" when running
Solution:
  • Ensure you're in the project root directory
  • Run: pip install -r requirements.txt
  • Check PYTHONPATH includes project root


═════════════════════════════════════════════════════════════════════════════════


✅ BEST PRACTICES
═══════════════════════════════════════════════════════════════════════════════

1. ALWAYS BACKUP BEFORE PRODUCTION
   $ ./migrate.sh backup

2. TEST IN DEVELOPMENT FIRST
   • Run migrations locally
   • Validate schema
   • Test application

3. CHECK FOR CHANGES REGULARLY
   $ ./migrate.sh check
   • Ensures no unexpected changes
   • Good before committing code

4. RUN FULL MIGRATION
   $ ./migrate.sh full
   • Comprehensive process
   • Detects + backs up + migrates + validates

5. KEEP BACKUP FILES
   • Don't delete old backups immediately
   • Keep at least 2-3 recent versions
   • Archive to external storage for production

6. MONITOR LOGS
   • Check Config/DB/migrations/migration.log
   • Review reports: ./migrate.sh report
   • Look for warnings and errors

7. DOCUMENT MODEL CHANGES
   • Add comments to modified models
   • Update API documentation
   • Note breaking changes


═════════════════════════════════════════════════════════════════════════════════


🔗 INTEGRATION WITH APPLICATION
═══════════════════════════════════════════════════════════════════════════════

The migrate.sh script works with your FastAPI application:

Workflow:
  1. Development: Modify models in App/models/
  2. Check: Run ./migrate.sh check
  3. If changes: Run ./migrate.sh migrate
  4. Test: Run FastAPI server and test endpoints
  5. Verify: Run ./migrate.sh validate
  6. Deploy: Follow PRE_DEPLOYMENT_CHECKLIST.md

Integration points:
  • Models: App/models/User_model.py, Document_model.py
  • Database: Config/DB/db.py (engine configuration)
  • Schemas: App/schema/ (Pydantic models)
  • Controllers: App/controllers/ (business logic)

Model changes typically needed when:
  • Adding new fields to entities
  • Creating new database tables
  • Changing field types
  • Adding/removing relationships
  • Modifying constraints


═════════════════════════════════════════════════════════════════════════════════


📚 ADDITIONAL RESOURCES
═══════════════════════════════════════════════════════════════════════════════

Related documentation:
  • Config/DB/db.py - Database configuration
  • App/models/ - Your database models
  • PRE_DEPLOYMENT_CHECKLIST.md - Before production
  • API_DOCUMENTATION.md - Your API reference

SQLAlchemy documentation:
  • https://docs.sqlalchemy.org/
  • Async support: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
  • Core documentation: https://docs.sqlalchemy.org/en/20/

PostgreSQL documentation:
  • https://www.postgresql.org/docs/


═════════════════════════════════════════════════════════════════════════════════


🎯 COMMON WORKFLOWS
═══════════════════════════════════════════════════════════════════════════════

Workflow 1: Initial Setup
───────────────────────
$ cd server/Config/DB
$ ./migrate.sh full
  ✅ Creates all tables from models
  ✅ Validates schema
  ✅ Generates report

Workflow 2: Add New Model
─────────────────────────
1. Create new model: App/models/MyModel.py
2. Check changes: ./migrate.sh check
3. Migrate: ./migrate.sh migrate
4. Validate: ./migrate.sh validate

Workflow 3: Modify Existing Model
─────────────────────────────────
1. Edit model: App/models/User_model.py
2. Check: ./migrate.sh check (should show MODIFIED)
3. Backup: ./migrate.sh backup
4. Migrate: ./migrate.sh migrate
5. Test application

Workflow 4: Regular Maintenance
──────────────────────────────
$ ./migrate.sh status       # Check status
$ ./migrate.sh report       # Generate report
$ ./migrate.sh validate     # Ensure schema is good

Workflow 5: Before Deployment
──────────────────────────────
$ ./migrate.sh check        # Ensure no changes pending
$ ./migrate.sh backup       # Create backup
$ ./migrate.sh full         # Run complete migration
$ ./migrate.sh report       # Document current state


═════════════════════════════════════════════════════════════════════════════════

That's it! You're ready to use the database migration manager.

For more help:
  ./migrate.sh help

Happy migrations! 🚀

EOF
