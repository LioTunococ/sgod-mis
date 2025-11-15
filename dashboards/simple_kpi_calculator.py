"""
Simple KPI Calculator for SMME Dashboard Table
Provides clean, focused calculations for the new simplified dashboard.
"""

from django.db.models import Sum, Count, Avg, Q
from typing import Dict, List, Optional, Tuple
from decimal import Decimal

from submissions.models import (
    Form1PctRow,
    Form1SLPRow, 
    ReadingAssessmentCRLA,
    ReadingAssessmentPHILIRI,
    Form1RMARow,
    Form1SupervisionRow,
    Form1ADMRow,
    Submission,
    Period
)
from submissions.constants import (
    SMEAActionArea,
    CRLAProficiencyLevel,
    PHILIRIReadingLevel,
    AssessmentPeriod
)
from organizations.models import School, District


class SimpleKPICalculator:
    """
    Clean, focused KPI calculator for the simplified table dashboard.
    Each method returns standardized data structure for easy display.
    """
    
    def __init__(self, school_year: int, quarter: str = None, district_id: int = None, 
                 school_id: int = None, assessment_period: str = None):
        """
        Initialize calculator with filter parameters.
        
        Args:
            school_year: School year start (e.g., 2025 for SY 2025-2026)
            quarter: Quarter filter (Q1, Q2, Q3, Q4) or None for all
            district_id: District ID filter or None for all
            school_id: School ID filter or None for all  
            assessment_period: Assessment period (bosy, mosy, eosy) for Reading/RMA
        """
        self.school_year = school_year
        self.quarter = quarter
        self.district_id = district_id
        self.school_id = school_id
        self.assessment_period = assessment_period or 'bosy'
        
        # Base queryset for submissions
        self.base_submissions = self._build_submission_queryset()
        
        # Cache for schools to avoid repeated queries
        self._schools_cache = None
    
    def _build_submission_queryset(self):
        """Build base submission queryset with all filters applied."""
        qs = Submission.objects.filter(
            period__school_year_start=self.school_year,
            status__in=['submitted', 'noted', 'approved']
        ).select_related('school', 'school__district', 'period')
        
        if self.quarter:
            qs = qs.filter(period__quarter_tag=self.quarter)
        
        if self.district_id:
            qs = qs.filter(school__district_id=self.district_id)
            
        if self.school_id:
            qs = qs.filter(school_id=self.school_id)
            
        return qs
    
    def get_schools(self) -> List[School]:
        """Get filtered list of schools with caching."""
        if self._schools_cache is None:
            school_ids = self.base_submissions.values_list('school_id', flat=True).distinct()
            self._schools_cache = list(
                School.objects.filter(id__in=school_ids)
                .select_related('district')
                .order_by('name')
            )
        return self._schools_cache
    
    # ============================================================================
    # 1. IMPLEMENTATION PERCENTAGE KPIs (Form1PctRow)
    # ============================================================================
    
    def calculate_implementation_kpis(self) -> List[Dict]:
        """
        Calculate implementation percentages for Access, Quality, Equity, Enabling.
        
        Returns:
            List of dicts with school info and implementation percentages
        """
        results = []
        
        for school in self.get_schools():
            school_submissions = self.base_submissions.filter(school=school)
            
            # Get implementation data for this school
            pct_data = Form1PctRow.objects.filter(
                header__submission__in=school_submissions
            ).values('area').annotate(
                avg_percent=Avg('percent')
            )
            
            # Organize by area
            impl_data = {row['area']: round(row['avg_percent'] or 0, 1) for row in pct_data}
            
            results.append({
                'school': school,
                'school_name': school.name,
                'district_name': school.district.name if school.district else 'Unassigned',
                'access_percent': impl_data.get(SMEAActionArea.ACCESS, 0),
                'quality_percent': impl_data.get(SMEAActionArea.QUALITY, 0),
                'equity_percent': impl_data.get(SMEAActionArea.EQUITY, 0),
                'enabling_percent': impl_data.get(SMEAActionArea.ENABLING_MECHANISMS, 0),
            })
        
        return results
    
    # ============================================================================
    # 2. SLP (SCHOOL LEVEL PROFICIENCY) KPIs (Form1SLPRow)
    # ============================================================================
    
    def calculate_slp_kpis(self, proficiency_filter: str = None, 
                          subject_filter: str = None, grade_filter: str = None) -> List[Dict]:
        """
        Calculate SLP proficiency distribution percentages.
        
        Args:
            proficiency_filter: Filter by proficiency (dnme, fs, s, vs, o) or None
            subject_filter: Filter by subject code or None  
            grade_filter: Filter by grade label or None
            
        Returns:
            List of dicts with school info and proficiency percentages
        """
        results = []
        
        for school in self.get_schools():
            school_submissions = self.base_submissions.filter(school=school)
            
            # Base SLP query
            slp_qs = Form1SLPRow.objects.filter(
                submission__in=school_submissions,
                is_offered=True
            )
            
            # Apply filters
            if subject_filter:
                slp_qs = slp_qs.filter(subject=subject_filter)
            if grade_filter:
                slp_qs = slp_qs.filter(grade_label=grade_filter)
            
            # Aggregate proficiency data
            totals = slp_qs.aggregate(
                total_enrollment=Sum('enrolment'),
                total_dnme=Sum('dnme'),
                total_fs=Sum('fs'),
                total_s=Sum('s'),
                total_vs=Sum('vs'),
                total_o=Sum('o')
            )
            
            enrollment = totals['total_enrollment'] or 0
            
            if enrollment > 0:
                dnme_pct = round((totals['total_dnme'] or 0) / enrollment * 100, 1)
                fs_pct = round((totals['total_fs'] or 0) / enrollment * 100, 1)
                s_pct = round((totals['total_s'] or 0) / enrollment * 100, 1)
                vs_pct = round((totals['total_vs'] or 0) / enrollment * 100, 1)
                o_pct = round((totals['total_o'] or 0) / enrollment * 100, 1)
            else:
                dnme_pct = fs_pct = s_pct = vs_pct = o_pct = 0
            
            results.append({
                'school': school,
                'school_name': school.name,
                'district_name': school.district.name if school.district else 'Unassigned',
                'total_enrollment': enrollment,
                'dnme_percent': dnme_pct,
                'fs_percent': fs_pct,
                's_percent': s_pct,
                'vs_percent': vs_pct,
                'o_percent': o_pct,
            })
        
        return results
    
    # ============================================================================
    # 3. CRLA READING ASSESSMENT KPIs (ReadingAssessmentCRLA)
    # ============================================================================
    
    def calculate_crla_kpis(self, subject_filter: str = None) -> List[Dict]:
        """
        Calculate CRLA proficiency distribution percentages.
        
        Args:
            subject_filter: Filter by subject (mt/fil/eng) or None
            
        Returns:
            List of dicts with school info and CRLA percentages
        """
        results = []
        
        for school in self.get_schools():
            school_submissions = self.base_submissions.filter(school=school)
            
            # Get CRLA data for assessment period
            crla_qs = ReadingAssessmentCRLA.objects.filter(
                submission__in=school_submissions,
                period=self.assessment_period
            )
            
            # Calculate totals across all grades and subjects
            totals = {}
            for level in [CRLAProficiencyLevel.LOW_EMERGING, CRLAProficiencyLevel.HIGH_EMERGING,
                         CRLAProficiencyLevel.DEVELOPING, CRLAProficiencyLevel.TRANSITIONING]:
                level_data = crla_qs.filter(level=level).aggregate(
                    mt_total=Sum('mt_grade_1') + Sum('mt_grade_2') + Sum('mt_grade_3'),
                    fil_total=Sum('fil_grade_2') + Sum('fil_grade_3'),
                    eng_total=Sum('eng_grade_3')
                )
                
                if subject_filter == 'mt':
                    totals[level] = level_data['mt_total'] or 0
                elif subject_filter == 'fil':
                    totals[level] = level_data['fil_total'] or 0
                elif subject_filter == 'eng':
                    totals[level] = level_data['eng_total'] or 0
                else:
                    # All subjects combined
                    totals[level] = (level_data['mt_total'] or 0) + \
                                  (level_data['fil_total'] or 0) + \
                                  (level_data['eng_total'] or 0)
            
            grand_total = sum(totals.values())
            
            if grand_total > 0:
                low_emerging_pct = round(totals[CRLAProficiencyLevel.LOW_EMERGING] / grand_total * 100, 1)
                high_emerging_pct = round(totals[CRLAProficiencyLevel.HIGH_EMERGING] / grand_total * 100, 1)
                developing_pct = round(totals[CRLAProficiencyLevel.DEVELOPING] / grand_total * 100, 1)
                transitioning_pct = round(totals[CRLAProficiencyLevel.TRANSITIONING] / grand_total * 100, 1)
            else:
                low_emerging_pct = high_emerging_pct = developing_pct = transitioning_pct = 0
            
            results.append({
                'school': school,
                'school_name': school.name,
                'district_name': school.district.name if school.district else 'Unassigned',
                'total_learners': grand_total,
                'low_emerging_percent': low_emerging_pct,
                'high_emerging_percent': high_emerging_pct,
                'developing_percent': developing_pct,
                'transitioning_percent': transitioning_pct,
            })
        
        return results
    
    # ============================================================================
    # 4. PHILIRI READING ASSESSMENT KPIs (ReadingAssessmentPHILIRI)
    # ============================================================================
    
    def calculate_philiri_kpis(self, subject_filter: str = None, 
                              grade_range: str = None) -> List[Dict]:
        """
        Calculate PHILIRI reading level distribution percentages.
        
        Args:
            subject_filter: Filter by subject (eng/fil) or None
            grade_range: Filter by grade range (elementary/junior/senior) or None
            
        Returns:
            List of dicts with school info and PHILIRI percentages
        """
        results = []
        
        for school in self.get_schools():
            school_submissions = self.base_submissions.filter(school=school)
            
            # Get PHILIRI data for assessment period
            philiri_qs = ReadingAssessmentPHILIRI.objects.filter(
                submission__in=school_submissions,
                period=self.assessment_period
            )
            
            # Calculate totals based on filters
            if subject_filter == 'eng':
                grade_fields = ['eng_grade_4', 'eng_grade_5', 'eng_grade_6', 
                               'eng_grade_7', 'eng_grade_8', 'eng_grade_9', 'eng_grade_10']
            elif subject_filter == 'fil':
                grade_fields = ['fil_grade_4', 'fil_grade_5', 'fil_grade_6', 
                               'fil_grade_7', 'fil_grade_8', 'fil_grade_9', 'fil_grade_10']
            else:
                # All subjects combined
                grade_fields = ['eng_grade_4', 'eng_grade_5', 'eng_grade_6', 
                               'eng_grade_7', 'eng_grade_8', 'eng_grade_9', 'eng_grade_10',
                               'fil_grade_4', 'fil_grade_5', 'fil_grade_6', 
                               'fil_grade_7', 'fil_grade_8', 'fil_grade_9', 'fil_grade_10']
            
            # Apply grade range filter
            if grade_range == 'elementary':
                grade_fields = [f for f in grade_fields if any(g in f for g in ['grade_4', 'grade_5', 'grade_6'])]
            elif grade_range == 'junior':
                grade_fields = [f for f in grade_fields if any(g in f for g in ['grade_7', 'grade_8', 'grade_9', 'grade_10'])]
            
            totals = {}
            for level in [PHILIRIReadingLevel.FRUSTRATION, PHILIRIReadingLevel.INSTRUCTIONAL, 
                         PHILIRIReadingLevel.INDEPENDENT]:
                level_total = 0
                level_records = philiri_qs.filter(level=level)
                for record in level_records:
                    for field in grade_fields:
                        level_total += getattr(record, field, 0) or 0
                totals[level] = level_total
            
            grand_total = sum(totals.values())
            
            if grand_total > 0:
                frustration_pct = round(totals[PHILIRIReadingLevel.FRUSTRATION] / grand_total * 100, 1)
                instructional_pct = round(totals[PHILIRIReadingLevel.INSTRUCTIONAL] / grand_total * 100, 1)
                independent_pct = round(totals[PHILIRIReadingLevel.INDEPENDENT] / grand_total * 100, 1)
            else:
                frustration_pct = instructional_pct = independent_pct = 0
            
            results.append({
                'school': school,
                'school_name': school.name,
                'district_name': school.district.name if school.district else 'Unassigned',
                'total_learners': grand_total,
                'frustration_percent': frustration_pct,
                'instructional_percent': instructional_pct,
                'independent_percent': independent_pct,
            })
        
        return results
    
    # ============================================================================
    # 5. RMA (READING & MATH ASSESSMENT) KPIs (Form1RMARow)
    # ============================================================================
    
    def calculate_rma_kpis(self, grade_filter: str = None) -> List[Dict]:
        """
        Calculate RMA proficiency distribution percentages.
        
        Args:
            grade_filter: Filter by grade label or None
            
        Returns:
            List of dicts with school info and RMA percentages
        """
        results = []
        
        for school in self.get_schools():
            school_submissions = self.base_submissions.filter(school=school)
            
            # Base RMA query
            rma_qs = Form1RMARow.objects.filter(submission__in=school_submissions)
            
            if grade_filter:
                rma_qs = rma_qs.filter(grade_label=grade_filter)
            
            # Aggregate proficiency data
            totals = rma_qs.aggregate(
                total_enrollment=Sum('enrolment'),
                total_not_proficient=Sum('emerging_not_proficient'),
                total_low_proficient=Sum('emerging_low_proficient'),
                total_nearly_proficient=Sum('developing_nearly_proficient'),
                total_proficient=Sum('transitioning_proficient'),
                total_at_grade_level=Sum('at_grade_level')
            )
            
            enrollment = totals['total_enrollment'] or 0
            
            if enrollment > 0:
                not_proficient_pct = round((totals['total_not_proficient'] or 0) / enrollment * 100, 1)
                low_proficient_pct = round((totals['total_low_proficient'] or 0) / enrollment * 100, 1)
                nearly_proficient_pct = round((totals['total_nearly_proficient'] or 0) / enrollment * 100, 1)
                proficient_pct = round((totals['total_proficient'] or 0) / enrollment * 100, 1)
                at_grade_level_pct = round((totals['total_at_grade_level'] or 0) / enrollment * 100, 1)
            else:
                not_proficient_pct = low_proficient_pct = nearly_proficient_pct = proficient_pct = at_grade_level_pct = 0
            
            results.append({
                'school': school,
                'school_name': school.name,
                'district_name': school.district.name if school.district else 'Unassigned',
                'total_enrollment': enrollment,
                'not_proficient_percent': not_proficient_pct,
                'low_proficient_percent': low_proficient_pct,
                'nearly_proficient_percent': nearly_proficient_pct,
                'proficient_percent': proficient_pct,
                'at_grade_level_percent': at_grade_level_pct,
            })
        
        return results
    
    # ============================================================================
    # 6. INSTRUCTIONAL SUPERVISION KPIs (Form1SupervisionRow)
    # ============================================================================
    
    def calculate_supervision_kpis(self) -> List[Dict]:
        """
        Calculate instructional supervision metrics.
        
        Returns:
            List of dicts with school info and supervision counts/metrics
        """
        results = []
        
        for school in self.get_schools():
            school_submissions = self.base_submissions.filter(school=school)
            
            # Aggregate supervision data
            supervision_data = Form1SupervisionRow.objects.filter(
                submission__in=school_submissions
            ).aggregate(
                total_teachers_supervised=Sum('teachers_supervised_observed_ta'),
                supervision_entries=Count('id')
            )
            
            # Calculate completion rate based on filled intervention/result fields
            completed_entries = Form1SupervisionRow.objects.filter(
                submission__in=school_submissions
            ).exclude(
                Q(intervention_support_provided='') | Q(result='')
            ).count()
            
            completion_rate = 0
            if supervision_data['supervision_entries'] > 0:
                completion_rate = round(
                    completed_entries / supervision_data['supervision_entries'] * 100, 1
                )
            
            results.append({
                'school': school,
                'school_name': school.name,
                'district_name': school.district.name if school.district else 'Unassigned',
                'teachers_supervised_count': supervision_data['total_teachers_supervised'] or 0,
                'supervision_entries': supervision_data['supervision_entries'] or 0,
                'completion_rate': completion_rate,
            })
        
        return results
    
    # ============================================================================
    # 7. ADM ONE-STOP-SHOP KPIs (Form1ADMRow)
    # ============================================================================
    
    def calculate_adm_kpis(self) -> List[Dict]:
        """
        Calculate ADM implementation and accomplishment percentages.
        
        Returns:
            List of dicts with school info and ADM percentages
        """
        results = []
        
        for school in self.get_schools():
            school_submissions = self.base_submissions.filter(school=school)
            
            # Check if school offers ADM
            adm_offered = school_submissions.filter(
                form1_adm_header__is_offered=True
            ).exists()
            
            if not adm_offered:
                results.append({
                    'school': school,
                    'school_name': school.name,
                    'district_name': school.district.name if school.district else 'Unassigned',
                    'adm_offered': False,
                    'physical_accomplishment_percent': 0,
                    'fund_utilization_percent': 0,
                    'overall_adm_percent': 0,
                })
                continue
            
            # Aggregate ADM data
            adm_data = Form1ADMRow.objects.filter(
                submission__in=school_submissions
            ).aggregate(
                avg_physical_percent=Avg('ppas_physical_percent'),
                avg_fund_percent=Avg('funds_percent_obligated'),
                adm_entries=Count('id')
            )
            
            physical_pct = round(adm_data['avg_physical_percent'] or 0, 1)
            fund_pct = round(adm_data['avg_fund_percent'] or 0, 1)
            overall_pct = round((physical_pct + fund_pct) / 2, 1) if (physical_pct or fund_pct) else 0
            
            results.append({
                'school': school,
                'school_name': school.name,
                'district_name': school.district.name if school.district else 'Unassigned',
                'adm_offered': True,
                'adm_entries': adm_data['adm_entries'] or 0,
                'physical_accomplishment_percent': physical_pct,
                'fund_utilization_percent': fund_pct,
                'overall_adm_percent': overall_pct,
            })
        
        return results


def get_filter_options(user) -> Dict:
    """
    Get available filter options for the dashboard.
    
    Args:
        user: Django user object for permission checking
        
    Returns:
        Dict with available school years, quarters, districts, etc.
    """
    from accounts import services as account_services
    from organizations.models import District
    
    # Get available school years
    school_years = Period.objects.values_list(
        'school_year_start', flat=True
    ).distinct().order_by('-school_year_start')
    
    school_year_choices = [
        (year, f'SY {year}-{year + 1}')
        for year in school_years
    ]
    
    # Get quarters
    quarter_choices = [
        ('', 'All Quarters'),
        ('Q1', 'Quarter 1'),
        ('Q2', 'Quarter 2'), 
        ('Q3', 'Quarter 3'),
        ('Q4', 'Quarter 4'),
    ]
    
    # Get districts (based on user permissions)
    allowed_districts = []
    if account_services.user_is_sgod_admin(user):
        allowed_districts = District.objects.all().order_by('name')
    else:
        # Add logic for other user types as needed
        pass
    
    district_choices = [('', 'All Districts')] + [
        (d.id, d.name) for d in allowed_districts
    ]
    
    # KPI Part choices
    kpi_part_choices = [
        ('implementation', '% Implementation'),
        ('slp', 'SLP (School Level Proficiency)'),
        ('crla', 'Reading CRLA'),
        ('philiri', 'Reading PHILIRI'),
        ('rma', 'RMA (Reading & Math Assessment)'),
        ('supervision', 'Instructional Supervision & TA'),
        ('adm', 'ADM One-Stop-Shop & EiE'),
    ]
    
    # Assessment period choices (for Reading/RMA)
    assessment_period_choices = [
        ('bosy', 'BOSY (Beginning of School Year)'),
        ('mosy', 'MOSY (Middle of School Year)'),
        ('eosy', 'EOSY (End of School Year)'),
    ]
    
    return {
        'school_year_choices': school_year_choices,
        'quarter_choices': quarter_choices,
        'district_choices': district_choices,
        'kpi_part_choices': kpi_part_choices,
        'assessment_period_choices': assessment_period_choices,
    }