# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GIS.lab Web plugin
 Publish your projects into GIS.lab Web application
 ***************************************************************************/
"""

import os
import json
import codecs

# Import the PyQt and QGIS libraries
from qgis.core import *
from PyQt4.QtGui import *
from PyQt4.QtCore import *

from utils import *
from wizard import WizardPage


CSS_STYLE = u"""<style type="text/css">
    body {
        background-color: #DDDDDD;
    }
    h3 {
        margin-bottom: 4px;
        margin-top: 6px;
        text-decoration: underline;
    }
    h4 {
        margin-bottom: 1px;
        margin-top: 2px;
    }
    div {
        margin-left: 10px;
    }
    ul {
        margin-top: 0px;
    }
    label {
        font-weight: bold;
    }
</style>"""


class PublishPage(WizardPage):

    def __init__(self, plugin, page):
        super(PublishPage, self).__init__(plugin, page)
        self.dialog.setButtonText(QWizard.CommitButton, "Publish")
        page.setCommitPage(True)

    def on_show(self):
        """Creates configuration summary of published project."""

        def format_template_data(data):
            iterator = data.iteritems() if type(data) == dict else enumerate(data)
            for key, value in iterator:
                if type(value) in (list, tuple):
                    if value and isinstance(value[0], Decimal):
                        value = [u'{0:.5f}'.format(v) for v in value]
                    data[key] = u', '.join(map(unicode, value))
            return data

        metadata = self.plugin.metadata
        data = {
            'DEFAULT_BASE_LAYER': self.dialog.default_baselayer.currentText(),
            'SCALES': self.plugin.resolutions_to_scales(metadata['tile_resolutions']),
            'PROJECTION': metadata['projection']['code'],
            'AUTHENTICATION': self.dialog.authentication.currentText(),
            'MESSAGE_TEXT': opt_value(metadata, 'message.text'),
            'MESSAGE_VALIDITY': opt_value(metadata, 'message.valid_until'),
            'EXPIRATION': metadata.get('expiration', ''),
        }

        for param in (
                'gislab_user',
                'gislab_unique_id',
                'gislab_version',
                'title',
                'abstract',
                'contact_person',
                'contact_mail',
                'contact_organization',
                'extent',
                'tile_resolutions',
                'units',
                'measure_ellipsoid',
                'use_mapcache'):
            data[param.upper()] = metadata[param]

        def fill_layer_tree(root, data, template_data):
            item = root
            for text in data:
                if isinstance(text, list):
                    for subtext in text:
                        subitem = QTreeWidgetItem(item)
                        subitem.setText(0, subtext.format(
                            *format_template_data(template_data))
                        )
                else:
                    item = QTreeWidgetItem(root)
                    item.setText(0, text.format(
                        *format_template_data(template_data))
                    )

        # collect base layer summary
        def collect_base_layer_summary(root, layer_data):
            sublayers = layer_data.get('layers')
            if sublayers:
                item = QTreeWidgetItem(root)
                item.setText(0, layer_data['name'])
                for sublayer_data in sublayers:
                    collect_base_layer_summary(item, sublayer_data)
            else:
                resolutions = layer_data['resolutions']
                if 'min_resolution' in layer_data:
                    resolutions = filter(
                        lambda res: res >= layer_data['min_resolution'] and
                            res <= layer_data['max_resolution'],
                        resolutions
                    )
                scales = self.plugin.resolutions_to_scales(resolutions)
                if 'metadata' in layer_data:
                    if 'visibility_scale_max' in layer_data:
                        scale_visibility = 'Maximum (inclusive): {0}, Minimum (exclusive): {1}'.format(
                            layer_data['visibility_scale_max'],
                            layer_data['visibility_scale_min']
                        )
                    else:
                        scale_visibility = ''
                    template_data = format_template_data([
                        layer_data['name'],
                        layer_data['extent'],
                        layer_data['projection'],
                        scale_visibility,
                        scales,
                        resolutions,
                        layer_data.get('provider_type', ''),
                        opt_value(layer_data, 'attribution.title'),
                        opt_value(layer_data, 'attribution.url'),
                        layer_data['metadata']['title'],
                        layer_data['metadata']['abstract'],
                        layer_data['metadata']['keyword_list'],
                    ])
                    layer_summary = [
                        "Extent: {1}",
                        "CRS: {2}",
                        "Scale based visibility: {3}",
                        "Visible scales: {4}",
                        "Visible resolutions: {5}",
                        "Provider type: {6}",
                        "Attribution:", ["Title: {7}", "URL: {8}"],
                        "Metadata:", ["Title: {9}", "Abstract: {10}", "Keyword list: {11}"]
                    ]

                    item = QTreeWidgetItem(root)
                    item.setText(0, '{0}'.format(*format_template_data(template_data)))
                    fill_layer_tree(item, layer_summary, template_data)

                # Special base layers
                else:
                    template_data = format_template_data([
                        layer_data['name'],
                        layer_data['extent'],
                        scales,
                        resolutions,
                    ])

                    layer_summary = [
                        "Extent: {1}",
                        "Visible scales: {2}",
                        "Visible resolutions: {3}"
                    ]
                    if layer_data['name'] == 'MAPBOX':
                        layer_summary.append("MapId: {}".format(layer_data['mapid']))
                        layer_summary.append("ApiKey: {}".format(layer_data['apikey']))
                    elif layer_data['name'].startswith('BING'):
                        layer_summary.append("ApiKey: {}".format(layer_data['apikey']))

                    item = QTreeWidgetItem(root)
                    item.setText(0, '{0}'.format(*format_template_data(template_data)))
                    fill_layer_tree(item, layer_summary, template_data)

        def collect_overlays_summary(root, layer_data):
            sublayers = layer_data.get('layers')
            if sublayers:
                item = QTreeWidgetItem(root)
                item.setText(0, layer_data['name'])
                for sublayer_data in sublayers:
                    collect_overlays_summary(item, sublayer_data)
            else:
                if 'visibility_scale_max' in layer_data:
                    scale_visibility = 'Maximum (inclusive): {0}, Minimum (exclusive): {1}'.format(
                        layer_data['visibility_scale_max'],
                        layer_data['visibility_scale_min']
                    )
                else:
                    scale_visibility = ''
                template_data = format_template_data([
                    layer_data['name'],
                    layer_data['visible'],
                    layer_data['queryable'],
                    layer_data['extent'],
                    layer_data['projection'],
                    layer_data.get('geom_type', ''),
                    scale_visibility,
                    layer_data.get('labels', False),
                    layer_data['provider_type'],
                    ", ".join([
                        attribute.get('title', attribute['name'])
                        for attribute in layer_data.get('attributes', [])
                    ]),
                    opt_value(layer_data, 'attribution.title'),
                    opt_value(layer_data, 'attribution.url'),
                    layer_data['metadata']['title'],
                    layer_data['metadata']['abstract'],
                    layer_data['metadata']['keyword_list'],
                ])

                layer_summary = [
                    "Visible: {1}",
                    "Queryable: {2}",
                    "Extent: {3}",
                    "CRS: {4}",
                    "Geometry type: {5}",
                        "Scale based visibility: {6}",
                    "Labels: {7}",
                    "Provider type: {8}",
                    "Attributes: {9}",
                    "Attribution:", ["Title: {10}", "URL: {11}"],
                    "Metadata:", ["Title: {12}", "Abstract: {13}", "Keyword list: {14}"],
                ]

                item = QTreeWidgetItem(root)
                item.setText(0, '{0}'.format(*format_template_data(template_data)))
                fill_layer_tree(item, layer_summary, template_data)

        # construct tree item
        tree = self.dialog.config_summary
        tree.setColumnCount(1)

        if self.plugin.run_in_gislab:
            item = QTreeWidgetItem(tree)
            item.setText(0, "General information")
            for text in ["GIS.lab user: {GISLAB_USER}",
                         "GIS.lab ID: {GISLAB_UNIQUE_ID}",
                         "GIS.lab version: {GISLAB_VERSION}"]:
                subitem = QTreeWidgetItem(item)
                subitem.setText(0, text.format(**format_template_data(data)))

        item = QTreeWidgetItem(tree)
        item.setText(0, "Project")
        for text in [
                "Title: {TITLE}",
                "Abstract: {ABSTRACT}",
                "Contact person: {CONTACT_PERSON}",
                "Contact mail: {CONTACT_MAIL}",
                "Contact organization: {CONTACT_ORGANIZATION}",
                "Extent: {EXTENT}",
                "Scales: {SCALES}",
                "Resolutions: {TILE_RESOLUTIONS}",
                "Projection: {PROJECTION}",
                "Units: {UNITS}",
                "Measure ellipsoid: {MEASURE_ELLIPSOID}",
                "Use cache: {USE_MAPCACHE}",
                "Authentication: {AUTHENTICATION}",
                "Expiration date: {EXPIRATION}",
                "Message text: {MESSAGE_TEXT}",
                "Message validity: {MESSAGE_VALIDITY}"
        ]:
            subitem = QTreeWidgetItem(item)
            subitem.setText(0, text.format(**format_template_data(data)))

        item = QTreeWidgetItem(tree)
        item.setText(0, "Base layers (default: {DEFAULT_BASE_LAYER})".format(
            **format_template_data(data))
        )
        for layer_data in metadata['base_layers']:
            collect_base_layer_summary(item, layer_data)

        item = QTreeWidgetItem(tree)
        item.setText(0, "Overlay layers")
        for layer_data in metadata['overlays']:
            collect_overlays_summary(item, layer_data)

        print_composers = []
        for composer_data in metadata['composer_templates']:
            template_data = (
                composer_data['name'],
                int(round(composer_data['width'])),
                int(round(composer_data['height']))
            )
            print_composers.append('{0} ( {1} x {2}mm )'.format(*template_data))

        item = QTreeWidgetItem(tree)
        item.setText(0, "Print composers")
        for text in print_composers:
            subitem = QTreeWidgetItem(item)
            subitem.setText(0, text)

        tree.expandToDepth(1)

    def publish_project(self):
        """Creates files required for publishing current project for GIS.lab Web application."""
        metadata = self.plugin.metadata
        project = self.plugin.project

        page_id = 0
        while page_id < self.dialog.currentId():
            page = self.dialog.page(page_id)
            page.handler.before_publish()
            page_id = page.nextId()

        publish_timestamp = str(metadata['publish_date_unix'])
        # create metadata file
        project_filename = os.path.splitext(project.fileName())[0]
        metadata_filename = "{0}_{1}.meta".format(project_filename, publish_timestamp)
        with open(metadata_filename, "w") as f:
            def decimal_default(obj):
                if isinstance(obj, Decimal):
                    return float(obj)
                raise TypeError
            json.dump(metadata, f, indent=2, default=decimal_default)

        # Create a copy of project's file with unique layer IDs (with publish timestamp)
        # to solve issue with duplicit layer ID when updating publish project.
        published_project_filename = "{0}_{1}.qgs".format(project_filename, publish_timestamp)
        with codecs.open(project.fileName(), 'r', 'utf-8') as fin,\
                codecs.open(published_project_filename, 'w', 'utf-8') as fout:
            project_data = fin.read()
            for layer in self.plugin.layers_list():
                project_data = project_data.replace(
                    '"{0}"'.format(layer.id()),
                    '"{0}_{1}"'.format(layer.id(), publish_timestamp)
                )
                project_data = project_data.replace(
                    '>{0}<'.format(layer.id()),
                    '>{0}_{1}<'.format(layer.id(), publish_timestamp)
                )
            fout.write(project_data)

        # If published project contains SpatiaLite layers, make sure they have filled
        # statistics info required to load layers by Mapserver. Without this procedure,
        # newly created layers in DB Manager wouldn't be loaded by Mapserver properly and
        # GetMap and GetLegendGraphics requests with such layers would cause server error.
        # The only way to update required statistics info is to create a new SpatiaLite
        # provider for every published SpatiaLite layer. (This is done automatically
        # when opening QGIS project file again).
        overlays_names = []
        def collect_overlays_names(layer_data):
            sublayers = layer_data.get('layers')
            if sublayers:
                for sublayer_data in sublayers:
                    collect_overlays_names(sublayer_data)
            else:
                overlays_names.append(layer_data['name'])

        for layer_data in metadata['overlays']:
            collect_overlays_names(layer_data)

        layers_registry = QgsMapLayerRegistry.instance()
        providers_registry = QgsProviderRegistry.instance()
        for layer_name in overlays_names:
            layer = layers_registry.mapLayersByName(layer_name)[0]
            if layer.dataProvider().name() == "spatialite":
                provider = providers_registry.provider(
                    "spatialite",
                    layer.dataProvider().dataSourceUri()
                )
                del provider

    def validate(self):
        self.publish_project()
        return True
