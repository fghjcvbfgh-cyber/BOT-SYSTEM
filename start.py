import subprocess
import sys

subprocess.Popen([sys.executable, "main_bot.py"])
subprocess.Popen([sys.executable, "protection_bot.py"])
subprocess.Popen([sys.executable, "ticket_roles_bot.py"])

# خلّ الملف يشتغل
import time
while True:
    time.sleep(60)
