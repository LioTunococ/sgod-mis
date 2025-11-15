from __future__ import annotations

import json
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from submissions.models import Submission, ReadingDifficultyPlan


class Command(BaseCommand):
    help = "Backfill ReadingDifficultyPlan rows from stored submission.data['reading_difficulties_json']"

    def add_arguments(self, parser):  # pragma: no cover - CLI wiring
        parser.add_argument(
            '--period',
            dest='period',
            help='Force reading period (bosy/mosy/eosy); if omitted derive per submission.'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Do not write changes; just report intended updates.'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Process only the first N submissions.'
        )

    def handle(self, *args, **options):
        forced_period = options.get('period')
        dry_run = options.get('dry_run')
        limit = options.get('limit')
        if forced_period and forced_period not in {'bosy', 'mosy', 'eosy'}:
            raise CommandError('Invalid --period value. Use bosy/mosy/eosy.')

        qs = Submission.objects.order_by('id')
        if limit is not None:
            qs = qs[:limit]

        total = 0
        updated = 0
        for submission in qs.iterator():
            raw = (submission.data or {}).get('reading_difficulties_json', [])
            if not raw:
                continue
            if not isinstance(raw, list):
                continue
            try:
                period = forced_period or self._derive_period(submission)
            except Exception:
                period = forced_period or 'bosy'
            number_to_label = {0:'k',1:'g1',2:'g2',3:'g3',4:'g4',5:'g5',6:'g6',7:'g7',8:'g8',9:'g9',10:'g10'}
            for entry in raw:
                grade_raw = entry.get('grade')
                try:
                    grade_num = int(str(grade_raw).strip())
                except Exception:
                    continue
                label = number_to_label.get(grade_num)
                if not label:
                    continue
                pairs = entry.get('pairs') or []
                cleaned = []
                for pair in pairs[:5]:
                    if not isinstance(pair, dict):
                        continue
                    diff = (pair.get('difficulty') or '').strip()
                    interv = (pair.get('intervention') or '').strip()
                    if not diff and not interv:
                        continue
                    cleaned.append({'difficulty': diff[:500], 'intervention': interv[:500]})
                if not cleaned:
                    continue
                plan, created = ReadingDifficultyPlan.objects.get_or_create(
                    submission=submission,
                    period=period,
                    grade_label=label,
                    defaults={'data': cleaned}
                )
                if not created and plan.data != cleaned:
                    if dry_run:
                        self.stdout.write(f"Would update {plan.id} {period} {label} -> {len(cleaned)} pairs")
                    else:
                        plan.data = cleaned
                        plan.save(update_fields=['data','updated_at'])
                        updated += 1
            total += 1
        self.stdout.write(self.style.SUCCESS(f"Processed {total} submissions; updated {updated} plan rows."))

    def _derive_period(self, submission) -> str:
        quarter_to_period = {'Q1':'eosy','Q2':'bosy','Q3':'bosy','Q4':'mosy'}
        base = quarter_to_period.get(getattr(getattr(submission,'period',None),'quarter_tag',''), 'bosy')
        override = getattr(getattr(submission,'form_template',None),'reading_timing_override','') or ''
        return override if override in {'bosy','mosy','eosy'} else base