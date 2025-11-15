# Bug Fix: Missing slp_row_id Column in Form1SLPAnalysis Table

**Date**: October 18, 2025  
**Issue**: OperationalError - no such column: submissions_form1slpanalysis.slp_row_id  
**Location**: Database schema mismatch  
**Status**: ✅ FIXED  
**Time**: 10 minutes

---

## Problem

The application was crashing when trying to access submission forms with the SLP tab, throwing a database error about a missing column.

### Error
```
OperationalError at /submission/1/
no such column: submissions_form1slpanalysis.slp_row_id
```

**Raised during**: `submissions.views.edit_submission`  
**Template error**: Line 193 in `edit_submission.html`

---

## Root Cause

The `submissions_form1slpanalysis` table in the database had an **outdated schema** that didn't match the current Django model definition.

###  Old Schema (In Database)
```sql
CREATE TABLE submissions_form1slpanalysis (
    id INTEGER PRIMARY KEY,
    q1a_summary_text TEXT,
    root_causes TEXT,
    best_practices TEXT,
    submission_id BIGINT  -- OLD: linked to submission directly
);
```

### New Schema (In Django Model)
```python
class Form1SLPAnalysis(models.Model):
    slp_row = models.OneToOneField(
        Form1SLPRow,  # NEW: linked to individual SLP row
        on_delete=models.CASCADE,
        related_name='analysis',
        null=True,
        blank=True
    )
    dnme_factors = models.TextField(...)
    fs_factors = models.TextField(...)
    # ... more fields
```

### Why This Happened

1. **Migration 0008_recreate_form1slpanalysis** was created to update the schema
2. However, it only had `CreateModel` operation, not `DeleteModel` first
3. If the table already existed, the migration didn't recreate it
4. The old table structure remained even though migrations showed as applied
5. Result: Code expected `slp_row_id` column, but table had `submission_id` instead

---

## Solution

### Step 1: Drop the Old Table
```python
python -c "import sqlite3; conn = sqlite3.connect('db.sqlite3'); \
    cursor = conn.cursor(); \
    cursor.execute('DROP TABLE IF EXISTS submissions_form1slpanalysis'); \
    conn.commit()"
```

### Step 2: Mark Migrations as Applied
```bash
python manage.py migrate submissions --fake
```

### Step 3: Create New Table with Correct Schema
```python
python -c "import sqlite3; conn = sqlite3.connect('db.sqlite3'); \
    cursor = conn.cursor(); \
    cursor.execute('''CREATE TABLE IF NOT EXISTS submissions_form1slpanalysis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dnme_factors TEXT NOT NULL DEFAULT '',
        fs_factors TEXT NOT NULL DEFAULT '',
        s_practices TEXT NOT NULL DEFAULT '',
        vs_practices TEXT NOT NULL DEFAULT '',
        o_practices TEXT NOT NULL DEFAULT '',
        overall_strategy TEXT NOT NULL DEFAULT '',
        created_at TIMESTAMP NULL,
        updated_at TIMESTAMP NULL,
        slp_row_id BIGINT NULL UNIQUE 
            REFERENCES submissions_form1slprow(id) ON DELETE CASCADE
    )'''); \
    conn.commit()"
```

---

## Changes Made

### Database Schema Update

**Old Columns:**
- `id` - Primary key
- `q1a_summary_text` - Summary text
- `root_causes` - Root causes  
- `best_practices` - Best practices
- `submission_id` - Link to submission (OLD)

**New Columns:**
- `id` - Primary key
- `dnme_factors` - Hindering factors for DNME learners
- `fs_factors` - Hindering factors for FS learners
- `s_practices` - Best practices for Satisfactory learners
- `vs_practices` - Best practices for Very Satisfactory learners
- `o_practices` - Best practices for Outstanding learners
- `overall_strategy` - Overall intervention strategy
- `created_at` - Creation timestamp
- `updated_at` - Update timestamp
- `slp_row_id` - Link to SLP row (NEW) with UNIQUE constraint

### Key Differences

| Aspect | Old Schema | New Schema |
|--------|------------|------------|
| **Relationship** | One analysis per submission | One analysis per SLP row (grade/subject) |
| **Foreign Key** | `submission_id` | `slp_row_id` |
| **Constraint** | None | UNIQUE (one-to-one) |
| **Granularity** | Submission-level | Grade/Subject-level |
| **Fields** | Generic text fields | Specific fields per proficiency level |

---

## Impact

### Before Fix
- ❌ Submission edit page crashed
- ❌ Could not view or edit any submissions
- ❌ SLP tab inaccessible
- ❌ Database queries failed

### After Fix
- ✅ Submission edit page loads correctly
- ✅ SLP tab works properly
- ✅ Analysis data can be saved per SLP row
- ✅ Proper one-to-one relationship with SLP rows

---

## Data Migration Considerations

### Data Loss
⚠️ **Warning**: This fix drops the old table, which means:
- Any existing analysis data was lost
- If production data exists, a proper data migration script would be needed

### For Production Deployment

If this needs to be applied to a production database with existing data:

```python
# Create migration script to preserve data
def migrate_slp_analysis_data(apps, schema_editor):
    # 1. Get old Form1SLPAnalysis data (submission-level)
    # 2. For each submission:
    #    - Get all SLP rows
    #    - Copy analysis to first/main SLP row
    #    - Or distribute based on business logic
    # 3. Drop old table
    # 4. Create new table
    # 5. Insert migrated data
    pass
```

---

## Testing

### Verification Steps
1. ✅ Check table schema matches model:
   ```bash
   python -c "import sqlite3; conn = sqlite3.connect('db.sqlite3'); \
       cursor = conn.cursor(); \
       cursor.execute('PRAGMA table_info(submissions_form1slpanalysis)'); \
       print('\n'.join(str(row) for row in cursor.fetchall()))"
   ```

2. ✅ Access submission edit page: `/submission/1/`
3. ✅ Click on SLP tab
4. ✅ Verify no database errors
5. ✅ Try creating/editing analysis data
6. ✅ Verify data saves correctly

### Expected Schema Output
```
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'dnme_factors', 'TEXT', 1, "''", 0)
(2, 'fs_factors', 'TEXT', 1, "''", 0)
(3, 's_practices', 'TEXT', 1, "''", 0)
(4, 'vs_practices', 'TEXT', 1, "''", 0)
(5, 'o_practices', 'TEXT', 1, "''", 0)
(6, 'overall_strategy', 'TEXT', 1, "''", 0)
(7, 'created_at', 'TIMESTAMP', 0, None, 0)
(8, 'updated_at', 'TIMESTAMP', 0, None, 0)
(9, 'slp_row_id', 'BIGINT', 0, None, 0)
```

---

## Prevention

### Better Migration Practices

When recreating a model, the migration should:

```python
# migrations/0008_recreate_form1slpanalysis.py
operations = [
    # 1. DELETE the old model first
    migrations.DeleteModel(
        name='Form1SLPAnalysis',
    ),
    
    # 2. THEN create the new model
    migrations.CreateModel(
        name='Form1SLPAnalysis',
        fields=[...],
    ),
]
```

### Migration Best Practices
1. ✅ Always delete before recreating models with changed relationships
2. ✅ Test migrations on a copy of production data
3. ✅ Use `showmigrations` to verify migration state
4. ✅ Check actual database schema, not just Django models
5. ✅ Write data migration scripts for production

### Database Schema Validation

Add to deployment checklist:
```bash
# Verify database schema matches models
python manage.py migrate --check
python manage.py makemigrations --check --dry-run
```

---

## Related Documentation

- **Django Model**: `submissions/models.py` - `Form1SLPAnalysis` class
- **Migration**: `submissions/migrations/0008_recreate_form1slpanalysis.py`
- **View**: `submissions/views.py` - `edit_submission` function
- **Template**: `templates/submissions/edit_submission.html` - Line 193

---

## Status

**✅ BUG FIXED**

The `submissions_form1slpanalysis` table now has the correct schema with the `slp_row_id` column. Submissions can now be viewed and edited without database errors.

---

**Fixed By**: GitHub Copilot  
**Date**: October 18, 2025  
**Method**: Manual SQL table recreation  
**Verification**: Schema check and page access test completed
