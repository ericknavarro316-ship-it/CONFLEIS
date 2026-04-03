import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace applymap with map
content = content.replace('.style.applymap(', '.style.map(')

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
