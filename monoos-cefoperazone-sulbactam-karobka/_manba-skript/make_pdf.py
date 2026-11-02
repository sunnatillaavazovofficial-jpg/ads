"""SVG -> vektor PDF (aniq mm o'lchamda). Ishlatish: python3 make_pdf.py <papka>"""
import glob
import os
import sys

import cairosvg

for f in sorted(glob.glob(os.path.join(sys.argv[1], "**", "*.svg"), recursive=True)):
    cairosvg.svg2pdf(url=f, write_to=f[:-4] + ".pdf")
    print("pdf:", os.path.relpath(f, sys.argv[1]))
