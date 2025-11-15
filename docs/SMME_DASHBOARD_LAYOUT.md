# SMME Admin Dashboard - Layout Design

**Date:** October 17, 2025  
**Design System:** Boring Design (Professional, Clean, Government-style)

---

## Layout Overview

```
┌────────────────────────────────────────────────────────────────────┐
│  [SGOD Logo]  SMME KPI Dashboard            [User Menu ▼] [Logout] │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  FILTERS                                                      │ │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────┐ │ │
│  │  │ School Year│  │  District  │  │  Section   │  │ Apply  │ │ │
│  │  │ 2025-2026 ▼│  │   All ▼    │  │   All ▼    │  │        │ │ │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────┘ │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  QUARTER NAVIGATION                                           │ │
│  │                                                                │ │
│  │  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐ │ │
│  │  │   Q1   │  │   Q2   │  │  ✓Q3   │  │   Q4   │  │  All   │ │ │
│  │  │   125  │  │   134  │  │  142   │  │   108  │  │  509   │ │ │
│  │  │ schools│  │ schools│  │ schools│  │ schools│  │ total  │ │ │
│  │  └────────┘  └────────┘  └────────┘  └────────┘  └────────┘ │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  KEY PERFORMANCE INDICATORS                                   │ │
│  │                                                                │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │ │
│  │  │ Total    │  │Submitted │  │  DNME    │  │ ADM Burn │     │ │
│  │  │ Schools  │  │  Forms   │  │    %     │  │  Rate %  │     │ │
│  │  │          │  │          │  │          │  │          │     │ │
│  │  │   142    │  │   118    │  │   12.4   │  │   68.5   │     │ │
│  │  │          │  │          │  │          │  │          │     │ │
│  │  │ 83% rate │  │ +5% ↑    │  │ -2% ↓    │  │ Target:  │     │ │
│  │  │          │  │          │  │          │  │   70%    │     │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │ │
│  │                                                                │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────────────┐   │ │
│  │  │ PHILIRI  │  │ CRLA     │  │                          │   │ │
│  │  │ Band 10  │  │ Progress │  │     [Export CSV]         │   │ │
│  │  │          │  │          │  │                          │   │ │
│  │  │  2,145   │  │   78%    │  │  Last updated: 2 hrs ago │   │ │
│  │  │          │  │          │  │                          │   │ │
│  │  │learners  │  │ on track │  │                          │   │ │
│  │  └──────────┘  └──────────┘  └──────────────────────────┘   │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  DISTRICT BREAKDOWN TABLE                                     │ │
│  │                                                                │ │
│  │  District     │Schools│Submitted│Rate%│DNME%│Burn%│PHILIRI  │ │
│  │  ────────────────────────────────────────────────────────────│ │
│  │  District 1   │   45  │   38    │ 84% │ 11% │ 72% │  856    │ │
│  │  District 2   │   38  │   32    │ 84% │ 13% │ 65% │  712    │ │
│  │  District 3   │   32  │   28    │ 88% │ 12% │ 70% │  577    │ │
│  │  District 4   │   27  │   20    │ 74% │ 14% │ 66% │  445    │ │
│  │  ────────────────────────────────────────────────────────────│ │
│  │  TOTAL        │  142  │  118    │ 83% │ 12% │ 69% │ 2,590   │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. Header & Navigation
```
┌────────────────────────────────────────────────┐
│  [Logo] SMME KPI Dashboard  [User ▼] [Logout] │
└────────────────────────────────────────────────┘
```
- **Design:** Simple, clean header with logo left, user menu right
- **Style:** White background, subtle bottom border
- **Height:** ~60px
- **Component:** Uses existing `includes/auth_nav.html`

---

### 2. Filter Bar
```
┌──────────────────────────────────────────────┐
│  FILTERS                                     │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────┐ │
│  │School Yr│ │District │ │ Section │ │Apply│
│  │2025-26▼ │ │  All ▼  │ │  All ▼  │ │    │
│  └─────────┘ └─────────┘ └─────────┘ └────┘ │
└──────────────────────────────────────────────┘
```

**Specifications:**
- **Background:** White card with border
- **Layout:** Grid with 4 columns (3 dropdowns + 1 button)
- **Spacing:** 1rem gap between elements
- **Padding:** 1.5rem inside card
- **Border:** 1px solid #e5e7eb
- **Border Radius:** 0.5rem
- **Margin Bottom:** 1.5rem

**CSS Class:** `.filter-bar`

**Behavior:**
- Dropdowns auto-submit on change
- "Apply" button for manual refresh
- Show loading spinner when filtering

---

### 3. Quarter Navigation
```
┌────────────────────────────────────────────────────┐
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  │
│  │   Q1   │  │   Q2   │  │  ✓Q3   │  │   Q4   │  │
│  │   125  │  │   134  │  │  142   │  │   108  │  │
│  │ schools│  │ schools│  │ schools│  │ schools│  │
│  └────────┘  └────────┘  └────────┘  └────────┘  │
│                                                    │
│  ┌────────────────┐                                │
│  │   View All     │                                │
│  │   509 schools  │                                │
│  └────────────────┘                                │
└────────────────────────────────────────────────────┘
```

**Specifications:**
- **Card Dimensions:** ~180px × 120px per quarter
- **Active State:** Blue border (#2563eb) + light blue background
- **Layout:** Grid with 5 columns (Q1-Q4 + All)
- **Typography:**
  - Label: 0.875rem, font-weight: 600, color: #6b7280
  - Value: 2rem, font-weight: 700, color: #2563eb
  - Hint: 0.75rem, color: #6b7280

**CSS Class:** `.quarter-card` (reuse from school dashboard)

**Behavior:**
- Click to filter by quarter
- Active quarter highlighted
- Shows total school count per quarter
- "View All" shows combined data

---

### 4. KPI Summary Cards
```
┌────────────────────────────────────────────────────────┐
│  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │ Total    │  │Submitted │  │  DNME    │            │
│  │ Schools  │  │  Forms   │  │    %     │            │
│  │          │  │          │  │          │            │
│  │   142    │  │   118    │  │   12.4   │            │
│  │          │  │          │  │          │            │
│  │ 83% rate │  │ +5% ↑    │  │ -2% ↓    │            │
│  └──────────┘  └──────────┘  └──────────┘            │
└────────────────────────────────────────────────────────┘
```

**Specifications:**
- **Card Size:** Responsive grid (min 200px, max 1fr)
- **Padding:** 1.25rem
- **Background:** White
- **Border:** 1px solid #e5e7eb
- **Border Radius:** 0.75rem
- **Gap:** 1rem between cards

**Card Structure:**
```
┌─────────────────┐
│ Label (small)   │  ← 0.875rem, #6b7280
│                 │
│    VALUE        │  ← 2rem, bold, #111827
│                 │
│ hint/trend      │  ← 0.75rem, #6b7280
└─────────────────┘
```

**Trend Indicators:**
- ↑ Green (#16a34a) for positive trends
- ↓ Red (#dc2626) for negative trends
- → Gray (#6b7280) for neutral

**CSS Class:** `.stats-card`

**Metrics to Show:**
1. **Total Schools** - Count + completion rate
2. **Submitted Forms** - Count + trend vs last quarter
3. **DNME %** - Percentage + trend
4. **ADM Burn Rate %** - Average + target indicator
5. **PHILIRI Band 10** - Count + context
6. **CRLA Progress** - Percentage + status

---

### 5. Export & Metadata
```
┌──────────────────────────────────────┐
│  [📊 Export CSV]  [📄 Export PDF]   │
│                                      │
│  Last updated: 2 hours ago           │
│  Data range: Q3 2025-2026            │
└──────────────────────────────────────┘
```

**Specifications:**
- **Position:** Right side, above table
- **Buttons:** Outlined style, icon + text
- **Metadata:** Small text, muted color
- **Padding:** 1rem
- **Border:** Top border only (subtle separator)

**CSS Classes:** `.export-bar`, `.btn--outline`

---

### 6. District Breakdown Table
```
┌──────────────────────────────────────────────────────┐
│  District     │Schools│Submitted│Rate%│DNME%│Burn% │
│  ───────────────────────────────────────────────────│
│  District 1   │   45  │   38    │ 84% │ 11% │ 72% │
│  District 2   │   38  │   32    │ 84% │ 13% │ 65% │
│  District 3   │   32  │   28    │ 88% │ 12% │ 70% │
│  ───────────────────────────────────────────────────│
│  TOTAL        │  142  │  118    │ 83% │ 12% │ 69% │
└──────────────────────────────────────────────────────┘
```

**Specifications:**
- **Width:** 100% (responsive)
- **Cell Padding:** 0.75rem
- **Border:** 1px solid #e5e7eb
- **Header Background:** #f9fafb
- **Zebra Striping:** Alternating row colors (#ffffff, #f9fafb)
- **Sticky Header:** On scroll
- **Footer Row:** Bold, slightly darker background

**CSS Class:** `.data-table--kpi`

**Behavior:**
- Horizontal scroll on small screens
- Sortable columns (click header)
- Hover row highlight
- Click row to drill down (future)

**Color Coding:**
- **Green cells** (>80%): Good performance
- **Yellow cells** (60-80%): Warning
- **Red cells** (<60%): Needs attention

---

## Responsive Behavior

### Desktop (>1200px)
- Full layout as shown
- KPI cards: 3 columns
- Table: All columns visible

### Tablet (768px - 1200px)
- Filter bar: 2×2 grid
- Quarter cards: 2×2 grid + "All" below
- KPI cards: 2 columns
- Table: Horizontal scroll

### Mobile (<768px)
- Filter bar: Stack vertically
- Quarter cards: Stack vertically
- KPI cards: 1 column (stack)
- Table: Horizontal scroll + simplified columns

---

## Color Palette

### Primary Colors
- **Primary Blue:** #2563eb (buttons, active states)
- **Success Green:** #16a34a (positive trends)
- **Warning Yellow:** #f59e0b (medium performance)
- **Error Red:** #dc2626 (low performance, negative trends)

### Neutral Colors
- **Text Primary:** #111827
- **Text Secondary:** #6b7280
- **Text Muted:** #9ca3af
- **Border:** #e5e7eb
- **Border Light:** #f3f4f6
- **Background:** #ffffff
- **Background Subtle:** #f9fafb

---

## Typography

### Headings
- **H1 (Page Title):** 2rem (32px), font-weight: 700
- **H2 (Section Title):** 1.5rem (24px), font-weight: 600
- **H3 (Card Title):** 1.125rem (18px), font-weight: 600

### Body Text
- **Base:** 1rem (16px), font-weight: 400
- **Small:** 0.875rem (14px), font-weight: 400
- **Tiny:** 0.75rem (12px), font-weight: 400

### Numbers/Metrics
- **Large Metrics:** 2rem (32px), font-weight: 700
- **Medium Metrics:** 1.5rem (24px), font-weight: 600
- **Small Metrics:** 1rem (16px), font-weight: 500

---

## Spacing System

```
--space-1: 0.25rem;   (4px)
--space-2: 0.5rem;    (8px)
--space-3: 0.75rem;   (12px)
--space-4: 1rem;      (16px)
--space-5: 1.25rem;   (20px)
--space-6: 1.5rem;    (24px)
--space-8: 2rem;      (32px)
--space-10: 2.5rem;   (40px)
```

### Component Spacing
- **Between sections:** 2rem (space-8)
- **Card padding:** 1.25rem (space-5)
- **Card gap:** 1rem (space-4)
- **Input padding:** 0.75rem (space-3)
- **Button padding:** 0.75rem 1.5rem

---

## Loading States

### Filter Loading
```
┌──────────────────────────────┐
│  ⏳ Loading data...           │
│  ▓▓▓░░░░░░░░░░░░ 25%        │
└──────────────────────────────┘
```

### Table Loading (Skeleton)
```
┌──────────────────────────────┐
│  ▓▓▓▓▓  ▓▓▓  ▓▓▓  ▓▓▓       │
│  ▓▓▓▓▓  ▓▓▓  ▓▓▓  ▓▓▓       │
│  ▓▓▓▓▓  ▓▓▓  ▓▓▓  ▓▓▓       │
└──────────────────────────────┘
```

---

## Empty States

### No Data Available
```
┌────────────────────────────────────┐
│                                    │
│         📊                         │
│                                    │
│   No data for selected filters    │
│                                    │
│   Try selecting a different        │
│   quarter or district              │
│                                    │
└────────────────────────────────────┘
```

### No Schools Found
```
┌────────────────────────────────────┐
│                                    │
│         🏫                         │
│                                    │
│   No schools in this district      │
│                                    │
└────────────────────────────────────┘
```

---

## Accessibility

### ARIA Labels
```html
<select aria-label="Select school year">...</select>
<button aria-label="Export data to CSV">Export CSV</button>
<table aria-label="District KPI breakdown">...</table>
```

### Keyboard Navigation
- **Tab:** Navigate through filters
- **Enter:** Submit form / activate button
- **Arrow Keys:** Navigate table cells (future)
- **Escape:** Close modals (if added)

### Screen Reader Friendly
- Proper heading hierarchy (H1 → H2 → H3)
- Table headers with `<th scope="col">`
- Link text descriptive (not "click here")
- Status messages announced

---

## Performance Considerations

### Optimization
- **Lazy load table rows** (if >50 districts)
- **Debounce filter changes** (300ms delay)
- **Cache district data** (client-side, 5 min)
- **Minimize CSS file size** (remove unused styles)

### Loading Times
- **Target:** <1 second page load
- **Acceptable:** <2 seconds with filters
- **Maximum:** 3 seconds (show spinner after)

---

## Implementation Checklist

### HTML Structure
- [ ] Remove inline styles from template
- [ ] Add semantic HTML5 tags (section, nav, article)
- [ ] Add proper heading hierarchy
- [ ] Add ARIA labels
- [ ] Add loading state placeholders

### CSS Components
- [ ] `.filter-bar` component
- [ ] `.quarter-card` (reuse/adapt from school dashboard)
- [ ] `.stats-card` component
- [ ] `.data-table--kpi` component
- [ ] `.export-bar` component
- [ ] Responsive breakpoints
- [ ] Loading state styles
- [ ] Empty state styles

### JavaScript (if needed)
- [ ] Auto-submit on filter change (already exists)
- [ ] Loading spinner on form submit
- [ ] Table sorting functionality
- [ ] Export button handlers

### Backend (minimal changes)
- [ ] Add quarter stats calculation (like school dashboard)
- [ ] Add export CSV endpoint
- [ ] Add last_updated timestamp to context

---

**Next Step:** Review this layout, then implement Phase 1 (CSS cleanup + base components)
