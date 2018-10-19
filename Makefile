build_dir := build
report := $(build_dir)/report.pdf
bibstyle := ieee.csl

default: $(report)

$(build_dir):
	mkdir -p $(build_dir)

$(report): $(build_dir)

$(build_dir)/%.pdf : %.md
	pandoc --include-in-header header.tex --toc --template tufte-template.tex --filter pandocCommentFilter.py --filter pandoc-citeproc --csl $(bibstyle) -s $< -o $@

$(build_dir)/%.png : %.svg
	inkscape --export-png=$@ --export-dpi=300 $<

clean: $(build_dir)
	rm $(build_dir)/*

