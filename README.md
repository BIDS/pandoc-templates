# Example Pandoc/Markdown report

You need [Pandoc](https://pandoc.org/installing.html) and LaTeX
installed.  If you want to compile SVG diagrams, you'll also need Inkscape.

Then, type `make` and view the example in `build/report.pdf`.

Here is [an example build](https://github.com/BIDS/pandoc-report/blob/build/build/report.pdf).

## Adding your own report

Copy `report.md` to `my_report.md` (or whatever you want to call it).
The `make` command will now also produce your report in
`build/my_report.pdf`.

## Vector graphics

All `.svg` images (Inkscape graphics) gets converted to PNG files in
the `build/` folder.  Those images can then be used in the document,
e.g.

```
![My Image Description](build/my_image.png)
```
