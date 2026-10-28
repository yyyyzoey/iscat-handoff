import sys
sys.path.insert(0, r"C:\iscat\v165\tools\v165_bundle\code")
sys.path.insert(0, r"C:\iscat\v165\tools")
from v165_io import archive_check, sha
r = archive_check(r"C:\iscat\v165\results\v164\iscat_v164_return.zip")
print(r)
print("external receipt sha match:", r["sha256"] == "3191f1d5600dd68d464f471480472946147910c0ce0865e7d0b030a134f73dd7")
