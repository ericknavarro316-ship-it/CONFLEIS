import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# I see that I deleted the lines 1878 to 2183, which probably contained
# the "Notificaciones a Clientes" module which was misplaced under elif seleccion == "Control de Honorarios":
