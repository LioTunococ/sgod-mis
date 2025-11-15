"""
Management command to migrate existing periods to flexible format
"""
from django.core.management.base import BaseCommand
from submissions.models import Period


class Command(BaseCommand):
    help = 'Migrate existing periods to flexible format'
    
    def handle(self, *args, **options):
        periods = Period.objects.all()
        
        if not periods.exists():
            self.stdout.write(self.style.WARNING("No periods found to migrate"))
            return
        
        migrated_count = 0
        
        for period in periods:
            updated = False
            
            # Set quarter_tag from old quarter field
            if period.quarter and not period.quarter_tag:
                period.quarter_tag = period.quarter
                self.stdout.write(f"Set quarter_tag={period.quarter} for {period.label}")
                updated = True
            
            # Set display_order based on quarter
            if period.quarter and period.display_order == 0:
                quarter_map = {'Q1': 1, 'Q2': 2, 'Q3': 3, 'Q4': 4}
                period.display_order = quarter_map.get(period.quarter, 0)
                self.stdout.write(f"Set display_order={period.display_order} for {period.label}")
                updated = True
            
            # Migrate dates from starts_on to open_date
            if period.starts_on and not period.open_date:
                period.open_date = period.starts_on
                self.stdout.write(f"Set open_date={period.open_date} for {period.label}")
                updated = True
            
            # Migrate dates from ends_on to close_date
            if period.ends_on and not period.close_date:
                period.close_date = period.ends_on
                self.stdout.write(f"Set close_date={period.close_date} for {period.label}")
                updated = True
            
            # Ensure is_active is set
            if not hasattr(period, 'is_active') or period.is_active is None:
                period.is_active = True
                updated = True
            
            if updated:
                period.save()
                migrated_count += 1
        
        if migrated_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f"Successfully migrated {migrated_count} periods")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("All periods already migrated")
            )
