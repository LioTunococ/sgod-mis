# SLP Analysis Accordion - Quick Reference

## Visual Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  Comprehensive SLP Analysis                                     │
│  Complete the analysis for each learning area...                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Grade 1 - Mathematics                      [INCOMPLETE]     ▼  │ ← Collapsed
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Grade 1 - Filipino                         [INCOMPLETE]     ▲  │ ← Expanded
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 1: Proficiency Distribution                              │
│  ┌───────────────┬───────────┬──────────┬──────────┬─────────┐ │
│  │ DNME: 25.0%   │ FS: 30.0% │ S: 25.0% │ VS: 15.0%│ O: 5.0% │ │
│  └───────────────┴───────────┴──────────┴──────────┴─────────┘ │
│                                                                 │
│  Step 2: Top 3 Least Learned Competencies                     │
│  ✓ Already filled in the LLC section above                    │
│                                                                 │
│  Step 3: Hindering Factors Analysis                           │
│  What are the root causes why learners Did Not Meet...        │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ [Textarea - 4 rows]                                       │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  What are the root causes why learners are Fairly...          │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ [Textarea - 4 rows]                                       │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Step 4: Best Practices for High-Performing Learners          │
│  What facilitating factors helped Satisfactory...             │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ [Textarea - 3 rows]                                       │ │
│  └───────────────────────────────────────────────────────────┘ │
│  [2 more textareas for VS and O]                              │
│                                                                 │
│  Step 5: Grade-Level Rankings                                 │
│  ┌─────────────────────┬─────────────────────────────────────┐ │
│  │ Top 5 DNME Grades   │ Top 5 Outstanding Grades           │ │
│  │ [Placeholder]       │ [Placeholder]                      │ │
│  └─────────────────────┴─────────────────────────────────────┘ │
│                                                                 │
│  Step 6: Overall Intervention Strategy                        │
│  At your level, what particular strategy...                   │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ [Textarea - 5 rows]                                       │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Completion: [████████────] 60% complete                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Grade 2 - English                          [COMPLETE]       ▼  │ ← Collapsed
└─────────────────────────────────────────────────────────────────┘
```

## Color Scheme

### Accordion States
- **Collapsed**: Light gray gradient background (#f8fafc → #fff)
- **Expanded**: Light blue background (#e0f2fe)
- **Hover**: Slightly darker gray (#f1f5f9)

### Status Badges
- **INCOMPLETE**: Yellow background (#fef3c7), brown text (#92400e)
- **COMPLETE**: Green background (#d1fae5), dark green text (#065f46)

### Proficiency Badges
- **DNME (Did Not Meet)**: Light red (#fef2f2), red border (#fecaca)
- **FS (Fairly Satisfactory)**: Light yellow (#fef3c7), yellow border (#fde68a)
- **S (Satisfactory)**: Light blue (#dbeafe), blue border (#bfdbfe)
- **VS (Very Satisfactory)**: Light purple (#e0e7ff), purple border (#c7d2fe)
- **O (Outstanding)**: Light green (#dcfce7), green border (#bbf7d0)

### Progress Bar
- **Track**: Light gray (#e5e7eb)
- **Fill**: Blue gradient (#3b82f6 → #2563eb)

## User Interactions

### Accordion
- **Click header** → Expand/collapse
- **Chevron icon** → Rotates 180° when expanded
- **Auto-calculate** → Proficiency percentages update on expand

### Progress Tracking
- **Real-time** → Updates as user types
- **Calculation** → (filled fields / total fields) × 100
- **Status change** → Badge updates at 100% completion

### Data Saving
- **Autosave** → Triggered on Next/Previous navigation
- **Field names** → `slp_analysis_{index}_{field_name}`
- **Database** → Saved to Form1SLPAnalysis table

## Keyboard Navigation

- **Tab** → Navigate through textareas
- **Shift+Tab** → Navigate backwards
- **Enter** → (on header) Expand/collapse accordion
- **Escape** → (future) Close accordion

## Responsive Behavior

### Desktop (> 768px)
- Rankings: 2-column grid
- Proficiency badges: Multi-column grid (auto-fit)
- Full accordion width

### Mobile (≤ 768px)
- Rankings: Stacks to 1 column
- Proficiency badges: Stacks vertically
- Accordion maintains full width
- Touch-friendly header size

## Technical Implementation

### HTML Structure
```html
<div class="slp-analysis-container">
  <div class="analysis-accordion" data-form-index="0">
    <div class="analysis-accordion-header">
      <span class="accordion-title">...</span>
      <span class="accordion-status">
        <span class="status-badge incomplete">Incomplete</span>
        <span class="accordion-icon">▼</span>
      </span>
    </div>
    <div class="analysis-accordion-content" style="display: none;">
      <!-- 6 analysis steps -->
    </div>
  </div>
</div>
```

### JavaScript Hooks
- `data-form-index` → Links accordion to SLP row
- `data-dnme-pct`, `data-fs-pct`, etc. → Proficiency display targets
- `data-progress` → Progress bar fill element
- `data-progress-text` → Progress text element
- `.analysis-textarea` → All monitored for completion tracking

### Django Template Tags
- `{{ forloop.counter0 }}` → 0-based index for JavaScript
- `{{ form.instance.analysis.dnme_factors }}` → Pre-populate fields
- `{{ form.instance.get_subject_display }}` → Subject label
- `|default:""` → Handle missing analysis records

## Data Flow

### Page Load
1. Django renders accordions (one per SLP row)
2. Template pre-fills textareas with existing analysis data
3. JavaScript initializes accordion handlers
4. Progress tracking calculates initial completion %

### User Interaction
1. User clicks accordion header
2. JavaScript toggles `.active` class
3. Content slides open (display: block)
4. Proficiency percentages calculate from row data
5. User fills textareas
6. Progress bar updates in real-time
7. Status badge changes when complete

### Form Submission
1. User clicks Next/Previous
2. Form submits with autosave=1
3. View loops through SLP rows
4. Extracts analysis fields by index
5. Calls `update_or_create()` for each row
6. Redirects to next tab

## Troubleshooting

### Accordion won't expand
- Check `initializeSLPAccordion()` is called
- Verify `data-form-index` matches between accordion and row
- Ensure `.analysis-accordion-header` exists

### Percentages show 0%
- Check if enrolment field has value > 0
- Verify input IDs match pattern `id$="-enrolment"`
- Ensure `updateProficiencyDisplay()` is called

### Progress not updating
- Check textareas have `.analysis-textarea` class
- Verify event listeners attached in `initializeSLPAnalysisTracking()`
- Console log `textareas.length` to confirm elements found

### Data not saving
- Check field names match `slp_analysis_{idx}_{field_name}`
- Verify POST handling in views.py
- Check `Form1SLPAnalysis.objects.filter(slp_row__submission=...)` returns records

### Template errors
- Ensure `form.instance.analysis` relation exists (OneToOne)
- Add `|default:""` to all analysis field references
- Check for missing closing tags in long template section
