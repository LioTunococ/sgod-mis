from django.db import migrations, models


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
        ("specialized_track", "Specialized / Strand Subject"),
    ],
    12: [
        ("practical_research", "Practical Research / Research in Daily Life"),
        ("inquiries_investigations", "Inquiries, Investigations, and Immersion"),
        ("work_immersion", "Work Immersion / Apprenticeship"),
        ("media_information_literacy", "Media and Information Literacy"),
        ("personal_development", "Personal Development"),
        ("specialized_track", "Specialized / Strand Subject"),
    ],
}


def _label_to_number():
    return {label: number for number, label in GRADE_NUMBER_TO_LABEL.items()}


def _subjects_for_label(label):
    number = _label_to_number().get(label)
    subjects = SLP_SUBJECTS_BY_GRADE.get(number)
    if subjects:
        return subjects
    return [SLP_DEFAULT_SUBJECT]


def forwards(apps, schema_editor):
    Form1SLPRow = apps.get_model("submissions", "Form1SLPRow")
    Submission = apps.get_model("submissions", "Submission")

    label_map = _label_to_number()

    for submission in Submission.objects.all().iterator():
        rows = list(Form1SLPRow.objects.filter(submission=submission))
        for row in rows:
            subjects = SLP_SUBJECTS_BY_GRADE.get(label_map.get(row.grade_label), [SLP_DEFAULT_SUBJECT])
            # delete existing row once replacements are created
            for subject_code, _ in subjects:
                Form1SLPRow.objects.create(
                    submission=submission,
                    grade_label=row.grade_label,
                    subject=subject_code,
                    enrolment=0,
                    dnme=0,
                    fs=0,
                    s=0,
                    vs=0,
                    o=0,
                    is_offered=True,
                    top_three_llc="",
                    intervention_plan="",
                )
            row.delete()


def backwards(apps, schema_editor):
    Form1SLPRow = apps.get_model("submissions", "Form1SLPRow")
    Submission = apps.get_model("submissions", "Submission")

    for submission in Submission.objects.all().iterator():
        grouped = {}
        for row in Form1SLPRow.objects.filter(submission=submission):
            grouped.setdefault(row.grade_label, row)
        Form1SLPRow.objects.filter(submission=submission).delete()
        for grade_label, original in grouped.items():
            Form1SLPRow.objects.create(
                submission=submission,
                grade_label=grade_label,
                subject=SLP_DEFAULT_SUBJECT[0],
                enrolment=original.enrolment,
                dnme=original.dnme,
                fs=original.fs,
                s=original.s,
                vs=original.vs,
                o=original.o,
                is_offered=True,
                top_three_llc=original.top_three_llc,
                intervention_plan=original.intervention_plan,
            )


class Migration(migrations.Migration):

    dependencies = [
        ("submissions", "0006_submissiontimeline"),
    ]

    operations = [
        migrations.AddField(
            model_name="form1slprow",
            name="subject",
            field=models.CharField(blank=True, default="overall", max_length=64),
        ),
        migrations.AddField(
            model_name="form1slprow",
            name="is_offered",
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(forwards, backwards),
        migrations.AlterModelOptions(
            name="form1slprow",
            options={"ordering": ["grade_label", "subject"]},
        ),
        migrations.AlterUniqueTogether(
            name="form1slprow",
            unique_together={("submission", "grade_label", "subject")},
        ),
    ]
