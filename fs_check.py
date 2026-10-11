# -*- coding: utf-8 -*-
import os, io

out = io.open(r"E:\0\fs_check.txt", "w", encoding="utf-8")
def listdir(path):
    out.write("=== %s ===\n" % path)
    try:
        names = sorted(os.listdir(path))
    except Exception as e:
        out.write("ERROR: %r\n" % e)
        return
    for n in names:
        full = os.path.join(path, n)
        try:
            sz = os.path.getsize(full) if os.path.isfile(full) else "<dir>"
        except Exception:
            sz = "?"
        out.write(repr(n) + " | " + str(sz) + "\n")
    out.write("\n")

listdir(r"E:\0")
listdir(r"C:\Users\ASUS\Desktop")
listdir(r"C:\Users\ASUS\Desktop\桌面简历")
out.close()
print("done")
