from django.core.management.base import BaseCommand
from submissions.models import Form1SLPRow
import random


class Command(BaseCommand):
    help = 'Add realistic test data to SLP rows to test KPI calculations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--commit',
            action='store_true',
            help='Actually save the changes (dry run by default)',
        )

    def handle(self, *args, **options):
        commit = options.get('commit', False)
        
        if not commit:
            self.stdout.write(self.style.WARNING("DRY RUN - Use --commit to actually save changes"))
        
        # Get all SLP rows with zero enrollment
        empty_rows = Form1SLPRow.objects.filter(enrolment=0)
        self.stdout.write(f"Found {empty_rows.count()} SLP rows with zero enrollment")
        
        updated_count = 0
        
        for row in empty_rows[:50]:  # Update first 50 rows for testing
            # Generate realistic enrollment based on grade level
            if 'Kinder' in row.grade_label or 'Grade 1' in row.grade_label:
                enrollment = random.randint(15, 35)
            elif 'Grade 2' in row.grade_label or 'Grade 3' in row.grade_label:
                enrollment = random.randint(20, 40)
            elif 'Grade 4' in row.grade_label or 'Grade 5' in row.grade_label or 'Grade 6' in row.grade_label:
                enrollment = random.randint(25, 45)
            else:  # High school
                enrollment = random.randint(30, 50)
            
            # Generate realistic performance distribution
            # Typical distribution: some struggling, most satisfactory, few outstanding
            dnme = random.randint(1, max(1, enrollment // 8))  # 5-15% struggling
            fs = random.randint(enrollment // 6, enrollment // 3)  # 15-35% fairly satisfactory
            
            remaining = enrollment - dnme - fs
            s = random.randint(remaining // 3, remaining // 2)  # 30-50% satisfactory
            
            remaining = remaining - s
            vs = random.randint(remaining // 3, remaining * 2 // 3)  # 20-40% very satisfactory
            
            o = remaining - vs  # Rest are outstanding
            
            # Ensure totals add up correctly
            total_check = dnme + fs + s + vs + o
            if total_check != enrollment:
                o = enrollment - (dnme + fs + s + vs)
                if o < 0:
                    o = 0
                    vs = enrollment - (dnme + fs + s)
            
            self.stdout.write(
                f"Updating {row.submission.school.name} - {row.subject} {row.grade_label}: "
                f"Enrollment: {enrollment}, DNME: {dnme}, FS: {fs}, S: {s}, VS: {vs}, O: {o}"
            )
            
            if commit:
                row.enrolment = enrollment
                row.dnme = dnme
                row.fs = fs
                row.s = s
                row.vs = vs
                row.o = o
                row.save()
            
            updated_count += 1
        
        if commit:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully updated {updated_count} SLP rows with realistic test data')
            )
        else:
            self.stdout.write(
                f'Would update {updated_count} SLP rows. Use --commit to save changes.'
            )