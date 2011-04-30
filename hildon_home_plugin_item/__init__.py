# From: http://gitorious.org/python-hildonhomepluginitem/python-hildonhomepluginitem/blobs/master/hildon_home_plugin_item/__init__.py by David Barnett
# Claims it is based on boilerplate code from http://maemo.org/downloads/product/Maemo5/conversations-inbox-widget/ amongst others.
# License: MIT License (according to gitorious)
import hildondesktop
import logging
import cairo
import gtk

class Corners(object):
    Top = object()
    Bottom = object()

class Styles(object):
    Gradient = object()
    Clear = object()

def rounded_rectangle(cr, x, y, w, h, r, corners):
    if Corners.Top in corners:
        cr.move_to(x, y + r)
        cr.arc(x + r, y + r, r, 3.14, 1.5 * 3.14)
        cr.line_to(x+w - r, y)
        cr.arc(x+w - r, y + r, r, 1.5 * 3.14, 0.0)
    else:
        cr.move_to(x, y)
        cr.line_to(x+w, y)
    if Corners.Bottom in corners:
        cr.line_to(x+w , y+h - r)
        cr.arc(x+w - r, y+h - r, r, 0.0, 0.5 * 3.14)
        cr.line_to(x + r, y+h)
        cr.arc(x + r, y+h - r, r, 0.5 * 3.14, 3.14)
    else:
        cr.line_to(x+w, y+h)
        cr.line_to(x, y+h)
    cr.close_path()

class HildonHomePluginItem(hildondesktop.HomePluginItem):
    CONTENT_OFFSET_X = 0
    CONTENT_OFFSET_Y_TOP = 0
    CONTENT_OFFSET_Y_BOTTOM = 0
    header_height = 50
    footer_height = 10

    def __init__(self, header, style=Styles.Gradient, corner_radius=7):
        hildondesktop.HomePluginItem.__init__(self)
        self.alpha_channel = None
        self.active_color = None
        self.active = False

        self.corner_radius = corner_radius

        self.screen_changed(self)
        self.set_decorated(0)
        self.set_app_paintable(1)
        self.set_colormap(self.get_screen().get_rgba_colormap())

        self.plugin_style = style

        self.contents = gtk.VBox()
        if header is None:
            self.header_label = None
            self.header_height = 0
        else:
            self.header_label = gtk.Label(header)
            self.header_label.set_size_request(-1, self.header_height)
            self.contents.pack_start(self.header_label, expand=False, fill=True)
        hildondesktop.HomePluginItem.add(self, self.contents)

        self.connect("expose-event", self.expose)
        self.connect("screen-changed", self.screen_changed)
        self.connect("style-set", self.style_set)
        self.connect("button-press-event", self.click_down)
        self.connect("button-release-event", self.click_up)
        self.connect("leave-notify-event", self.click_up)

    def add(self, *args, **kw):
        return self.contents.add(*args, **kw)

    def show_all(self, *args, **kw):
        return self.contents.show_all(*args, **kw)

    def expose(self, widget, event):
        cr = widget.window.cairo_create()

        if self.alpha_channel == True:
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.0)
        else:
            cr.set_source_rgb(1.0, 1.0, 1.0)

        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()

        width, height = self.allocation[2], self.allocation[3]
        radius = min(self.corner_radius, width/2, height/2)
        c_width = width - 2*self.CONTENT_OFFSET_X
        c_height = height - (self.CONTENT_OFFSET_Y_TOP + self.CONTENT_OFFSET_Y_BOTTOM)
        active_color = (self.active_color if self.active_color is not None else {'red': 0, 'green': 0, 'blue': 0})

        # draw bound box
        cr.set_source_rgba(0.4, 0.4, 0.4, 0.1)
        cr.set_line_width(3.0)
        rounded_rectangle(cr,
                self.CONTENT_OFFSET_X,
                self.CONTENT_OFFSET_Y_TOP,
                c_width,
                c_height,
                radius,
                [Corners.Top, Corners.Bottom])
        cr.stroke()

        # draw header
        if self.header_label is not None:
            bg_color = (active_color if self.active else {'red': 0.2, 'green': 0.2, 'blue': 0.2})
            cr.set_source_rgba(bg_color['red'], bg_color['green'], bg_color['blue'], 0.8)
            cr.set_line_width(1.0)
            cr.translate(self.CONTENT_OFFSET_X, self.CONTENT_OFFSET_Y_TOP)
            rounded_rectangle(cr, 0, 0,
                    c_width,
                    self.header_height,
                    radius,
                    [Corners.Top])
            cr.fill()

            cr.set_source_rgba(active_color['red'], active_color['green'],
                    active_color['blue'], 1.0)
            cr.move_to(0, self.header_height)
            cr.line_to(c_width, self.header_height)
            cr.stroke()

        # draw body
        if self.plugin_style == Styles.Clear:
            bg_color = (active_color if self.active else {'red': 0.2, 'green': 0.2, 'blue': 0.2})
            cr.set_source_rgba(bg_color['red'], bg_color['green'], bg_color['blue'], 0.8)
        else:       # assume Styles.Gradient:
            grad = cairo.LinearGradient(0, self.header_height, 0, c_height - self.footer_height)
            bg_color = (active_color if self.active else {'red': 0.4, 'green': 0.4, 'blue': 0.4})
            grad.add_color_stop_rgba(0.5, bg_color['red'], bg_color['green'],
                    bg_color['blue'], 0.8)
            grad.add_color_stop_rgba(1.0, bg_color['red']/2, bg_color['green']/2,
                    bg_color['blue']/2, 0.8)
            cr.set_source(grad)
        corners_to_round = ([Corners.Bottom] if self.header_label is not None else [Corners.Top, Corners.Bottom])
        rounded_rectangle(cr, 0, self.header_height, c_width, c_height - self.header_height, radius,
                corners_to_round)
        cr.fill()

        return False

    def screen_changed(self, widget, old_screen=None):
        screen = widget.get_screen()
        colormap = screen.get_rgba_colormap()
        if colormap == None:
            colormap = screen.get_rgb_colormap()
            self.alpha_channel = False
        else:
            self.alpha_channel = True

        widget.set_colormap(colormap)

        return False

    def style_set(self, widget, prev_style):
        active_color = widget.get_style().lookup_color("ActiveTextColor")
        if active_color is None:
            self.active_color = None
            logging.debug("Active color is now undefined")
        else:
            self.active_color = {'red': float(active_color.red)/65535,
                    'green': float(active_color.green)/65535,
                    'blue': float(active_color.blue)/65535}
            hexcolor = lambda c: (255*c['red'], 255*c['green'], 255*c['blue'])
            logging.debug("Active color is #%02X%02X%02X" % hexcolor(self.active_color))

    def click_down(self, widget, event):
        self.active = True
        widget.queue_draw()

    def click_up(self, widget, event):
        self.active = False
        widget.queue_draw()
