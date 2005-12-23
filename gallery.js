/*
   WebXiangpianbu gallery.js, version 1.0
   Copyright (C) 2005 Wojciech Polak.

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

function follow (id) {
  var a = document.getElementById (id);
  if (a) {
    document.location = a.href;
    return true;
  }
  else
    return false;
}

document.onkeypress = function (e) {
  var code;
  if (!e) var e = window.event;
  if (e.keyCode) code = e.keyCode;
  else if (e.which) code = e.which;
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
