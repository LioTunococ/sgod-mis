# Period Management System - User Guide

**Last Updated**: Task 9 Documentation (October 2025)  
**Status**: Production Ready ✅

---

## Overview

The SGOD MIS uses a simplified **School Year and Quarter** system for organizing and filtering submission data. Periods are purely categorical labels used for statistics and comparison—they do not control when forms can be submitted (that's handled by FormTemplate open/close dates).

### Key Concepts

- **School Year**: Spans two calendar years (e.g., SY 2025-2026)
- **Quarters**: Each school year has 4 quarters (Q1, Q2, Q3, Q4)
- **No Date Fields**: Periods don't have start/end dates—they're just labels for filtering
- **Categorical Filtering**: Use periods to group and compare data across time

---

## For Administrators

### Creating a New School Year

1. **Access Directory Tools**
   - Log in as SGOD Admin
   - Navigate to **Directory Tools** (top navigation)
   - Click the **[📅 Periods]** tab

2. **Create School Year Form**
   - **School Year Start**: Enter the starting year (e.g., 2025)
   - Click **"Create School Year with 4 Quarters"**

3. **What Happens**
   - System automatically creates 4 periods:
     - Q1 - SY 2025-2026
     - Q2 - SY 2025-2026
     - Q3 - SY 2025-2026
     - Q4 - SY 2025-2026
   - Display order is set automatically (Q1=1, Q2=2, Q3=3, Q4=4)
   - All quarters are marked as active

### Example

**Input:**
```
School Year Start: 2025
```

**Result:**
```
✅ Created 4 periods:
   - Q1 - SY 2025-2026 (display order: 1)
   - Q2 - SY 2025-2026 (display order: 2)
   - Q3 - SY 2025-2026 (display order: 3)
   - Q4 - SY 2025-2026 (display order: 4)
```

### Managing Existing Periods

#### View All Periods

The Periods tab displays a table with:
- **Label**: Display name (e.g., "Q1 - SY 2025-2026")
- **School Year**: Year range (e.g., "SY 2025-2026")
- **Quarter**: Quarter tag (Q1, Q2, Q3, Q4)
- **Active**: Status indicator
- **Actions**: Delete button

#### Deleting Periods

⚠️ **Warning**: Deleting a period will affect:
- Dashboard filters (period will no longer appear)
- Reports (data associated with this period remains but can't be filtered)
- Form templates (if assigned to this period, they'll become orphaned)

**Steps:**
1. Click the **[Delete]** button next to a period
2. Confirm deletion in the modal
3. Period is permanently removed

#### Deactivating Periods (Recommended Alternative)

Instead of deleting, you can deactivate periods:
1. Go to **Django Admin** → **Periods**
2. Find the period
3. Uncheck **"Is active"**
4. Save
5. Period is hidden from filters but data remains intact

---

## For Users

### Understanding Periods in Dashboards

#### What Periods Are Used For

1. **Filtering Data**
   - Select a school year to view data for that year
   - Select "All Quarters" to see aggregate data
   - Select a specific quarter (Q1-Q4) to drill down

2. **Comparing Statistics**
   - View KPI trends across quarters
   - Compare school year performance year-over-year
   - Analyze quarterly progress

3. **Organizing Submissions**
   - Each submission is tagged with a period
   - Submissions are grouped by period in reports
   - Export data filtered by period

#### Period Selection Examples

**Example 1: View All Data for SY 2025-2026**
```
School Year: 2025-2026
Quarter: All Quarters
→ Shows aggregated data across Q1-Q4
```

**Example 2: View Q1 Data Only**
```
School Year: 2025-2026
Quarter: Q1
→ Shows data only from Q1 - SY 2025-2026
```

**Example 3: Compare Multiple School Years**
```
Navigate to different school years and compare KPI values
→ See year-over-year trends
```

---

## Database Structure

### Period Model

```python
class Period(models.Model):
    """Categorical label for organizing submissions—no date validation"""
    
    label = models.CharField(max_length=100)
    # Display label (e.g., "Q1", "Q2", "Q3", "Q4")
    
    school_year_start = models.PositiveIntegerField()
    # Starting year (e.g., 2025 for SY 2025-2026)
    
    quarter_tag = models.CharField(max_length=20)
    # Quarter identifier (Q1, Q2, Q3, Q4)
    
    display_order = models.PositiveIntegerField(default=0)
    # Sort order (Q1=1, Q2=2, Q3=3, Q4=4)
    
    is_active = models.BooleanField(default=True)
    # Whether this period appears in filters
```

### Unique Constraint

```python
unique_together = [['school_year_start', 'quarter_tag']]
```

**Effect**: Cannot create duplicate periods (e.g., two "Q1 - SY 2025-2026")

### Properties

```python
@property
def school_year_end(self):
    return self.school_year_start + 1

@property
def is_open(self):
    return self.is_active
```

---

## Form Submission Period vs. Display Period

### Important Distinction

**Period (Categorical Label)**
- Used for filtering and statistics
- No date restrictions
- Can be changed anytime
- Example: "Q1 - SY 2025-2026"

**FormTemplate Open/Close Dates**
- Controls when forms can be submitted
- Has actual start and end dates
- Enforces submission deadlines
- Example: "Open: 2025-06-01, Close: 2025-08-31"

### How They Work Together

1. **FormTemplate** has `open_date` and `close_date`
   - Schools can only submit forms within this window

2. **Submission** is tagged with a `period`
   - Used to categorize the submission
   - Used for dashboard filtering

3. **Example Flow**:
   ```
   FormTemplate "SMEA Form 1 Q1"
   ├── Open Date: June 1, 2025
   ├── Close Date: August 31, 2025
   └── Period: Q1 - SY 2025-2026
   
   → Schools can submit June 1 - August 31
   → Submission is tagged as "Q1 - SY 2025-2026"
   → Dashboard shows it when filtering by Q1
   ```

---

## API Integration

### Filtering by Period

```python
# Get all submissions for Q1 of SY 2025-2026
period = Period.objects.get(school_year_start=2025, quarter_tag='Q1')
submissions = Submission.objects.filter(period=period)

# Get all submissions for entire school year
periods = Period.objects.filter(school_year_start=2025, quarter_tag__in=['Q1', 'Q2', 'Q3', 'Q4'])
submissions = Submission.objects.filter(period__in=periods)
```

### AJAX Endpoint Example

```javascript
// Fetch dashboard data for Q1 2025
fetch('/dashboards/smme-kpi/data/?school_year=2025&quarter=Q1')
  .then(response => response.json())
  .then(data => {
    console.log('Filtered data:', data);
  });
```

See [API Documentation](API_DOCUMENTATION.md) for complete endpoint details.

---

## Best Practices

### For Administrators

1. **Create School Years in Advance**
   - Create next school year before the current one ends
   - Ensures smooth transition for form creation

2. **Never Delete Active Periods**
   - Deactivate instead to preserve data integrity
   - Deleting removes historical data from filters

3. **Consistent Naming**
   - System auto-generates labels (Q1, Q2, Q3, Q4)
   - Don't manually edit period labels in Django Admin

4. **One School Year at a Time**
   - Create school years sequentially
   - Avoid gaps (e.g., don't skip 2025-2026)

### For Users

1. **Filter by Quarter for Detailed Analysis**
   - Use specific quarters to drill down
   - Use "All Quarters" for overview

2. **Compare Across School Years**
   - Look for trends year-over-year
   - Identify improvement areas

3. **Understand Period is Not Submission Window**
   - Period is just a label
   - Check FormTemplate dates for submission deadlines

---

## Troubleshooting

### "No Periods Available" Error

**Cause**: No periods created for the selected school year

**Solution**:
1. Admin: Create periods for that school year
2. User: Select a different school year

### "Duplicate Period" Error

**Cause**: Attempting to create Q1-Q4 for a school year that already exists

**Solution**:
1. Check existing periods in the Periods tab
2. Use a different school year start
3. Delete existing periods if they were created incorrectly

### Missing Data in Dashboard

**Cause**: Submissions may be tagged with a different period

**Solution**:
1. Try "All Quarters" filter to see all data
2. Admin: Check submission records in Django Admin
3. Verify correct period was assigned during submission

### Period Not Showing in Filter

**Cause**: Period is marked as inactive

**Solution**:
1. Admin: Go to Django Admin → Periods
2. Find the period and check "Is active"
3. Save changes
4. Refresh dashboard

---

## Migration Notes

### From Old System (with dates)

If upgrading from an older version with date fields:

1. **Backup Database** before migration
2. **Run Migration**: `python manage.py migrate`
3. **Verify Data**: Check that existing periods migrated correctly
4. **Update Forms**: Ensure FormTemplates have proper open/close dates
5. **Test Filters**: Verify dashboard filtering works as expected

### Data Preserved

- ✅ All existing Period records
- ✅ All Submission-Period relationships
- ✅ Historical data and reports

### Data Removed

- ✂️ `open_date` field (migrated to FormTemplate.open_date)
- ✂️ `close_date` field (migrated to FormTemplate.close_date)
- ✂️ `starts_on` field (removed, not used)
- ✂️ `ends_on` field (removed, not used)

---

## Related Documentation

- **[User Guide](USER_GUIDE.md)** - Complete system guide
- **[API Documentation](API_DOCUMENTATION.md)** - AJAX endpoints
- **[Task 10 Implementation](TASK_10_NEW_SCHOOL_YEAR_SYSTEM_COMPLETE.md)** - Technical details
- **[KPI Calculations](KPI_CALCULATIONS.md)** - How periods affect KPIs

---

## Support

For issues or questions:
1. Check this guide first
2. Review error messages carefully
3. Contact SGOD Admin for period management issues
4. Contact technical support for system bugs

---

**Document Version**: 2.0 (Task 9)  
**Period System Version**: Simplified (No Dates)  
**Last Reviewed**: October 2025
