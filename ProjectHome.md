# pyComicMetaThis #

## Description ##
This Python script screen scrapes comic book metadata from ComicVine's api into the ComicBookInfo format as described [here](http://code.google.com/p/comicbookinfo/).  It was written for Mac OS X but theoretically should work on Windows or Unix as long as Python is installed.

## Download ##
You can get the latest (possibly unstable) version at the project's [source page](http://code.google.com/p/pycomicmetathis/source/browse/#svn/trunk)

## Misc ##
There's a setting in the newest version of the script for the path to the zip command.  If' you've recompiled zip with support for longer comments (highly recommended) as described in
[this posting](http://pixelverse.lefora.com/2010/11/23/cbr-to-cbz-conversion-with-commentstags-intact-a-t/#post0), you will want to change that setting to point to your recompiled version of zip.  If you don't do this and have a lot of metadata, extra newline characters are inserted by zip and will mangle your metadata.

This script uses the Python simplejson module which is included in Python 2.6 and higher.

## Donations ##
If you find this software to be of value and feel the need to donate money, please donate money to the charity of your choice.