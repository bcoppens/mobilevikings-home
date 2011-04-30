# (c) 2011 Bart Coppens
# Licensed under GPLv3+

import gtk
import cairo
import hildon
import hildondesktop
import pycurl
import StringIO
import math
from xml.dom.minidom import parseString
import sys
import ConfigParser
import base64
import dbus
import gobject
import dbus.glib
import conic

conic_magic = 0xAA55 # WTH is this, the python example uses this but what purpose does it serve? No explanation given...

INSTALLDIR = '/opt/mobilevikings/'
sys.path.append(INSTALLDIR)
from hildon_home_plugin_item import HildonHomePluginItem

CONFIGFILE = '/home/user/.mobilevikings'

# for future reference: drawing code (transparency and outlined text) vaguely inspired by
# http://www.linux.com/community/blogs/n900-desktop-widget-lucid-dreaming-reality-check.html
# http://www.mail-archive.com/maemo-developers%40maemo.org/msg22895.html

class XMLGetter:
    def __init__(self, username, password):
        self.username = username
        self.password = password

    def requestXML(self, action):
        c = pycurl.Curl()
        c.setopt(pycurl.SSL_VERIFYPEER, True)
        c.setopt(pycurl.CAPATH, "/etc/certs/common-ca/")
        c.setopt(pycurl.TIMEOUT, 70) # timeout in seconds, in case network is down. TODO ### Check if network is down, ask for connection!

        c.setopt(pycurl.URL, 'https://%s:%s@mobilevikings.com/api/1.0/rest/mobilevikings/%s.xml' % (self.username, self.password, action))
        b = StringIO.StringIO()
        c.setopt(pycurl.WRITEFUNCTION, b.write)
        c.perform()
        return b.getvalue()

# TODO: What with people with multiple SIMs???
# <dict>
#  <valid_until>2011-02-11T08:35:09.000997</valid_until>
#  <data>2123475904</data>
#  <sms>1000</sms>
#  <credits>14.28</credits>
#  <sms_super_on_net>999</sms_super_on_net>
#  <is_expired>False</is_expired>
# </dict>
class MVBalance:
    def __init__(self, dom):
        self.valid_until      = self.getText(dom.getElementsByTagName("valid_until")[0])
        self.data             = int(self.getText(dom.getElementsByTagName("data")[0]))
        self.sms              = int(self.getText(dom.getElementsByTagName("sms")[0]))
        self.sms_super_on_net = int(self.getText(dom.getElementsByTagName("sms_super_on_net")[0]))
        self.is_expired       = self.getText(dom.getElementsByTagName("is_expired")[0]) == True
        self.credit           = self.getText(dom.getElementsByTagName("credits")[0])
        # A HACK! XXX ###
        split = self.valid_until.split('T')
        self.valid_until_short= split[0] # + ' ' + split[1].split('.')[0]

    def getText(self, element):
        rc = []
        for node in element.childNodes:
            if node.nodeType == node.TEXT_NODE:
                rc.append(node.data)
        return ''.join(rc)

# When something goes wrong we use this one
class DummyBalance:
    data = 0
    sms = 0
    sms_super_on_net = 0
    is_expired = True
    credit = "0"
    def __init__(self, reason):
        self.valid_until = reason
        self.valid_until_short = reason

class InfoDrawer:
    def outlinedText(self, cr, text):
        # Use Text path => fill and stroke so we have an outline
        cr.set_source_rgb(0,0,0)
        cr.text_path(text)
        cr.fill_preserve()
        cr.set_source_rgb(0xFFFF,0xFFFF,0xFFFF)
        cr.stroke()

    def setFont(self, cr, size):
        # Font: Tahoma, Bold, Size 50
        cr.select_font_face("tahoma", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(size)

    def drawInfo(self, drawee, cr):
        return # Do nothing

    def load(self):
        self.set_size_request(200,200)

class StartingDrawer(InfoDrawer):
    def load(self, drawee):
        drawee.set_size_request(300,125)

    def drawInfo(self, drawee, cr):
        self.setFont(cr, 40)
        cr.move_to(10, drawee.header_height + 42)
        self.outlinedText(cr, "Loading...")

class NoUserInfoDrawer(InfoDrawer):
    def load(self, drawee):
        drawee.set_size_request(300,125)

    def drawInfo(self, drawee, cr):
        self.setFont(cr, 40)
        cr.move_to(10, drawee.header_height + 42)
        self.outlinedText(cr, "No User Info!")

class CouldntGetDataDrawer(InfoDrawer):
    def load(self, drawee):
        drawee.set_size_request(400,125)

    def drawInfo(self, drawee, cr):
        self.setFont(cr, 40)
        cr.move_to(10, drawee.header_height + 42)
        self.outlinedText(cr, "Couldn't get data!")


class RegularInfoDrawer(InfoDrawer):
    def __init__(self):
        self.loadImages()

    # Because we draw on ourselves, we have to set a size :-)
    def load(self, drawee):
        drawee.set_size_request(300,275)

    def loadImages(self):
        # my images are 40x40
        self.credit = cairo.ImageSurface.create_from_png(INSTALLDIR + "images/credit.png")
        self.data   = cairo.ImageSurface.create_from_png(INSTALLDIR + "images/data.png")
        self.sms    = cairo.ImageSurface.create_from_png(INSTALLDIR + "images/envelope.png")
        self.smsmv  = cairo.ImageSurface.create_from_png(INSTALLDIR + "images/envelope_mv.png")
        self.ok     = cairo.ImageSurface.create_from_png(INSTALLDIR + "images/ok.png")
        self.notok  = cairo.ImageSurface.create_from_png(INSTALLDIR + "images/notok.png")

    def drawInfo(self, drawee, cr):
        self.setFont(cr, 35)

        cr.translate(10, drawee.header_height + 10) # The header from HildonHomePluginItem and a small visual niceness offset :-)
        for i in [(self.data,   "%.1f MiB" % (float(drawee.balance.data) / 1024 / 1024)),
                  (self.sms,    str(drawee.balance.sms)),
                  (self.smsmv,  str(drawee.balance.sms_super_on_net)),
                  (self.credit, drawee.balance.credit)]:
            cr.set_source_surface(i[0])
            cr.paint()
            cr.move_to(60, 32)
            self.outlinedText(cr, i[1])
            cr.translate(0, 40) # For next iteration
        cr.move_to(60, 32)
        self.outlinedText(cr, drawee.balance.valid_until_short)

        if drawee.balance.is_expired:
            cr.set_source_surface(self.notok)
        else:
            cr.set_source_surface(self.ok)
        cr.paint()

class MobileVikingsPlugin(HildonHomePluginItem):
    def __init__(self):
        HildonHomePluginItem.__init__(self, header = "Mobile Vikings", corner_radius = 7)

        self.regularinfo = RegularInfoDrawer() # so we cache the images
        self.drawer = StartingDrawer()

        self.connect("show-settings", self.showSettings)
        self.set_settings(True)

        self.connect("button-release-event", self.click_update)

        self.isConnected = False
        self.connection = conic.Connection()
        self.connection.connect("connection-event", self.connectionEvent, conic_magic)
        res = self.connection.request_connection(conic.CONNECT_FLAG_NONE)
        assert(res == True)

        self.loadConfig() # Also does initial update(), sets self.drawer

        self.show_all()


    def connectionEvent(self, connection, event, magic):
        status = event.get_status()

        if status == conic.STATUS_CONNECTED:
            self.isConnected = True
        else:
            self.isConnected = False

        if self.isConnected and self.updatePending:
            self.update()

    def setDrawer(self, drawer):
        self.drawer = drawer
        drawer.load(self)

    def loadConfig(self):
        config = ConfigParser.RawConfigParser()
        try:
            config.read(CONFIGFILE)
            self.username = base64.b64decode(config.get('General', 'username'))
            self.password = base64.b64decode(config.get('General', 'password'))
            self.hasSettings = True
        except:
            self.hasSettings = False
            self.username = ""
            self.password = ""
        self.xml = XMLGetter(self.username, self.password)
        self.update() # Can also be the initial GET! :-)

    def showSettings(self, widget):
        usernameLabel = gtk.Label("Username")
        usernameEntry = gtk.Entry()
        usernameEntry.set_text(self.username)
        usernameBox = gtk.HBox()
        usernameBox.pack_start(usernameLabel)
        usernameBox.pack_start(usernameEntry)

        passwordLabel = gtk.Label("Password")
        passwordEntry = gtk.Entry()
        passwordEntry.set_invisible_char("*")
        passwordEntry.set_visibility(False)
        passwordEntry.set_text(self.password)
        passwordBox = gtk.HBox()
        passwordBox.pack_start(passwordLabel)
        passwordBox.pack_start(passwordEntry)

        dialog = gtk.Dialog(title   = "Account Settings",
                            flags   = gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT)
        dialog.add_button("Cancel", gtk.RESPONSE_OK)
        dialog.add_button("Ok", gtk.RESPONSE_ACCEPT)

        dialog.vbox.pack_start(usernameBox)
        dialog.vbox.pack_start(passwordBox)

        dialog.show_all()
        if dialog.run() == gtk.RESPONSE_ACCEPT:
            self.saveSettings(usernameEntry.get_text(), passwordEntry.get_text())
        dialog.destroy()

    def saveSettings(self, username, password):
        self.username = username
        self.password = password
        self.hasSettings = True

        config = ConfigParser.RawConfigParser()
        config.add_section('General')
        config.set('General', 'username', base64.b64encode(self.username))
        config.set('General', 'password', base64.b64encode(self.password))
        configfile = open(CONFIGFILE, 'wb')
        config.write(configfile) # Close?
        self.update() # This kinda recurses potentially, but should be ok with the return in self.update

    def click_update(self, widget, event):
        self.update()

    def update(self): # Redraws automatically it seems :)
        if not self.hasSettings:
            hildon.hildon_banner_show_information(self, "", "No user info configured!")
            self.balance = DummyBalance("No info!")
            self.setDrawer(NoUserInfoDrawer())
            self.showSettings(None) ### Shouldn't be necessary TODO
            return
        if not self.isConnected:
            self.updatePending = True
            self.setDrawer(CouldntGetDataDrawer())
            self.connection.request_connection(conic.CONNECT_FLAG_NONE)
            return

        self.updatePending = False
        hildon.hildon_banner_show_information(self, "", "Getting Mobile Vikings info")

        try:
            dom = parseString(self.xml.requestXML('sim_balance'))
            self.balance = MVBalance(dom)
            self.setDrawer(self.regularinfo)
            hildon.hildon_banner_show_information(self, "", "Mobile Vikings info updated")
        except:
            self.balance = DummyBalance("Failed to get")
            self.setDrawer(CouldntGetDataDrawer())
            hildon.hildon_banner_show_information(self, "", "Getting Mobile Vikings info went wrong!")

    def drawInfo(self, cr):
        self.drawer.drawInfo(self, cr)

    # So we can draw stuff with Cairo and have pretty transparency!
    def do_expose_event(self, event):
        HildonHomePluginItem.do_expose_event(self, event)
        cr = self.window.cairo_create()
        cr.rectangle(event.area.x, event.area.y,
                     event.area.width, event.area.height)
        cr.clip()
        self.drawInfo(cr)


hd_plugin_type = MobileVikingsPlugin

# The code below is just for testing purposes.
# It allows to run the widget as a standalone process.
if __name__ == "__main__":
    import gobject
    gobject.type_register(hd_plugin_type)
    obj = gobject.new(hd_plugin_type, plugin_id="plugin_id")
    obj.show()
    gtk.main()

