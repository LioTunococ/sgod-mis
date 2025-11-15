# API Documentation

This document describes the AJAX API endpoints available in the SGOD MIS system.

## Overview

The dashboard uses AJAX endpoints to provide real-time filtering and data updates without requiring full page reloads. All endpoints require authentication and return JSON responses.

---

## Authentication

All API endpoints require the user to be logged in. If not authenticated, the request will be redirected to the login page.

**Authentication Method**: Django session-based authentication via `@login_required` decorator

---

## Endpoints

### 1. SMME KPI Dashboard Data

**URL**: `/dashboards/smme-kpi/data/`  
**Method**: `GET`  
**Authentication**: Required (Reviewer/Admin access)  
**Description**: Returns KPI data for the SMME (National) dashboard with filtering options

#### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `school_year` | string | No | Latest year | School year start (e.g., "2025") |
| `quarter` | string | No | "all" | Quarter filter: "all", "Q1", "Q2", "Q3", "Q4" |
| `school` | string | No | "all" | School filter: "all" or school ID |
| `kpi_metric` | string | No | "dnme" | KPI to display: "dnme", "access", "quality", "equity", "governance", "management", "leadership", "slp", "crla", "philiri", "rma" |

#### Response Format

```json
{
  "summary_cards": [
    {
      "title": "Total Schools",
      "value": "45",
      "icon": "🏫",
      "status_class": ""
    },
    {
      "title": "DNME %",
      "value": "12.5%",
      "icon": "📊",
      "status_class": "warning"
    }
  ],
  "chart_labels": ["Q1", "Q2", "Q3", "Q4"],
  "chart_values": [75.5, 78.2, 82.1, 85.0],
  "school_list": [
    {
      "id": 1,
      "name": "School A",
      "kpi_value": 85.0,
      "status": "Excellent"
    }
  ],
  "filters": {
    "school_years": ["2025", "2024", "2023"],
    "quarters": [
      {"value": "all", "label": "All Quarters"},
      {"value": "Q1", "label": "Q1"},
      {"value": "Q2", "label": "Q2"},
      {"value": "Q3", "label": "Q3"},
      {"value": "Q4", "label": "Q4"}
    ],
    "schools": [
      {"value": "all", "label": "All Schools"},
      {"value": "1", "label": "School A"}
    ],
    "kpi_metrics": [
      {"value": "dnme", "label": "DNME Percentage"}
    ]
  },
  "selected_filters": {
    "school_year": "2025",
    "quarter": "all",
    "school": "all",
    "kpi_metric": "dnme"
  }
}
```

#### Status Codes

- `200 OK` - Success
- `403 Forbidden` - User does not have reviewer/admin access
- `400 Bad Request` - Invalid parameters

#### Example Usage

```javascript
// JavaScript fetch example
fetch('/dashboards/smme-kpi/data/?school_year=2025&quarter=Q1&kpi_metric=dnme')
  .then(response => response.json())
  .then(data => {
    console.log('Summary Cards:', data.summary_cards);
    console.log('Chart Data:', data.chart_labels, data.chart_values);
  });
```

---

### 2. SMME KPI School Comparison

**URL**: `/dashboards/smme-kpi/comparison/`  
**Method**: `GET`  
**Authentication**: Required (Reviewer/Admin access)  
**Description**: Returns comparison data for multiple schools across periods

#### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `school_year` | string | Yes | - | School year start (e.g., "2025") |
| `quarter` | string | No | "all" | Quarter filter: "all", "Q1", "Q2", "Q3", "Q4" |
| `kpi_metric` | string | No | "dnme" | KPI to compare |
| `school_ids` | string | Yes | - | Comma-separated list of school IDs (e.g., "1,2,3") |

#### Response Format

```json
{
  "schools": [
    {
      "name": "School A",
      "kpi_values": [75.5, 78.2, 82.1, 85.0]
    },
    {
      "name": "School B",
      "kpi_values": [70.0, 72.5, 75.0, 78.0]
    }
  ],
  "quarters": ["Q1", "Q2", "Q3", "Q4"],
  "kpi_name": "DNME Percentage"
}
```

#### Status Codes

- `200 OK` - Success
- `400 Bad Request` - Missing or invalid parameters
- `403 Forbidden` - User does not have reviewer/admin access
- `404 Not Found` - No periods or schools found for the given parameters

#### Error Response Format

```json
{
  "error": "Missing parameters"
}
```

#### Example Usage

```javascript
// Compare three schools for Q1 2025
fetch('/dashboards/smme-kpi/comparison/?school_year=2025&quarter=Q1&school_ids=1,2,3&kpi_metric=access')
  .then(response => response.json())
  .then(data => {
    data.schools.forEach(school => {
      console.log(`${school.name}: ${school.kpi_values.join(', ')}`);
    });
  });
```

---

## KPI Metrics Available

The following KPI metrics can be requested via the `kpi_metric` parameter:

### Core Indicators
- **`dnme`** - DNME (Did Not Meet Expectations) Percentage
- **`access`** - Access Implementation Area Percentage
- **`quality`** - Quality Implementation Area Percentage
- **`equity`** - Equity Implementation Area Percentage
- **`governance`** - Governance Implementation Area Percentage
- **`management`** - Management Implementation Area Percentage
- **`leadership`** - Leadership Implementation Area Percentage

### Supplementary Indicators
- **`slp`** - School Learning Plan indicators
  - `slp_complete` - Schools with complete SLP
  - `slp_needs_improvement` - Schools needing SLP improvement
  - `slp_no_plan` - Schools without SLP
- **`crla`** - Curriculum Reform Literacy Assessment
  - `crla_independent` - Students reading independently
  - `crla_instructional` - Students at instructional level
  - `crla_frustration` - Students at frustration level
- **`philiri`** - PHILIRI Assessment
  - `philiri_independent` - Students reading independently
  - `philiri_instructional` - Students at instructional level
  - `philiri_frustration` - Students at frustration level
- **`rma`** - Reading Materials Adequacy indicators

---

## Period Management

### Period Model

Periods are defined by:
- **`school_year_start`** (integer) - Starting year of school year (e.g., 2025 for SY 2025-2026)
- **`quarter_tag`** (string) - Quarter identifier: "Q1", "Q2", "Q3", "Q4"
- **`label`** (string, auto-generated) - Display label (e.g., "Q1 - SY 2025-2026")
- **`display_order`** (integer, auto-generated) - Sort order

### Period Filtering

When filtering by quarter:
- **`quarter=all`** - Returns data aggregated across all quarters (Q1-Q4) for the school year
- **`quarter=Q1`** - Returns data only for Q1
- **`quarter=Q2`** - Returns data only for Q2
- **`quarter=Q3`** - Returns data only for Q3
- **`quarter=Q4`** - Returns data only for Q4

---

## Error Handling

All endpoints follow a consistent error handling pattern:

### Common Error Responses

```json
// Missing required parameters
{
  "error": "Missing parameters"
}

// Invalid data type
{
  "error": "Invalid school year"
}

// No data found
{
  "error": "No periods found"
}

// Permission denied
{
  "error": "Access denied"
}
```

### HTTP Status Codes

- `200` - Success
- `400` - Bad Request (invalid parameters)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found (no data matching criteria)
- `500` - Internal Server Error

---

## AJAX Integration Example

### Complete Dashboard Filter Implementation

```javascript
// dashboard_filters.js

// Update dashboard when filters change
function updateDashboard() {
    const schoolYear = document.getElementById('school_year').value;
    const quarter = document.getElementById('quarter').value;
    const school = document.getElementById('school').value;
    const kpiMetric = document.getElementById('kpi_metric').value;
    
    // Build query string
    const params = new URLSearchParams({
        school_year: schoolYear,
        quarter: quarter,
        school: school,
        kpi_metric: kpiMetric
    });
    
    // Show loading state
    const container = document.getElementById('dashboard-content');
    container.classList.add('loading');
    
    // Fetch new data
    fetch(`/dashboards/smme-kpi/data/?${params}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Update summary cards
            updateSummaryCards(data.summary_cards);
            
            // Update chart
            updateChart(data.chart_labels, data.chart_values);
            
            // Update school list
            updateSchoolList(data.school_list);
            
            // Remove loading state
            container.classList.remove('loading');
        })
        .catch(error => {
            console.error('Error fetching dashboard data:', error);
            container.classList.remove('loading');
            showError('Failed to load dashboard data. Please try again.');
        });
}

// Update summary cards
function updateSummaryCards(cards) {
    const container = document.getElementById('summary-cards');
    container.innerHTML = cards.map(card => `
        <div class="card ${card.status_class}">
            <div class="card-icon">${card.icon}</div>
            <div class="card-title">${card.title}</div>
            <div class="card-value">${card.value}</div>
        </div>
    `).join('');
}

// Update chart using Chart.js
function updateChart(labels, values) {
    if (window.dashboardChart) {
        window.dashboardChart.data.labels = labels;
        window.dashboardChart.data.datasets[0].data = values;
        window.dashboardChart.update('active');
    }
}

// Update school list table
function updateSchoolList(schools) {
    const tbody = document.getElementById('school-list-body');
    tbody.innerHTML = schools.map(school => `
        <tr>
            <td>${school.name}</td>
            <td>${school.kpi_value}%</td>
            <td><span class="badge ${school.status.toLowerCase()}">${school.status}</span></td>
        </tr>
    `).join('');
}

// Attach event listeners to all filters
document.addEventListener('DOMContentLoaded', function() {
    const filters = ['school_year', 'quarter', 'school', 'kpi_metric'];
    filters.forEach(filterId => {
        const element = document.getElementById(filterId);
        if (element) {
            element.addEventListener('change', updateDashboard);
        }
    });
});
```

---

## Rate Limiting & Performance

### Best Practices

1. **Debouncing**: When implementing filters, use debouncing to avoid excessive API calls
2. **Caching**: Cache filter options (school years, schools list) to reduce repeated requests
3. **Loading States**: Always show loading indicators during API calls
4. **Error Handling**: Implement proper error handling and user feedback

### Performance Considerations

- Dashboard data endpoint is optimized with `select_related` and `prefetch_related`
- KPI calculations are cached per period to avoid redundant computation
- Queries are filtered at the database level to minimize data transfer

---

## Security

### Access Control

All endpoints implement role-based access control:
- **SMME Dashboard**: Requires reviewer access (SGOD Admin or PSDS)
- **District Dashboard**: Requires district-level access
- **School Dashboard**: School heads can only see their own school data

### CSRF Protection

All POST requests (if any) must include CSRF tokens as per Django's CSRF protection requirements.

### SQL Injection Prevention

All query parameters are sanitized and validated before being used in database queries.

---

## Testing

### Manual Testing

Use browser developer tools or curl to test endpoints:

```bash
# Test SMME dashboard data
curl -X GET "http://localhost:8000/dashboards/smme-kpi/data/?school_year=2025&quarter=Q1" \
  -H "Cookie: sessionid=YOUR_SESSION_ID"

# Test school comparison
curl -X GET "http://localhost:8000/dashboards/smme-kpi/comparison/?school_year=2025&school_ids=1,2,3" \
  -H "Cookie: sessionid=YOUR_SESSION_ID"
```

### Automated Testing

Unit tests are available in `tests/test_dashboards.py`:

```python
def test_smme_kpi_dashboard_data(client, admin_user):
    client.force_login(admin_user)
    response = client.get('/dashboards/smme-kpi/data/?school_year=2025')
    assert response.status_code == 200
    data = response.json()
    assert 'summary_cards' in data
    assert 'chart_labels' in data
```

---

## Changelog

### Version 1.0 (Current)
- Initial API documentation
- SMME KPI Dashboard data endpoint
- School comparison endpoint
- Period-based filtering system
- Support for all KPI metrics (DNME, Access, Quality, SLP, CRLA, PHILIRI, RMA)

---

## Support

For issues or questions regarding the API:
1. Check the error message in the JSON response
2. Verify authentication and permissions
3. Ensure all required parameters are provided
4. Review the Django debug toolbar for SQL query performance

---

**Last Updated**: Task 9 Implementation (2025)  
**Maintainer**: SGOD Development Team
