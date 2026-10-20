"""Create a clearly synthetic, redistributable PDF to exercise the reader."""
from pathlib import Path
import pymupdf as fitz

root=Path(__file__).resolve().parent
doc=fitz.open();page=doc.new_page()
page.insert_text((55,65),'SYNTHETIC READING DEMO - NOT A RESEARCH PAPER',fontsize=14)
page.insert_text((55,110),'This is a unique sentence for evidence matching.',fontsize=12)
page.insert_text((55,150),'This document demonstrates evidence links and annotations only.',fontsize=11)
doc.save(root/'demo.pdf');doc.close()
print(root/'demo.pdf')
