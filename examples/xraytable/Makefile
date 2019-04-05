# Makefile for xray periodic table

TARGET = xray_table

.PHONY: pdf clean distclean

pdf:
	make $(TARGET).pdf

atoms.tex:  gen_atoms.py
	python gen_atoms.py > atoms.tex

$(TARGET).pdf: atoms.tex $(TARGET).tex elines.tex
	pdflatex $(TARGET)

clean:
	rm -f *.log *.aux *.pyc *.synctex.gz

distclean:
	make clean
	rm -f $(TARGET).pdf atoms.tex
