<?php

//  WebXiangpianbu, version 0.994 (2005-06-29)
//  Copyright (C) 2004, 2005 Wojciech Polak.
//
//  This program is free software; you can redistribute it and/or modify
//  it under the terms of the GNU General Public License as published by
//  the Free Software Foundation; either version 2, or (at your option)
//  any later version.
//
//  This program is distributed in the hope that it will be useful,
//  but WITHOUT ANY WARRANTY; without even the implied warranty of
//  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//  GNU General Public License for more details.
//
//  You should have received a copy of the GNU General Public License
//  along with this program; if not, write to the Free Software Foundation,
//  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA

require 'config.php';

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
$meta['charset'] = 'US-ASCII';
$meta['style'] = 'style.css';
$meta['title'] = '';
$meta['ppp'] = 5;
$meta['columns'] = 1;
$meta['reverseOrder'] = false;
$meta['copyright'] = '';

$xml_state = '';
$inside_parent = false;
$inside_entry  = false;

if ($gdatadir)
  $filename = $gdatadir .'/'. $q . $gdataext;
else
  $filename = $q . $gdataext;

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
  header ("Location: $site/$photodir/$gscript");
  exit;
}

// XHTML

header ("Content-Type: text/html; charset=$meta[charset]");
echo '<?xml version="1.0" encoding="'.$meta['charset'].'"?>'."\n";

?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">

<head>
<title>[gallery] <? echo substr (strip_tags ($meta['title']), 0, 80); ?></title>
<meta http-equiv="Content-Type" content="text/html; charset=<? echo $meta['charset']; ?>" />
<meta name="author" content="Wojciech Polak" />
<meta name="generator" content="WebXiangpianbu" />
<meta name="robots" content="noindex,nofollow" />
<link rel="stylesheet" href="<? echo $gdatadir.'/css/'.$meta['style']; ?>" type="text/css" />
</head>
<body>

<table border="0" cellpadding="0" cellspacing="0" width="100%">
<tr><td align="center">
<table border="0" cellpadding="0" cellspacing="0" width="700">
<tr><td align="left">

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

  echo "<div class=\"center\">\n";
  echo '<span class="navigation">';
  echo '<a href="'.$site.'/'.$photodir.'/'.$gscript.'">all galleries</a>';
  if ($meta['parent']['album'])
  {
    echo ' / <a href="?q='.$meta['parent']['album'].'">';
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

    echo ' <a href="?q='.$q;
    if ($rev)
      echo '&amp;rev=1';
    echo '">'.$q.'</a>';
  }
  echo "</span>\n";

  switch (trim ($size))
  {
    case 'small':  $selectedSize = 0; break;
    case 'medium': $selectedSize = 1; break;
    case 'large':  $selectedSize = 2; break;
    default:
      $selectedSize = 1;
  }

  if (is_numeric ($photo))
  {
    echo '<p class="navigation">';

    if ($meta['reverseOrder'])
    {
      if ($photo < $index_cnt) {
	echo "<a href=\"?q=$q";
	if ($rev)
	  echo '&amp;rev=1';
 	if ($page == 'all')
 	  echo '&amp;page=all';
	echo "&amp;photo=".($photo+1);
	if ($size)
	  echo '&amp;size='.$size;
	echo "\">&laquo; previous</a>";
      }
      else
	echo "&laquo; previous";
      echo ' | ';
      if ($photo >= 2) {
	echo "<a href=\"?q=$q";
	if ($rev)
	  echo '&amp;rev=1';
	if ($page == 'all')
 	  echo '&amp;page=all';
	echo "&amp;photo=".($photo-1);
	if ($size)
	  echo '&amp;size='.$size;
	echo "\">next &raquo;</a>";
      }
      else
	echo "next &raquo;";
    }
    else // !reverseOrder
    {
      if ($photo >= 2) {
	echo "<a href=\"?q=$q";
	if ($rev)
	  echo '&amp;rev=1';
 	if ($page == 'all')
	  echo '&amp;page=all';
	echo "&amp;photo=".($photo-1);
	if ($size)
	  echo '&amp;size='.$size;
	echo "\">&laquo; previous</a>";
      }
      else
	echo "&laquo; previous";
      echo ' | ';
      if ($photo < $index_cnt) {
	echo "<a href=\"?q=$q";
	if ($rev)
	  echo '&amp;rev=1';
 	if ($page == 'all')
	  echo '&amp;page=all';
	echo "&amp;photo=".($photo+1);
	if ($size)
	  echo '&amp;size='.$size;
	echo "\">next &raquo;</a>";
      }
      else
	echo "next &raquo;";
    }

    echo "</p>\n";

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
      echo '<a href="?q='.$q;
      if ($rev)
	echo '&amp;rev=1';
      if ($allpages > 1)
	echo '&amp;page='.$page;
      else if ($page == 'all')
	echo '&amp;page=all';
      echo '"><img src="';

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
	echo '<p class="description">'.htmlentities($index[$idx]['description']).'</p>';

      if ($imgSize > 0)
      {
	echo '<p class="otherSizes">other sizes: ';
	if ($imgSize >= 0) {
	  if ($selectedSize == 0)
	    echo 'small';
	  else {
	    echo '<a href="?q='.$q;
	    if ($rev)
	      echo '&amp;rev=1';
 	    if ($page == 'all')
	      echo '&amp;page=all';
	    echo '&amp;photo='.$photo.'&amp;size=small"';
	    if ($index[$idx][0]->width && $index[$idx][0]->height)
	      echo ' title="'.$index[$idx][0]->width.' x '.$index[$idx][0]->height.' pixels"';
	    echo'>small</a>';
	  }
	}
	if ($imgSize >= 1) {
	  if ($selectedSize == 1)
	    echo ', medium';
	  else {
	    echo ', <a href="?q='.$q;
	    if ($rev)
	      echo '&amp;rev=1';
	    if ($page == 'all')
	      echo '&amp;page=all';
	    echo '&amp;photo='.$photo.'&amp;size=medium"';
	    if ($index[$idx][1]->width && $index[$idx][1]->height)
	      echo ' title="'.$index[$idx][1]->width.' x '.$index[$idx][1]->height.' pixels"';
	    echo'>medium</a>';
	  }
	}
	if ($imgSize >= 2) {
	  if ($selectedSize == 2)
	    echo ', large';
	  else {
	    echo ', <a href="?q='.$q;
	    if ($rev)
	      echo '&amp;rev=1';
	    if ($page == 'all')
	      echo '&amp;page=all';
	    echo '&amp;photo='.$photo.'&amp;size=large"';
	    if ($index[$idx][2]->width && $index[$idx][2]->height)
	      echo ' title="'.$index[$idx][2]->width.' x '.$index[$idx][2]->height.' pixels"';
	    echo'>large</a>';
	  }
	}
	echo "</p>\n";
      }
    }
  }
  else // photo index
  {
    ###### PHOTO INDEX ###############

    if ($meta['title'])
      echo '<p class="title">'.$meta['title']."</p>\n";
    else
      echo "<p />\n";

    echo "<table class=\"thumbnails\">\n";

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

      echo ' <td align="center"><a href="?q='.$q;
      if ($rev)
	echo '&amp;rev=1';
      if ($page == 'all')
	echo '&amp;page=all';
      if ($meta['reverseOrder'])
	echo '&amp;photo='.($lastElement - $i).'">';
      else
	echo '&amp;photo='.($i+1).'">';

      echo '<img src="';

      if ($index[$i][$selectedSize]->directory)
	echo $index[$i][$selectedSize]->directory.'/';
      else if (isset ($meta['directory'][$selectedSize]))
	echo $meta['directory'][$selectedSize].'/';

      echo $index[$i][$selectedSize]->filename.'" alt="[photo]"';
      if ($index[$i][$selectedSize]->width && $index[$i][$selectedSize]->height)
        echo ' width="'.$index[$i][$selectedSize]->width.'" height="'.$index[$i][$selectedSize]->height.'"';
      echo ' /></a>';

      if (isset ($index[$i]['album']))
        echo '<br /><a href="?q='.$index[$i]['album'].'">&raquo; enter &laquo;</a>';

      if (isset ($index[$i]['comment']) && $index[$i]['comment'])
	echo '<br /><span class="comment">'.$index[$i]['comment'].'</span>'."\n";

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
  echo "</div>\n";
}
else // gallery index
{
  @include 'inc/gallery-index.html';

  if (is_numeric ($page))
    count_pages ();

  if ($meta['title'])
    echo '<p class="title">'.$meta['title']."</p>\n";

  ###### GALLERY INDEX #############

  echo "<table class=\"thumbnails\">\n";

  $td_counter = 1;

  for ($i = $start; $i < $end; $i++)
  {
    if (!isset ($index[$i][0]))
      continue;

    if ($td_counter == 1)
      echo "<tr valign=\"top\">\n";

    echo ' <td align="center"><a href="?q='.$index[$i]['album'].'"><img src="';

    if ($index[$i][0]->directory)
      echo $index[$i][0]->directory.'/';
    else if (isset ($meta['directory'][$selectedSize]))
      echo $meta['directory'][$selectedSize].'/';

    echo $index[$i][0]->filename.'" alt="[photo]"';
    if ($index[$i][0]->width && $index[$i][0]->height)
      echo ' width="'.$index[$i][0]->width.'" height="'.$index[$i][0]->height.'"';

    echo ' /></a>';
    if (isset ($index[$i]['comment']) && $index[$i]['comment'])
      echo '<br /><span class="comment">'.$index[$i]['comment'].'</span>';

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
  {
    echo '<div align="center">';
    paging ();
    echo '</div>';
  }
}

if ($meta['copyright'])
  echo '<p class="copyright">Copyright (C) '.$meta['copyright']."</p>\n";

$duration = microtime_diff ($start_time, microtime ());
$duration = sprintf ("%0.6f", $duration);
print "\n<!-- processing took $duration seconds -->";
print "\n<!-- powered by WebXiangpianbu -->\n\n";

?>
</td></tr></table>
</td></tr></table>

</body></html>
<?php

// FUNCTIONS

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

  echo '<p class="pages">';

  $wa = 5;
  if ($page > 1) {
    echo '<a href="?q='.$q;
    if ($rev)
      echo '&amp;rev=1';
    echo '&amp;page='.($page-1).'" title="previous page">&laquo;</a> ';
  }

  if ($page <= $wa + 1)
    $cs = 1;
  else {
    $cs = $page - $wa;
    $back = $cs - 1;
    echo '<a href="?q='.$q;
    if ($rev)
      echo '&amp;rev=1';
    echo '&amp;page='.$back.'">...</a> ';
  }

  $ce = $page + $wa;
  if ($ce >= $allpages)
    $ce = $allpages;
  else
    $next = $ce + 1;

  for ($i = $cs; $i <= $ce; $i++)
  {
    if ($page == $i)
      echo "$i ";
    else {
      echo '<a href="?q='.$q;
      if ($rev)
	echo '&amp;rev=1';
      echo '&amp;page='.$i.'">'.$i.'</a> ';
    }
  }

  if ($ce < $allpages) {
    echo '<a href="?q='.$q;
    if ($rev)
      echo '&amp;rev=1';
    echo '&amp;page='.$next.'">...</a> ';
  }

  if ($allpages > $page) {
    echo '<a href="?q='.$q;
    if ($rev)
      echo '&amp;rev=1';
    echo '&amp;page='.($page+1).'" title="next page">&raquo;</a>';
  }

  echo "</p>\n";
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

function microtime_diff ($a, $b)
{
  list ($a_dec, $a_sec) = explode (' ', $a);
  list ($b_dec, $b_sec) = explode (' ', $b);
  return $b_sec - $a_sec + $b_dec - $a_dec;
}

?>
