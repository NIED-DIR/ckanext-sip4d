// Dataset map module extent defextent
this.ckan.module('sip4ddataset-map', function (jQuery, _) {

  return {
    _bounds : null,
    extent : null,
    defextent: null,
    pkg_new : true,

    options: {
      i18n: {
      },
      styles: {
        point:{
          iconUrl: '/img/marker.png',
          iconSize: [14, 25],
          iconAnchor: [7, 25]
        },
        polygon :{
          color: '#F06F64',
          weight: 2,
          opacity: 1,
          fillColor: '#F06F64',
          fillOpacity: 0.1,
          clickable: false
        },
        default_:{
          color: '#B52',
          weight: 2,
          opacity: 1,
          fillColor: '#FCF6CF',
          fillOpacity: 0.4
        }
      },
    },
    template : {
      forms :  [
        '<div id="dataset-map-edit-buttons" style="margin-bottom: 30px;">',
        '<input id="spatial-extentbbox" type="text" name="spatial-extentbbox" style="width:98%;font-weight:bold;text-align: right;" disabled="true">',
        '<input id="spatial-extentjson" type="hidden" name="spatial-extentjson" value="">',
        '<br/>',
        '<a href="javascript:;" class="btn defaultextent" style="float: right;margin-top: -5px;margin-left: 5px;">Set Defalut Area</a> ',
        '<a href="javascript:;" class="btn cancel" style="float: right;margin-top: -5px;margin-left: 0px;">Undo</a> ',
        '<br/>',
        '</div>'
      ].join('')
    },

    _setFormButtonText : function()
    {
      //$(".apply").text(this._('Set spatial'));
      if (this.pkg_new.toLowerCase() === 'true') {
         $(".cancel").css('display', 'none');
      } else {
         $(".cancel").text(this._('Undo'));
      }
      $(".defaultextent").text(this._('Set Defalut Area'));
    },

    _setLayerExtentForm : function(bounds, geometry) {
      if (bounds&&geometry) {
          if ($('#spatial-extentbbox')) {
            var minx = bounds.getWest();
            var miny = bounds.getSouth();
            var maxx = bounds.getEast();
            var maxy = bounds.getNorth();
            var bboxvalue = '['+minx+", "+miny+"] - ["+maxx+", "+maxy+"]";
            $('#spatial-extentbbox').val(bboxvalue);
          }
          if ($('#spatial-extentjson')&&geometry) {
            $('#spatial-extentjson').val(JSON.stringify(geometry));
          }
      }
    },

    _setSpatailField : function() {
      var minx,miny,maxx,maxy;
      if (this._bounds) {
        minx = this._bounds.getWest();
        miny = this._bounds.getSouth();
        maxx = this._bounds.getEast();
        maxy = this._bounds.getNorth();
      }
      if ($('#spatial-extentjson')) {
        var spval = $('#spatial-extentjson').val();
        var isSpatial = false;
        if ($('#field-spatial').length) {
          $('#field-spatial').val(spval);
          isSpatial = true;
        }
        if (!isSpatial) {
          alert(this._('spatial field not found in Custom Fields.'));
        } else {
          //alert(this._('Entered a spatial value.'));
        }
      }
    },
    _getJsonGeometry : function(geojson)
    {
      if (geojson.type=='FeatureCollection') {
        var features = geojson.features;
        for (var num in features) {
          var feature = features[num];
          if (feature.type=='Feature') {
            if (feature.geometry) return feature.geometry;
          }
        }
      }
      else if (geojson.type=='Feature') {
        if (geojson.geometry) return geojson.geometry;
      }
      else if (geojson.type=='Polygon') {
        return geojson;
      }
    },

    _initialize_extent: function(extentjson) {
      if (extentjson.type == 'Polygon'
        && extentjson.coordinates[0].length == 5) {
        _coordinates = extentjson.coordinates[0]
        w = _coordinates[0][0];
        e = _coordinates[2][0];
        if (w >= 0 && e < 0) {
          w_new = w
          while (w_new > e) w_new -=360
          for (var i = 0; i < _coordinates.length; i++) {
            if (_coordinates[i][0] == w) {
              _coordinates[i][0] = w_new
            };
          };
          extentjson.coordinates[0] = _coordinates
        };
      };
      return extentjson;
    },

    initialize: function () {

      this.extent = this.el.data('extent');
      this.defextent = this.el.data('defextent');
      this.pkg_new = this.el.data('pkgnew');
      if (this.extent) {
        this.extent = this._initialize_extent(this.extent);
      }
      if (this.defextent) {
        this.defextent = this._initialize_extent(this.defextent);
      }
      // hack to make leaflet use a particular location to look for images
      L.Icon.Default.imagePath = this.options.site_url + 'js/vendor/leaflet/images';

      jQuery.proxyAll(this, /_on/);
      this.el.ready(this._onReady);

    },

    _onReady: function(){

      var module = this;
      var map, backgroundLayer, extentLayer, ckanIcon;

      if (!this.extent) {
          return false;
      }

      map = ckan.commonLeafletMap('dataset-map-container', this.options.map_config, {
        attributionControl: false,
        drawControlTooltips: false
      });

      // Initialize the draw control
      map.addControl(new L.Control.Draw({
        position: 'topright',
        draw: {
          polyline: false,
          polygon: false,
          circle: false,
          marker: false,
          rectangle: {
            shapeOptions: module.options.styles.polygon
          }
        }
      }));

      // When user finishes drawing the box, record it and add it to the map
      map.on('draw:created', function (e) {
        if (extentLayer) {
          map.removeLayer(extentLayer);
        }
        extentLayer = e.layer;
        map.addLayer(extentLayer);
        var feature = extentLayer.toGeoJSON();
        if (feature.geometry) module._setLayerExtentForm(extentLayer.getBounds(),feature.geometry);

        module._bounds = extentLayer.getBounds();
        module._setSpatailField();
      });

      var forms = $(module.template.forms).insertAfter('.dataset-map-section ');
      this._setFormButtonText();

      // Handle the cancel expanded action
      $('.cancel', forms).on('click', function() {
        if (extentLayer) {
          if (!confirm(module._('Undo Spatial Value'))) return;
          map.removeLayer(extentLayer);
          extentLayer = L.geoJson(module.extent, {
            style: module.options.styles.default_,
            pointToLayer: function (feature, latLng) {
              return new L.Marker(latLng, {icon: new ckanIcon})
          }});
          map.addLayer(extentLayer);
          if (extentLayer) {
            module._bounds = extentLayer.getBounds();
            var geometry = module._getJsonGeometry(extentLayer.toGeoJSON());
            module._setLayerExtentForm(extentLayer.getBounds(),geometry);
            module._setSpatailField();
          }
        }
      });

      // Handle the apply expanded action
//      $('.apply', forms).on('click', function() {
//        if (extentLayer) {
//          if (!confirm(module._('Replace Spatial Value'))) return;
//          module._bounds = extentLayer.getBounds();
//          module._setSpatailField();
//        }
//      });

      $('.defaultextent', forms).on('click', function() {
        if (extentLayer) {
          if (!confirm(module._('Set Default Spatial Value'))) return;
          map.removeLayer(extentLayer);
          extentLayer = L.geoJson(module.defextent, {
            style: module.options.styles.default_,
            pointToLayer: function (feature, latLng) {
              return new L.Marker(latLng, {icon: new ckanIcon})
          }});
          map.addLayer(extentLayer);
          if (extentLayer) {
            module._bounds = extentLayer.getBounds();
            var geometry = module._getJsonGeometry(extentLayer.toGeoJSON());
            module._setLayerExtentForm(extentLayer.getBounds(),geometry);
            module._setSpatailField();
          }
        }
      });


      var ckanIcon = L.Icon.extend({options: this.options.styles.point});

      var extentLayer = L.geoJson(this.extent, {
          style: this.options.styles.default_,
          pointToLayer: function (feature, latLng) {
            return new L.Marker(latLng, {icon: new ckanIcon})
          }});
      extentLayer.addTo(map);
      if (extentLayer) {

        module._bounds = extentLayer.getBounds();
        module._setLayerExtentForm(extentLayer.getBounds(),this.extent);
      }

      if (this.extent.type == 'Point'){
        map.setView(L.latLng(this.extent.coordinates[1], this.extent.coordinates[0]), 9);
      } else {
        map.fitBounds(extentLayer.getBounds());
      }
    }
  }
});
