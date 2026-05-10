"""
Run all tests with coverage and generate a PDF report.
Usage: python generate_test_report.py
"""
import subprocess
import sys
import os
import re
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

PYTHON = sys.executable
BACKEND = os.path.dirname(os.path.abspath(__file__))


def run_tests():
    """Run tests and capture output."""
    print("Running 261 tests across authx, detection, companion ...")
    result = subprocess.run(
        [PYTHON, '-m', 'coverage', 'run',
         '--source=authx,detection,companion',
         '--omit=*/migrations/*,*/tests/*',
         'manage.py', 'test',
         'authx.tests', 'detection.tests', 'companion.tests',
         '--verbosity=2', '--no-input'],
        capture_output=True, text=True, cwd=BACKEND
    )
    output = result.stdout + '\n' + result.stderr
    return output, result.returncode


def run_coverage_report():
    """Get coverage text report."""
    result = subprocess.run(
        [PYTHON, '-m', 'coverage', 'report', '--show-missing'],
        capture_output=True, text=True, cwd=BACKEND
    )
    return result.stdout + '\n' + result.stderr


def parse_test_lines(raw):
    """Extract individual test result lines."""
    lines = []
    for line in raw.split('\n'):
        line = line.strip()
        if not line or ' ... ' not in line:
            continue
        # Must look like "test_name (module.Class.method) ... ok"
        if not re.search(r'\.\.\.\s*(ok|FAIL|ERROR)', line):
            continue
        # Skip noise lines that happen to contain ' ... '
        if any(noise in line for noise in [
            'Loading weights', 'BertModel', 'embeddings', 'UNEXPECTED',
            'Warning:', 'Notes:', 'UserWarning', 'RuntimeWarning',
        ]):
            continue
        # Normalize: strip everything after the result word
        clean = re.sub(r'\s*(ok|FAIL|ERROR)\s*$', r' \1', line).strip()
        if clean and ' ... ' in clean:
            lines.append(clean)
    return lines


def build_pdf(test_output, coverage_output, exit_code):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, HRFlowable
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    pdf_path = os.path.join(BACKEND, '..', '..', 'Test_Coverage_Report.pdf')
    pdf_path = os.path.abspath(pdf_path)
    doc = SimpleDocTemplate(pdf_path, pagesize=A4,
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=20*mm, bottomMargin=20*mm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title2', parent=styles['Title'],
                                  fontSize=22, spaceAfter=6,
                                  textColor=colors.HexColor('#1a237e'))
    subtitle_style = ParagraphStyle('Sub', parent=styles['Normal'],
                                     fontSize=11, alignment=TA_CENTER,
                                     textColor=colors.grey, spaceAfter=20)
    heading_style = ParagraphStyle('H2', parent=styles['Heading2'],
                                    fontSize=14, spaceBefore=16, spaceAfter=8,
                                    textColor=colors.HexColor('#283593'))
    normal = styles['Normal']
    small = ParagraphStyle('Small', parent=normal, fontSize=7.5, leading=9.5)
    mono = ParagraphStyle('Mono', parent=normal, fontName='Courier', fontSize=7, leading=9)

    story = []

    # Title
    story.append(Paragraph("DementiaNext - Test & Coverage Report", title_style))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5,
                             color=colors.HexColor('#1a237e')))
    story.append(Spacer(1, 10))

    # Summary
    test_lines = parse_test_lines(test_output)
    total = len(test_lines)
    passed = sum(1 for l in test_lines if l.rstrip().endswith('ok'))
    failed = total - passed

    ran_match = re.search(r'Ran (\d+) test', test_output)
    time_match = re.search(r'in ([\d.]+)s', test_output)
    total_ran = ran_match.group(1) if ran_match else str(total)
    duration = time_match.group(1) if time_match else '—'

    cov_match = re.search(r'TOTAL\s+\d+\s+\d+\s+(\d+)%', coverage_output)
    cov_pct = cov_match.group(1) + '%' if cov_match else '—'

    status_color = colors.HexColor('#2e7d32') if failed == 0 else colors.HexColor('#c62828')
    status_text = 'ALL PASSED' if failed == 0 else f'{failed} FAILED'

    summary_data = [
        ['Total Tests', 'Passed', 'Failed', 'Duration', 'Coverage', 'Status'],
        [total_ran, str(passed), str(failed), f'{duration}s', cov_pct, status_text],
    ]
    summary_table = Table(summary_data, colWidths=[80, 70, 70, 80, 70, 90])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#283593')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#e8eaf6')),
        ('TEXTCOLOR', (5, 1), (5, 1), status_color),
        ('FONTNAME', (5, 1), (5, 1), 'Helvetica-Bold'),
        ('ROWHEIGHTS', (0, 0), (-1, -1), 28),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 16))

    # Test Results by Module
    story.append(Paragraph("Test Results by Module", heading_style))

    modules = {}
    for line in test_lines:
        parts = line.split(' ... ')
        if len(parts) == 2:
            full_name = parts[0].strip()
            result = parts[1].strip()
            # extract module: e.g. authx.tests.test_auth
            dot_parts = full_name.split('.')
            if len(dot_parts) >= 3:
                mod = '.'.join(dot_parts[:3])
            else:
                mod = full_name
            # extract just test name
            test_name = full_name.split('(')[0].strip() if '(' in full_name else full_name
            # get class.method
            if '(' in full_name:
                inner = full_name.split('(')[1].rstrip(')')
                short = inner.split('.')[-2] + '.' + inner.split('.')[-1] if '.' in inner else inner
            else:
                short = full_name.split('.')[-1]

            if mod not in modules:
                modules[mod] = []
            modules[mod].append((short, 'PASS' if 'ok' in result else 'FAIL'))

    for mod, tests in modules.items():
        mod_passed = sum(1 for _, r in tests if r == 'PASS')
        mod_total = len(tests)
        story.append(Paragraph(
            f"<b>{mod}</b> — {mod_passed}/{mod_total} passed", normal))
        story.append(Spacer(1, 4))

        tdata = [['#', 'Test Case', 'Result']]
        for i, (name, res) in enumerate(tests, 1):
            tdata.append([str(i), name, res])

        t = Table(tdata, colWidths=[25, 370, 55])
        row_colors = []
        for i in range(1, len(tdata)):
            bg = colors.HexColor('#e8f5e9') if tdata[i][2] == 'PASS' else colors.HexColor('#ffebee')
            row_colors.append(('BACKGROUND', (0, i), (-1, i), bg))

        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#37474f')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7.5),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#bdbdbd')),
            ('ROWHEIGHTS', (0, 0), (-1, -1), 16),
        ] + row_colors))
        story.append(t)
        story.append(Spacer(1, 10))

    # Coverage Report
    story.append(PageBreak())
    story.append(Paragraph("Code Coverage Report", heading_style))
    story.append(Spacer(1, 6))

    cov_lines = coverage_output.strip().split('\n')
    cov_data = []
    for line in cov_lines:
        if line.startswith('Name') or line.startswith('TOTAL') or (line and not line.startswith('-') and '%' in line):
            cols = line.split()
            if len(cols) >= 4:
                name = cols[0]
                stmts = cols[1]
                miss = cols[2]
                cover = cols[3]
                missing = ' '.join(cols[4:]) if len(cols) > 4 else ''
                cov_data.append([name, stmts, miss, cover, missing])

    if cov_data:
        cov_table_data = [['File', 'Stmts', 'Miss', 'Cover', 'Missing Lines']]
        for row in cov_data:
            cov_table_data.append(row)

        ct = Table(cov_table_data, colWidths=[150, 45, 40, 50, 175])
        cov_row_styles = []
        for i in range(1, len(cov_table_data)):
            pct_str = cov_table_data[i][3].replace('%', '')
            try:
                pct = int(pct_str)
                if pct >= 80:
                    bg = colors.HexColor('#e8f5e9')
                elif pct >= 50:
                    bg = colors.HexColor('#fff8e1')
                else:
                    bg = colors.HexColor('#ffebee')
            except ValueError:
                bg = colors.white
            cov_row_styles.append(('BACKGROUND', (0, i), (-1, i), bg))
            if cov_table_data[i][0] == 'TOTAL':
                cov_row_styles.append(('FONTNAME', (0, i), (-1, i), 'Helvetica-Bold'))
                cov_row_styles.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#e3f2fd')))

        ct.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#283593')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('ALIGN', (1, 0), (3, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#bdbdbd')),
            ('ROWHEIGHTS', (0, 0), (-1, -1), 15),
        ] + cov_row_styles))
        story.append(ct)

    # Footer
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"DementiaNext Backend Test Report — Django + DRF — "
        f"{datetime.now().strftime('%Y-%m-%d')}", 
        ParagraphStyle('Footer', parent=normal, fontSize=8,
                        alignment=TA_CENTER, textColor=colors.grey)))

    doc.build(story)
    return pdf_path


if __name__ == '__main__':
    print("=" * 60)
    print("  DementiaNext Test & Coverage Report Generator")
    print("=" * 60)

    test_output, exit_code = run_tests()
    print("Tests completed.")

    print("Generating coverage report ...")
    coverage_output = run_coverage_report()
    print(coverage_output)

    print("Building PDF ...")
    pdf_path = build_pdf(test_output, coverage_output, exit_code)
    print(f"\nPDF saved to: {pdf_path}")
    print("Done!")
