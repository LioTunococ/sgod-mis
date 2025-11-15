# SGOD MIS

A Django-based Management Information System for SGOD (Schools Governance and Operations Division).

## Overview

SGOD MIS is a comprehensive web application designed to manage school data submissions, monitor Key Performance Indicators (KPIs), and provide role-based dashboards for educational administrators at various levels (National, Regional, Division, District, School).

## Key Features

- 📊 **Multi-Level Dashboards** - Tailored views for SMME (National), Regional, Division, District, and School administrators
- 📝 **Form Management** - Flexible form templates with period-based submissions
- 📈 **KPI Tracking** - Automated calculation of educational indicators (DNME, Access, Quality, SLP, CRLA, PHILIRI, RMA)
- 🔐 **Role-Based Access Control** - Hierarchical permissions based on organizational scope
- 🎯 **Period Management** - School year and quarter-based data organization
- 🔄 **Real-time Updates** - AJAX-powered filters for smooth user experience
- 📤 **Data Export** - Excel export capabilities for reporting

## Phase 1 Scope
- School report submissions per section
- Section Admin review & noting
- "Who Didn't Submit" dashboard
- Multi-unit school support
- KPI dashboard with comprehensive indicators

## Setup (Development)

### Prerequisites
- Python 3.8+
- pip (Python package manager)
- SQLite (included with Python)

### Installation

1. Create virtual environment:
   ```bash
   py -m venv .venv
   .\.venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run migrations:
   ```bash
   python manage.py migrate
   ```

4. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

5. Start the development server:
   ```bash
   python manage.py runserver
   ```

6. Visit http://localhost:8000

## Demo Data Seeds

Run the seed script to load demo districts, schools, and sample accounts:

```bash
python manage.py shell -c "from scripts.seed_data import run; run()"
```

The script prints ready-to-use credentials such as `sgod.admin@example.com` / `demo12345` so you can sign in immediately after starting `runserver`.

After seeding you can run the smoke suite with `pytest`, which exercises the scoped dashboards, exports, and locking logic.

## Documentation

### User Guides
- **[User Guide](docs/USER_GUIDE.md)** - Complete guide for administrators and users
  - Dashboard navigation and usage
  - Creating school years and periods
  - Managing forms and submissions
  - Understanding KPI indicators

### Technical Documentation
- **[KPI Calculations](docs/KPI_CALCULATIONS.md)** - Detailed explanation of all KPI calculation methods
- **[Period Management](docs/PERIOD_MANAGEMENT_COMPLETE.md)** - School year and quarter system
- **[API Documentation](docs/API_DOCUMENTATION.md)** - AJAX endpoints and filter APIs
- **[Access Matrix](docs/access-matrix.md)** - Role-based permissions and scoping

### Implementation Guides
- **[Flexible Period System](docs/FLEXIBLE_PERIOD_IMPLEMENTATION_COMPLETE.md)** - Period management implementation
- **[SMME Dashboard](docs/SMME_DASHBOARD_COMPLETE.md)** - National-level dashboard features
- **[School Multi-Unit Support](docs/SCHOOL_MULTI_UNIT_DASHBOARD_IMPLEMENTATION.md)** - Multi-unit school handling
- **[Directory Tools](docs/DIRECTORY_TOOLS_COMPLETE.md)** - School and organization management

### Deployment
- **[Deploy Checklist](docs/deploy-checklist.md)** - Production deployment steps
- **[Demo Guide](docs/demo-guide.md)** - Demonstration walkthrough

### Development
- **[Development Log](docs/dev-log.md)** - Project development history
- **[Action Plan](docs/ACTION_PLAN.md)** - Feature roadmap and priorities
- **[Phase B Roadmap](docs/phase-b-roadmap.md)** - Future enhancements

## Project Structure

```
SGOD_Project/
├── accounts/          # User authentication and role management
├── api/              # API endpoints and views
├── common/           # Shared utilities and models
├── dashboards/       # Dashboard views and KPI calculators
├── organizations/    # Schools, districts, divisions hierarchy
├── submissions/      # Form submissions and templates
├── templates/        # HTML templates
├── static/           # CSS, JavaScript, images
├── docs/            # Documentation files
└── manage.py        # Django management script
```

## Testing

Run the test suite:
```bash
pytest
```

Run specific tests:
```bash
pytest tests/test_dashboards.py
pytest -k "test_kpi"
```

## Contributing

1. Follow the existing code style and structure
2. Write tests for new features
3. Update documentation as needed
4. Use meaningful commit messages

## License

Proprietary - SGOD Internal Use Only
