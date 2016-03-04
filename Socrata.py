# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Socrata
                                 A QGIS plugin
 Automatically Download or Upload to Socrata
                              -------------------
        begin                : 2016-03-01
        git sha              : $Format:%H$
        copyright            : (C) 2016 by Socrata, Inc
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
from PyQt4.QtCore import *
from PyQt4.QtGui import *
# Initialize Qt resources from file resources.py
import resources
from authenticate import Authenticate
# Import the code for the dialog
from Socrata_dialog import SocrataDialog
from Socrata_dialog import MapDialog
from Socrata_dialog import ErrorDialog
import os.path
import urllib2
import json

class Socrata:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
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
        QObject.connect(self.dlg.pushButton, SIGNAL("clicked()"), self.showMaps)
        '''
        Error box
        '''
        self.edlg = ErrorDialog()
        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Socrata')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'Socrata')
        self.toolbar.setObjectName(u'Socrata')

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

    def throwError(self, message):
        self.edlg.label.setText(message)
        self.edlg.show()
        return

    def get_settings(self):
        domain = self.dlg.domain.text()
        uid = self.dlg.uid.text()
        return domain, uid

    def get_metadata(self):
        resource = 'https://'+self.domain+"/api/views/"+self.uid
        response = urllib2.urlopen(resource)
        return json.load(response)

    def get_new_uid(self):
        metadata = self.get_metadata()
        new_uid = metadata['childViews'][0]
        return new_uid

    def get_maps(self):
        resource = 'https://'+self.domain+"/api/search/views.json?limitTo=maps"
        r = urllib2.urlopen(resource)
        response = json.load(r)
        if not "results" in response:
            self.throwError("This domain requires authentication")
            return
        else:
            return response

    def showMaps(self):
        self.domain, self.uid = self.get_settings()
        self.mdlg.listWidget.clear()
        get_all_maps = self.get_maps()
        if not get_all_maps:
            return

        items_to_add = list()
        for maps in get_all_maps['results']:
            items_to_add.append(maps['view']['name'])
        self.mdlg.listWidget.addItems(items_to_add)
        self.mdlg.listWidget.sortItems()
        self.mdlg.show()

        result = self.mdlg.exec_()

        if result:
            self.item = self.mdlg.listWidget.currentItem()
            self.item = self.item.text()
            for maps in get_all_maps['results']:
                if self.item == maps['view']['name']:
                    self.uid = maps['view']['id']
            self.dlg.uid.setText(self.uid)
            self.new_uid = self.get_new_uid() 

    def Auth(self):
        if Authenticate(self.domain, self.username, self.password, self.app_token):
            return True
        else:
            return False
    def run(self):
        """Run method that performs all the real work"""
        
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code. 
            url = 'https://'+self.domain+"/resource/"+self.new_uid+".geojson"
            layer = self.iface.addVectorLayer(url,self.item,"ogr")
