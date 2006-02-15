/*
   WebXiangpianbu gallery.js, version 1.1
   Copyright (C) 2005, 2006 Wojciech Polak.

   This program is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation; either version 2, or (at your option)
   any later version.
  
   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.
  
   You should have received a copy of the GNU General Public License
   along with this program; if not, write to the Free Software Foundation,
   Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA
*/

var nua = navigator.userAgent.toLowerCase ();
var opera = nua.indexOf ('opera') != -1;
var msie = nua.indexOf ('msie') != -1 && (document.all && !opera);
var inprogress = 0;
var queue = new Array ();
var mem = new Object ();
var memCnt = 0;

function follow (id) {
  var a = document.getElementById (id);
  if (a) {
    document.location = a.href;
    return true;
  }
  else
    return false;
}

function fadeIn (iobj) {
  var img = iobj;
  var intv = setInterval (function () {
      try {
	var count = msie ? img.filters.alpha.opacity : (img.style.opacity * 100);
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
	}
      }
      catch (e) {}
    }, 25);
}

function inif () {
  if (document.images.length > 1) {
    for (var i = 0; i < document.images.length; i++) {
      var img = document.images[i];
      if (!img.complete) {
	img.style.filter = 'alpha(opacity=0)';
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
    }
    fadeInRandom (queue.length);
  }
}

function fadeInRandom (n) {
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
    setTimeout (function () { fadeInRandom (n); }, 400);
}

document.onkeypress = function (e) {
  var code;
  if (!e) var e = window.event;
  if (e.keyCode) code = e.keyCode;
  else if (e.which) code = e.which;
  if (e.ctrlKey) return;
  switch (code) {
    case 110: /* n */
      follow ('nextPhoto');
      break;
    case 112: /* p */
      follow ('prevPhoto');
      break;
    case 116: /* t */
      follow ('levelTop');
      break;
    case 117: /* u */
      var r = follow ('levelIndex');
      if (!r) r = follow ('levelParent');
      if (!r) follow ('levelTop');
      break;
  }
};
