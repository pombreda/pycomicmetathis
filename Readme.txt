pyComicMetaThis.py 0.2 (2010-12-07)
Copyright (c) MMX, Andre <andre.messier@gmail.com>;Sasha <sasha@goldnet.ca>

    ComicBookInfo (CBI) implementation
    See http://code.google.com/p/comicbookinfo for information on CBI.

    Usage:
    pyComicMetaThis.py [command] [options]

    Calling with no commands/options will iterate through the current
    folder updating all CBZ files.  You will be prompted for series 
    name and issue number for any CBZ files that don't have a CBI header
    or don't have those values filled out in the current CBI header.

    Commands:
      get		read CBI from .cbz file
      set		write CBI to .cbz file
      autoset		set metadata from ComicVine database
			using autoset causes all other options
			to be ignored.  Autoset options are 
			set by editing the script.
	
    Options:
      --version		print version and exit
      -h, --help		print this message and exit
      -f..., -f=...		subject .cbz file
      -s.., --series=...	set/get series name
      -t..., --title=...	set/get comic book title
      -p..., --publisher...	set/get comic book publisher
      -i..., --issue...	set/get comic book issue
      -v..., --volume...	set/get comic book volume
      -d..., --date...	set/get comic book date [format MM-YYYY]
      -c, --credits		get comic book credits


Some features can be set by editing the script.

updateTags: set the "tag" values
updateCredits: set the "credit" tags
purgeExistingTags: if set to True, will delete existing tags first.  Set this to False if you want to preserve your existing tags.  This will result in duplicate tags if you have this set to False and run the script repeatedly.
purgeExistingTags: if set to True, will delete existing credits first.  Set this to False if you want to preserve your existing credits.  This will result in duplicate tags if you have this set to False and run the script repeatedly.
includeCharactersAsTags: if set to True, character listing will be included as Tags
includeItemsAsTags: if set to True, item listing will be included as Tags
includeDescriptionAsComment: if set to True, issue description will be set as Comment
interactiveMode: if set to True, you will be prompted to resolve cases where more than one issue matches the search.
logFileName: file that will log any issues that can't be determined automatically if you are running in non-interactive mode.
promptSeriesNameIfBlank: Do you want to be asked for the issue name if it can't be determined?
assumeDirIsSeries: is the file in a folder named for the series?  If this is True, you will never be prompted for the issue name.
displayIssueDescriptionOnDupe: Do you want the issue's description shown when more than one match is found?
displaySeriesDescriptionOnDupe: Do you want the series' description shown when more than one match is found? 
maxDescriptionLength: How many characters of the description do you want to see?
searchSubFolders: Check subfolders for CBZ files?
