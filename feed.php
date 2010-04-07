<?php

//  WebXiangpianbu, feed.php
//  Copyright (C) 2010 Wojciech Polak.
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

require 'config.php';
if (!isset ($CONF)) exit;

$files = array ();
$max_entries = $CONF['webxiang.feed.maxentries'];

if (isset ($CONF['webxiang.feed.whitealbums'])) {
  $albums = $CONF['webxiang.feed.whitealbums'];
}
else {
  $albums = array ();
  $d = @dir ($CONF['webxiang.path.albums']) or exit;
  while (false !== ($entry = $d->read ()))
    {
      if ($entry[0] == '.' || $entry == 'index.xml')
	continue;
      if (substr ($entry, -3) != 'xml')
	continue;
      $albums[] = $entry;
    }
}

foreach ($albums as $album) {
  $xml = simplexml_load_file ($CONF['webxiang.path.albums'].'/'.$album);
  $entries = $xml->xpath ('//entry');

  if ($xml->meta->{'reverse-order'} == true)
    $entries = array_reverse ($entries);
  $len = count ($entries);

  $count = 0;
  foreach ($entries as $i => $e) {

    $s_file = $CONF['webxiang.url.photos'].'/';
    if ($xml->meta->directory->small)
      $s_file .= $xml->meta->directory->small.'/';
    $s_file .= $e->image->small;

    $m_file = $CONF['webxiang.url.photos'].'/';
    if ($xml->meta->directory->medium)
      $m_file .= $xml->meta->directory->medium.'/';
    $m_file .= $e->image->medium;

    $f = array ('s_name'   => $s_file,
		'm_name'   => $m_file,
		'mtime'    => @filemtime ($s_file),
		'groupdate'=> date ('YmdH', @filemtime ($m_file)),
		'album'    => substr ($album, 0, -4),
		's_width'  => $e->image->small->attributes ()->width,
		's_height' => $e->image->small->attributes ()->height);

    if ($e->image->medium) {
      $f['m_width']  = $e->image->medium->attributes ()->width;
      $f['m_height'] = $e->image->medium->attributes ()->height;
    }

    if ($xml->meta->{'reverse-order'} == true)
      $f['index'] = $len - $i;
    else
      $f['index'] = $i + 1;

    if ($e->copyright)
      $f['copyright'] = $e->copyright;
    else if ($xml->meta->copyright)
      $f['copyright'] = $xml->meta->copyright;

    $files[] = $f;
    if ($count > $max_entries)
      break;
    $count++;
  }
}

usort ($files, 'sort_mtime_desc');

$groups = array ();
foreach ($files as $v)
{
  if (!isset ($groups[$v['groupdate']]))
    $groups[$v['groupdate']] = array ();
  array_push ($groups[$v['groupdate']], $v);
}
foreach ($groups as $k => $v)
{
  usort ($groups[$k], 'sort_mtime_asc');
}

$groups = array_slice ($groups, 0, $max_entries);
$pubdate = gmdate ('Y-m-d\TH:i:s\Z', $files[0]['mtime']);

header ('Content-Type: application/atom+xml; charset=UTF-8');
echo "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n";

echo '
<feed xmlns="http://www.w3.org/2005/Atom"
  xmlns:media="http://search.yahoo.com/mrss/">
  <title>Photo Gallery</title>
  <updated>'.$pubdate.'</updated>
  <generator>WebXiangpianbu</generator>
  <id>'.$CONF['webxiang.feed.taguri'].'</id>
  <author><name>'.$CONF['webxiang.feed.author.name'].'</name></author>
  <link rel="self" type="application/atom+xml" href="'.$CONF['webxiang.url.site'].'/feed.xml"/>
  <link rel="alternate" type="text/html" href="'.$CONF['webxiang.url.site'].'/"/>
';

foreach ($groups as $files)
{
  $v = $files[0];

  $dt = gmdate ('Y-m-d\TH:i:s\Z', $v['mtime']);
  $album = $CONF['webxiang.url.site'].'/'.$v['album'];

  echo '
  <entry>
    <id>'.$CONF['webxiang.feed.taguri'].'/'.$v['groupdate'].'</id>
    <author><name>'.$CONF['webxiang.feed.author.name'].'</name></author>
    <updated>'.$dt.'</updated>'."\n";
  if (count ($files) > 1)
    echo '    <title>Posted Photos in '.ucfirst ($v['album']).'</title>
    <link rel="alternate" type="text/html" href="'.$album.'/"/>';
  else
    echo '    <title>Posted Photo '.substr (basename ($v['m_name']), 0, -4).'</title>
    <link rel="alternate" type="text/html" href="'.$album.'/'.$v['index'].'"/>';
  echo '
    <rights>'.$v['copyright'].'</rights>
    <content type="xhtml" xml:space="preserve">
    <div xmlns="http://www.w3.org/1999/xhtml">
      <p class="thumbnails">'."\n";
  $s = array ();
  foreach ($files as $v) {
    if (in_array ($v['s_name'], $s))
      continue;
    echo '        <a href="'.$CONF['webxiang.url.site'].'/'.$v['album'].'/'.
      $v['index'].'"><img src="'.$CONF['webxiang.url.site'].'/'.
      $v['s_name'].'" alt="photo" width="'.$v['s_width'].'" height="'.
      $v['s_height'].'" /></a>'."\n";
    array_push ($s, $v['s_name']);
  }
  echo '      </p>
    </div>
    </content>'."\n";
  $s = array ();
  foreach ($files as $v) {
    if (in_array ($v['s_name'], $s))
      continue;
    echo '    <media:content url="'.$CONF['webxiang.url.site'].'/'.
      $v['m_name'].'" medium="image" type="image/jpeg" width="'.$v['m_width'].
      '" height="'.$v['m_height'].'"/>'."\n";
    array_push ($s, $v['s_name']);
  }
  echo '  </entry>
';
}

echo "</feed>\n";

function sort_mtime_desc ($a, $b) {
  if ($a['mtime'] == $b['mtime']) {
    return 0;
  }
  return ($a['mtime'] > $b['mtime']) ? -1 : 1;
}

function sort_mtime_asc ($a, $b) {
  if ($a['mtime'] == $b['mtime']) {
    return 0;
  }
  return ($a['mtime'] < $b['mtime']) ? -1 : 1;
}

?>
