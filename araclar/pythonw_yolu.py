import os
import sys

klasor = os.path.dirname(sys.executable)
yol = os.path.join(klasor, "pythonw.exe")
print(yol if os.path.exists(yol) else sys.executable)
