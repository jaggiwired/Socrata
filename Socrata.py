# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Socrata
                                 A QGIS plugin
 Automatically Download or Upload to Socrata
                              -------------------
        begin                : 2016-03-01
        git sha              : $Format:%H$
        copyright            : (C) 2016 by Peter Moore
        email                : peter.moore@socrata.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from builtins import str
from builtins import object
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from qgis.PyQt.QtWidgets import QAction, QDialog, QDialogButtonBox

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .Socrata_dialog import SocrataDialog, MapDialog, MessageDialog

#Standard Libraries
import os.path
import urllib.request, urllib.error, urllib.parse
import json
from base64 import b64encode

# NOTE: SOCRATA USES TLSv1.1+ BY DEFAULT. CURRENTLY, BOTH MAC AND WINDOWS
# VERSIONS DO NOT ALLOW YOU TO SET UP YOUR OWN CERTIFICATES, SO YOUR TRAFFIC
# IS NOT GOING TO BE SSL-ED UNTIL IT IS FIXED
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
try:
    import gdal
    gdal.SetConfigOption("GDAL_HTTP_UNSAFESSL", "YES")
except ModuleNotFoundError:
    pass


class Socrata(object):
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'Socrata_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        '''
        Main dialog box
        '''
        self.dlg = SocrataDialog()
        '''
        Domain maps
        '''
        self.mdlg = MapDialog()
        self.dlg.pushButton.clicked.connect(self.showMaps)
        '''
        Message box
        '''
        self.edlg = MessageDialog()
        '''
        Bind Authentication method
        '''
        self.dlg.auth.clicked.connect(self.Auth)
        # Declare iface attributes
        self.actions = []
        self.menu = self.tr(u'&Socrata')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'Socrata')
        self.toolbar.setObjectName(u'Socrata')

        self.domain = ""
        self.uid = ""
        self.search_api_base = "http://api.us.socrata.com/api/catalog/v1"

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('Socrata', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToWebMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/Socrata/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Socrata Plugin'),
            callback=self.run,
            parent=self.iface.mainWindow())


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Socrata'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def showMessage(self, message):
        self.edlg.label.setText(message)
        self.edlg.show()
        return

    def get_settings(self):
        self.domain = self.dlg.domain.text()
        self.uid = self.dlg.uid.text()
        return

    def get_auth(self):
        self.username = self.dlg.username.text()
        self.password = self.dlg.password.text()
        return

    def get_maps(self):
        self.get_auth()
        if not self.username and not self.password:
            try:
                resource = f"{self.search_api_base}?only=maps&domains={self.domain}&limit=9999&offset=0"
                r = urllib.request.urlopen(resource)
                response = json.load(r)
                if not "results" in response.keys():
                    self.showMessage("This domain requires authentication")
                else:
                    return response
            except urllib.error.URLError as e:
                self.showMessage("Domain not found or improperly formatted. Reason: "+str(e.reason))
        else:
            try:
                resource = f"{self.search_api_base}?only=maps&domains={self.domain}&limit=9999&offset=0"
                if self.Authenticate():
                    request = urllib.request.urlopen(resource, headers=get_headers(
                        self.domain, self.username, self.password, self.app_token))
                    r = urllib.request.urlopen(resource)
                    response = json.load(r)
                    return response
                else:
                    return
            except urllib.error.URLError as e:
                self.showMessage("Domain not found or improperly formatted. Reason: "+str(e.reason))

    def showMaps(self):
        self.get_settings()

        self.mdlg.listWidget.clear()
        get_all_maps = self.get_maps()
        if not get_all_maps:
            return

        items_to_add = dict()
        for maps in get_all_maps['results']:
            items_to_add[maps['resource']['name']] = maps['resource']['id']
        self.mdlg.listWidget.addItems(items_to_add.keys())
        self.mdlg.listWidget.sortItems()
        self.mdlg.show()

        result = self.mdlg.exec_()

        if result:
            self.item = self.mdlg.listWidget.currentItem()
            self.item = self.item.text()
            self.uid = items_to_add.get(self.item)
            self.dlg.uid.setText(self.uid)

    def Authenticate(self):
        try:
            resource = 'https://'+self.domain+"/api/users/current.json"
            request = urllib.request.urlopen(resource, headers=get_headers(
                self.domain, self.username, self.password, self.app_token))
            r = urllib.request.urlopen(request)
            response = json.load(r)
            if "rights" in response:
                return True
            else:
                self.showMessage("Unauthenticated User, requires Admin, Publisher, or Editor rights")
                return False
        except urllib.error.URLError as e:
            self.showMessage("Authentication error: "+str(e.reason))
            return False

    def Auth(self):
        self.domain = self.dlg.domain.text()
        self.get_auth()
        if self.domain and self.username and self.password and self.app_token:
            if self.Authenticate():
                self.showMessage("Authenticated")
                return True
        else:
            self.showMessage("Please enter credentials and domain")
            return False

    def run(self):
        """Run method that performs all the real work"""
        # show the dialogbox
        self.dlg.show()
        # Run the dialogbox event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        self.get_settings()
        if self.domain == "" or self.uid == "":
            self.showMessage("Please enter domain and/or dataset id")
        if result and len(self.uid) > 6:
            url = 'https://'+self.domain+"/resource/"+self.uid+".geojson?$limit=10000000"
            layer = self.iface.addVectorLayer(url, f"{self.item}-{self.uid}", "ogr")

def get_headers(domain, username, password, app_token):
    headers = {}

    headers["Authorization"] = "Basic %s" % get_auth_token(username=username,password=password)

    headers['X-Socrata-Host'] = domain

    return headers

def get_auth_token(auth = None, username = None, password = None):
    if auth is not None:
        result = b64encode(b"%s" % auth).decode("ascii")
    else:
        result = b64encode(b"{0}:{1}".format(username, password).decode("ascii"))
    return result
