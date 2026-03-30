import subprocess
result = subprocess.run(["git", "push", "origin", "HEAD:main", "-f"], capture_output=True, text=True)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
