build_dir := build
excluded := README.md

sources := $(filter-out $(excluded),$(wildcard *.md))
letters = $(addprefix $(build_dir)/,$(sources:.md=.pdf))

.PHONY: default
default: $(letters)

$(build_dir)/:
	mkdir -p $@

$(build_dir)/letterhead.pdf: letterhead.tex | $(build_dir)/
	cp letterhead.tex $(build_dir)
	cd $(build_dir) && xelatex $<

$(letters): $(build_dir)/%.pdf : %.md | $(build_dir)/letterhead.pdf template.tex
	# See https://pandoc.org/MANUAL.html#extensions for a list of extensions
	pandoc --pdf-engine=xelatex \
	       --template template.tex \
	       -s -o $@ $<

# Add the build directory as an order only prerequisite
$(foreach letter,$(letters),$(eval $(letter): | $(dir $(report))))

clean: $(build_dir)
	rm -rf $(build_dir)
