from django.core.management.base import BaseCommand
from organizations.models import School
from submissions.models import Form1SLPRow, Submission


class Command(BaseCommand):
    help = 'Test SLP subject data for the dashboard'

    def handle(self, *args, **options):
        # Get SLP data statistics
        total_slp_rows = Form1SLPRow.objects.count()
        self.stdout.write(f"Total SLP rows: {total_slp_rows}")
        
        # Get schools with SLP data
        schools_with_slp = Form1SLPRow.objects.values('submission__school__name', 'submission__school__id').distinct()[:10]
        self.stdout.write(f"\nSchools with SLP data:")
        for school in schools_with_slp:
            self.stdout.write(f"- {school['submission__school__name']} (ID: {school['submission__school__id']})")
        
        # Get subject areas
        subjects = Form1SLPRow.objects.values_list('subject', flat=True).distinct()
        subjects = [s for s in subjects if s]  # Remove None/empty
        self.stdout.write(f"\nAvailable subjects: {subjects}")
        
        # Test a specific school's SLP data
        if schools_with_slp:
            test_school_id = schools_with_slp[0]['submission__school__id']
            test_school = School.objects.get(id=test_school_id)
            
            self.stdout.write(f"\nAnalyzing school: {test_school.name}")
            if hasattr(test_school, 'profile') and test_school.profile:
                self.stdout.write(f"Grade span: {test_school.profile.grade_span_start}-{test_school.profile.grade_span_end}")
                school_level = 'Elementary' if (test_school.profile.grade_span_end and test_school.profile.grade_span_end <= 6) else 'Secondary' if (test_school.profile.grade_span_start and test_school.profile.grade_span_start >= 7) else 'Mixed'
                self.stdout.write(f"School level: {school_level}")
            
            slp_rows = Form1SLPRow.objects.filter(
                submission__school=test_school
            )
            
            # Check submission statuses
            statuses = slp_rows.values_list('submission__status', flat=True).distinct()
            self.stdout.write(f"Submission statuses: {list(statuses)}")
            
            # Filter for submitted/noted
            submitted_slp_rows = slp_rows.filter(submission__status__in=['submitted', 'noted'])
            self.stdout.write(f"Submitted SLP rows: {submitted_slp_rows.count()}")
            
            slp_rows = submitted_slp_rows if submitted_slp_rows.exists() else slp_rows
            
            self.stdout.write(f"SLP rows for this school: {slp_rows.count()}")
            
            # Group by subject
            subjects_data = {}
            for row in slp_rows:
                subject = row.subject or 'Unknown Subject'
                if subject not in subjects_data:
                    subjects_data[subject] = {
                        'enrolment': 0,
                        's': 0,
                        'vs': 0,
                        'o': 0,
                        'dnme': 0,
                        'rows': 0,
                        'grades': set(),
                    }
                
                data = subjects_data[subject]
                data['enrolment'] += row.enrolment or 0
                data['s'] += row.s or 0
                data['vs'] += row.vs or 0
                data['o'] += row.o or 0
                data['dnme'] += row.dnme or 0
                data['rows'] += 1
                data['grades'].add(row.grade_label or 'Unknown')
            
            self.stdout.write("\nSubject breakdown:")
            for subject, data in subjects_data.items():
                proficient = data['s'] + data['vs'] + data['o']
                proficiency_rate = (proficient / data['enrolment'] * 100) if data['enrolment'] > 0 else 0
                self.stdout.write(
                    f"  {subject}: {data['enrolment']} enrolled, "
                    f"{proficient} proficient ({proficiency_rate:.1f}%), "
                    f"{data['dnme']} DNME, "
                    f"Grades: {sorted(data['grades'])}"
                )
        
        self.stdout.write(self.style.SUCCESS('\nSLP subject analysis complete!'))