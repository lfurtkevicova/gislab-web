(function() {
  'use strict';

  angular
    .module('gl.features')
    .controller('AttributeTableController', AttributeTableController);

  function AttributeTableController($scope, $timeout, projectProvider, gislabClient, featuresViewer, tool) {
    // console.log('AttributeTableController: INIT');
    featuresViewer.initialize();
    $scope.tool = tool;
    console.log($scope);

    var comparators = {
      TEXT: [
        {
          label: '=',
          operand: '=',
          format: 'Text'
        }, {
          label: '!=',
          operand: '!=',
          format: 'Text'
        }, {
          label: 'LIKE',
          operand: '~',
          format: 'Text'
        }, {
          label: 'IN',
          operand: 'IN',
          format: 'Text,Text,...'
        }
      ],
      INTEGER: [
        {
          label: '=',
          operand: '=',
          format: 'Integer',
        }, {
          label: '!=',
          operand: '!=',
          format: 'Integer'
        }, {
          label: '<',
          operand: '<',
          format: 'Integer'
        }, {
          label: '<=',
          operand: '<=',
          format: 'Integer'
        }, {
          label: '>',
          operand: '>',
          format: 'Integer'
        }, {
          label: '>=',
          operand: '>=',
          format: 'Integer'
        }, {
          label: 'IN',
          operand: 'IN',
          format: 'Integer,Integer,...'
        }, {
          label: 'BETWEEN',
          operand: 'BETWEEN',
          format: 'Integer,Integer'
        }, {
          label: 'NOT BETWEEN',
          operand: '',
          format: 'Integer,Integer'
        }
      ],
      DOUBLE: [
        {
          label: '=',
          operand: '=',
          format: 'Real'
        }, {
          label: '!=',
          operand: '!=',
          format: 'Real'
        }, {
          label: '<',
          operand: '<',
          format: 'Real'
        }, {
          label: '<=',
          operand: '<=',
          format: 'Real'
        }, {
          label: '>',
          operand: '>',
          format: 'Real'
        }, {
          label: '>=',
          operand: '>=',
          format: 'Real'
        }, {
          label: 'IN',
          operand: 'IN',
          format: 'Real,Real,...'
          // encode: encoders.LIST
        }, {
          label: 'BETWEEN',
          operand: '',
          format: 'Real,Real'
        }, {
          label: 'NOT BETWEEN',
          operand: '',
          format: 'Real,Real'
        }
      ]
    }

    var layers = [];
    projectProvider.layers.list.forEach(function(layer, index) {
      if (layer.queryable) {
        var attributes = [];
        layer.attributes.forEach(function(attr) {
          attributes.push({
            label: attr.alias || attr.name,
            //type: attr.type,
            name: attr.name,
            comparators: comparators[attr.type]
          });
        });
        layers.push({
          name: layer.name,
          index: index,
          attributes: attributes,
          features: []
        });
      }
    });
    $scope.layers = layers;

    $scope.setActiveLayer = function(layer) {
      if ($scope.activeLayer !== layer) {
        $scope.activeLayer = layer;
        if (!layer.features.length) {
          $scope.search();
        }
        featuresViewer.setActiveFeaturesLayer(layer.name);
        featuresViewer.removeLayerFeatures(layer.name);
        featuresViewer.selectFeature(null);
      }
    };

    $scope.selectFeature = function(feature) {
      featuresViewer.selectFeature(feature);
      $scope.selectedFeature = feature;
    };

    $scope.zoomToFeature = function(feature) {
      var params = {
        'VERSION': '1.0.0',
        'SERVICE': 'WFS',
        'REQUEST': 'GetFeature',
        'OUTPUTFORMAT': 'GeoJSON',
        'FEATUREID': feature.id
      }
      $scope.progress = gislabClient.get(projectProvider.config.ows_url, params)
        .then(function(data) {
          var parser = new ol.format.GeoJSON();
          var feature = parser.readFeatures(data)[0];
          //console.log(feature);
          $scope.selectFeature(feature);
          featuresViewer.zoomToFeature(feature);
        });
    }

    function fetchFeatures (filters) {
      var layerName = $scope.activeLayer.name;
      // convert to WFS layer name
      while (layerName.indexOf(' ') != -1) {
        layerName = layerName.replace(' ', '_');
      }
      var wfsParams = {
        'layer': layerName,
        'maxfeatures': $scope.tool.limit,
        'startindex': 0,
        'filters': filters
      }
      if ($scope.tool.searchInExtent) {
        var size = projectProvider.map.getSize();
        wfsParams['bbox'] = projectProvider.map.getView().calculateExtent(size);
      }
      $scope.progress = gislabClient.post(
        '/filter/?PROJECT={0}'.format(projectProvider.config.project),
        wfsParams)
        .then(function (data) {
          $scope.activeLayer.features = data.features;
        });
    };

    $scope.search = function() {
      var filters = [];
      $scope.activeLayer.attributes.forEach(function (attribute) {
        if (attribute.filterValue) {
          filters.push({
            attribute: attribute.name,
            value: attribute.filterValue,
            operator: attribute.comparator.operand
          });
        }
      });
      fetchFeatures(filters);
    };

    $scope.$on("$destroy", function() {
      // console.log('AttributeTableController: DESTROY');
      featuresViewer.setActiveFeaturesLayer('');
      featuresViewer.selectFeature(null);
    });
  };
})();
