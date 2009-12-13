"""\
SVG renderer for the aafigure package.

(C) 2006 Chris Liechti <cliechti@gmx.net>

This is open source software under the BSD license. See LICENSE.txt for more
details.
"""

import sys
from xml.sax.saxutils import escape

class SVGOutputVisitor:
    """Render a list of shapes as SVG image."""

    def __init__(self, options):
        self.options = options
        self.file_like = options['file_like']
        self.scale = options['scale']*7
        self.line_width = options['line_width']
        self.foreground = options['foreground']
        self.background = options['background']
        self.fillcolor = options['fill']
        self.indent = ''
        # if front is given explicit, use it instead of textual/proportional flags
        if 'font' in options:
            self.font = options['font']
        else:
            if options['proportional']:
                self.font = 'sans-serif'
            else:
                self.font = 'monospace'

    def _num(self, number):
        """helper to scale numbers for svg output"""
        return number * self.scale

    def get_size_attrs(self):
        """get image size as svg text"""
        #this function is here beacuse of a hack. the rst2html converter
        #has to know the size of the figure it inserts
        return 'width="%s" height="%s"' % (
            self._num(self.width),
            self._num(self.height)
        )

    def visit_image(self, aa_image, xml_header=True):
        """Process the given ASCIIArtFigure and output the shapes in
           the SVG file
        """
        self.aa_image = aa_image        #save for later XXX not optimal to do it here
        self.width = (aa_image.width+1)*aa_image.nominal_size*aa_image.aspect_ratio
        self.height = (aa_image.height+1)*aa_image.nominal_size
        if xml_header:
            self.file_like.write("""\
<?xml version="1.0" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"
 "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">

<svg width="%s" height="%s" version="1.1" xmlns="http://www.w3.org/2000/svg"
  xmlns:xlink="http://www.w3.org/1999/xlink">
<!-- automatically generated by aafigure -->
""" % (
                '100%', #self._num(self.width),
                '100%', #self._num(self.height)
            ))
        else:
            self.file_like.write("""<svg width="%s" height="%s" version="1.1" xmlns="http://www.w3.org/2000/svg">\n""" % (
                self._num(self.width),
                self._num(self.height)
            ))
        self.visit_shapes(aa_image.shapes)
        self.file_like.write("</svg>\n")

    def visit_shapes(self, shapes):
        for shape in shapes:
            shape_name = shape.__class__.__name__.lower()
            visitor_name = 'visit_%s' % shape_name
            if hasattr(self, visitor_name):
                getattr(self, visitor_name)(shape)
            else:
                sys.stderr.write("WARNING: don't know how to handle shape %r\n"
                    % shape)

    # - - - - - - SVG drawing helpers - - - - - - -
    def _line(self, x1, y1, x2, y2, thick):
        """Draw a line, coordinates given as four decimal numbers"""
        self.file_like.write(
            """%s<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" />\n""" % (
            self.indent,
            self._num(x1),
            self._num(y1),
            self._num(x2),
            self._num(y2),
            self.foreground,
            self.line_width*(1+bool(thick))))

    def _rectangle(self, x1, y1, x2, y2, style=''):
        """Draw a rectangle, coordinates given as four decimal numbers.
           ``style`` is inserted in the SVG. It could be e.g. "fill:yellow"
        """
        if x1 > x2: x1, x2 = x2, x1
        if y1 > y2: y1, y2 = y2, y1
        self.file_like.write("""\
%s<rect x="%s" y="%s" width="%s" height="%s" stroke="%s" fill="%s" stroke-width="%s" style="%s" />
""" % (
            self.indent,
            self._num(x1), self._num(y1),
            self._num(x2-x1), self._num(y2-y1),
            #~ self.foreground, #stroke:%s;
            self.fillcolor, #stroke:%s;
            self.fillcolor,
            self.line_width,
            style
        ))

    # - - - - - - visitor function for the different shape types - - - - - - -

    def visit_point(self, point):
        self.file_like.write("""\
%s<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="%s" stroke-width="%s" />
""" % (
        self.indent,
        self._num(point.x), self._num(point.y),
        self._num(0.2),
        self.foreground, self.foreground,
        self.line_width))

    def visit_line(self, line):
        x1, x2 = line.start.x, line.end.x
        y1, y2 = line.start.y, line.end.y
        self._line(x1, y1, x2, y2, line.thick)

    def visit_rectangle(self, rectangle):
        self._rectangle(
            rectangle.p1.x, rectangle.p1.y,
            rectangle.p2.x, rectangle.p2.y
        )


    def visit_circle(self, circle):
        self.file_like.write("""\
%s<circle cx="%s" cy="%s" r="%s" stroke="%s" stroke-width="%s" fill="%s" />
""" % (
        self.indent,
        self._num(circle.center.x), self._num(circle.center.y),
        self._num(circle.radius),
        self.foreground,
        self.line_width,
        self.fillcolor))

    def visit_label(self, label):
        #  font-weight="bold"   style="stroke:%s"
        self.file_like.write("""\
%s<text x="%s" y="%s" font-family="%s" font-size="%s" fill="%s" >
  %s
%s</text>
""" % (
        self.indent,
        self._num(label.position.x), self._num(label.position.y-0.3), # XXX static offset not good in all situations
        self.font,
        self._num(self.aa_image.nominal_size),
        self.foreground,
        escape(label.text.encode('utf8')),
        self.indent
        ))

    def visit_group(self, group):
        self.file_like.write("<g>\n")
        old_indent = self.indent
        self.indent += '    '
        self.visit_shapes(group.shapes)
        self.indent = old_indent
        self.file_like.write("</g>\n")

    def visit_arc(self, arc):
        p1, p2 = arc.start, arc.end
        c1 = arc.start_control_point()
        c2 = arc.end_control_point()
        self.file_like.write("""\
%s<path d="M%s,%s C%s,%s %s,%s %s,%s" fill="none" stroke="%s" stroke-width="%s" />
""" % (
        self.indent,
        self._num(p1.x), self._num(p1.y),
        self._num(c1.x), self._num(c1.y),
        self._num(c2.x), self._num(c2.y),
        self._num(p2.x), self._num(p2.y),
        self.foreground,
        self.line_width
        ))
