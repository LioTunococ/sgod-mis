"""
KPI Calculation Functions for SMME Dashboard

Calculates Key Performance Indicators from SMEA Form 1 data:
1. SLP (Student Learning Progress) - Proficiency distribution (DNME, FS, S, VS, O)
2. Implementation Areas - Action area implementation percentages (Access, Quality, Equity, Enabling)
3. CRLA Reading Assessment - Early grade reading proficiency levels
4. PHILIRI Reading Assessment - Intermediate grade reading levels
5. RMA (Reading-Math Assessment) - Performance band distribution
"""

from django.db.models import Avg, Sum, Q, Count
from submissions.models import (
    Form1SLPRow,
    Form1PctRow,
    ReadingAssessmentCRLA,
    ReadingAssessmentPHILIRI,
    Form1RMARow,
    Form1SupervisionRow,
    Form1ADMRow,
    Submission
)


def calculate_slp_kpis(period, section_code='smme'):
    """
    Calculate Student Learning Progress KPIs - Complete proficiency distribution.
    
    Returns percentages of students across all 5 proficiency levels:
    - DNME (Does Not Meet Expectations)
    - FS (Fairly Satisfactory)
    - S (Satisfactory)
    - VS (Very Satisfactory)
    - O (Outstanding)
    
    Args:
        period: Period object to calculate for
        section_code: Section code (default 'smme')
    
    Returns:
        dict: {
            'dnme_percentage': float,
            'fs_percentage': float,
            'satisfactory_percentage': float,
            'very_satisfactory_percentage': float,
            'outstanding_percentage': float,
            'total_enrollment': int,
            'total_schools': int
        }
    """
    slp_rows = Form1SLPRow.objects.filter(
        submission__period=period,
        submission__form_template__section__code__iexact=section_code,
        submission__status__in=['submitted', 'noted', 'approved'],
        is_offered=True
    )
    
    if not slp_rows.exists():
        return {
            'dnme_percentage': 0.0,
            'fs_percentage': 0.0,
            'satisfactory_percentage': 0.0,
            'very_satisfactory_percentage': 0.0,
            'outstanding_percentage': 0.0,
            'total_enrollment': 0,
            'total_schools': 0
        }
    
    # Aggregate totals
    total_enrollment = sum(row.enrolment for row in slp_rows)
    total_dnme = sum(row.dnme for row in slp_rows)
    total_fs = sum(row.fs for row in slp_rows)
    total_s = sum(row.s for row in slp_rows)
    total_vs = sum(row.vs for row in slp_rows)
    total_o = sum(row.o for row in slp_rows)
    total_schools = slp_rows.values('submission__school').distinct().count()
    
    if total_enrollment == 0:
        return {
            'dnme_percentage': 0.0,
            'fs_percentage': 0.0,
            'satisfactory_percentage': 0.0,
            'very_satisfactory_percentage': 0.0,
            'outstanding_percentage': 0.0,
            'total_enrollment': 0,
            'total_schools': total_schools
        }
    
    return {
        'dnme_percentage': round((total_dnme / total_enrollment) * 100, 1),
        'fs_percentage': round((total_fs / total_enrollment) * 100, 1),
        'satisfactory_percentage': round((total_s / total_enrollment) * 100, 1),
        'very_satisfactory_percentage': round((total_vs / total_enrollment) * 100, 1),
        'outstanding_percentage': round((total_o / total_enrollment) * 100, 1),
        'total_enrollment': total_enrollment,
        'total_schools': total_schools
    }


def calculate_implementation_kpis(period, section_code='smme'):
    """
    Calculate Implementation Area KPIs - From Form1PctRow data.
    
    Returns average implementation percentages for 4 SMEA action areas:
    - Access: Learner access to education
    - Quality: Quality of education delivery
    - Equity: Educational equity across groups
    - Enabling Mechanisms: Support systems and mechanisms
    
    Args:
        period: Period object to calculate for
        section_code: Section code (default 'smme')
    
    Returns:
        dict: {
            'access_percentage': float,
            'quality_percentage': float,
            'equity_percentage': float,
            'enabling_percentage': float,
            'overall_average': float,
            'total_schools': int
        }
    """
    from submissions.constants import SMEAActionArea
    
    # Get all Form1PctRow entries for this period
    pct_rows = Form1PctRow.objects.filter(
        header__submission__period=period,
        header__submission__form_template__section__code__iexact=section_code,
        header__submission__status__in=['submitted', 'noted', 'approved']
    )
    
    if not pct_rows.exists():
        return {
            'access_percentage': 0.0,
            'quality_percentage': 0.0,
            'equity_percentage': 0.0,
            'enabling_percentage': 0.0,
            'overall_average': 0.0,
            'total_schools': 0
        }
    
    # Calculate average percent for each area
    access_avg = pct_rows.filter(area=SMEAActionArea.ACCESS).aggregate(avg=Avg('percent'))['avg'] or 0
    quality_avg = pct_rows.filter(area=SMEAActionArea.QUALITY).aggregate(avg=Avg('percent'))['avg'] or 0
    equity_avg = pct_rows.filter(area=SMEAActionArea.EQUITY).aggregate(avg=Avg('percent'))['avg'] or 0
    enabling_avg = pct_rows.filter(area=SMEAActionArea.ENABLING_MECHANISMS).aggregate(avg=Avg('percent'))['avg'] or 0
    
    total_schools = pct_rows.values('header__submission__school').distinct().count()
    overall_avg = (access_avg + quality_avg + equity_avg + enabling_avg) / 4
    
    return {
        'access_percentage': round(access_avg, 1),
        'quality_percentage': round(quality_avg, 1),
        'equity_percentage': round(equity_avg, 1),
        'enabling_percentage': round(enabling_avg, 1),
        'overall_average': round(overall_avg, 1),
        'total_schools': total_schools
    }


def calculate_crla_kpis(period, section_code='smme', assessment_period='baseline'):
    """
    Calculate CRLA Reading Assessment KPIs - Early grade reading proficiency.
    
    Returns distribution of learners across CRLA proficiency levels:
    - Independent: Reading independently at grade level
    - Instructional: Reading with teacher support
    - Frustration: Struggling to read at grade level
    - Non-Reader: Not yet reading
    
    Args:
        period: Period object to calculate for
        section_code: Section code (default 'smme')
        assessment_period: Assessment period (default 'baseline', options: 'baseline', 'midyear', 'endyear')
    
    Returns:
        dict: {
            'independent_percentage': float,
            'instructional_percentage': float,
            'frustration_percentage': float,
            'nonreader_percentage': float,
            'total_learners': int,
            'total_schools': int
        }
    """
    from submissions.constants import CRLAProficiencyLevel
    
    crla_rows = ReadingAssessmentCRLA.objects.filter(
        submission__period=period,
        submission__form_template__section__code__iexact=section_code,
        submission__status__in=['submitted', 'noted', 'approved'],
        period=assessment_period
    )
    
    if not crla_rows.exists():
        return {
            'independent_percentage': 0.0,
            'instructional_percentage': 0.0,
            'frustration_percentage': 0.0,
            'nonreader_percentage': 0.0,
            'total_learners': 0,
            'total_schools': 0
        }
    
    # Calculate totals by level
    independent_total = sum(
        row.total_learners() 
        for row in crla_rows.filter(level=CRLAProficiencyLevel.INDEPENDENT)
    )
    instructional_total = sum(
        row.total_learners() 
        for row in crla_rows.filter(level=CRLAProficiencyLevel.INSTRUCTIONAL)
    )
    frustration_total = sum(
        row.total_learners() 
        for row in crla_rows.filter(level=CRLAProficiencyLevel.FRUSTRATION)
    )
    nonreader_total = sum(
        row.total_learners() 
        for row in crla_rows.filter(level=CRLAProficiencyLevel.NON_READER)
    )
    
    total_learners = independent_total + instructional_total + frustration_total + nonreader_total
    total_schools = crla_rows.values('submission__school').distinct().count()
    
    if total_learners == 0:
        return {
            'independent_percentage': 0.0,
            'instructional_percentage': 0.0,
            'frustration_percentage': 0.0,
            'nonreader_percentage': 0.0,
            'total_learners': 0,
            'total_schools': total_schools
        }
    
    return {
        'independent_percentage': round((independent_total / total_learners) * 100, 1),
        'instructional_percentage': round((instructional_total / total_learners) * 100, 1),
        'frustration_percentage': round((frustration_total / total_learners) * 100, 1),
        'nonreader_percentage': round((nonreader_total / total_learners) * 100, 1),
        'total_learners': total_learners,
        'total_schools': total_schools
    }


def calculate_philiri_kpis(period, section_code='smme', assessment_period='baseline'):
    """
    Calculate PHILIRI Reading Assessment KPIs - Intermediate grade reading levels.
    
    Returns distribution of learners across PHILIRI reading levels:
    - Independent: Reading independently at grade level
    - Instructional: Reading with teacher support
    - Frustration: Struggling to read at grade level
    - Non-Reader: Not yet reading
    
    Args:
        period: Period object to calculate for
        section_code: Section code (default 'smme')
        assessment_period: Assessment period (default 'baseline', options: 'baseline', 'midyear', 'endyear')
    
    Returns:
        dict: {
            'independent_percentage': float,
            'instructional_percentage': float,
            'frustration_percentage': float,
            'nonreader_percentage': float,
            'total_learners': int,
            'total_schools': int
        }
    """
    from submissions.constants import PHILIRIReadingLevel
    
    philiri_rows = ReadingAssessmentPHILIRI.objects.filter(
        submission__period=period,
        submission__form_template__section__code__iexact=section_code,
        submission__status__in=['submitted', 'noted', 'approved'],
        period=assessment_period
    )
    
    if not philiri_rows.exists():
        return {
            'independent_percentage': 0.0,
            'instructional_percentage': 0.0,
            'frustration_percentage': 0.0,
            'nonreader_percentage': 0.0,
            'total_learners': 0,
            'total_schools': 0
        }
    
    # Calculate totals by level
    independent_total = sum(
        row.total_learners() 
        for row in philiri_rows.filter(level=PHILIRIReadingLevel.INDEPENDENT)
    )
    instructional_total = sum(
        row.total_learners() 
        for row in philiri_rows.filter(level=PHILIRIReadingLevel.INSTRUCTIONAL)
    )
    frustration_total = sum(
        row.total_learners() 
        for row in philiri_rows.filter(level=PHILIRIReadingLevel.FRUSTRATION)
    )
    nonreader_total = sum(
        row.total_learners() 
        for row in philiri_rows.filter(level=PHILIRIReadingLevel.NON_READER)
    )
    
    total_learners = independent_total + instructional_total + frustration_total + nonreader_total
    total_schools = philiri_rows.values('submission__school').distinct().count()
    
    if total_learners == 0:
        return {
            'independent_percentage': 0.0,
            'instructional_percentage': 0.0,
            'frustration_percentage': 0.0,
            'nonreader_percentage': 0.0,
            'total_learners': 0,
            'total_schools': total_schools
        }
    
    return {
        'independent_percentage': round((independent_total / total_learners) * 100, 1),
        'instructional_percentage': round((instructional_total / total_learners) * 100, 1),
        'frustration_percentage': round((frustration_total / total_learners) * 100, 1),
        'nonreader_percentage': round((nonreader_total / total_learners) * 100, 1),
        'total_learners': total_learners,
        'total_schools': total_schools
    }


def calculate_rma_kpis(period, section_code='smme'):
    """
    Calculate RMA (Reading-Math Assessment) KPIs - Performance band distribution.
    
    Returns distribution of students across performance bands:
    - High Performers: 85-100% (bands 85-89 and 90-100)
    - Average Performers: 75-84% (bands 75-79 and 80-84)
    - Below Standard: <75% (band below 75)
    
    Args:
        period: Period object to calculate for
        section_code: Section code (default 'smme')
    
    Returns:
        dict: {
            'high_performers_percentage': float,     # 85-100%
            'average_performers_percentage': float,  # 75-84%
            'below_standard_percentage': float,      # <75%
            'band_90_100_percentage': float,
            'band_85_89_percentage': float,
            'band_80_84_percentage': float,
            'band_75_79_percentage': float,
            'band_below_75_percentage': float,
            'total_enrollment': int,
            'total_schools': int
        }
    """
    rma_rows = Form1RMARow.objects.filter(
        submission__period=period,
        submission__form_template__section__code__iexact=section_code,
        submission__status__in=['submitted', 'noted', 'approved']
    )
    
    if not rma_rows.exists():
        return {
            'high_performers_percentage': 0.0,
            'average_performers_percentage': 0.0,
            'below_standard_percentage': 0.0,
            'band_90_100_percentage': 0.0,
            'band_85_89_percentage': 0.0,
            'band_80_84_percentage': 0.0,
            'band_75_79_percentage': 0.0,
            'band_below_75_percentage': 0.0,
            'total_enrollment': 0,
            'total_schools': 0
        }
    
    # Aggregate band totals
    total_enrollment = sum(row.enrolment for row in rma_rows)
    total_below_75 = sum(row.band_below_75 for row in rma_rows)
    total_75_79 = sum(row.band_75_79 for row in rma_rows)
    total_80_84 = sum(row.band_80_84 for row in rma_rows)
    total_85_89 = sum(row.band_85_89 for row in rma_rows)
    total_90_100 = sum(row.band_90_100 for row in rma_rows)
    total_schools = rma_rows.values('submission__school').distinct().count()
    
    if total_enrollment == 0:
        return {
            'high_performers_percentage': 0.0,
            'average_performers_percentage': 0.0,
            'below_standard_percentage': 0.0,
            'band_90_100_percentage': 0.0,
            'band_85_89_percentage': 0.0,
            'band_80_84_percentage': 0.0,
            'band_75_79_percentage': 0.0,
            'band_below_75_percentage': 0.0,
            'total_enrollment': total_enrollment,
            'total_schools': total_schools
        }
    
    # Calculate grouped percentages
    high_performers = total_85_89 + total_90_100
    average_performers = total_75_79 + total_80_84
    below_standard = total_below_75
    
    return {
        'high_performers_percentage': round((high_performers / total_enrollment) * 100, 1),
        'average_performers_percentage': round((average_performers / total_enrollment) * 100, 1),
        'below_standard_percentage': round((below_standard / total_enrollment) * 100, 1),
        'band_90_100_percentage': round((total_90_100 / total_enrollment) * 100, 1),
        'band_85_89_percentage': round((total_85_89 / total_enrollment) * 100, 1),
        'band_80_84_percentage': round((total_80_84 / total_enrollment) * 100, 1),
        'band_75_79_percentage': round((total_75_79 / total_enrollment) * 100, 1),
        'band_below_75_percentage': round((total_below_75 / total_enrollment) * 100, 1),
        'total_enrollment': total_enrollment,
        'total_schools': total_schools
    }


def calculate_all_kpis_for_period(period, section_code='smme', assessment_period='baseline'):
    """
    Calculate ALL KPIs for a single period - Complete SMEA Form 1 indicators.
    
    Returns comprehensive KPI structure with all 5 categories:
    1. SLP - Student Learning Progress proficiency distribution
    2. Implementation - Action area implementation percentages
    3. CRLA - Early grade reading assessment
    4. PHILIRI - Intermediate grade reading assessment
    5. RMA - Reading-Math performance bands
    
    Args:
        period: Period object to calculate for
        section_code: Section code (default 'smme')
        assessment_period: Reading assessment period (default 'baseline')
    
    Returns:
        dict: {
            'period': Period object,
            'period_label': str,
            'slp': dict (SLP KPIs),
            'implementation': dict (Implementation KPIs),
            'crla': dict (CRLA KPIs),
            'philiri': dict (PHILIRI KPIs),
            'rma': dict (RMA KPIs)
        }
    """
    return {
        'period': period,
        'period_label': period.quarter_tag or period.label,
        'slp': calculate_slp_kpis(period, section_code),
        'implementation': calculate_implementation_kpis(period, section_code),
        'crla': calculate_crla_kpis(period, section_code, assessment_period),
        'philiri': calculate_philiri_kpis(period, section_code, assessment_period),
        'rma': calculate_rma_kpis(period, section_code),
        'supervision': calculate_supervision_kpis(period, section_code),
        'adm': calculate_adm_kpis(period, section_code)
    }


def calculate_school_kpis_simple(school, periods, section_code='smme'):
    """
    Calculate simple average KPIs for a school across multiple periods.
    Returns basic percentages for dashboard display.
    
    Args:
        school: School object
        periods: QuerySet or list of Period objects
        section_code: Section code (default 'smme')
    
    Returns:
        dict: Simple percentage averages for each KPI area
    """
    from submissions.models import Form1SLPRow, Form1PctRow
    from submissions.models import ReadingAssessmentCRLA, ReadingAssessmentPHILIRI, Form1RMARow
    from submissions.models import Form1SupervisionRow, Form1ADMHeader, Form1ADMRow
    from django.db.models import Avg, Count, Sum
    
    # Initialize totals
    kpi_totals = {
        'implementation': 0,
        'implementation_access': 0,
        'implementation_quality': 0,
        'implementation_equity': 0,
        'implementation_enabling': 0,
        'slp': 0,
        'reading_crla': 0,
        'reading_philiri': 0,
        'rma': 0,
        'supervision': 0,
        'adm': 0,
        'period_count': 0
    }
    
    has_any_data = False
    
    for period in periods:
        # Check if school has submissions for this period
        submissions = Submission.objects.filter(
            school=school,
            period=period,
            form_template__section__code__iexact=section_code
        )
        
        if submissions.exists():
            has_any_data = True
            kpi_totals['period_count'] += 1
            
            # SLP KPI - Proficiency rate (S + VS + O percentage per subject)
            slp_rows = Form1SLPRow.objects.filter(
                submission__in=submissions,
                is_offered=True  # Only count offered subjects
            )
            if slp_rows.exists():
                subject_proficiency_rates = []
                
                # Calculate proficiency rate for each SLP row (grade-subject pair)
                for row in slp_rows:
                    if row.enrolment > 0:
                        proficient_count = (row.s or 0) + (row.vs or 0) + (row.o or 0)
                        proficiency_rate = (proficient_count / row.enrolment) * 100
                        subject_proficiency_rates.append(proficiency_rate)
                
                # Average proficiency rate across all subjects
                if subject_proficiency_rates:
                    avg_proficiency = sum(subject_proficiency_rates) / len(subject_proficiency_rates)
                    kpi_totals['slp'] += avg_proficiency
            
            # Implementation KPI - average of PCT rows
            pct_rows = Form1PctRow.objects.filter(
                header__submission__in=submissions
            )
            if pct_rows.exists():
                # Compute area-specific averages
                from submissions.constants import SMEAActionArea
                access_avg = pct_rows.filter(area=SMEAActionArea.ACCESS).aggregate(avg=Avg('percent'))['avg'] or 0
                quality_avg = pct_rows.filter(area=SMEAActionArea.QUALITY).aggregate(avg=Avg('percent'))['avg'] or 0
                equity_avg = pct_rows.filter(area=SMEAActionArea.EQUITY).aggregate(avg=Avg('percent'))['avg'] or 0
                enabling_avg = pct_rows.filter(area=SMEAActionArea.ENABLING_MECHANISMS).aggregate(avg=Avg('percent'))['avg'] or 0

                # Overall implementation as mean of the four areas (if data exists)
                if any([access_avg, quality_avg, equity_avg, enabling_avg]):
                    impl_avg = (access_avg + quality_avg + equity_avg + enabling_avg) / 4
                else:
                    impl_avg = pct_rows.aggregate(avg=Avg('percent'))['avg'] or 0

                kpi_totals['implementation'] += impl_avg
                kpi_totals['implementation_access'] += access_avg
                kpi_totals['implementation_quality'] += quality_avg
                kpi_totals['implementation_equity'] += equity_avg
                kpi_totals['implementation_enabling'] += enabling_avg
            
            # Reading KPIs - updated for new CRLA model structure
            crla_rows = ReadingAssessmentCRLA.objects.filter(
                submission__in=submissions
            )
            if crla_rows.exists():
                # Calculate total learners across all grades and subjects
                total_crla = crla_rows.aggregate(
                    total=Sum('mt_grade_1') + Sum('mt_grade_2') + Sum('mt_grade_3') + 
                          Sum('fil_grade_2') + Sum('fil_grade_3') + Sum('eng_grade_3')
                )['total'] or 0
                
                # For success indicator, use the highest proficiency levels (Developing and Transitioning)
                from submissions.constants import CRLAProficiencyLevel
                high_proficiency_rows = crla_rows.filter(
                    level__in=[CRLAProficiencyLevel.DEVELOPING, CRLAProficiencyLevel.TRANSITIONING]
                )
                high_proficiency_total = high_proficiency_rows.aggregate(
                    total=Sum('mt_grade_1') + Sum('mt_grade_2') + Sum('mt_grade_3') + 
                          Sum('fil_grade_2') + Sum('fil_grade_3') + Sum('eng_grade_3')
                )['total'] or 0
                
                if total_crla > 0:
                    kpi_totals['reading_crla'] += (high_proficiency_total / total_crla) * 100
            
            philiri_rows = ReadingAssessmentPHILIRI.objects.filter(
                submission__in=submissions
            )
            if philiri_rows.exists():
                # Calculate total learners across all grades and subjects
                total_philiri = philiri_rows.aggregate(
                    total=Sum('eng_grade_4') + Sum('eng_grade_5') + Sum('eng_grade_6') + Sum('eng_grade_7') +
                          Sum('eng_grade_8') + Sum('eng_grade_9') + Sum('eng_grade_10') +
                          Sum('fil_grade_4') + Sum('fil_grade_5') + Sum('fil_grade_6') + Sum('fil_grade_7') +
                          Sum('fil_grade_8') + Sum('fil_grade_9') + Sum('fil_grade_10')
                )['total'] or 0
                
                # Use Independent level as success indicator (highest proficiency level)
                from submissions.constants import PHILIRIReadingLevel
                independent_rows = philiri_rows.filter(level=PHILIRIReadingLevel.INDEPENDENT)
                independent_total = independent_rows.aggregate(
                    total=Sum('eng_grade_4') + Sum('eng_grade_5') + Sum('eng_grade_6') + Sum('eng_grade_7') +
                          Sum('eng_grade_8') + Sum('eng_grade_9') + Sum('eng_grade_10') +
                          Sum('fil_grade_4') + Sum('fil_grade_5') + Sum('fil_grade_6') + Sum('fil_grade_7') +
                          Sum('fil_grade_8') + Sum('fil_grade_9') + Sum('fil_grade_10')
                )['total'] or 0
                
                if total_philiri > 0:
                    kpi_totals['reading_philiri'] += (independent_total / total_philiri) * 100
            
            # RMA KPI - High performance percentage (Transitioning + At Grade Level)
            rma_rows = Form1RMARow.objects.filter(
                submission__in=submissions
            )
            if rma_rows.exists():
                total_rma_learners = rma_rows.aggregate(total=Sum('enrolment'))['total'] or 0
                high_performance_rma = rma_rows.aggregate(
                    total=Sum('transitioning_proficient') + Sum('at_grade_level')
                )['total'] or 0
                if total_rma_learners > 0:
                    kpi_totals['rma'] += (high_performance_rma / total_rma_learners) * 100
            
            # Supervision KPI - Teacher supervision completion rate
            supervision_rows = Form1SupervisionRow.objects.filter(
                submission__in=submissions
            ).exclude(grade_label='')  # Exclude empty rows
            if supervision_rows.exists():
                total_supervision_entries = supervision_rows.count()
                completed_supervision = supervision_rows.exclude(
                    intervention_support_provided='',
                    result=''
                ).count()
                if total_supervision_entries > 0:
                    kpi_totals['supervision'] += (completed_supervision / total_supervision_entries) * 100
            
            # ADM KPI - Alternative Delivery Mode implementation completion rate
            adm_header_exists = Form1ADMHeader.objects.filter(
                submission__in=submissions,
                is_offered=True
            ).exists()
            
            if adm_header_exists:
                adm_rows = Form1ADMRow.objects.filter(
                    submission__in=submissions
                ).exclude(ppas_conducted='')  # Only count rows with actual data
                if adm_rows.exists():
                    adm_completion_rates = []
                    for row in adm_rows:
                        if row.ppas_physical_target > 0:
                            completion_rate = min(100, (row.ppas_physical_actual / row.ppas_physical_target) * 100)
                            adm_completion_rates.append(completion_rate)
                    
                    if adm_completion_rates:
                        avg_adm_completion = sum(adm_completion_rates) / len(adm_completion_rates)
                        kpi_totals['adm'] += avg_adm_completion
    
    # Calculate averages
    if kpi_totals['period_count'] > 0 and has_any_data:
        return {
            'implementation': round(kpi_totals['implementation'] / kpi_totals['period_count'], 1),
            'implementation_access': round(kpi_totals['implementation_access'] / kpi_totals['period_count'], 1),
            'implementation_quality': round(kpi_totals['implementation_quality'] / kpi_totals['period_count'], 1),
            'implementation_equity': round(kpi_totals['implementation_equity'] / kpi_totals['period_count'], 1),
            'implementation_enabling': round(kpi_totals['implementation_enabling'] / kpi_totals['period_count'], 1),
            'slp': round(kpi_totals['slp'] / kpi_totals['period_count'], 1),
            'reading_crla': round(kpi_totals['reading_crla'] / kpi_totals['period_count'], 1),
            'reading_philiri': round(kpi_totals['reading_philiri'] / kpi_totals['period_count'], 1),
            'rma': round(kpi_totals['rma'] / kpi_totals['period_count'], 1),
            'supervision': round(kpi_totals['supervision'] / kpi_totals['period_count'], 1),
            'adm': round(kpi_totals['adm'] / kpi_totals['period_count'], 1),
            'has_data': True
        }
    else:
        return {
            'implementation': 0,
            'implementation_access': 0,
            'implementation_quality': 0,
            'implementation_equity': 0,
            'implementation_enabling': 0,
            'slp': 0,
            'reading_crla': 0,
            'reading_philiri': 0,
            'rma': 0,
            'supervision': 0,
            'adm': 0,
            'has_data': False
        }


def calculate_supervision_kpis(period, section_code='smme'):
    """
    Calculate Instructional Supervision KPIs - From Form1SupervisionRow data.
    
    Returns supervision metrics including teacher counts and completion rates.
    
    Args:
        period: Period object to calculate for
        section_code: Section code (default 'smme')
    
    Returns:
        dict: {
            'total_teachers_supervised': int,
            'supervision_entries': int,
            'completion_rate': float,
            'total_schools': int
        }
    """
    supervision_rows = Form1SupervisionRow.objects.filter(
        submission__period=period,
        submission__form_template__section__code__iexact=section_code,
        submission__status__in=['submitted', 'noted', 'approved']
    )
    
    if not supervision_rows.exists():
        return {
            'total_teachers_supervised': 0,
            'supervision_entries': 0,
            'completion_rate': 0.0,
            'total_schools': 0
        }
    
    # Aggregate supervision data
    supervision_data = supervision_rows.aggregate(
        total_teachers_supervised=Sum('teachers_supervised_observed_ta'),
        supervision_entries=Count('id')
    )
    
    # Calculate completion rate based on filled intervention/result fields
    completed_entries = supervision_rows.exclude(
        Q(intervention_support_provided='') | Q(result='')
    ).count()
    
    completion_rate = 0.0
    if supervision_data['supervision_entries'] > 0:
        completion_rate = round(
            completed_entries / supervision_data['supervision_entries'] * 100, 1
        )
    
    total_schools = supervision_rows.values('submission__school').distinct().count()
    
    return {
        'total_teachers_supervised': supervision_data['total_teachers_supervised'] or 0,
        'supervision_entries': supervision_data['supervision_entries'] or 0,
        'completion_rate': completion_rate,
        'total_schools': total_schools
    }


def calculate_adm_kpis(period, section_code='smme'):
    """
    Calculate ADM One-Stop-Shop KPIs - From Form1ADMRow data.
    
    Returns ADM implementation and accomplishment percentages.
    
    Args:
        period: Period object to calculate for
        section_code: Section code (default 'smme')
    
    Returns:
        dict: {
            'schools_offering_adm': int,
            'physical_accomplishment_avg': float,
            'fund_utilization_avg': float,
            'overall_adm_avg': float,
            'total_schools': int
        }
    """
    # Check schools offering ADM
    adm_submissions = Submission.objects.filter(
        period=period,
        form_template__section__code__iexact=section_code,
        status__in=['submitted', 'noted', 'approved'],
        form1_adm_header__is_offered=True
    )
    
    if not adm_submissions.exists():
        return {
            'schools_offering_adm': 0,
            'physical_accomplishment_avg': 0.0,
            'fund_utilization_avg': 0.0,
            'overall_adm_avg': 0.0,
            'total_schools': 0
        }
    
    # Get ADM data from schools offering ADM
    adm_rows = Form1ADMRow.objects.filter(
        submission__in=adm_submissions
    )
    
    if not adm_rows.exists():
        return {
            'schools_offering_adm': adm_submissions.count(),
            'physical_accomplishment_avg': 0.0,
            'fund_utilization_avg': 0.0,
            'overall_adm_avg': 0.0,
            'total_schools': adm_submissions.count()
        }
    
    # Aggregate ADM data
    adm_data = adm_rows.aggregate(
        avg_physical_percent=Avg('ppas_physical_percent'),
        avg_fund_percent=Avg('funds_percent_obligated')
    )
    
    physical_avg = round(adm_data['avg_physical_percent'] or 0, 1)
    fund_avg = round(adm_data['avg_fund_percent'] or 0, 1)
    overall_avg = round((physical_avg + fund_avg) / 2, 1) if (physical_avg or fund_avg) else 0.0
    
    return {
        'schools_offering_adm': adm_submissions.count(),
        'physical_accomplishment_avg': physical_avg,
        'fund_utilization_avg': fund_avg,
        'overall_adm_avg': overall_avg,
        'total_schools': adm_submissions.count()
    }


def calculate_kpis_for_quarters(school_year, section_code='smme', assessment_period='baseline'):
    """
    Calculate KPIs for Q1, Q2, Q3, Q4 of a school year.
    
    Args:
        school_year: School year start (e.g., 2025)
        section_code: Section code (default 'smme')
        assessment_period: Reading assessment period (default 'baseline')
    
    Returns:
        list: List of KPI dictionaries for each quarter
    """
    from submissions.models import Period
    
    periods = Period.objects.filter(
        school_year_start=school_year,
        quarter_tag__in=['Q1', 'Q2', 'Q3', 'Q4'],
        is_active=True
    ).order_by('display_order')
    
    kpi_data = []
    for period in periods:
        kpis = calculate_all_kpis_for_period(period, section_code, assessment_period)
        kpi_data.append(kpis)
    
    return kpi_data


# Legacy function for backward compatibility (used by existing views)
def calculate_all_kpis(slp_rows_queryset):
    """
    Calculate basic KPIs from a filtered queryset of Form1SLPRow objects.
    
    DEPRECATED: Use calculate_all_kpis_for_period() for complete KPI structure.
    This function is kept for backward compatibility with existing views.
    
    Args:
        slp_rows_queryset: QuerySet of Form1SLPRow objects (already filtered)
    
    Returns:
        dict: Basic SLP metrics (DNME percentage only)
    """
    if not slp_rows_queryset.exists():
        return {
            'dnme': {'dnme_percentage': 0, 'dnme_count': 0, 'total_schools': 0}
        }
    
    total_schools = slp_rows_queryset.values('submission__school').distinct().count()
    total_enrollment = sum(row.enrolment for row in slp_rows_queryset)
    total_dnme = sum(row.dnme for row in slp_rows_queryset)
    
    dnme_percentage = round((total_dnme / total_enrollment * 100) if total_enrollment > 0 else 0, 1)
    
    return {
        'dnme': {
            'dnme_percentage': dnme_percentage,
            'dnme_count': int(total_dnme),
            'total_schools': total_schools
        }
    }
