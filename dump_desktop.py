# -*- coding: utf-8 -*-
import io, os
from docx import Document

def dump(path, label):
    out.write("\n========== %s ==========\n" % label)
    out.write("size=%s\n" % os.path.getsize(path))
    d = Document(path)
    for i, p in enumerate(d.paragraphs):
        out.write("[%d] %s\n" % (i, p.text))

out = io.open(r"E:\0\docx_dump.txt", "w", encoding="utf-8")
dump(r"C:\Users\ASUS\Desktop\桌面简历\策划简历.docx", "策划简历.docx (NEW)")
dump(r"C:\Users\ASUS\Desktop\桌面简历\技术策划简历_旧版.docx", "技术策划简历_旧版.docx (backup)")
out.close()
print("done")
