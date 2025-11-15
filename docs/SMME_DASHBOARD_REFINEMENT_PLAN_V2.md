# SMME Dashboard Refinement Plan V2 - UPDATED

**Date**: October 17, 2025  
**Status**: Planning Phase - UPDATED with new requirements  
**Priority**: HIGH

---

## 🎯 NEW REQUIREMENTS ADDED

### **1. Advanced Filtering System**
- ✅ Filter by School Year (already exists)
- ✅ Filter by Quarter (Q1, Q2, Q3, Q4) (already exists)
- 🆕 **Filter by Quarter with "All Quarters" option**
- 🆕 **Filter by Individual School** (dropdown with all schools)
- 🆕 **"All Schools" option** to see aggregated data

### **2. School Comparison Feature**
- 🆕 **Compare Performance Per School**
  - Side-by-side comparison of multiple schools
  - Show each school's DNME%, Access%, Quality%, etc.
  - Visual comparison using grouped bar charts
  - Highlight best/worst performers

### **3. Detailed Statistics Table Enhancement**
- 🆕 **Show ALL KPIs for ALL Schools in Table Format**
  - Scrollable table with all schools as rows
  - All KPI metrics as columns
  - Sortable by any column
  - Color-coded cells (red for DNME, green for good performance)
  - Export to Excel option

---

## 📊 UPDATED DASHBOARD STRUCTURE

### **New Layout**:

```
┌────────────────────────────────────────────────────────────────┐
│  SGOD MIS Navigation Bar                           [User Menu]  │
└────────────────────────────────────────────────────────────────┘

  SMME KPI Dashboard
  School Management, Monitoring and Evaluation

┌────────────────────────────────────────────────────────────────┐
│  FILTERS                                                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │School Year│ │Quarter    │ │School     │ │KPI Metric│        │
│  │SY 2025-26 │ │Q1        │ │All Schools│ │DNME %    │        │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘        │
│                                                                 │
│  Quarter Options:                                               │
│  - All Quarters (aggregate)                                     │
│  - Q1 only                                                      │
│  - Q2 only                                                      │
│  - Q3 only                                                      │
│  - Q4 only                                                      │
│                                                                 │
│  School Options:                                                │
│  - All Schools (aggregate/compare)                              │
│  - [Individual school names from dropdown]                      │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│  SUMMARY CARDS                                                  │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐      │
│  │Total  │ │DNME  │ │Access│ │Quality│ │Govern│ │Mgmt  │      │
│  │Schools│ │ 15%  │ │ 85%  │ │ 78%  │ │ 82%  │ │ 88%  │      │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘      │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│  CHART VISUALIZATION                                            │
│  Selected: DNME Percentage by Quarter - All Schools            │
│                                                                 │
│   20% ┤                    ██                                  │
│   15% ┤           ██       ██                                  │
│   10% ┤     ██    ██       ██                                  │
│    5% ┤ ██  ██    ██       ██                                  │
│       └─────────────────────────────                           │
│        Q1  Q2    Q3       Q4                                   │
│                                                                 │
│  🆕 WHEN SPECIFIC SCHOOL SELECTED:                             │
│  "DNME Percentage - Pulong Tala ES" (single school trend)      │
│                                                                 │
│  🆕 SCHOOL COMPARISON MODE:                                    │
│  [Button: Compare Schools]                                      │
│  Select schools to compare: [☑ School A] [☑ School B] [☑ C]   │
│                                                                 │
│  Grouped bar chart showing all selected schools side-by-side   │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│  🆕 DETAILED STATISTICS - ALL SCHOOLS, ALL KPIs                │
│  [Export to Excel Button]                                       │
│                                                                 │
│  Scrollable Table:                                              │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │School Name    │DNME%│Access│Quality│Govern│Mgmt│Leader│  │
│  ├─────────────────────────────────────────────────────────┤  │
│  │Pulong Tala ES │ 12% │ 88%  │ 75%   │ 80%  │85% │ 90% │  │
│  │Ampid I ES     │ 18% │ 82%  │ 70%   │ 78%  │82% │ 85% │  │
│  │Bagong Silang  │ 25% │ 75%  │ 65%   │ 72%  │78% │ 80% │  │
│  │... (scrollable to see all schools)                       │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Features:                                                      │
│  - Sortable by clicking column headers                          │
│  - Color-coded cells (Red: <70%, Yellow: 70-85%, Green: >85%) │
│  - Search/filter within table                                   │
│  - Shows data for selected quarter or all quarters             │
└────────────────────────────────────────────────────────────────┘
```

---

## 📋 IMPLEMENTATION PLAN - UPDATED

---

## **PHASE 1: UI & Navigation Fixes** ✅ COMPLETED

### **Task 1.1: Remove Emoji** ✅ DONE
- Removed "📊" from dashboard title

### **Task 1.2: Add Navigation Bar** ✅ DONE
- Integrated top_nav.html
- Proper site navigation

---

## **PHASE 2: Core KPI Calculations** ✅ COMPLETED

### **Task 2.1: Create KPI Calculators** ✅ DONE
- Created `dashboards/kpi_calculators.py`
- Functions for DNME%, Access%, Quality%, Governance%, Management%, Leadership%

### **Task 2.2: Update Dashboard View** ✅ DONE
- Modified `smme_kpi_dashboard` to calculate real KPIs
- Query SMEA Form 1 submissions

---

## **PHASE 3: Advanced Filtering** 🆕 NEW

**Priority**: HIGH  
**Estimated Time**: 2 hours

### **Task 3.1: Add "All Quarters" Option** (30 min)

**Current State**:
- View Type dropdown has: "Quarterly Comparison (Q1-Q4)", "All Periods", "Single Period"

**New Requirement**:
- Quarter dropdown should have: "All Quarters", "Q1", "Q2", "Q3", "Q4"

**Implementation**:

**File**: `dashboards/views.py` - Update filtering logic

```python
def smme_kpi_dashboard(request):
    # ... existing code ...
    
    # Get filters
    school_year = request.GET.get('school_year', default_school_year)
    quarter_filter = request.GET.get('quarter', 'all')  # 🆕 NEW: all, q1, q2, q3, q4
    school_filter = request.GET.get('school', 'all')     # 🆕 NEW: all or school_id
    kpi_metric = request.GET.get('kpi_metric', 'dnme')
    chart_type = request.GET.get('chart_type', 'bar')
    
    # Filter periods based on quarter selection
    if quarter_filter == 'all':
        # Get all quarters for the school year
        periods = Period.objects.filter(
            school_year_start=int(school_year),
            quarter_tag__in=['Q1', 'Q2', 'Q3', 'Q4']
        ).order_by('display_order')
    else:
        # Get specific quarter
        periods = Period.objects.filter(
            school_year_start=int(school_year),
            quarter_tag__iexact=quarter_filter
        )
    
    # 🆕 Filter schools
    if school_filter == 'all':
        schools = School.objects.all()
    else:
        schools = School.objects.filter(id=int(school_filter))
    
    # Calculate KPIs per period and school
    kpi_data = []
    for period in periods:
        for school in schools:
            # Get SMEA Form 1 submissions for this period and school
            submissions = Form1SLPLLCEntry.objects.filter(
                school=school,
                period=period
            )
            
            if submissions.exists():
                kpis = calculate_all_kpis(submissions)
                kpi_data.append({
                    'period': period,
                    'school': school,
                    'kpis': kpis
                })
    
    # Aggregate or separate based on filters
    if school_filter == 'all' and quarter_filter == 'all':
        # Aggregate: Average across all schools and all quarters
        chart_data = aggregate_kpis(kpi_data)
    elif school_filter == 'all':
        # Show average per quarter across all schools
        chart_data = aggregate_by_quarter(kpi_data)
    elif quarter_filter == 'all':
        # Show single school across all quarters
        chart_data = aggregate_by_school(kpi_data)
    else:
        # Single school, single quarter
        chart_data = single_school_quarter(kpi_data)
    
    context = {
        'school_years': get_available_school_years(),
        'periods': periods,
        'schools': School.objects.all().order_by('name'),  # 🆕 For dropdown
        'selected_school': school_filter,
        'selected_quarter': quarter_filter,
        'selected_kpi': kpi_metric,
        'chart_data': chart_data,
        'kpi_data': kpi_data,  # 🆕 For detailed table
        # ... rest of context ...
    }
    
    return render(request, 'dashboards/smme_kpi_dashboard.html', context)
```

**File**: `templates/dashboards/smme_kpi_dashboard.html` - Update filters

```html
<!-- Replace view_type dropdown with quarter dropdown -->
<div>
    <label class="form-label" style="font-weight: 600;">Quarter</label>
    <select name="quarter" class="form-input" onchange="this.form.submit()">
        <option value="all" {% if selected_quarter == 'all' %}selected{% endif %}>
            All Quarters
        </option>
        <option value="Q1" {% if selected_quarter == 'Q1' %}selected{% endif %}>
            Quarter 1
        </option>
        <option value="Q2" {% if selected_quarter == 'Q2' %}selected{% endif %}>
            Quarter 2
        </option>
        <option value="Q3" {% if selected_quarter == 'Q3' %}selected{% endif %}>
            Quarter 3
        </option>
        <option value="Q4" {% if selected_quarter == 'Q4' %}selected{% endif %}>
            Quarter 4
        </option>
    </select>
</div>

<!-- 🆕 NEW: Add school dropdown -->
<div>
    <label class="form-label" style="font-weight: 600;">School</label>
    <select name="school" class="form-input" onchange="this.form.submit()">
        <option value="all" {% if selected_school == 'all' %}selected{% endif %}>
            All Schools
        </option>
        {% for school in schools %}
        <option value="{{ school.id }}" 
                {% if selected_school == school.id|stringformat:'s' %}selected{% endif %}>
            {{ school.name }}
        </option>
        {% endfor %}
    </select>
</div>
```

---

## **PHASE 4: School Comparison Feature** 🆕 NEW

**Priority**: MEDIUM  
**Estimated Time**: 2 hours

### **Task 4.1: Add Comparison Mode Toggle** (30 min)

**UI Addition**:
```html
<section class="card" style="margin-bottom: 1.5rem;">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <h3>Chart Visualization</h3>
        
        <!-- 🆕 Comparison Mode Toggle -->
        <div>
            <button type="button" id="toggleComparison" class="btn btn--outline">
                📊 Compare Schools
            </button>
        </div>
    </div>
    
    <!-- 🆕 School Selection for Comparison (hidden by default) -->
    <div id="comparisonPanel" style="display: none; margin-top: 1rem; padding: 1rem; background: #f3f4f6; border-radius: 8px;">
        <p style="font-weight: 600; margin-bottom: 0.5rem;">Select schools to compare:</p>
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.5rem;">
            {% for school in schools %}
            <label style="display: flex; align-items: center; gap: 0.5rem;">
                <input type="checkbox" name="compare_schools" value="{{ school.id }}" class="form-checkbox">
                <span>{{ school.name }}</span>
            </label>
            {% endfor %}
        </div>
        <button type="button" id="applyComparison" class="btn" style="margin-top: 1rem;">
            Apply Comparison
        </button>
    </div>
</section>
```

### **Task 4.2: Implement Comparison Chart** (1 hour)

**JavaScript Update**:
```javascript
// Handle comparison mode
document.getElementById('toggleComparison').addEventListener('click', function() {
    const panel = document.getElementById('comparisonPanel');
    panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
});

document.getElementById('applyComparison').addEventListener('click', function() {
    const checkboxes = document.querySelectorAll('input[name="compare_schools"]:checked');
    const schoolIds = Array.from(checkboxes).map(cb => cb.value);
    
    if (schoolIds.length < 2) {
        alert('Please select at least 2 schools to compare');
        return;
    }
    
    // Fetch comparison data
    const params = new URLSearchParams({
        school_year: '{{ school_year }}',
        quarter: '{{ selected_quarter }}',
        kpi_metric: '{{ selected_kpi }}',
        comparison: 'true',
        school_ids: schoolIds.join(',')
    });
    
    fetch(`/dashboards/smme-kpi-comparison/?${params}`)
        .then(response => response.json())
        .then(data => {
            renderComparisonChart(data);
        });
});

function renderComparisonChart(data) {
    // Create grouped bar chart
    const datasets = data.schools.map((school, index) => {
        const colors = [
            '#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6',
            '#ec4899', '#06b6d4', '#14b8a6'
        ];
        
        return {
            label: school.name,
            data: school.kpi_values,
            backgroundColor: colors[index % colors.length],
            borderColor: colors[index % colors.length],
            borderWidth: 2
        };
    });
    
    myChart.data = {
        labels: data.quarters,  // ['Q1', 'Q2', 'Q3', 'Q4']
        datasets: datasets
    };
    
    myChart.options.plugins.title.text = `School Comparison: ${data.kpi_name}`;
    myChart.update();
}
```

### **Task 4.3: Create Comparison API Endpoint** (30 min)

**File**: `dashboards/views.py` - Add new view

```python
@login_required
def smme_kpi_comparison(request):
    """API endpoint for school comparison data"""
    school_year = request.GET.get('school_year')
    quarter = request.GET.get('quarter')
    kpi_metric = request.GET.get('kpi_metric')
    school_ids = request.GET.get('school_ids', '').split(',')
    
    # Get periods
    if quarter == 'all':
        periods = Period.objects.filter(
            school_year_start=int(school_year),
            quarter_tag__in=['Q1', 'Q2', 'Q3', 'Q4']
        ).order_by('display_order')
    else:
        periods = Period.objects.filter(
            school_year_start=int(school_year),
            quarter_tag__iexact=quarter
        )
    
    # Get schools
    schools = School.objects.filter(id__in=school_ids)
    
    # Calculate KPIs for each school
    comparison_data = []
    for school in schools:
        school_kpis = []
        for period in periods:
            submissions = Form1SLPLLCEntry.objects.filter(
                school=school,
                period=period
            )
            
            if submissions.exists():
                kpis = calculate_all_kpis(submissions)
                kpi_value = kpis.get(kpi_metric, 0)
                school_kpis.append(kpi_value)
            else:
                school_kpis.append(0)
        
        comparison_data.append({
            'name': school.name,
            'kpi_values': school_kpis
        })
    
    return JsonResponse({
        'schools': comparison_data,
        'quarters': [p.quarter_tag for p in periods],
        'kpi_name': get_kpi_display_name(kpi_metric)
    })
```

**File**: `dashboards/urls.py` - Add URL

```python
urlpatterns = [
    # ... existing urls ...
    path('smme-kpi-comparison/', views.smme_kpi_comparison, name='smme_kpi_comparison'),
]
```

---

## **PHASE 5: Detailed Statistics Table** 🆕 NEW

**Priority**: HIGH  
**Estimated Time**: 3 hours

### **Task 5.1: Create Scrollable KPI Table** (2 hours)

**File**: `templates/dashboards/smme_kpi_dashboard.html` - Add new section

```html
<!-- 🆕 NEW: Detailed Statistics Table -->
<section class="card" style="margin-top: 2rem;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
        <h3 style="font-size: 1.25rem; font-weight: 600;">
            Detailed Statistics - All Schools, All KPIs
        </h3>
        
        <!-- Export Button -->
        <a href="{% url 'export_smme_kpis_excel' %}?school_year={{ school_year }}&quarter={{ selected_quarter }}" 
           class="btn btn--primary">
            📥 Export to Excel
        </a>
    </div>
    
    <!-- Search/Filter within table -->
    <div style="margin-bottom: 1rem;">
        <input type="text" 
               id="tableSearch" 
               class="form-input" 
               placeholder="🔍 Search schools..."
               style="max-width: 400px;">
    </div>
    
    <!-- Scrollable Table Container -->
    <div style="overflow-x: auto; max-height: 600px; border: 1px solid #e5e7eb; border-radius: 8px;">
        <table class="table" id="kpiTable" style="min-width: 1400px;">
            <thead style="position: sticky; top: 0; background: #f9fafb; z-index: 10;">
                <tr>
                    <th style="cursor: pointer;" onclick="sortTable(0)">
                        School Name ↕
                    </th>
                    <th style="cursor: pointer;" onclick="sortTable(1)">
                        DNME % ↕
                        <br><small style="font-weight: normal;">(Lower is better)</small>
                    </th>
                    <th style="cursor: pointer;" onclick="sortTable(2)">
                        Access % ↕
                    </th>
                    <th style="cursor: pointer;" onclick="sortTable(3)">
                        Quality % ↕
                    </th>
                    <th style="cursor: pointer;" onclick="sortTable(4)">
                        Equity % ↕
                    </th>
                    <th style="cursor: pointer;" onclick="sortTable(5)">
                        Governance % ↕
                    </th>
                    <th style="cursor: pointer;" onclick="sortTable(6)">
                        Management % ↕
                    </th>
                    <th style="cursor: pointer;" onclick="sortTable(7)">
                        Leadership % ↕
                    </th>
                    <th style="cursor: pointer;" onclick="sortTable(8)">
                        Overall Score ↕
                    </th>
                </tr>
            </thead>
            <tbody>
                {% for school_data in detailed_kpi_table %}
                <tr>
                    <td style="font-weight: 600; white-space: nowrap;">
                        {{ school_data.school_name }}
                    </td>
                    
                    <!-- DNME % - Red if high -->
                    <td style="text-align: center; {% if school_data.dnme > 20 %}background-color: #fee2e2; color: #991b1b;{% elif school_data.dnme > 10 %}background-color: #fef3c7; color: #92400e;{% else %}background-color: #d1fae5; color: #065f46;{% endif %} font-weight: 600;">
                        {{ school_data.dnme|floatformat:1 }}%
                    </td>
                    
                    <!-- Access % - Green if high -->
                    <td style="text-align: center; {% if school_data.access < 70 %}background-color: #fee2e2; color: #991b1b;{% elif school_data.access < 85 %}background-color: #fef3c7; color: #92400e;{% else %}background-color: #d1fae5; color: #065f46;{% endif %} font-weight: 600;">
                        {{ school_data.access|floatformat:1 }}%
                    </td>
                    
                    <!-- Quality % -->
                    <td style="text-align: center; {% if school_data.quality < 70 %}background-color: #fee2e2; color: #991b1b;{% elif school_data.quality < 85 %}background-color: #fef3c7; color: #92400e;{% else %}background-color: #d1fae5; color: #065f46;{% endif %} font-weight: 600;">
                        {{ school_data.quality|floatformat:1 }}%
                    </td>
                    
                    <!-- Equity % -->
                    <td style="text-align: center; {% if school_data.equity < 70 %}background-color: #fee2e2; color: #991b1b;{% elif school_data.equity < 85 %}background-color: #fef3c7; color: #92400e;{% else %}background-color: #d1fae5; color: #065f46;{% endif %} font-weight: 600;">
                        {{ school_data.equity|floatformat:1 }}%
                    </td>
                    
                    <!-- Governance % -->
                    <td style="text-align: center; {% if school_data.governance < 70 %}background-color: #fee2e2; color: #991b1b;{% elif school_data.governance < 85 %}background-color: #fef3c7; color: #92400e;{% else %}background-color: #d1fae5; color: #065f46;{% endif %} font-weight: 600;">
                        {{ school_data.governance|floatformat:1 }}%
                    </td>
                    
                    <!-- Management % -->
                    <td style="text-align: center; {% if school_data.management < 70 %}background-color: #fee2e2; color: #991b1b;{% elif school_data.management < 85 %}background-color: #fef3c7; color: #92400e;{% else %}background-color: #d1fae5; color: #065f46;{% endif %} font-weight: 600;">
                        {{ school_data.management|floatformat:1 }}%
                    </td>
                    
                    <!-- Leadership % -->
                    <td style="text-align: center; {% if school_data.leadership < 70 %}background-color: #fee2e2; color: #991b1b;{% elif school_data.leadership < 85 %}background-color: #fef3c7; color: #92400e;{% else %}background-color: #d1fae5; color: #065f46;{% endif %} font-weight: 600;">
                        {{ school_data.leadership|floatformat:1 }}%
                    </td>
                    
                    <!-- Overall Score -->
                    <td style="text-align: center; {% if school_data.overall < 70 %}background-color: #fee2e2; color: #991b1b;{% elif school_data.overall < 85 %}background-color: #fef3c7; color: #92400e;{% else %}background-color: #d1fae5; color: #065f46;{% endif %} font-weight: 600; font-size: 1.1rem;">
                        {{ school_data.overall|floatformat:1 }}%
                    </td>
                </tr>
                {% empty %}
                <tr>
                    <td colspan="9" style="text-align: center; padding: 2rem; color: #6b7280;">
                        No data available for selected filters
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    
    <!-- Table Legend -->
    <div style="margin-top: 1rem; display: flex; gap: 1rem; font-size: 0.875rem;">
        <div style="display: flex; align-items: center; gap: 0.5rem;">
            <div style="width: 20px; height: 20px; background-color: #d1fae5; border: 1px solid #065f46;"></div>
            <span>Good (≥85%)</span>
        </div>
        <div style="display: flex; align-items: center; gap: 0.5rem;">
            <div style="width: 20px; height: 20px; background-color: #fef3c7; border: 1px solid #92400e;"></div>
            <span>Fair (70-84%)</span>
        </div>
        <div style="display: flex; align-items: center; gap: 0.5rem;">
            <div style="width: 20px; height: 20px; background-color: #fee2e2; border: 1px solid #991b1b;"></div>
            <span>Needs Improvement (<70%)</span>
        </div>
    </div>
</section>

<script>
// Table search functionality
document.getElementById('tableSearch').addEventListener('keyup', function() {
    const searchValue = this.value.toLowerCase();
    const table = document.getElementById('kpiTable');
    const rows = table.getElementsByTagName('tbody')[0].getElementsByTagName('tr');
    
    for (let row of rows) {
        const schoolName = row.cells[0].textContent.toLowerCase();
        if (schoolName.includes(searchValue)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    }
});

// Table sorting functionality
let sortDirection = {};

function sortTable(columnIndex) {
    const table = document.getElementById('kpiTable');
    const tbody = table.getElementsByTagName('tbody')[0];
    const rows = Array.from(tbody.getElementsByTagName('tr'));
    
    // Toggle sort direction
    if (!sortDirection[columnIndex]) {
        sortDirection[columnIndex] = 'asc';
    } else {
        sortDirection[columnIndex] = sortDirection[columnIndex] === 'asc' ? 'desc' : 'asc';
    }
    
    rows.sort((a, b) => {
        let aValue, bValue;
        
        if (columnIndex === 0) {
            // School name - text sort
            aValue = a.cells[columnIndex].textContent.trim();
            bValue = b.cells[columnIndex].textContent.trim();
        } else {
            // KPI values - numeric sort
            aValue = parseFloat(a.cells[columnIndex].textContent.replace('%', ''));
            bValue = parseFloat(b.cells[columnIndex].textContent.replace('%', ''));
        }
        
        if (sortDirection[columnIndex] === 'asc') {
            return aValue > bValue ? 1 : -1;
        } else {
            return aValue < bValue ? 1 : -1;
        }
    });
    
    // Re-append sorted rows
    rows.forEach(row => tbody.appendChild(row));
}
</script>
```

### **Task 5.2: Generate Table Data in View** (1 hour)

**File**: `dashboards/views.py` - Update view

```python
def smme_kpi_dashboard(request):
    # ... existing filtering code ...
    
    # 🆕 Generate detailed KPI table data
    detailed_kpi_table = []
    
    schools = School.objects.all().order_by('name')
    
    for school in schools:
        # Get submissions for this school based on filters
        submissions_query = Form1SLPLLCEntry.objects.filter(school=school)
        
        if quarter_filter == 'all':
            # All quarters for school year
            submissions_query = submissions_query.filter(
                period__school_year_start=int(school_year),
                period__quarter_tag__in=['Q1', 'Q2', 'Q3', 'Q4']
            )
        else:
            # Specific quarter
            submissions_query = submissions_query.filter(
                period__school_year_start=int(school_year),
                period__quarter_tag__iexact=quarter_filter
            )
        
        if submissions_query.exists():
            # Calculate all KPIs for this school
            kpis = calculate_all_kpis(submissions_query)
            
            detailed_kpi_table.append({
                'school_name': school.name,
                'dnme': kpis['dnme_percentage'],
                'access': kpis['access_percentage'],
                'quality': kpis['quality_percentage'],
                'equity': kpis['equity_percentage'],
                'governance': kpis['governance_percentage'],
                'management': kpis['management_percentage'],
                'leadership': kpis['leadership_percentage'],
                'overall': kpis['overall_score']
            })
        else:
            # No data for this school
            detailed_kpi_table.append({
                'school_name': school.name,
                'dnme': 0,
                'access': 0,
                'quality': 0,
                'equity': 0,
                'governance': 0,
                'management': 0,
                'leadership': 0,
                'overall': 0
            })
    
    context = {
        # ... existing context ...
        'detailed_kpi_table': detailed_kpi_table,  # 🆕 NEW
    }
    
    return render(request, 'dashboards/smme_kpi_dashboard.html', context)
```

---

## **PHASE 6: Excel Export Feature** 🆕 NEW

**Priority**: MEDIUM  
**Estimated Time**: 1.5 hours

### **Task 6.1: Create Excel Export View** (1 hour)

**File**: `dashboards/views.py` - Add export view

```python
from django.http import HttpResponse
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

@login_required
def export_smme_kpis_excel(request):
    """Export SMME KPIs to Excel"""
    school_year = request.GET.get('school_year')
    quarter = request.GET.get('quarter', 'all')
    
    # Create workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"SMME KPIs SY {school_year}"
    
    # Header row
    headers = [
        'School Name',
        'DNME %',
        'Access %',
        'Quality %',
        'Equity %',
        'Governance %',
        'Management %',
        'Leadership %',
        'Overall Score'
    ]
    
    # Style header
    header_fill = PatternFill(start_color='3b82f6', end_color='3b82f6', fill_type='solid')
    header_font = Font(bold=True, color='FFFFFF')
    
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center')
    
    # Get data
    schools = School.objects.all().order_by('name')
    row_num = 2
    
    for school in schools:
        submissions_query = Form1SLPLLCEntry.objects.filter(school=school)
        
        if quarter == 'all':
            submissions_query = submissions_query.filter(
                period__school_year_start=int(school_year),
                period__quarter_tag__in=['Q1', 'Q2', 'Q3', 'Q4']
            )
        else:
            submissions_query = submissions_query.filter(
                period__school_year_start=int(school_year),
                period__quarter_tag__iexact=quarter
            )
        
        if submissions_query.exists():
            kpis = calculate_all_kpis(submissions_query)
            
            # Write data
            ws.cell(row=row_num, column=1).value = school.name
            ws.cell(row=row_num, column=2).value = kpis['dnme_percentage']
            ws.cell(row=row_num, column=3).value = kpis['access_percentage']
            ws.cell(row=row_num, column=4).value = kpis['quality_percentage']
            ws.cell(row=row_num, column=5).value = kpis['equity_percentage']
            ws.cell(row=row_num, column=6).value = kpis['governance_percentage']
            ws.cell(row=row_num, column=7).value = kpis['management_percentage']
            ws.cell(row=row_num, column=8).value = kpis['leadership_percentage']
            ws.cell(row=row_num, column=9).value = kpis['overall_score']
            
            # Color-code cells
            for col in range(2, 10):
                cell = ws.cell(row=row_num, column=col)
                value = cell.value
                
                if col == 2:  # DNME - lower is better
                    if value > 20:
                        cell.fill = PatternFill(start_color='fee2e2', end_color='fee2e2', fill_type='solid')
                    elif value > 10:
                        cell.fill = PatternFill(start_color='fef3c7', end_color='fef3c7', fill_type='solid')
                    else:
                        cell.fill = PatternFill(start_color='d1fae5', end_color='d1fae5', fill_type='solid')
                else:  # Others - higher is better
                    if value < 70:
                        cell.fill = PatternFill(start_color='fee2e2', end_color='fee2e2', fill_type='solid')
                    elif value < 85:
                        cell.fill = PatternFill(start_color='fef3c7', end_color='fef3c7', fill_type='solid')
                    else:
                        cell.fill = PatternFill(start_color='d1fae5', end_color='d1fae5', fill_type='solid')
                
                cell.alignment = Alignment(horizontal='center')
            
            row_num += 1
    
    # Adjust column widths
    for col in range(1, 10):
        ws.column_dimensions[get_column_letter(col)].width = 18
    
    # Prepare response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f'SMME_KPIs_SY{school_year}_{"All_Quarters" if quarter == "all" else quarter}.xlsx'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    wb.save(response)
    return response
```

### **Task 6.2: Add URL and Install openpyxl** (30 min)

**File**: `dashboards/urls.py`
```python
urlpatterns = [
    # ... existing urls ...
    path('export-smme-kpis-excel/', views.export_smme_kpis_excel, name='export_smme_kpis_excel'),
]
```

**Install openpyxl**:
```bash
pip install openpyxl
```

---

## 📊 UPDATED SUMMARY

### **New Features Added**:

1. ✅ **Quarter Filter with "All Quarters"**
   - Dropdown: All Quarters, Q1, Q2, Q3, Q4
   - Show aggregate or specific quarter data

2. ✅ **School Filter**
   - Dropdown: All Schools, [individual schools]
   - Filter charts and table by specific school

3. ✅ **School Comparison Mode**
   - Toggle button to enable comparison
   - Select multiple schools
   - Grouped bar chart showing side-by-side comparison

4. ✅ **Detailed Statistics Table**
   - All schools in rows
   - All KPIs in columns
   - Scrollable (600px max height)
   - Sortable by any column
   - Color-coded cells (red/yellow/green)
   - Search within table

5. ✅ **Excel Export**
   - Export table data to Excel
   - Includes all KPIs for all schools
   - Color-coded cells in Excel
   - Dynamic filename based on filters

---

## 🎯 PRIORITY ORDER - UPDATED

### **IMMEDIATE**:
1. ✅ Fix template errors (navbar integration)
2. 🔄 Phase 3: Add "All Quarters" and School filter (2 hours)

### **HIGH PRIORITY**:
3. 🔄 Phase 5: Detailed Statistics Table (3 hours)
4. 🔄 Phase 4: School Comparison Feature (2 hours)

### **MEDIUM PRIORITY**:
5. 🔄 Phase 6: Excel Export (1.5 hours)

---

## ⏱️ TOTAL ESTIMATED TIME

- Phase 3 (Filtering): 2 hours
- Phase 4 (Comparison): 2 hours
- Phase 5 (Table): 3 hours
- Phase 6 (Export): 1.5 hours

**Total: 8.5 hours**

---

## 📝 FILES TO MODIFY

1. **dashboards/views.py**
   - Update `smme_kpi_dashboard` with new filtering
   - Add `smme_kpi_comparison` API endpoint
   - Add `export_smme_kpis_excel` export view
   - Add helper functions for aggregation

2. **templates/dashboards/smme_kpi_dashboard.html**
   - Update filters section (quarter + school dropdowns)
   - Add comparison mode UI
   - Add detailed statistics table
   - Add JavaScript for sorting, search, comparison

3. **dashboards/urls.py**
   - Add comparison endpoint URL
   - Add export endpoint URL

4. **dashboards/kpi_calculators.py** (already exists)
   - May need aggregation helper functions

5. **requirements.txt** (or similar)
   - Add `openpyxl` for Excel export

---

## ❓ READY TO PROCEED?

All requirements are now documented in this plan. Ready to implement:

**Phase 3 First**: Quarter + School filtering (2 hours)

Shall I start implementing Phase 3?
