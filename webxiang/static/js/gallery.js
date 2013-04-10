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

  function fadeInAll() {
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

  function fadeInRandomly() {
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
    case 39: /* left */
    case 78: /* n */
      follow (GID ('nextPhoto') || GID ('nextPage'));
      break;
    case 37: /* right */
    case 80: /* p */
      follow (GID ('prevPhoto') || GID ('prevPage'));
      break;
    case 84: /* t */
      follow ('levelTop');
      break;
    case 85: /* u */
      follow ('levelIndex') ||
        follow ('levelParent') ||
        follow ('levelTop');
      break;
    }
  };

  $(document).ready (function () {
      if (GID ('story'))
        fadeInAll ();
      else
        fadeInRandomly ();

      $('.geo').each (function () {
          var geo = $(this);
          var size = geo.width () + 'x100';
          var latlng = geo.data ('geo');
          var zoom = latlng == '0,0' ? 1 : 11;
          geo.html ('<a href="http://maps.google.com/maps?q='+ latlng +
                    '" target="_blank"><img src="//maps.googleapis.com/maps/api/staticmap?sensor=false&zoom='+
                    zoom +'&size='+ size +'&scale=2&markers='+ latlng +'" alt="Map"/></a>');
        });

      $('html').swipe ()
        .bind ('swipeLeft', function () {
            follow (GID ('nextPhoto') || GID ('nextPage'));
          })
        .bind ('swipeRight', function () {
            follow (GID ('prevPhoto') || GID ('prevPage'));
          });
    });
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
