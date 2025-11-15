from __future__ import annotations

from django.utils.translation import gettext_lazy as _


GRADE_NUMBER_TO_LABEL = {
    0: "Kinder",
    1: "Grade 1",
    2: "Grade 2",
    3: "Grade 3",
    4: "Grade 4",
    5: "Grade 5",
    6: "Grade 6",
    7: "Grade 7",
    8: "Grade 8",
    9: "Grade 9",
    10: "Grade 10",
    11: "Grade 11",
    12: "Grade 12",
}

GRADE_LABEL_TO_NUMBER = {label: number for number, label in GRADE_NUMBER_TO_LABEL.items()}

RMA_GRADE_LABEL_FOR_NUMBER = {
    0: "k",
    1: "g1",
    2: "g2",
    3: "g3",
    4: "g4",
    5: "g5",
    6: "g6",
    7: "g7",
    8: "g8",
    9: "g9",
    10: "g10",
}

SLP_DEFAULT_SUBJECT = ("overall", "Overall Progress")

SLP_SUBJECTS_BY_GRADE = {
    0: [
        ("mother_tongue", "Mother Tongue"),
        ("filipino", "Filipino"),
        ("english", "English"),
        ("mathematics", "Mathematics"),
        ("araling_panlipunan", "Araling Panlipunan"),
        ("mapeh", "MAPEH"),
        ("esp", "Edukasyon sa Pagpapakatao"),
    ],
    1: [
        ("mother_tongue", "Mother Tongue"),
        ("filipino", "Filipino"),
        ("english", "English"),
        ("mathematics", "Mathematics"),
        ("araling_panlipunan", "Araling Panlipunan"),
        ("mapeh", "MAPEH"),
        ("esp", "Edukasyon sa Pagpapakatao"),
    ],
    2: [
        ("mother_tongue", "Mother Tongue"),
        ("filipino", "Filipino"),
        ("english", "English"),
        ("mathematics", "Mathematics"),
        ("araling_panlipunan", "Araling Panlipunan"),
        ("mapeh", "MAPEH"),
        ("esp", "Edukasyon sa Pagpapakatao"),
    ],
    3: [
        ("mother_tongue", "Mother Tongue"),
        ("filipino", "Filipino"),
        ("english", "English"),
        ("mathematics", "Mathematics"),
        ("science", "Science"),
        ("araling_panlipunan", "Araling Panlipunan"),
        ("mapeh", "MAPEH"),
        ("esp", "Edukasyon sa Pagpapakatao"),
    ],
    4: [
        ("filipino", "Filipino"),
        ("english", "English"),
        ("mathematics", "Mathematics"),
        ("science", "Science"),
        ("araling_panlipunan", "Araling Panlipunan"),
        ("mapeh", "MAPEH"),
        ("esp", "Edukasyon sa Pagpapakatao"),
        ("epp", "Edukasyong Pantahanan at Pangkabuhayan"),
    ],
    5: [
        ("filipino", "Filipino"),
        ("english", "English"),
        ("mathematics", "Mathematics"),
        ("science", "Science"),
        ("araling_panlipunan", "Araling Panlipunan"),
        ("mapeh", "MAPEH"),
        ("esp", "Edukasyon sa Pagpapakatao"),
        ("epp", "Edukasyong Pantahanan at Pangkabuhayan"),
    ],
    6: [
        ("filipino", "Filipino"),
        ("english", "English"),
        ("mathematics", "Mathematics"),
        ("science", "Science"),
        ("araling_panlipunan", "Araling Panlipunan"),
        ("mapeh", "MAPEH"),
        ("esp", "Edukasyon sa Pagpapakatao"),
        ("tle", "Technology and Livelihood Education"),
    ],
    7: [
        ("filipino", "Filipino"),
        ("english", "English"),
        ("mathematics", "Mathematics"),
        ("science", "Science"),
        ("araling_panlipunan", "Araling Panlipunan"),
        ("mapeh", "MAPEH"),
        ("esp", "Edukasyon sa Pagpapakatao"),
        ("tle", "Technology and Livelihood Education"),
    ],
    8: [
        ("filipino", "Filipino"),
        ("english", "English"),
        ("mathematics", "Mathematics"),
        ("science", "Science"),
        ("araling_panlipunan", "Araling Panlipunan"),
        ("mapeh", "MAPEH"),
        ("esp", "Edukasyon sa Pagpapakatao"),
        ("tle", "Technology and Livelihood Education"),
    ],
    9: [
        ("filipino", "Filipino"),
        ("english", "English"),
        ("mathematics", "Mathematics"),
        ("science", "Science"),
        ("araling_panlipunan", "Araling Panlipunan"),
        ("mapeh", "MAPEH"),
        ("esp", "Edukasyon sa Pagpapakatao"),
        ("tle", "Technology and Livelihood Education"),
    ],
    10: [
        ("filipino", "Filipino"),
        ("english", "English"),
        ("mathematics", "Mathematics"),
        ("science", "Science"),
        ("araling_panlipunan", "Araling Panlipunan"),
        ("mapeh", "MAPEH"),
        ("esp", "Edukasyon sa Pagpapakatao"),
        ("tle", "Technology and Livelihood Education"),
    ],
    11: [
        ("oral_communication", "Oral Communication"),
        ("reading_and_writing", "Reading and Writing"),
        ("komunikasyon", "Komunikasyon at Pananaliksik"),
        ("pagbasa", "Pagbasa at Pagsusuri"),
        ("literature21", "21st Century Literature"),
        ("arts_from_regions", "Contemporary Philippine Arts"),
        ("media_information_literacy", "Media and Information Literacy"),
        ("general_mathematics", "General Mathematics"),
        ("statistics_probability", "Statistics and Probability"),
        ("earth_life_science", "Earth and Life Science"),
        ("physical_science", "Physical Science"),
        ("personal_development", "Personal Development"),
        ("ucsp", "Understanding Culture, Society, and Politics"),
        ("philosophy", "Introduction to Philosophy"),
        ("pe_health", "Physical Education and Health"),
        # Specialized subjects by strand (Grade 11)
        # STEM
        ("stem_pre_calculus", "STEM: Pre-Calculus"),
        ("stem_basic_calculus", "STEM: Basic Calculus"),
        ("stem_gen_biology_1", "STEM: General Biology 1"),
        ("stem_gen_physics_1", "STEM: General Physics 1"),
        ("stem_gen_chemistry_1", "STEM: General Chemistry 1"),
        # ABM
        ("abm_applied_economics", "ABM: Applied Economics"),
        ("abm_business_ethics", "ABM: Business Ethics and Social Responsibility"),
        ("abm_fabm1", "ABM: Fundamentals of Accountancy, Business and Management 1"),
        ("abm_business_math", "ABM: Business Math"),
        ("abm_business_finance", "ABM: Business Finance"),
        ("abm_org_and_mgmt", "ABM: Organization and Management"),
        ("abm_marketing", "ABM: Principles of Marketing"),
        # HUMSS
        ("humss_creative_writing", "HUMSS: Creative Writing"),
        ("humss_creative_nonfiction", "HUMSS: Creative Nonfiction"),
        ("humss_world_religions", "HUMSS: World Religions and Belief Systems"),
        ("humss_tnct", "HUMSS: Trends, Networks, and Critical Thinking"),
        ("humss_philippine_politics", "HUMSS: Philippine Politics and Governance"),
        ("humss_diss", "HUMSS: Disciplines and Ideas in the Social Sciences"),
        ("humss_diams", "HUMSS: Disciplines and Ideas in the Applied Social Sciences"),
        # GAS
        ("gas_humanities_1", "GAS: Humanities 1"),
        ("gas_social_science_1", "GAS: Social Science 1"),
        ("gas_applied_economics", "GAS: Applied Economics"),
        ("gas_organization_management", "GAS: Organization and Management"),
        ("gas_drr", "GAS: Disaster Readiness and Risk Reduction"),
        # TVL - ICT
        ("tvl_ict_css", "TVL-ICT: Computer Systems Servicing"),
        ("tvl_ict_programming", "TVL-ICT: Programming"),
        ("tvl_ict_animation", "TVL-ICT: Animation"),
        ("tvl_ict_illustration", "TVL-ICT: Illustration"),
        # TVL - HE
        ("tvl_he_cookery", "TVL-HE: Cookery"),
        ("tvl_he_bpp", "TVL-HE: Bread and Pastry Production"),
        ("tvl_he_housekeeping", "TVL-HE: Housekeeping"),
        ("tvl_he_fbs", "TVL-HE: Food and Beverage Services"),
        # TVL - IA
        ("tvl_ia_smaw", "TVL-IA: Shielded Metal Arc Welding"),
        ("tvl_ia_eim", "TVL-IA: Electrical Installation and Maintenance"),
        ("tvl_ia_carpentry", "TVL-IA: Carpentry"),
        ("tvl_ia_plumbing", "TVL-IA: Plumbing"),
        # TVL - Agri-Fishery
        ("tvl_agri_crop_production", "TVL-Agri-Fishery: Crop Production"),
        ("tvl_agri_animal_production", "TVL-Agri-Fishery: Animal Production"),
        ("tvl_agri_fish_processing", "TVL-Agri-Fishery: Fish Processing"),
        ("tvl_agri_aquaculture", "TVL-Agri-Fishery: Aquaculture"),
        # Arts & Design
        ("ad_creative_industries", "Arts & Design: Creative Industries"),
        ("ad_media_arts", "Arts & Design: Media Arts"),
        ("ad_visual_arts", "Arts & Design: Visual Arts"),
        ("ad_performing_arts", "Arts & Design: Performing Arts"),
        # Sports
        ("sports_physical_fitness", "Sports: Physical Fitness"),
        ("sports_fitness_testing", "Sports: Fitness Testing"),
        ("sports_officiating", "Sports: Sports Officiating"),
        ("sports_coaching", "Sports: Coaching"),
        ("sports_safety_first_aid", "Sports: Safety and First Aid"),
    ],
    12: [
        ("practical_research", "Practical Research / Research in Daily Life"),
        ("inquiries_investigations", "Inquiries, Investigations, and Immersion"),
        ("work_immersion", "Work Immersion / Apprenticeship"),
        ("media_information_literacy", "Media and Information Literacy"),
        ("personal_development", "Personal Development"),
        # Specialized subjects by strand (Grade 12)
        # STEM
        ("stem_gen_biology_2", "STEM: General Biology 2"),
        ("stem_gen_physics_2", "STEM: General Physics 2"),
        ("stem_gen_chemistry_2", "STEM: General Chemistry 2"),
        # ABM
        ("abm_fabm2", "ABM: Fundamentals of Accountancy, Business and Management 2"),
        # HUMSS
        ("humss_community_engagement", "HUMSS: Community Engagement, Solidarity and Citizenship"),
        # GAS
        ("gas_humanities_2", "GAS: Humanities 2"),
        ("gas_social_science_2", "GAS: Social Science 2"),
        # TVL - ICT
        ("tvl_ict_desktop_publishing", "TVL-ICT: Desktop Publishing"),
        ("tvl_ict_broadband", "TVL-ICT: Broadband Installation"),
        # TVL - HE
        ("tvl_he_tourism", "TVL-HE: Tourism Promotion Services"),
        ("tvl_he_front_office", "TVL-HE: Front Office Services"),
        # TVL - IA
        ("tvl_ia_drafting", "TVL-IA: Drafting"),
        ("tvl_ia_mechanics", "TVL-IA: Automotive Servicing"),
        # TVL - Agri-Fishery
        ("tvl_agri_organic_agriculture", "TVL-Agri-Fishery: Organic Agriculture"),
        ("tvl_agri_farm_business", "TVL-Agri-Fishery: Farm Business Management"),
        # Arts & Design
        ("ad_creative_industries_2", "Arts & Design: Creative Industries 2"),
        ("ad_performing_arts_2", "Arts & Design: Performing Arts 2"),
        # Sports
        ("sports_psychology", "Sports: Sports Psychology"),
        ("sports_leadership", "Sports: Sports Leadership and Management"),
    ],
}

SLP_SUBJECT_LABELS = {SLP_DEFAULT_SUBJECT[0]: SLP_DEFAULT_SUBJECT[1]}
for _subjects in SLP_SUBJECTS_BY_GRADE.values():
    for code, label in _subjects:
        SLP_SUBJECT_LABELS.setdefault(code, label)


# SHS strand definitions for bulk actions and display ordering
SHS_STRANDS = [
    ("stem", "STEM", "stem_"),
    ("abm", "ABM", "abm_"),
    ("humss", "HUMSS", "humss_"),
    ("gas", "GAS", "gas_"),
    ("tvl_ict", "TVL-ICT", "tvl_ict_"),
    ("tvl_he", "TVL-HE", "tvl_he_"),
    ("tvl_ia", "TVL-IA", "tvl_ia_"),
    ("tvl_agri", "TVL-Agri-Fishery", "tvl_agri_"),
    ("arts", "Arts & Design", "ad_"),
    ("sports", "Sports", "sports_"),
]


class SMEAActionArea:
    ACCESS = "access"
    QUALITY = "quality"
    EQUITY = "equity"
    ENABLING_MECHANISMS = "enabling_mechanisms"

    CHOICES = (
        (ACCESS, _("Access")),
        (QUALITY, _("Quality")),
        (EQUITY, _("Equity")),
        (ENABLING_MECHANISMS, _("Enabling Mechanisms")),
    )


class CRLALevel:
    GRADE1 = "g1"
    GRADE2 = "g2"
    GRADE3 = "g3"
    GRADE4 = "g4"
    GRADE5 = "g5"
    GRADE6 = "g6"

    CHOICES = (
        (GRADE1, _("Grade 1")),
        (GRADE2, _("Grade 2")),
        (GRADE3, _("Grade 3")),
        (GRADE4, _("Grade 4")),
        (GRADE5, _("Grade 5")),
        (GRADE6, _("Grade 6")),
    )


class CRLATiming:
    BOY = "boy"
    MOY = "moy"
    EOY = "eoy"

    CHOICES = (
        (BOY, _("Beginning of Year")),
        (MOY, _("Middle of Year")),
        (EOY, _("End of Year")),
    )


class CRLASubject:
    ENGLISH = "english"
    FILIPINO = "filipino"
    MOTHER_TONGUE = "mother_tongue"

    CHOICES = (
        (ENGLISH, _("English")),
        (FILIPINO, _("Filipino")),
        (MOTHER_TONGUE, _("Mother Tongue")),
    )


class CRLABand:
    FRUSTRATION = "frustration"
    INSTRUCTIONAL = "instructional"
    INDEPENDENT = "independent"

    CHOICES = (
        (FRUSTRATION, _("Frustration")),
        (INSTRUCTIONAL, _("Instructional")),
        (INDEPENDENT, _("Independent")),
    )


class PHILIRILanguage:
    ENGLISH = "english"
    FILIPINO = "filipino"
    ILOKANO = "ilokano"
    OTHERS = "others"

    CHOICES = (
        (ENGLISH, _("English")),
        (FILIPINO, _("Filipino")),
        (ILOKANO, _("Ilokano")),
        (OTHERS, _("Others")),
    )


class AssessmentTiming:
    BOY = "boy"
    MOY = "moy"
    EOY = "eoy"

    CHOICES = (
        (BOY, _("Beginning of Year")),
        (MOY, _("Middle of Year")),
        (EOY, _("End of Year")),
    )


class RMAGradeLabel:
    KINDER = "k"
    GRADE1 = "g1"
    GRADE2 = "g2"
    GRADE3 = "g3"
    GRADE4 = "g4"
    GRADE5 = "g5"
    GRADE6 = "g6"
    GRADE7 = "g7"
    GRADE8 = "g8"
    GRADE9 = "g9"
    GRADE10 = "g10"

    CHOICES = (
        (KINDER, _("Kinder")),
        (GRADE1, _("Grade 1")),
        (GRADE2, _("Grade 2")),
        (GRADE3, _("Grade 3")),
        (GRADE4, _("Grade 4")),
        (GRADE5, _("Grade 5")),
        (GRADE6, _("Grade 6")),
        (GRADE7, _("Grade 7")),
        (GRADE8, _("Grade 8")),
        (GRADE9, _("Grade 9")),
        (GRADE10, _("Grade 10")),
    )


# New CRLA Proficiency Levels (2025-26)
class CRLAProficiencyLevel:
    LOW_EMERGING = "low_emerging"
    HIGH_EMERGING = "high_emerging"
    DEVELOPING = "developing"
    TRANSITIONING = "transitioning"

    CHOICES = (
        (LOW_EMERGING, _("Low Emerging")),
        (HIGH_EMERGING, _("High Emerging")),
        (DEVELOPING, _("Developing")),
        (TRANSITIONING, _("Transitioning")),
    )


# New Assessment Period (BOSY, MOSY, EOSY)
class AssessmentPeriod:
    BOSY = "bosy"
    MOSY = "mosy"
    EOSY = "eosy"

    CHOICES = (
        (BOSY, _("BOSY (Beginning of School Year)")),
        (MOSY, _("MOSY (Middle of School Year)")),
        (EOSY, _("EOSY (End of School Year)")),
    )


# PHILIRI Reading Levels
class PHILIRIReadingLevel:
    FRUSTRATION = "frustration"
    INSTRUCTIONAL = "instructional"
    INDEPENDENT = "independent"

    CHOICES = (
        (FRUSTRATION, _("Frustration")),
        (INSTRUCTIONAL, _("Instructional")),
        (INDEPENDENT, _("Independent")),
    )
