build_dir := build
excluded := README.md
sources := $(filter-out $(excluded),$(wildcard *.md))
reports = $(addprefix $(build_dir)/,$(sources:.md=.pdf))
vector_images = $(wildcard *.svg)
images := $(addprefix $(build_dir)/,$(vector_images:.svg=.png))
static := static
bin := bin

# Look up your bibliography style at https://www.zotero.org/styles
# Download the CSL file to the static directory and modify `bibstyle`
# below
bibstyle := ieee-with-url.csl

.PHONY: default
default: $(reports)

$(build_dir)/:
	mkdir -p $@

$(reports): $(build_dir)/%.pdf : %.md | $(images)
	# See https://pandoc.org/MANUAL.html#extensions for a list of extensions
	# To disable TOC comment out --toc
	# To disable Bibliography comment the line containing pandoc-citeproc
	pandoc --from markdown+implicit_figures \
	       --template $(static)/tufte-template.tex \
	       --filter $(bin)/pandocCommentFilter.py \
	       --include-in-header $(static)/header.tex \
	       --toc \
	       --filter pandoc-citeproc --csl $(static)/$(bibstyle) \
	       -s -o $@ $<

$(images): $(build_dir)/%.png : %.svg
	-inkscape --export-png=$@ --export-dpi=300 $<

# Add the build directory as an order only prerequisite
$(foreach report,$(reports),$(eval $(report): | $(dir $(report))))
$(foreach image,$(images),$(eval $(image): | $(dir $(image))))

clean: $(build_dir)
	rm -rf $(build_dir)
