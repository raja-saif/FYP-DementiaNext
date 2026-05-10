import subprocess, sys, os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

result = subprocess.run(
    [sys.executable, '-m', 'coverage', 'run',
     '--source=authx,detection,companion',
     '--omit=*/migrations/*,*/tests/*',
     'manage.py', 'test',
     'authx.tests', 'detection.tests', 'companion.tests',
     '--verbosity=2', '--no-input'],
    capture_output=True, text=True, timeout=1200
)

with open(r'c:\Users\iba\Downloads\FinalVer\test_output.txt', 'w', encoding='utf-8') as f:
    f.write("=== STDOUT ===\n")
    f.write(result.stdout)
    f.write("\n=== STDERR ===\n")
    f.write(result.stderr)
    f.write(f"\n=== EXIT CODE: {result.returncode} ===\n")

print(f"Exit code: {result.returncode}")
print("Output written to test_output.txt")

cov = subprocess.run(
    [sys.executable, '-m', 'coverage', 'report', '--show-missing'],
    capture_output=True, text=True
)
with open(r'c:\Users\iba\Downloads\FinalVer\coverage_output.txt', 'w', encoding='utf-8') as f:
    f.write(cov.stdout)
    f.write(cov.stderr)

print("Coverage written to coverage_output.txt")
