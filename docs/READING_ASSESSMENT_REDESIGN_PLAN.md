# Reading Assessment Redesign Plan

## Current Issues
- Current CRLA/PHILIRI section is too simplistic
- Doesn't capture the complete assessment framework
- Missing timing-based data collection (BOSY, MOSY, EOSY)
- Doesn't account for different school grade configurations

## New Requirements

### PART A: CRLA RESULT (2025-26)

**Structure:**
- **4 Proficiency Levels:** Low Emerging, High Emerging, Developing, Transitioning
- **3 Assessment Timings:**
  - BOSY (Beginning of School Year) - Report in Q3
  - MOSY (Middle of School Year) - Report in Q4
  - EOSY (End of School Year) - Report in Q1
- **Subjects & Grades:**
  - Mother Tongue: Grades I, II, III
  - English: Grade III only
  - Filipino: Grades II, III

**Data Collection:**
For each timing × level combination, schools enter learner counts per subject/grade

### PART B: PHILIRI RESULT (2025-26)

**Structure:**
- **3 Reading Levels:** Frustration, Instructional, Independent
- **3 Assessment Timings:**
  - BOSY - Report in Q3
  - MOSY - Report in Q4
  - EOSY - Report in Q1
- **Subjects & Grades:**
  - English: Grades 4/7, 5/8, 6/9, 10
  - Filipino: Grades 4/7, 5/8, 6/9, 10
  - **Note:** Grade offerings vary by school (e.g., 1-6, 1-10, 7-10, 1-12, 7-12)

**Data Collection:**
For each timing × level combination, schools enter learner counts per subject/grade
Must be dynamic based on school's grade configuration

### PART C: Interventions (Top 5)

**Structure:**
- List 5 priority interventions developed based on assessment results
- Free text fields

## Database Schema Changes

### New Model: `ReadingCRLARow`
```python
class ReadingCRLARow(models.Model):
    LEVEL_CHOICES = [
        ('low_emerging', 'Low Emerging'),
        ('high_emerging', 'High Emerging'),
        ('developing', 'Developing'),
        ('transitioning', 'Transitioning'),
    ]
    
    TIMING_CHOICES = [
        ('bosy', 'BOSY'),
        ('mosy', 'MOSY'),
        ('eosy', 'EOSY'),
    ]
    
    SUBJECT_CHOICES = [
        ('mother_tongue_g1', 'Mother Tongue - Grade I'),
        ('mother_tongue_g2', 'Mother Tongue - Grade II'),
        ('mother_tongue_g3', 'Mother Tongue - Grade III'),
        ('english_g3', 'English - Grade III'),
        ('filipino_g2', 'Filipino - Grade II'),
        ('filipino_g3', 'Filipino - Grade III'),
    ]
    
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE)
    timing = models.CharField(max_length=20, choices=TIMING_CHOICES)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    subject = models.CharField(max_length=50, choices=SUBJECT_CHOICES)
    count = models.IntegerField(default=0)
```

### New Model: `ReadingPHILIRIRow`
```python
class ReadingPHILIRIRow(models.Model):
    LEVEL_CHOICES = [
        ('frustration', 'Frustration'),
        ('instructional', 'Instructional'),
        ('independent', 'Independent'),
    ]
    
    TIMING_CHOICES = [
        ('bosy', 'BOSY'),
        ('mosy', 'MOSY'),
        ('eosy', 'EOSY'),
    ]
    
    GRADE_CHOICES = [
        ('4_7', 'Grade 4/7'),
        ('5_8', 'Grade 5/8'),
        ('6_9', 'Grade 6/9'),
        ('10', 'Grade 10'),
    ]
    
    SUBJECT_CHOICES = [
        ('english', 'English'),
        ('filipino', 'Filipino'),
    ]
    
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE)
    timing = models.CharField(max_length=20, choices=TIMING_CHOICES)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    grade = models.CharField(max_length=10, choices=GRADE_CHOICES)
    subject = models.CharField(max_length=20, choices=SUBJECT_CHOICES)
    count = models.IntegerField(default=0)
    
    # Filter by school's available grades (dynamic)
    class Meta:
        verbose_name = "PHILIRI Reading Assessment Row"
```

### Update Model: `ReadingIntervention`
```python
class ReadingIntervention(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE)
    order = models.IntegerField()  # 1-5
    description = models.TextField()
```

## UI Design

### Layout Structure
```
┌─────────────────────────────────────────────────────────────┐
│ Reading (CRLA/PHILIRI)                         [Tab]         │
├─────────────────────────────────────────────────────────────┤
│ Document reading assessment results and interventions        │
│ for the school year.                                         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ PART A: CRLA RESULT (2025-26)                                │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ [Timing Selector: BOSY | MOSY | EOSY]                       │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            Low Emerging Results                      │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │ Mother Tongue G1: [___]  English G3:     [___]      │   │
│  │ Mother Tongue G2: [___]  Filipino G2:    [___]      │   │
│  │ Mother Tongue G3: [___]  Filipino G3:    [___]      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            High Emerging Results                      │   │
│  │ [Same layout...]                                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  [Repeat for Developing, Transitioning]                      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ PART B: PHILIRI RESULT (2025-26)                             │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ [Timing Selector: BOSY | MOSY | EOSY]                       │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            Frustration Level Results                  │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │ English  - Grade 4/7: [___]  Grade 5/8: [___]       │   │
│  │            Grade 6/9: [___]  Grade 10:  [___]       │   │
│  │                                                       │   │
│  │ Filipino - Grade 4/7: [___]  Grade 5/8: [___]       │   │
│  │            Grade 6/9: [___]  Grade 10:  [___]       │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  [Repeat for Instructional, Independent]                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Interventions Developed Based on Assessment Results          │
├─────────────────────────────────────────────────────────────┤
│ 1. [________________________________...]                     │
│ 2. [________________________________...]                     │
│ 3. [________________________________...]                     │
│ 4. [________________________________...]                     │
│ 5. [________________________________...]                     │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Steps

### Phase 1: Database & Models
1. Create new models: `ReadingCRLARow`, `ReadingPHILIRIRow`
2. Update `ReadingIntervention` model
3. Create migrations
4. Remove old CRLA/PHILIRI models

### Phase 2: Forms
1. Create `ReadingCRLAFormSet` (formset factory)
2. Create `ReadingPHILIRIFormSet` (formset factory, filtered by school grades)
3. Update `ReadingInterventionFormSet` (limit to 5)

### Phase 3: Views
1. Update `edit_submission` view to handle new formsets
2. Add logic to filter PHILIRI grades based on school
3. Add validation for timing-based reporting (Q3=BOSY, Q4=MOSY, Q1=EOSY)

### Phase 4: Templates
1. Redesign Reading tab with tabbed timing interface
2. Create grouped input sections for each level
3. Add dynamic grade filtering for PHILIRI
4. Style with simple, clean CSS (no colors, professional)

### Phase 5: Testing
1. Test with schools having different grade configurations
2. Validate data entry and calculations
3. Test quarterly reporting constraints

## Design Principles
- **Simple & Clean:** No fancy colors, gradients, or decorations
- **Performance:** Minimize JavaScript, use native HTML forms
- **Accessibility:** Proper labels, semantic HTML
- **Responsive:** Works on tablets/mobile devices
- **Efficient:** Group related inputs, minimize scrolling

## Notes
- PHILIRI grades must be dynamically shown based on school's `grade_levels` field
- Timing validation should warn users about appropriate quarters
- Consider adding totals/summaries for each timing period
- May need help text explaining when to report each timing
