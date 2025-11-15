# Reading Difficulties & Targeted Interventions

This feature captures up to five priority reading difficulties per grade with a paired targeted intervention. Data is stored in two layers:

1. Raw JSON in `Submission.data['reading_difficulties_json']`
2. Structured per-grade rows in `ReadingDifficultyPlan` (one row per grade & reading period)

## JSON Schema

```jsonc
[
  {
    "grade": "4",            // Numeric grade (Kinder=0)
    "pairs": [
      { "difficulty": "Low decoding accuracy", "intervention": "Daily guided phonics groups" },
      { "difficulty": "Limited vocabulary", "intervention": "Context-clue mini lessons" }
      // ... up to 5 pairs
    ]
  },
  // ... additional grade entries
]
```

Empty rows (both difficulty & intervention blank) are ignored. Each field is trimmed to 500 characters before persistence in `ReadingDifficultyPlan`.

## Reading Period Resolution

Default quarter→reading period mapping:

| Quarter | Reading Period |
|---------|----------------|
| Q1      | EOSY           |
| Q2      | BOSY           |
| Q3      | BOSY           |
| Q4      | MOSY           |

Override precedence: if `FormTemplate.reading_timing_override` is one of `bosy`, `mosy`, `eosy`, that value is used instead of the default mapping.

## Model Synchronization

On save of the Reading tab, the raw JSON is first persisted, then synchronized into `ReadingDifficultyPlan` rows for the resolved reading period. Only grades supported by the per-grade model are updated. (Grades 11–12 are skipped if not defined in `RMAGradeLabel.CHOICES`).

## Export

The Reading export now includes a table: **"Reading Difficulties & Targeted Interventions"** with columns:

`Period, Grade, Pair #, Difficulty, Intervention`

Model rows are preferred; if none are present the system falls back to the raw JSON.

## Backfill Command

Run the management command to populate historical submissions:

```
python manage.py backfill_reading_difficulty_plans --dry-run
python manage.py backfill_reading_difficulty_plans
```

Optional flags:
`--period bosy|mosy|eosy` force a period; `--limit N` process only first N submissions.

## Future Enhancements

- Extend model choices to include Grades 11–12 if senior high tracking is required.
- Add per-field validation (e.g. prohibit identical consecutive difficulties).
- Add analytics aggregation across submissions for top recurring difficulties.
- UI enhancements: dynamic add/remove rows (still enforcing max 5).

---
Updated: This document complements `export-spec.md` and `API_DOCUMENTATION.md`.