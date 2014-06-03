/*
   WebXiangpianbu gallery.js
   Copyright (C) 2005-2006, 2010, 2013 Wojciech Polak

   This program is free software; you can redistribute it and/or modify it
   under the terms of the GNU General Public License as published by the
   Free Software Foundation; either version 3 of the License, or (at your
   option) any later version.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License along
   with this program.  If not, see <http://www.gnu.org/licenses/>.
*/

(function () {
  var nua = navigator.userAgent.toLowerCase ();
  var opera = nua.indexOf ('opera') != -1;
  var msie = nua.indexOf ('msie') != -1 && (document.all && !opera);
  var inprogress = 0;
  var queue = [];
  var mem = {};
  var memCnt = 0;
  var cookie_showmap = 'showMap';

  function GID (id) {
    return document.getElementById (id);
  }

  function follow (a) {
    if (typeof a == 'string')
      a = GID (a);
    if (a && a.href) {
      window.location = a.href;
      return true;
    }
    else
      return false;
  }

  function fadeIn (img) {
    var intv = setInterval (function () {
        try {
          var count = msie ? img.filters.alpha.opacity :
          (img.style.opacity * 100);
          count += 5;
          if (count <= 100) {
            if (msie)
              img.filters.alpha.opacity = count;
            else
              img.style.opacity = (count / 100);
          }
          else {
            clearInterval (intv);
            inprogress--;
            $(img).addClass ('loaded');
          }
        }
        catch (e) {}
      }, 25);
  }

  function fadeInAll () {
    for (var i = 0; i < document.images.length; i++) {
      var img = document.images[i];
      if (!img.complete) {
        if (msie) {
          img.style.filter = 'alpha(opacity=0)';
          img.src = img.src; /* weird IE cached images fix */
        }
        else
          img.style.opacity = 0;
        img.onload = function () {
          fadeIn (this);
        };
      }
      else {
        $(img).addClass ('loaded');
      }
    }
  }

  function fadeInRandomly () {
    var top_fadein = 20;
    var len = document.images.length > top_fadein ?
      top_fadein : document.images.length;
    if (len > 1) {
      for (var i = 0; i < len; i++) {
        var img = document.images[i];
        if (!img.complete) {
          if (msie) {
            img.style.filter = 'alpha(opacity=0)';
            img.src = img.src;
          }
          else
            img.style.opacity = 0;
          if (inprogress == 0) {
            inprogress++;
            img.onload = function () {
              fadeIn (this);
            };
          }
          else
            queue[queue.length] = img;
        }
        else {
          $(img).addClass ('loaded');
        }
      }
      fadeInNextRandom (queue.length);
      for (var i = top_fadein; i < document.images.length; i++) {
        $(document.images[i]).addClass ('loaded');
      }
    }
  }

  function fadeInNextRandom (n) {
    if (!n) return;
    while (true) {
      var r = Math.round ((n - 1) * Math.random ());
      if (!queue[r].complete)
        break;
      if (!mem[r]) {
        mem[r] = true;
        memCnt++;
        fadeIn (queue[r]);
        break;
      }
    }
    if (memCnt < n)
      setTimeout (function () { fadeInNextRandom (n); }, 400);
  }

  function nextPhoto () {
    if (!follow (GID ('nextPhoto'))) {
      var $cur = $('#story .item.current');
      if (!$cur.length)
        $cur = $('#story .item:first').addClass ('current');
      if ($cur.length) {
        var $next = $cur.next ();
        if (!$next.length) $next = $('#story .item:first');
        $next.addClass ('current').siblings().removeClass ('current');
        $next.length && scrollToElement ($next, 'c');
      }
    }
  }

  function previousPhoto () {
    if (!follow (GID ('prevPhoto'))) {
      var $cur = $('#story .item.current');
      if ($cur.length) {
        var $prev = $cur.prev ();
        if ($prev.length) {
          $prev.addClass ('current').siblings().removeClass ('current');
          $prev.length && scrollToElement ($prev, 'c');
        }
      }
    }
  }

  function scrollToElement (el, offset) {
    offset = offset || 0;
    if (offset == 'c') {
      var diff = $(window).height () - $(el).height ();
      offset = diff > 16 ? - parseInt (diff / 2, 10) : 0;
    }
    var t = $(el).offset ().top + offset;
    $('html,body').animate ({scrollTop: t}, 200);
  }

  function showDialog (id) {
    var $el = $(id);
    var h = $(window).height ();
    var w = $(window).width ();
    var dtop = (h / 2) - ($el.height () / 1.5) + $(window).scrollTop ();
    var dleft = (w / 2) - ($el.width () / 2);
    $('#overlay').css ({height: h, width: w}).show ();
    $el.css ({top: dtop, left: dleft}).fadeIn ('fast');
  }

  window.navigateBack = function (a) {
    if (typeof document.referrer != 'undefined' &&
        typeof a != 'undefined') {
      if (document.referrer == a.href) {
        history.back ();
        return false;
      }
    }
    return true;
  }

  document.onkeydown = function (e) {
    if (!e) var e = window.event;
    if (e.keyCode) code = e.keyCode;
    else if (e.which) code = e.which;
    if (e.ctrlKey || e.altKey) return;

    switch (code) {
    case 39: /* right */
    case 74: /* j */
      nextPhoto();
      break;
    case 37: /* left */
    case 75: /* k */
      previousPhoto();
      break;
    case 78: /* n */
      follow (GID ('nextPage') || GID ('nextPhoto'));
      break;
    case 80: /* p */
      follow (GID ('prevPage') || GID ('prevPhoto'));
      break;
    case 84: /* t */
      follow ('levelTop');
      break;
    case 85: /* u */
      follow ('levelIndex') || follow ('levelParent') || follow ('levelTop');
      break;
    case 77: /* m */
      if (GID ('story') || $('.thumbnails').length) {
        if (GID ('geomap'))
          window.location = './';
        else if ($('.has-geomap').length)
          window.location = 'geomap';
      }
      else {
        $('.geo').trigger ('toggle').each (function () {
            if ($(this).is (':visible'))
              scrollToElement (this);
          });
        if (read_cookie (cookie_showmap))
          write_cookie (cookie_showmap, '', -1);
        else
          write_cookie (cookie_showmap, 1, 31);
      }
      break;
    case 72: /* h - show dialog (help) */
      showDialog ('#help');
      break;
    case 191: /* question mark */
      if (e.shiftKey)
        showDialog ('#help');
      break;
    case 27: /* esc - hide dialog */
      $('.dialog .close').click ();
      break;
    }
  };

  $(document).ready (function () {
      if (GID ('story')) {
        /* support image lazy loading plugins */
        if ($.fn.lazyload) {
          $('img').lazyload ({
            threshold: 1200,
            effect: 'fadeIn',
            data_attribute: 'src',
            load: function (img) {
                $(this).addClass ('loaded');
            }
          });
        }
        else if ($.fn.lazy) {
          $('img').lazy ({
            threshold: 1200,
            effect: 'fadeIn',
            effectTime: 250,
            enableThrottle: true,
            throttle: 250,
            afterLoad: function (img) {
                $(this).addClass ('loaded');
            }
          });
        }
        else
          fadeInAll ();
      }
      else
        fadeInRandomly ();

      $('.geo')
        .bind ('toggle', function () {
            $(this).trigger ($(this).is (':visible') ? 'hide' : 'show');
          })
        .bind ('show', function () {
            var geo = $(this);
            var size = geo.width () + 'x100';
            var latlng = geo.data ('geo');
            var zoom = latlng == '0,0' ? 1 : 11;
            geo.html ('<a href="https://maps.google.com/maps?q='+ latlng +
                      '" target="_blank"><img src="//maps.googleapis.com/maps/api/staticmap?sensor=false&zoom='+
                      zoom +'&size='+ size +'&scale=2&markers='+ latlng +'" alt="Map"/></a>');
            geo.fadeIn ();
          })
        .bind ('hide', function () {
            $(this).hide ();
          })
        .each (function () {
            if (!read_cookie (cookie_showmap))
              $(this).trigger ('hide');
            else
              $(this).trigger ('show');
          });

      $('html').swipe ()
        .bind ('swipeLeft', function () {
            if (window.getSelection && window.getSelection ().toString ())
              return;
            follow (GID ('nextPhoto') || GID ('nextPage'));
          })
        .bind ('swipeRight', function () {
            if (window.getSelection && window.getSelection ().toString ())
              return;
            follow (GID ('prevPhoto') || GID ('prevPage'));
          });

      $('#show-help').click (function (e) {
          e.preventDefault();
          showDialog ('#help');
        });
      $(document).on ('click', '.dialog .close', function (e) {
          e.preventDefault ();
          $('.dialog, #overlay').hide ();
        });

      if (GID ('geomap')) {
        window.wxpb_init_map = function () {
          var gmap = new google.maps.Map (GID ('geomap'), {
            mapTypeId: google.maps.MapTypeId.ROADMAP,
            zoomControlOptions: {style: google.maps.ZoomControlStyle.LARGE},
            keyboardShortcuts: false,
            center: new google.maps.LatLng (0, 0),
            zoom: 1
          });
          var bounds = new google.maps.LatLngBounds ();
          for (var i = 0; i < wxpb_geo_points.length; i++) {
            add_marker (gmap, bounds, wxpb_geo_points[i]);
          }
          if (!bounds.isEmpty ()) {
            gmap.setCenter (bounds.getCenter ());
            gmap.fitBounds (bounds);
          }

          $(document).keyup (function (e) {
              switch (e.which) {
              case 37: /* left */
                if (!streetview)
                  $('.inav.prev').click ();
                break;
              case 39: /* right */
                if (!streetview)
                  $('.inav.next').click ();
                break;
              case 83: /* s - toggle streetview */
                if (streetview && streetview.getVisible ()) {
                  streetview.setVisible (false);
                  streetview = null;
                }
                else if (last_marker) {
                  streetview = gmap.getStreetView ();
                  streetview.setPosition (last_marker.getPosition ());
                  streetview.setVisible (true);
                  google.maps.event
                    .addListener (streetview, 'visible_changed', function () {
                        if (!this.getVisible ())
                          streetview = null;
                      });
                }
                break;
              }
          });
        };

        var lang = (window.navigator.userLanguage ||
                    window.navigator.language || 'en').substr (0, 2);

        var script = document.createElement ('script');
        var src = 'https://maps-api-ssl.google.com/maps/api/js?sensor=false';
        script.type = 'text/javascript';
        script.src = src + '&language=' + lang + '&callback=wxpb_init_map';
        document.body.appendChild (script);

        $(document).on ('click', '.inav', function (e) {
            e.preventDefault ();
            var $this = $(this);
            var cur = $this.data ('idx');
            if ($this.hasClass ('prev'))
              var idx = cur > 0 ? cur - 1 : markers.length - 1;
            else if ($this.hasClass ('next'))
              var idx = cur < markers.length - 1 ? cur + 1 : 0;
            google.maps.event.trigger (markers[idx], 'click');
          });
      }
    });

  var last_marker = null;
  var streetview = null;
  var markers = [];

  function add_marker (gmap, bounds, data) {
    var gs = data[0].split (',');
    var mark = new google.maps.Marker ({
      map: gmap,
      position: new google.maps.LatLng (gs[0], gs[1])
    });
    mark.chain_idx = markers.length;
    markers.push (mark);
    bounds.extend (mark.getPosition ());

    google.maps.event.addListener (mark, 'click', function () {
        last_marker && last_marker.close ();
        var content = [];
        for (var i = 0; i < data[1].length; i++) {
          var x = data[1][i];

          var maxwidth = 300, maxheight = 270;
          var size = x.image.size || x.size;
          var rw = size[0] / maxwidth;
          var rh = size[1] / maxheight;
          if (rw > rh) {
            var width = maxwidth;
            var height = parseInt (size[1] / rw);
          }
          else {
            var width = parseInt (size[0] / rh);
            var height = maxheight;
          }

          content.push ('<p><a class="gminiphoto" href="'+ x.link +
                        '" target="_blank"><img src="' + x.url_full +
                        '" width="'+ width +'" height="'+ height +
                        '" alt="[photo]"></a></p>');
          if (x.description)
            content.push ('<p>' + x.description + '</p>');
        }
        content.push ('<p>');
        content.push ('<a href="#" class="inav prev" data-idx="' +
                      this.chain_idx + '">&lt;&lt;</a> ');
        content.push ('| <a href="#" class="inav next" data-idx="' +
                      this.chain_idx + '">&gt;&gt;</a>');
        content.push ('</p>');
        last_marker = new google.maps.InfoWindow ({
          content: content.join ('')
        });
        last_marker.setPosition (this.getPosition ());
        last_marker.open (streetview || gmap, this);
      });
  }

  function read_cookie (name) {
    var nameEq = name + '=';
    var ca = document.cookie.split (';');
    for (var i = 0; i < ca.length; i++) {
      var c = ca[i];
      while (c.charAt (0) == ' ')
        c = c.substring (1, c.length);
      if (c.indexOf (nameEq) == 0)
        return c.substring (nameEq.length, c.length);
    }
    return null;
  }

  function write_cookie (name, value, days) {
    var expires = '';
    if (days) {
      var date = new Date ();
      date.setTime (date.getTime () + (days * 86400000));
      var expires = '; expires=' + date.toGMTString ();
    }
    document.cookie = name +'='+ value + expires + '; path=/';
  }
}());

(function ($) {
  $.fn.swipe = function (preventDefault) {
    var has_touch = 'ontouchstart' in window || navigator.msMaxTouchPoints;
    return this.each (function () {
        var startX;
        var startY;
        var step = 50;
        var $this = $(this);

        if (has_touch)
          $this.bind ('touchstart', touchstart);

        function touchstart (event) {
          if (preventDefault)
            event.preventDefault ();
          var t = event.originalEvent.touches;
          if (t && t.length) {
            startX = t[0].pageX;
            startY = t[0].pageY;
            $this.bind ('touchmove', touchmove);
          }
        }

        function touchmove (event) {
          if (preventDefault)
            event.preventDefault ();
          var t = event.originalEvent.touches;
          if (t && t.length) {
            var deltaX = startX - t[0].pageX;
            var deltaY = startY - t[0].pageY;

            if (deltaX >= step)
              $this.trigger ('swipeLeft');
            else if (deltaX <= -step)
              $this.trigger ('swipeRight');
            if (deltaY >= step)
              $this.trigger ('swipeUp');
            else if (deltaY <= -step)
              $this.trigger ('swipeDown');

            if (Math.abs (deltaX) >= step ||
                Math.abs (deltaY) >= step) {
              $this.unbind ('touchmove', touchmove);
            }
          }
        }

        if (!has_touch)
          $this.bind ('mousedown', mousestart);

        function mousestart (event) {
          if (preventDefault)
            event.preventDefault ();
          var t = event.originalEvent;
          if (t) {
            startX = t.pageX;
            startY = t.pageY;
            $this.bind ('mousemove', mousemove);
            $this.bind ('mouseup', function () {
                $this.unbind ('mousemove', mousemove);
              });
          }
        }

        function mousemove (event) {
          if (preventDefault)
            event.preventDefault ();
          var t = event.originalEvent;
          if (t) {
            var deltaX = startX - t.pageX;
            var deltaY = startY - t.pageY;

            if (deltaX >= step)
              $this.trigger ('swipeLeft');
            else if (deltaX <= -step)
              $this.trigger ('swipeRight');
            if (deltaY >= step)
              $this.trigger ('swipeUp');
            else if (deltaY <= -step)
              $this.trigger ('swipeDown');

            if (Math.abs (deltaX) >= step ||
                Math.abs (deltaY) >= step) {
              $this.unbind ('mousemove', mousemove);
            }
          }
        }
      });
  };
})(jQuery);
