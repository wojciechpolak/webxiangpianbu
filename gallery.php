<?php

//  WebXiangpianbu, version 1.2 (2008-01-01)
//  Copyright (C) 2004, 2005, 2006, 2007, 2008 Wojciech Polak.
//
//  This program is free software; you can redistribute it and/or modify it
//  under the terms of the GNU General Public License as published by the
//  Free Software Foundation; either version 3 of the License, or (at your
//  option) any later version.
//
//  This program is distributed in the hope that it will be useful,
//  but WITHOUT ANY WARRANTY; without even the implied warranty of
//  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//  GNU General Public License for more details.
//
//  You should have received a copy of the GNU General Public License along
//  with this program.  If not, see <http://www.gnu.org/licenses/>.

if (!ereg ("^apache2", @php_sapi_name ()))
  ob_start ('ob_gzhandler');

require 'config.php';
if (!isset ($CONF)) exit;

class Image
{
  var $filename;
  var $width;
  var $height;
  var $directory;

  function Image ()
  {
    $this->filename  = '';
    $this->width     = '';
    $this->height    = '';
    $this->directory = '';
  }
}

$start_time = microtime ();
getvars ('q,photo,size,page,rev');

if ($q)
{
  $q = basename (trim ($q));

  if (is_numeric ($photo)) {
    if ($photo < 1)
      $photo = 'index';
  }

  if ($q[0] == '.' || $q == 'index.html')
    die ('Get lost, lame!');
}
else
  $q = 'index';

if ($page)
{
  if (is_numeric ($page)) {
    if ($page < 1)
      $page = 1;
  }
  else if ($page != 'all')
    $page = 1;
}
else
  $page = 1;

// DATA

$index = array ();
$index_cnt = 0;

$imgSize = -1;
$selectedSize = 0;

$meta['parent']['album'] = '';
$meta['parent']['title'] = '';
$meta['directory'] = array ();
$meta['charset'] = 'UTF-8';
$meta['style'] = 'style.css';
$meta['title'] = '';
$meta['ppp'] = 5;
$meta['columns'] = 1;
$meta['reverseOrder'] = false;
$meta['copyright'] = '';

$xml_state = '';
$inside_parent = false;
$inside_entry  = false;

if ($CONF['webxiang.path.albums'])
  $filename = $CONF['webxiang.path.albums'].'/'
    . $q . $CONF['webxiang.album.ext'];
else
  $filename = $q . $CONF['webxiang.album.ext'];

// XML PARSING

if (is_file ($filename) && is_readable ($filename))
{
  $fileSize = filesize ($filename);
  if ($fileSize > 1048576)
    die ('Album file is too big');

  if (!($fp = fopen ($filename, 'r')))
    die ();

  if (!($xml_parser = xml_parser_create ()))
    die ();

  xml_set_element_handler ($xml_parser, 'startElement', 'endElement');
  xml_set_character_data_handler ($xml_parser, 'characterData');

  while ($data = fread ($fp, $fileSize))
  {
    if (!xml_parse ($xml_parser, $data, feof ($fp)))
      break;
  }
  xml_parser_free ($xml_parser);  
}
else
{
  header ('Location: '.$CONF['webxiang.url.site'].'/');
  exit;
}

// XHTML

header ("Content-Type: text/html; charset=$meta[charset]");
echo '<?xml version="1.0" encoding="'.$meta['charset'].'"?>'."\n";

?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">

<head>
<title>[gallery]<? echo ' '.substr (strip_tags ($meta['title']), 0, 80); ?></title>
<meta http-equiv="Content-Type" content="text/html; charset=<? echo $meta['charset']; ?>" />
<meta name="author" content="Wojciech Polak" />
<meta name="generator" content="WebXiangpianbu" />
<meta name="robots" content="<?php echo ($q == 'index' ? 'index' : 'noindex'); ?>,nofollow" />
<base href="<? echo $CONF['webxiang.url.site'].'/'; ?>" />
<link rel="stylesheet" href="<? echo $CONF['webxiang.url.css'].'/'.$meta['style']; ?>" type="text/css" />
<script type="text/javascript" src="gallery.js"></script>
</head>
<body>

<div id="content">
<?php

$start = 0;
$end = $index_cnt;
$allpages = 1;

if ($rev == '1' || $rev == 'true') {
  $rev = true;
  $meta['reverseOrder'] = !$meta['reverseOrder'];
} else {
  $rev = false;
}

if ($q != 'index')
{
  if (is_numeric ($page))
    count_pages ();

  // searching a photo by name
  if (!is_numeric ($photo) && $photo != '')
  {
    $searchQuery = trim ($photo);
    foreach ($index as $idx => $v)
    {
      if (preg_match ('/'.$searchQuery.'/', $v[1]->filename)) {
	$photo = $idx + 1;
	break;
      }
    }
  }

  echo "<div id=\"menu\">";

  echo '<a id="levelTop" href="'.$CONF['webxiang.url.site'].'/">all galleries</a>';
  if ($meta['parent']['album'])
  {
    echo ' / <a id="levelParent" href="'.genQueryLink ($meta['parent']['album']).'">';
    if ($meta['parent']['title'])
      echo $meta['parent']['title'];
    else
      echo $meta['parent']['album'];
    echo '</a>';
  }
  echo ' /';

  if (is_numeric ($photo))
  {
    if ($photo > $index_cnt)
      $photo = 'index';

    if ($page != 'all')
    {
      if ($meta['reverseOrder'])
	$page = floor (($index_cnt - $photo) / $meta['ppp']) + 1;
      else
	$page = ceil ($photo / $meta['ppp']);
    }

    echo ' <a href="';
    echo genQueryLink ($q, array ('rev' => $rev));
    echo '">'.$q.'</a>';
  }
  echo "</div>\n"; /* menu */

  switch (trim ($size))
  {
    case 'small':  $selectedSize = 0; break;
    case 'medium': $selectedSize = 1; break;
    case 'large':  $selectedSize = 2; break;
    default:
      $selectedSize = 1;
  }

  $prefetch = false;

  if (is_numeric ($photo))
  {
    echo "<div id=\"navigation\">";

    if ($meta['reverseOrder'])
    {
      if ($photo < $index_cnt) {
	echo "<a id=\"prevPhoto\" href=\"";
	$params = array ('rev'  => $rev,
			 'photo'=> $photo + 1,
			 'size' => $size);
	if ($page == 'all') $params['page'] = 'all';
	echo genQueryLink ($q, $params);
	echo "\">&laquo; previous</a>";
      }
      else
	echo "&laquo; previous";
      echo ' | ';
      if ($photo >= 2) {
	echo "<a id=\"nextPhoto\" href=\"";
	$params = array ('rev'   => $rev,
			 'photo' => $photo - 1,
			 'size'  => $size);
	if ($page == 'all') $params['page'] = 'all';
	echo genQueryLink ($q, $params);
	echo "\">next &raquo;</a>";

	if (!isset ($index[$photo-2][$selectedSize]))
	  $selectedSize = 0;
	if (!isset ($index[$photo-2][$selectedSize]))
	  $selectedSize = 2;

	if ($index[$photo-2][$selectedSize]->directory)
	  $prefetch = $CONF['webxiang.url.photos'].'/'.$index[$photo-2][$selectedSize]->directory.'/';
	else if (isset ($meta['directory'][$selectedSize]))
	  $prefetch = $CONF['webxiang.url.photos'].'/'.$meta['directory'][$selectedSize].'/';
	else
	  $prefetch = $CONF['webxiang.url.photos'].'/';
	$prefetch .= $index[$photo-2][$selectedSize]->filename;
      }
      else
	echo "next &raquo;";
    }
    else // !reverseOrder
    {
      if ($photo >= 2) {
	echo "<a id=\"prevPhoto\" href=\"";
	$params = array ('rev'   => $rev,
			 'photo' => $photo - 1,
			 'size'  => $size);
	if ($page == 'all') $params['page'] = 'all';
	echo genQueryLink ($q, $params);
	echo "\">&laquo; previous</a>";
      }
      else
	echo "&laquo; previous";
      echo ' | ';
      if ($photo < $index_cnt) {
	echo "<a id=\"nextPhoto\" href=\"";
	$params = array ('rev'   => $rev,
			 'photo' => $photo + 1,
			 'size'  => $size);
	if ($page == 'all') $params['page'] = 'all';
	echo genQueryLink ($q, $params);
	echo "\">next &raquo;</a>";

	if (!isset ($index[$photo][$selectedSize]))
	  $selectedSize = 0;
	if (!isset ($index[$photo][$selectedSize]))
	  $selectedSize = 2;

	if ($index[$photo][$selectedSize]->directory)
	  $prefetch = $CONF['webxiang.url.photos'].'/'.$index[$photo][$selectedSize]->directory.'/';
	else if (isset ($meta['directory'][$selectedSize]))
	  $prefetch = $CONF['webxiang.url.photos'].'/'.$meta['directory'][$selectedSize].'/';
	else
	  $prefetch = $CONF['webxiang.url.photos'].'/';
	$prefetch .= $index[$photo][$selectedSize]->filename;
      }
      else
	echo "next &raquo;";
    }

    echo "</div>\n\n"; /* navigation */

    if ($prefetch) {
      if (!strstr ($prefetch, 'http') && substr ($prefetch, 0, 1) != '/')
	$prefetch = $CONF['webxiang.url.site'].'/'.$prefetch; 
      header ('Link: <'.$prefetch.'>; rel=prefetch');
    }

    $idx = $photo - 1;

    if (isset ($index[$idx]['copyright']))
      $meta['copyright'] = $index[$idx]['copyright'];

    if (isset ($index[$idx]['imgSize']))
    {
      $imgSize = $index[$idx]['imgSize'];
      if ($selectedSize > $imgSize)
	$selectedSize = $imgSize;
    }

    if ($photo <= $index_cnt && isset ($index[$idx][$selectedSize]))
    {
      echo "<table class=\"photo\">\n<tr><td>";
      echo '<a id="levelIndex" href="';
      $params = array ('rev' => $rev);
      if ($allpages > 1)
	$params['page'] = $page;
      else if ($page == 'all')
	$params['page'] = 'all';
      echo genQueryLink ($q, $params);
      echo '"><img src="'.$CONF['webxiang.url.photos'].'/';

      if ($index[$idx][$selectedSize]->directory)
	echo $index[$idx][$selectedSize]->directory.'/';
      else if (isset ($meta['directory'][$selectedSize]))
	echo $meta['directory'][$selectedSize].'/';

      echo $index[$idx][$selectedSize]->filename.'" alt="[photo]"';
      if ($index[$idx][$selectedSize]->width && $index[$idx][$selectedSize]->height)
        echo ' width="'.$index[$idx][$selectedSize]->width.'" height="'.$index[$idx][$selectedSize]->height.'"';
      echo ' /></a>';

      echo "</td></tr>\n";
      if (isset ($index[$idx]['date']) && $index[$idx]['date'])
	echo '<tr><td align="left"><span class="date">'.$index[$idx]['date']."</span></td></tr>\n";
      echo "</table>";

      if (isset ($index[$idx]['comment']) && $index[$idx]['comment'])
	echo "\n".'<div class="comment">'.$index[$idx]['comment'].'</div>';

      echo "\n";

      if (isset ($index[$idx]['description']) && $index[$idx]['description'])
	echo '<p class="description">'.htmlentities2($index[$idx]['description']).'</p>';

      if ($imgSize > 0)
      {
	echo '<div id="otherSizes">other sizes: ';
	if ($imgSize >= 0) {
	  if ($selectedSize == 0)
	    echo 'small';
	  else {
	    echo '<a href="';
	    $params = array ('rev'   => $rev,
			     'photo' => $photo,
			     'size'  => 'small');
	    if ($page == 'all') $params['page'] = 'all';
	    echo genQueryLink ($q, $params);
	    echo '"';
	    if ($index[$idx][0]->width && $index[$idx][0]->height)
	      echo ' rel="nofollow" title="'.$index[$idx][0]->width
		.' x '.$index[$idx][0]->height.' pixels"';
	    echo '>small</a>';
	  }
	}
	if ($imgSize >= 1) {
	  if ($selectedSize == 1)
	    echo ', medium';
	  else {
	    echo ', <a href="';
	    $params = array ('rev'   => $rev,
			     'photo' => $photo,
			     'size'  => 'medium');
	    if ($page == 'all') $params['page'] = 'all';
	    echo genQueryLink ($q, $params);
	    echo '"';
	    if ($index[$idx][1]->width && $index[$idx][1]->height)
	      echo ' rel="nofollow" title="'.$index[$idx][1]->width
		.' x '.$index[$idx][1]->height.' pixels"';
	    echo '>medium</a>';
	  }
	}
	if ($imgSize >= 2) {
	  if ($selectedSize == 2)
	    echo ', large';
	  else {
	    echo ', <a href="';
	    $params = array ('rev'   => $rev,
			     'photo' => $photo,
			     'size'  => 'large');
	    if ($page == 'all') $params['page'] = 'all';
	    echo genQueryLink ($q);
	    echo '"';
	    if ($index[$idx][2]->width && $index[$idx][2]->height)
	      echo ' rel="nofollow" title="'.$index[$idx][2]->width
		.' x '.$index[$idx][2]->height.' pixels"';
	    echo '>large</a>';
	  }
	}
	echo "</div>\n"; /* otherSizes */
      }
    }
  }
  else // photo index
  {
    ###### PHOTO INDEX ###############

    if ($meta['title'])
      echo '<div id="title">'.$meta['title']."</div>\n";
    else
      echo "<p />\n";

    if (is_numeric ($page) && $index_cnt > $limit)
      paging ();

    echo "\n<table class=\"thumbnails\">\n";

    $td_counter   = 1;
    $selectedSize = 0;
    $lastElement  = 0;

    if ($meta['reverseOrder'])
    {
      $index = array_reverse ($index);
      $lastElement = count ($index);
    }

    for ($i = $start; $i < $end; $i++)
    {
      if ($index[$i]['hidden'])
	continue;
      if (!isset ($index[$i][$selectedSize]))
	continue;

      if ($td_counter == 1)
	echo "<tr valign=\"top\">\n";

      echo ' <td align="center"><a href="';
      if (isset ($index[$i]['album'])) {
	echo genQueryLink ($index[$i]['album']);
      }
      else {
	$params = array ('rev' => $rev);
	if ($page == 'all') $params['page'] = 'all';
	if ($meta['reverseOrder'])
	  $params['photo'] = $lastElement - $i;
	else
	  $params['photo'] = $i + 1;
	echo genQueryLink ($q, $params);
      }
      echo '">';
      echo '<img src="'.$CONF['webxiang.url.photos'].'/';
      if ($index[$i][$selectedSize]->directory)
	echo $index[$i][$selectedSize]->directory.'/';
      else if (isset ($meta['directory'][$selectedSize]))
	echo $meta['directory'][$selectedSize].'/';

      echo $index[$i][$selectedSize]->filename.'" alt="[photo]"';
      if ($index[$i][$selectedSize]->width && $index[$i][$selectedSize]->height)
        echo ' width="'.$index[$i][$selectedSize]->width.'" height="'.$index[$i][$selectedSize]->height.'"';
      echo ' /></a>';

      if (isset ($index[$i]['album'])) {
        echo '<div class="enter"><br /><a href="'.genQueryLink ($index[$i]['album'])
	  .'">enter <em>'.($index[$i]['album']).'</em> &raquo;</a></div>';
      }
      if (isset ($index[$i]['comment']) && $index[$i]['comment'])
	echo '<div class="comment">'.$index[$i]['comment'].'</div>'."\n";

      echo "</td>\n";

      if ($td_counter == $meta['columns']) {
	$td_counter = 1;
	echo "</tr>\n";
      }
      else
	$td_counter++;
    }

    if ($td_counter != 1)
      echo "</tr>\n";

    echo "</table>\n";

    ##################################

    if (is_numeric ($page) && $index_cnt > $limit)
      paging ();
  }
}
else // gallery index
{
  @include 'inc/gallery-index.html';

  if (is_numeric ($page))
    count_pages ();

  if ($meta['title'])
    echo '<div id="title">'.$meta['title']."</div>\n";

  ###### GALLERY INDEX #############

  echo "\n<table class=\"thumbnails\">\n";

  $td_counter = 1;

  for ($i = $start; $i < $end; $i++)
  {
    if (!isset ($index[$i][0]))
      continue;

    if ($td_counter == 1)
      echo "<tr valign=\"top\">\n";

    echo ' <td align="center"><a href="'.genQueryLink ($index[$i]['album'])
      .'"><img src="'.$CONF['webxiang.url.photos'].'/';

    if ($index[$i][0]->directory)
      echo $index[$i][0]->directory.'/';
    else if (isset ($meta['directory'][$selectedSize]))
      echo $meta['directory'][$selectedSize].'/';

    echo $index[$i][0]->filename.'" alt="[photo]"';
    if ($index[$i][0]->width && $index[$i][0]->height)
      echo ' width="'.$index[$i][0]->width.'" height="'.$index[$i][0]->height.'"';

    echo ' /></a>';
    if (isset ($index[$i]['comment']) && $index[$i]['comment'])
      echo '<div class="comment">'.$index[$i]['comment'].'</div>';
    echo "</td>\n";

    if ($td_counter == $meta['columns']) {
      $td_counter = 1;
      echo "</tr>\n";
    }
    else
      $td_counter++;
  }

  if ($td_counter != 1)
    echo "</tr>\n";

  echo "</table>\n";

  ##################################

  if (is_numeric ($page) && $index_cnt > $limit)
    paging ();
}

if ($meta['copyright'])
  echo "\n<p class=\"copyright\">Copyright (C) ".$meta['copyright']."</p>\n";
?>
</div>

<script type="text/javascript">inif()</script>
<?php
  if ($CONF['webxiang.google.analytics']) {
    echo '<script type="text/javascript" src="http://www.google-analytics.com/ga.js"></script>
<script type="text/javascript">var tracker = _gat._getTracker (\''.
    $CONF['webxiang.google.analytics']."');
tracker._initData (); tracker._trackPageview ();</script>\n";
  }
?>
</body></html>
<?php

$duration = microtime_diff ($start_time, microtime ());
$duration = sprintf ("%0.6f", $duration);
print "\n<!-- processing took $duration seconds -->";
print "\n<!-- powered by WebXiangpianbu -->\n\n";

// FUNCTIONS

function genQueryLink ($q, $params = array ())
{
  global $CONF;

  $s = '';
  if ($CONF['webxiang.prettyURI'])
    $s .= $q . '/';
  else
    $s .= '?q='. $q;

  if ($CONF['webxiang.prettyURI']) {
    if (isset ($params['photo'])) {
      $s .= $params['photo'];
      unset ($params['photo']);
    }
    if (isset ($params['size'])) {
      $s .= '/'.$params['size'];
      unset ($params['size']);
    }
  }

  if (count ($params)) {
    $arr = array ();
    foreach ($params as $k => $v) {
      if (trim ($v) != '')
	array_push ($arr, $k.'='.urlencode ($v));
    }
    if (count ($arr)) {
      $s .= $CONF['webxiang.prettyURI'] ? '?' : '&amp;';
      $s .= implode ('&amp;', $arr);
    }
  }
  return $s;
}

function startElement ($parser, $element_name, $element_attributes)
{
  global $xml_state, $inside_parent, $inside_entry, $index, $index_cnt, $imgSize;
  $xml_state = $element_name;

  switch ($element_name)
  {
    case 'ENTRY':
      $inside_entry = true;
      $imgSize = -1;
      break;
    case 'PARENT':
      $inside_parent = true;
      break;
    case 'SMALL':
    case 'MEDIUM':
    case 'LARGE':
      if ($inside_entry)
      {
	$index[$index_cnt]['imgSize'] = ++$imgSize;
	$image = new Image ();

	if (isset ($element_attributes['WIDTH']))
	  $image->width     = trim ($element_attributes['WIDTH']);
	if (isset ($element_attributes['HEIGHT']))
	  $image->height    = trim ($element_attributes['HEIGHT']);
	if (isset ($element_attributes['DIRECTORY']))
	  $image->directory = trim ($element_attributes['DIRECTORY']);

	$index[$index_cnt][$imgSize]  = $image;
	$index[$index_cnt]['hidden']  = false;
      }
      break;
  }
}

function endElement ($parser, $element_name)
{
  global $xml_state, $index_cnt, $inside_parent, $inside_entry;
  $xml_state = '';

  switch ($element_name)
  {
    case 'ENTRY':
      $index_cnt++;
      $inside_entry = false;
      break;
    case 'PARENT':
      $inside_parent = false;
      break;
  }
}

function characterData ($parser, $data)
{
  global $xml_state, $index, $index_cnt;
  global $imgSize, $inside_parent, $inside_entry, $meta;

  if ($inside_entry)
  {
    switch ($xml_state)
    {
      case 'ALBUM':
	$index[$index_cnt]['album'] = trim ($data);
	break;
      case 'SMALL':
	$index[$index_cnt][$imgSize]->filename = trim ($data);
	break;
      case 'MEDIUM':
	$index[$index_cnt][$imgSize]->filename = trim ($data);
	break;
      case 'LARGE':
	$index[$index_cnt][$imgSize]->filename = trim ($data);
	break;
      case 'DATE':
	concat ($index[$index_cnt]['date'], $data);
	break;
      case 'COMMENT':
	concat ($index[$index_cnt]['comment'], $data);
	break;
      case 'DESCRIPTION':
	concat ($index[$index_cnt]['description'], $data);
	break;
      case 'COPYRIGHT':
	concat ($index[$index_cnt]['copyright'], $data);
	break;
      default:
	return;
    }
  }
  else if ($inside_parent)
  {
    switch ($xml_state)
    {
      case 'ALBUM':
	$meta['parent']['album'] = trim ($data);
	break;
      case 'TITLE':
	concat ($meta['parent']['title'], $data);
	break;
    }
  }
  else // inside meta
  {
    switch ($xml_state)
    {
      case 'SMALL':
	$meta['directory'][0] = trim ($data);
	break;
      case 'MEDIUM':
	$meta['directory'][1] = trim ($data);
	break;
      case 'LARGE':
	$meta['directory'][2] = trim ($data);
	break;
      case 'CHARSET':
	$meta['charset'] = trim ($data);
	break;
      case 'STYLE':
	$meta['style']   = trim ($data);
	break;
      case 'TITLE':
	concat ($meta['title'], $data);
	break;
      case 'PPP':
	$n = trim ($data);
	if (is_numeric ($n) && $n > 0)
	  $meta['ppp'] = $n;
	break;
      case 'COLUMNS':
	$n = trim ($data);
	if (is_numeric ($n) && $n > 0)
	  $meta['columns'] = $n;
	break;
      case 'REVERSE-ORDER':
	if (trim ($data) == 'true')
	  $meta['reverseOrder'] = true;
	break;
      case 'COPYRIGHT':
	concat ($meta['copyright'], $data);
	break;
      default:
	return;
    }
  }
}

function count_pages ()
{
  global $index_cnt, $page, $allpages;
  global $start, $end, $limit, $meta;

  $limit = $meta['ppp'];
  $start = $limit * ($page - 1);

  $allpages = ceil ($index_cnt / $limit);
  if ($page > $allpages)
    $page = $allpages;
  
  if (($start + $limit) > $index_cnt)
    $end = $index_cnt;
  else
    $end = $start + $limit;
}

function paging ()
{
  global $q, $allpages, $page, $rev;

  echo '<div class="pages">';

  $wa = 5;
  if ($page > 1) {
    echo '<a href="';
    echo genQueryLink ($q, array ('rev'  => $rev,
				  'page' => $page - 1));
    echo '" title="previous page">&laquo;</a> ';
  }

  if ($page <= $wa + 1)
    $cs = 1;
  else {
    $cs = $page - $wa;
    $back = $cs - 1;
    echo '<a href="';
    echo genQueryLink ($q, array ('rev'  => $rev,
				  'page' => $back));
    echo '" title="page '.$back.'">...</a> ';
  }

  $ce = $page + $wa;
  if ($ce >= $allpages)
    $ce = $allpages;
  else
    $next = $ce + 1;

  for ($i = $cs; $i <= $ce; $i++)
  {
    if ($page == $i)
      echo '<span class="thisPage">'.$i.'</span> ';
    else {
      echo '<a href="';
      echo genQueryLink ($q, array ('rev'  => $rev,
				    'page' => $i));
      echo '" title="page '.$i.'">'.$i.'</a> ';
    }
  }

  if ($ce < $allpages) {
    echo '<a href="';
    echo genQueryLink ($q, array ('rev'  => $rev,
				  'page' => $next));
    echo '" title="page '.$next.'">...</a> ';
  }

  if ($allpages > $page) {
    echo '<a href="';
    echo genQueryLink ($q, array ('rev'  => $rev,
				  'page' => $page + 1));
    echo '" title="next page">&raquo;</a>';
  }

  echo "</div>\n"; /* pages */
}

function getvars ($names)
{
  $arr = explode (',', $names);
  foreach ($arr as $v)
  {
    global $$v;
    if (empty ($$v))
      if (isset ($_REQUEST[$v]))
	$$v = trim ($_REQUEST[$v]);
  }
} 

function concat (&$s1, $s2 = '')
{
  if (!isset ($s1))
    $s1 = '';
  $s1 .= $s2;
}

function htmlentities2 ($htmlcode) {
  static $htmlEntities;
  static $entitiesDecoded;
  static $utf8Entities;
  if (!isset ($htmlEntities))
    $htmlEntities = array_values (get_html_translation_table (HTML_ENTITIES, ENT_QUOTES));
  if (!isset ($entitiesDecoded))
    $entitiesDecoded = array_keys (get_html_translation_table (HTML_ENTITIES, ENT_QUOTES));
  if (!isset ($utf8Entities)) {
    $num = count ($entitiesDecoded);
    for ($u = 0; $u < $num; $u++)
      $utf8Entities[$u] = '&#'.ord ($entitiesDecoded[$u]).';';
  }
  return str_replace ($htmlEntities, $utf8Entities, $htmlcode);
}

function microtime_diff ($a, $b)
{
  list ($a_dec, $a_sec) = explode (' ', $a);
  list ($b_dec, $b_sec) = explode (' ', $b);
  return $b_sec - $a_sec + $b_dec - $a_dec;
}

?>
