import json, time, statistics
from typing import Optional
from django.core.management.base import BaseCommand, CommandError
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.db import connection, reset_queries
from submissions.models import Submission, Form1SLPRow
from accounts.roles import get_profile

User = get_user_model()

class Command(BaseCommand):
    help = "Profile the SLP save_subject fast-path by issuing repeated POSTs and reporting timing + query metrics."

    def add_arguments(self, parser):
        parser.add_argument("submission_id", type=int, help="Existing submission id to target. If omitted we error.")
        parser.add_argument("--iterations", type=int, default=20, help="Number of POST iterations (default: 20)")
        parser.add_argument("--row-index", type=int, default=0, help="SLP row index to target (default: 0)")
        parser.add_argument("--username", type=str, default=None, help="Existing username to use; if missing create temp user")
        parser.add_argument("--password", type=str, default="pass123", help="Password for created user (default: pass123)")
        parser.add_argument("--json", action="store_true", help="Emit final summary as JSON only")

    def _ensure_user(self, username: Optional[str], password: str, submission: Submission):
        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                raise CommandError(f"Username '{username}' not found.")
        else:
            uname = f"prof_user_{int(time.time()*1000)}"
            user = User.objects.create_user(username=uname, password=password)
        profile = get_profile(user)
        if profile.school != submission.school:
            profile.school = submission.school
            profile.save(update_fields=["school", "updated_at"])
        return user

    def _build_payload(self, submission: Submission, row_index: int) -> dict:
        first_row = (
            Form1SLPRow.objects.filter(submission=submission)
            .order_by("id")[row_index:row_index+1]
            .first()
        )
        if not first_row:
            raise CommandError(f"Row index {row_index} not found for submission {submission.id}")
        prefix = f"slp_rows-{row_index}"
        return {
            "tab": "slp",
            "action": "save_subject",
            "current_subject_prefix": prefix,
            "current_subject_index": str(row_index),
            "current_subject_id": str(first_row.id),
            f"{prefix}-enrolment": str(first_row.enrolment or 30),
            f"{prefix}-dnme": str(first_row.dnme or 5),
            f"{prefix}-fs": str(first_row.fs or 5),
            f"{prefix}-s": str(first_row.s or 5),
            f"{prefix}-vs": str(first_row.vs or 5),
            f"{prefix}-o": str(first_row.o or 10),
            f"{prefix}-top_three_llc": first_row.top_three_llc or "1. competency A\n2. competency B",
            f"{prefix}-non_mastery_reasons": first_row.non_mastery_reasons or "a",
            f"{prefix}-non_mastery_other": "",
            f"{prefix}-intervention_plan": first_row.intervention_plan or json.dumps([{ "code": "a", "intervention": "Updated Drill" }]),
        }

    def handle(self, *args, **options):
        submission_id = options["submission_id"]
        iterations = options["iterations"]
        row_index = options["row_index"]
        username = options["username"]
        password = options["password"]
        emit_json = options["json"]
        try:
            submission = Submission.objects.get(id=submission_id)
        except Submission.DoesNotExist:
            raise CommandError(f"Submission {submission_id} not found.")

        user = self._ensure_user(username, password, submission)
        client = Client()
        if not client.login(username=user.username, password=password):
            raise CommandError("Login failed for profiling user.")

        url = reverse("edit_submission", args=[submission.id])
        timings = []
        query_counts = []
        max_query_durations = []

        # Warm-up single request (not timed) to pay first-load cost
        payload = self._build_payload(submission, row_index)
        client.post(url, payload, follow=True)

        for i in range(iterations):
            payload = self._build_payload(submission, row_index)
            reset_queries()
            t0 = time.perf_counter()
            resp = client.post(url, payload, follow=True)
            dt_ms = (time.perf_counter() - t0) * 1000
            if resp.status_code not in (200, 302):
                raise CommandError(f"Unexpected status {resp.status_code} on iteration {i}")
            timings.append(dt_ms)
            qlen = len(connection.queries)
            query_counts.append(qlen)
            max_q_dur = 0.0
            for q in connection.queries:
                try:
                    dur = float(q.get("time", 0))
                except (TypeError, ValueError):
                    dur = 0.0
                if dur > max_q_dur:
                    max_q_dur = dur
            max_query_durations.append(max_q_dur * 1000)  # convert to ms if seconds

        summary = {
            "submission_id": submission.id,
            "iterations": iterations,
            "row_index": row_index,
            "timings_ms": timings,
            "avg_ms": statistics.mean(timings),
            "median_ms": statistics.median(timings),
            "p95_ms": statistics.quantiles(timings, n=20)[18] if len(timings) >= 20 else None,
            "min_ms": min(timings),
            "max_ms": max(timings),
            "avg_queries": statistics.mean(query_counts),
            "median_queries": statistics.median(query_counts),
            "max_query_duration_ms_avg": statistics.mean(max_query_durations),
        }

        if emit_json:
            self.stdout.write(json.dumps(summary, indent=2))
        else:
            self.stdout.write("SLP save_subject profiling summary:\n")
            self.stdout.write(f"  Submission: {summary['submission_id']} iterations={summary['iterations']} row_index={summary['row_index']}\n")
            self.stdout.write(f"  avg={summary['avg_ms']:.1f} ms median={summary['median_ms']:.1f} ms min={summary['min_ms']:.1f} ms max={summary['max_ms']:.1f} ms\n")
            if summary['p95_ms'] is not None:
                self.stdout.write(f"  p95={summary['p95_ms']:.1f} ms\n")
            self.stdout.write(f"  avg queries={summary['avg_queries']:.1f} median queries={summary['median_queries']:.1f}\n")
            self.stdout.write(f"  avg max single query duration={summary['max_query_duration_ms_avg']:.3f} ms\n")
            self.stdout.write("  timings=" + ", ".join(f"{t:.1f}" for t in timings) + "\n")
            self.stdout.write("  queries per iteration=" + ", ".join(str(q) for q in query_counts) + "\n")

        # Do not delete submission; command assumes existing data context.
