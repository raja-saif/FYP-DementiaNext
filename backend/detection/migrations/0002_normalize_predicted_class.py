from django.db import migrations


def normalize_predicted_class(apps, schema_editor):
    DetectionResult = apps.get_model('detection', 'DetectionResult')
    FHIRDiagnosticReport = apps.get_model('detection', 'FHIRDiagnosticReport')

    mapping = {
        "Alzheimer's Disease (AD)": 'alzheimers',
        "Alzheimer's": 'alzheimers',
        'AD': 'alzheimers',
        'Alzheimers': 'alzheimers',
        'Alzheimers Disease': 'alzheimers',
        'alzheimers': 'alzheimers',
        'Alzheimer\'s Disease': 'alzheimers',
        'Control (CN)': 'cn',
        'CN': 'cn',
        'Control': 'cn',
        'Normal': 'cn',
        'normal': 'cn',
        'cn': 'cn'
    }

    # Normalize DetectionResult.predicted_class values
    for det in DetectionResult.objects.all():
        current = det.predicted_class
        if not current:
            continue
        key = mapping.get(current)
        if not key:
            # Try lowercase start match
            lc = current.lower()
            if 'alz' in lc:
                key = 'alzheimers'
            elif 'cn' in lc or 'control' in lc or 'normal' in lc:
                key = 'cn'
        if key and det.predicted_class != key:
            det.predicted_class = key
            det.save()

    # Regenerate FHIR report JSON for all existing reports, to ensure conclusions/codes are aligned with normalized detection values
    for report in FHIRDiagnosticReport.objects.all():
        try:
            # Regenerate JSON with current values
            report.generate_fhir_json()
            report.save()
        except Exception:
            # Skip problematic ones but log if needed
            continue


class Migration(migrations.Migration):

    dependencies = [
        ('detection', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(normalize_predicted_class),
    ]
