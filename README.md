# BIDS Pandoc Templates

You need [Pandoc](https://pandoc.org/installing.html) and LaTeX
installed.  If you want to compile SVG diagrams, you'll also need
Inkscape.

## Report

Change into `report` and type `make`.  The result is in
`build/report.pdf`.

Here is [an example build](https://github.com/BIDS/pandoc-report/blob/build/build/report.pdf).

The report is derived
from [this template](https://github.com/jez/pandoc-starter) which is
[MIT licensed](https://jez.io/MIT-LICENSE.txt).

### Adding your own report

Copy `report.md` to `my_report.md` (or whatever you want to call it).
The `make` command will now also produce your report in
`build/my_report.pdf`.

### Vector graphics

All `.svg` images (Inkscape graphics) gets converted to PNG files in
the `build/` folder.  Those images can then be used in the document,
e.g.

```
![My Image Description](build/my_image.png)
```

## Letter

The letter template works very much like the report.  Any custom
adjustments can be made to `static/tufte_template.tex`.  It is derived
from [this template](https://github.com/mrzool/letter-boilerplate)
which is [MIT licensed](https://opensource.org/licenses/MIT).
