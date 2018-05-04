# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Socrata
                                 A QGIS plugin
 Automatically Download or Upload to Socrata
                             -------------------
        begin                : 2016-03-01
        copyright            : (C) 2016 by Socrata, Inc
        email                : peter.moore@socrata.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):
    """Load Socrata class from file Socrata.

    :param iface: A QGIS interface.
    :type iface: QgsInterface
    """
    #
    from .Socrata import Socrata
    return Socrata(iface)
