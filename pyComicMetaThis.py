#!/usr/bin/python

"""
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
      -z, --zerocache           override use of seriesID.txt cache file.
"""
__program__ = 'pyComicMetaThis.py'
__version__ = '0.2k'
__author__ = "Andre (andre.messier@gmail.com)"
__date__ = "2011-03-09"
__copyright__ = "Copyright (c) MMX, Andre <andre.messier@gmail.com>;Sasha <sasha@goldnet.ca>"
__license__ = "GPL"

import sys
import urllib
import subprocess
import zipfile
import time
import decimal 
import getopt
import os.path
import re
import ConfigParser
try: import simplejson as json
except ImportError: import json


configFile = './pyComicMetaThis.conf'

APIKEY="e75dd8dd18cfdd80e1638de4262ed47ed890b96e"

updateTags = True
updateCredits = True
# setting purgeExistingTags or purgeExistingCredits to False 
# could be dangerous if you run this on the same files 
# repeatedly as the tags will be duplicated
purgeExistingTags = True
purgeExistingCredits = True
includeCharactersAsTags = True
includeItemsAsTags = True
includeStoryArcAsTags = True
includeDescriptionAsComment = True
# interactiveMode will prompt the user for series and issue info 
# if it can't be determined automatically.  If interactiveMode
# is turned off, the file will be skipped
interactiveMode = True

# if interactiveMode is disabled, any issues that can't be
# identified automatically will be logged to this file.
# The file is appended to.
logFileName = 'pyComicMetaThis.log'

# if the series name can't be determined by looking at the CBI
# ask the user to enter it.  Cannot be used if assumeDirIsSeries
# is set to True 
promptSeriesNameIfBlank = True
# if the series name can't be determined AND promptSeriesNameIfBlank
# is set to False, ask the user to enter the series ID
promptSeriesIdIfBlank = False
# if the series name is blank assume the directory is named after
# the series.  Setting this to true will cause the 
# promptSeriesNameIfBlank flag to be ignored.
assumeDirIsSeries = False

# if more than one match is found and we are in interactiveMode
# these flags determine if the Issue description and/or
# series description are displayed
displayIssueDescriptionOnDupe = True
displaySeriesDescriptionOnDupe = True

# how many characters of the issues/series description to show
# if the includeDescriptionAsComment is true, this will also
# limit how many characters are used there
maxDescriptionLength = 800

searchSubFolders = True
showSearchProgress = False

# if you've recompiled zip with support for longer comments, set the 
# zipCommand variable to the path to the new version
# without this, ComicBookInfo records over 256 characters
# will not work properly
zipCommand = "/bin/ziplong"
#zipCommand = "zip"

# as an optimization you can set the useSeriesCacheFile value
# to true.  This will save the first seriesId found in 
# a folder in a file called seriesId.txt.  All subsequent
# files in that folder will will be assumed to be in the 
# same series
useSeriesCacheFile = True

# if you want the first year the series was published
# to be used as the "volume" set useStartYearAsVolume to 
# True.  Otherwise set it to False.  Currently setting 
# it to False means Volume will be left blank
useStartYearAsVolume = True

# userSeriesWhenNoTitle: if the issue doesn't have a title, 
# use the series name plus issue number as the title
# padIssueNumber: how many characters you want the issue 
# number to be in the title.  Zeroes will be used to pad
# to this length 
useSeriesWhenNoTitle = False
padIssueNumber = 3

#list of fields to display when more than one series is found
# valid options are id, name, publisher, start_year, description, count_of_issues, aliases
# id is REQUIRED
seriesDisplayFields = ['name','publisher','start_year','description','count_of_issues','id','aliases']

# amount of logging desired.  0 is none.  1 logs the filenames that
# can't be processed. 2 logs an error message along with the filename
logLevel = 1

baseURL="http://api.comicvine.com/"
searchURL = baseURL + 'search'
issueURL = baseURL + 'issue'

# maybe we'll add .cbr support?
fileExtList = [".cbz"]

def usage ():
	print __program__ + " " +__version__+ " (" + __date__ + ")"
	print __copyright__
	print __doc__

def readConfig():
	if os.path.exists(configFile) == True:
		print 'Config file found.  Reading options...'
		config = ConfigParser.ConfigParser()
		config.read(configFile)
		baseURL = config.get('ComicVine','baseURL')
		searchURL = config.get('ComicVine','searchURL')
		issueURL = config.get('ComicVine','issueURL')
		APIKEY = config.get('ComicVine', 'APIKEY')
		logLevel = config.get('Preferences', 'logLevel')
		try:
			seriesDisplayFields = config.get('Preferences', 'seriesDisplayFields')
		except ConfigParser.NoOptionError:
			pass
		try:
			padIssueNumber = config.get('Preferences', 'padIssueNumber')
		except ConfigParser.NoOptionError:
			pass
		try:
			useSeriesWhenNoTitle = config.get('Preferences', 'useSeriesWhenNoTitle')
		except ConfigParser.NoOptionError:
			pass
		try:
			useStartYearAsVolume = config.get('Preferences', 'useStartYearAsVolume')
		except ConfigParser.NoOptionError:
			pass
		try:
			useSeriesCacheFile = config.get('Preferences', 'useSeriesCacheFile')
		except ConfigParser.NoOptionError:
			pass
		try:
			zipCommand = config.get('Preferences', 'zipCommand')
		except ConfigParser.NoOptionError:
			pass
		try:
			showSearchProgress = config.get('Preferences', 'showSearchProgress')
		except ConfigParser.NoOptionError:
			pass
		try:
			searchSubFolders = config.get('Preferences', 'searchSubFolders')
		except ConfigParser.NoOptionError:
			pass
		try:
			maxDescriptionLength = config.get('Preferences', 'maxDescriptionLength')
		except ConfigParser.NoOptionError:
			pass
		try:
			displaySeriesDescriptionOnDupe = config.get('Preferences', 'displaySeriesDescriptionOnDupe')
		except ConfigParser.NoOptionError:
			pass
		try:
			displayIssueDescriptionOnDupe = config.get('Preferences', 'displayIssueDescriptionOnDupe')
		except ConfigParser.NoOptionError:
			pass
		try:
			assumeDirIsSeries = config.get('Preferences', 'assumeDirIsSeries')
		except ConfigParser.NoOptionError:
			pass
		try:
			promptSeriesNameIfBlank = config.get('Preferences','promptSeriesNameIfBlank')
		except ConfigParser.NoOptionError:
			pass
		try:
			promptSeriesIdIfBlank = config.get('Preferences','promptSeriesIdIfBlank')
		except ConfigParser.NoOptionError:
			pass
		try:
			logFileName = config.get('Preferences', 'logFileName')
		except ConfigParser.NoOptionError:
			pass
		try:
			interactiveMode = config.get('Preferences', 'interactiveMode')
		except ConfigParser.NoOptionError:
			pass
		try:
			includeDescriptionAsComment = config.get('Preferences', 'includeDescriptionAsComment')
		except ConfigParser.NoOptionError:
			pass
		try:
			includeStoryArcAsTags = config.get('Preferences', 'includeStoryArcAsTags')
		except ConfigParser.NoOptionError:
			pass
		try:
			includeItemsAsTags = config.get('Preferences', 'includeItemsAsTags')
		except ConfigParser.NoOptionError:
			pass
		try:
			includeCharactersAsTags = config.get('Preferences','includeCharactersAsTags')
		except ConfigParser.NoOptionError:
			pass
		try:
			purgeExistingCredits = config.get('Preferences','purgeExistingCredits')
		except ConfigParser.NoOptionError:
			pass
		try:
			purgeExistingTags = config.get('Preferences', 'purgeExistingTags')
		except ConfigParser.NoOptionError:
			pass
		try:
			updateCredits = config.get('Preferences','updateCredits')
		except ConfigParser.NoOptionError:
			pass
		try:
			updateTags = config.get('Preferences', 'updateTags')
		except ConfigParser.NoOptionError:
			pass

	#else:
	#	createConfig()

def createConfig():
	if os.path.exists(configFile) == True:
		print 'Config file already exists'
	else:
		print 'No config file found.  Creating one...'
		config = ConfigParser.ConfigParser()
		config.add_section('ComicVine')
		config.set('ComicVine', 'issueURL', issueURL)
		config.set('ComicVine', 'searchURL', searchURL)
		config.set('ComicVine', 'baseURL', baseURL)
		config.set('ComicVine', 'APIKEY', APIKEY)
		config.add_section('Preferences')
		config.set('Preferences', 'logLevel', logLevel)
		config.set('Preferences', 'seriesDisplayFields', seriesDisplayFields)
		config.set('Preferences', 'padIssueNumber', padIssueNumber)
		config.set('Preferences', 'useSeriesWhenNoTitle', useSeriesWhenNoTitle)
		config.set('Preferences', 'useStartYearAsVolume', useStartYearAsVolume)
		config.set('Preferences', 'useSeriesCacheFile', useSeriesCacheFile)
		config.set('Preferences', 'zipCommand', zipCommand)
		config.set('Preferences', 'showSearchProgress', showSearchProgress)
		config.set('Preferences', 'searchSubFolders', searchSubFolders)
		config.set('Preferences', 'maxDescriptionLength', maxDescriptionLegnth)
		config.set('Preferences', 'displaySeriesDescriptionOnDupe', displaySeriesDescriptionOnDupe)
		config.set('Preferences', 'displayIssueDescriptionOnDupe', displayIssueDescriptionOnDupe)
		config.set('Preferences', 'assumeDirIsSeries', assumeDirIsSeries)
		config.set('Preferences', 'promptSeriesNameIfBlank', promptSeriesNameIfBlank)
		config.set('Preferences', 'promptSeriesIdIfBlank', promptSeriesIdIfBlank)
		config.set('Preferences', 'logFileName', logFileName)
		config.set('Preferences', 'interactiveMode', interactiveMode)
		config.set('Preferences', 'includeDescriptionAsComment', includeDescriptionAsComment)
		config.set('Preferences', 'includeStoryArcAsTags', includeStoryArcAsTags)
		config.set('Preferences', 'includeItemsAsTags', includeItemsAsTags)
		config.set('Preferences', 'includeCharactersAsTags', includeCharactersAsTags)
		config.set('Preferences', 'purgeExistingCredits', purgeExistingCredits)
		config.set('Preferences', 'purgeExistingTags', purgeExistingTags)
		config.set('Preferences', 'updateCredits', updateCredits)
		config.set('Preferences', 'updateTags', updateTags)

		with open(configFile, 'wb') as confFile:
			config.write(confFile)
		
	readConfig()

def blankCBI():
	emptyCBIContainer = {}
	emptyCBI = {}
	emptyCBI['series'] = ''
	emptyCBI['issue'] = ''
	emptyCBIContainer['ComicBookInfo/1.0'] = emptyCBI
	emptyCBIContainer['appID'] = __program__ + '/' + __version__
	emptyCBIContainer['lastModified'] = time.strftime("%Y-%m-%d %H:%M%S +0000", time.gmtime())
	return emptyCBIContainer

def remove_html_tags(data):
	p = re.compile(r'<[^<]*?>')
	datastring = p.sub('',data)
	datastring = remove_html_escapes(datastring)
	return datastring

def remove_html_escapes(data):
	data = data.replace('&nbsp;',' ')
	data = data.replace('&amp;','&')
	return data

def getfiles(directory):
	entries = os.listdir(directory)
	fileList = [f for f in entries if os.path.splitext(f)[1].lower() in fileExtList and len(os.path.splitext(f)[0]) and os.path.isfile(os.path.join(directory, f))]
	fileList.sort()
	dirList = []
	if searchSubFolders == True:
		# Get a list of all sub dirs 
		dirList = [d for d in entries if os.path.isdir(os.path.join(directory, d)) and not d[0] == '.']
		dirList.sort()	
	return (fileList,dirList)

def readComment(dir, filename):
	# I was using pythons ZipFile object but it doesn't seem to handle zipcomments well

	# read the zip comment into a temp text file
	txtFile = os.path.join(dir, filename) + '.txt'
	cmdLine = ' unzip -z "' + os.path.join(dir, filename) + '" > "' + txtFile + '"'
	#p1 = subprocess.Popen(['unzip','-z','"' + os.path.join(dir,filename) + '"'], stdout=PIPE)
	#p2 = subprocess.Popen(["tr","-d","\r"], stdin=p1.stdout, stdout=PIPE)
	#print cmdLine
	p = subprocess.Popen(cmdLine, shell=True)
	os.waitpid(p.pid,0)

	# strip the first line since it just tells us the filename and isn't part of the JSON header
	txtFile2 = os.path.join(dir, filename) + '_.txt'
	cmdLine = 'sed \'1d\' "' + txtFile  + '"  > "' + txtFile2 + '"' 
	#cmdLine = 'tr -d \'\\n\' <  "' + txtFile  + '" > "' + txtFile2 + '"'
	#print cmdLine
	p = subprocess.Popen(cmdLine, shell=True)
	os.waitpid(p.pid,0)
	os.remove(txtFile)

	# strip newline characters from the file
	# which should leave us with the json 
	#jsonFile = os.path.join(dir, filename) + '.json'
	jsonFile = os.path.join(dir, filename) + '.json'

	cmdLine = 'tr -d \'\\n\' <  "' + txtFile2  + '" > "' + jsonFile + '"'
	#cmdLine = 'sed \'1d\' ' + txtFile2  + '  > ' + jsonFile 
	#print cmdLine
	p = subprocess.Popen(cmdLine, shell=True)
	os.waitpid(p.pid,0)
	os.remove(txtFile2)	

	# read the comment file into a variable and strip the newlines
	time.sleep(2)	
	cbzComment = ''
	file = open(jsonFile, 'r')
	for line in file:
		cbzComment += line.strip()

	#archivefile = file(filename)
	#cbz = zipfile.ZipFile(archivefile)
	#cbzComment = cbz.comment
	#cbz.close()
	cbzComment = cbzComment.replace('\r\n','')
	#print cbzComment
	return cbzComment	

def fixSpaces(title):
	placeholders = ['[-._]','  +']
	for ph in placeholders:
		title = re.sub(ph, ' ', title)
	print "After fixing spaces, title is: " + title
	return title

def parseIssueNumberFromName(filename):
	issueNumber = ''
	# remove the extension
	filename = os.path.splitext(filename)[0]
	# replace any name seperators with spaces
	filename = fixSpaces(filename)
	fileWords = filename.split(' ')
	# assume the last number in the filename that is under 4 digits is the issue number
	for word in reversed(fileWords):
		if issueNumber == 0 and word.isdigit() == True and len(word) < 4:
			issueNumber = word
	issueNumber = issueNumber.lstrip("0")
	return issueNumber

def searchByFileName(filename):
	issueId = 0
	seriesId = 0
	seriesName = ''
	issueNumber = 0
	# remove the extension
	filename = os.path.splitext(filename)[0]
	# replace any name seperators with spaces
	filename = fixSpaces(filename)
	issueList = {}
	cvBaseSearchURL = searchURL + '?api_key=' + APIKEY + '&query=' + urllib.quote(filename) + '&resources=issue' 
	#TODO: after this is working, limit the results to the fields we use
	#cvBaseSearchURL = cvBaseSearchURL + '&field_list=name,start_year,id,description,issue_number'
	cvBaseSearchURL = cvBaseSearchURL + '&format=json'
	offset = 0
	cvSearchURL = cvBaseSearchURL
	print 'Querying the ComicVine for the Issue based on the filename...'
	cvSearchResults = json.load(urllib.urlopen(cvSearchURL))
	resultCount = cvSearchResults['number_of_page_results']
	if resultCount == 1:
		seriesId = cvSearchResults['results'][0]['volume']['id']
		seriesName = cvSearchResults['results'][0]['volume']['name']
		issueId = cvSearchResults['results'][0]['id']
		issueNumberD = decimal.Decimal(str(cvSearchResults['results'][0]['issue_number'] ))
		issueNumberI = int(issueNumberD)
		issueNumber = str(issueNumberI).rstrip()
	return issueId, seriesId, seriesName,issueNumber

def searchForIssue(seriesName, issueNumber, seriesId):
	issueList = {}
	#TODO: if we have a seriesID but no seriesName, use that in our query
	
	if seriesId != 0:
		#cvBaseSearchURL = baseURL + 'volume/' + str(seriesId) + '/' + APIKEY + '&query=' + urllib.quote(issueNumber) + '&resources=issue'
		cvBaseSearchURL = baseURL + 'volume/' + str(seriesId) + '/?api_key=' + APIKEY + '&field_list=count_of_issues'
		cvBaseSearchURL = cvBaseSearchURL + '&format=json'
		cvSearchURL = cvBaseSearchURL
		resultCount = 0
		if showSearchProgress == True:
			print cvSearchURL
		print 'Querying ComicVine for the IssueID...'
		i = 0
		cvSearchResults = json.load(urllib.urlopen(cvSearchURL))
		resultCount = cvSearchResults['results']['count_of_issues']
		if resultCount == 0:
			print 'No issues found for the series'
		for issue in cvSearchResults['results']['issues']:
			i = i + 1
			if showSearchProgress == True:
				print i
			currentIssueD = decimal.Decimal(str(issue['issue_number']))
			currentIssueI = int(currentIssueD)
			currentIssue = str(currentIssueI).rstrip()
			# for those odd issue number 0.5
			if currentIssueD == decimal.Decimal(issueNumber):
					comic = {}
					comic['id'] = issue['id']
					comic['name'] = issue['name']
					comic['description'] = ''
					issueList[issue['id']] = comic
			if currentIssue == issueNumber:
					comic = {}
					comic['id'] = issue['id']
					comic['name'] = issue['name']
					comic['description'] = ''
					issueList[issue['id']] = comic
		resultCount = resultCount - 1
		return issueList
	if seriesName != '':
		cvBaseSearchURL = searchURL + '?api_key=' + APIKEY + '&query=' + urllib.quote(seriesName + ' ' + issueNumber) + '&resources=issue' 
	
	#TODO: after this is working, limit the results to the fields we use
	#cvBaseSearchURL = cvBaseSearchURL + '&field_list=name,start_year,id,description,issue_number'
	cvBaseSearchURL = cvBaseSearchURL + '&format=json'
	offset = 0
	resultCount = 20
	cvSearchURL = cvBaseSearchURL
	if showSearchProgress == True:
		print cvSearchURL
	print 'Querying ComicVine for the Issue...'
	i = 0
	while resultCount >= 20:
		cvSearchResults = json.load(urllib.urlopen(cvSearchURL))
		resultCount = cvSearchResults['number_of_page_results']
		if resultCount == 0:
			print 'No issues found for the series'
		for issue in cvSearchResults['results']:
			i = i + 1
			if showSearchProgress == True:
				print i
			if issue['resource_type'] == 'issue' and str(issue['volume']['id']) == str(seriesId):
				currentIssueD = decimal.Decimal(str(issue['issue_number']))
				currentIssueI = int(currentIssueD)
				currentIssue = str(currentIssueI).rstrip()
				if currentIssue == issueNumber:
					comic = {}
					comic['id'] = issue['id']
					comic['name'] = issue['name']
					comic['description'] = issue['description']
					issueList[issue['id']] = comic
		offset = offset + resultCount
		cvSearchURL = cvBaseSearchURL + '&offset=' + str(offset)
	return issueList

def searchForSeries(seriesName, offset=0):
	seriesList = {}
	cvBaseSearchURL = searchURL + '?api_key=' + APIKEY + '&query=' + urllib.quote(seriesName) 
	csBaseSearchURL = searchURL + '&resources=volume'
	#cvBaseSearchURL = cvBaseSearchURL + '&field_list=volume,name,start_year,id,description'
	cvBaseSearchURL = cvBaseSearchURL + '&format=json'
	offset = 0
	resultCount = 20
	cvSearchURL = cvBaseSearchURL 
	print 'Querying ComicVine for the Series...'
	i = 0
	while resultCount >= 20:
		cvSearchResults = json.load(urllib.urlopen(cvSearchURL))
		resultCount = cvSearchResults['number_of_page_results']
		for series in cvSearchResults['results']:
			i = i + 1
			if showSearchProgress == True: 
				print i
			if series['resource_type'] == 'volume':
				volume = {}
				for field in seriesDisplayFields:
					# publisher is a dictionary so we need to pull the name value from that
					if field == 'publisher' and series['publisher'] != None:
						volume[field] = series[field]["name"]
					# everything else is a string
					else:
						fieldType = type(series[field])
						
						if fieldType == type(int()):
							volume[field] = series[field]
						if fieldType == type(str()):
							volume[field] = remove_html_tags(str(series[field]))
						if fieldType == type(unicode()):
							fieldAsString = series[field].encode('utf8','ignore')
							print fieldAsString
							volume[field] = remove_html_tags(fieldAsString)
				seriesList[series['id']] = volume
		offset = offset + resultCount
		cvSearchURL = cvBaseSearchURL + '&offset=' + str(offset)

	return seriesList
	
def compareSeriesByYear (a, b):

	return cmp(str(a.get('start_year','0')),str(b.get('start_year','0')))

def displaySeriesInfo(seriesList):
	sortedList = sorted(seriesList.values(), compareSeriesByYear)

	print '***************************************************'
	for volume in sortedList:
		for field in seriesDisplayFields:
			print '%s:\t%s' % (field, volume.get(field,'undefined'))
		print '***************************************************'

def getIssueData(issueId):
	cvIssueURL = issueURL + '/' + str(issueId) + '/' +  '?api_key=' + APIKEY + '&format=json'
	cvIssueResults = json.load(urllib.urlopen(cvIssueURL))
	return cvIssueResults

def getVolumeDataFromURL(volumeURL):
	volumeURL = volumeURL + '?api_key=' + APIKEY  + '&format=json'
	#TODO: add field limit so we only get the fields we are going to use
	cvVolumeResults = json.load(urllib.urlopen(volumeURL))
	return cvVolumeResults

def getVolumeNameFromID(seriesId):
	volumeURL = baseURL + 'volume/' + seriesId.strip() + '/?api_key=' + APIKEY + '&field_list=name&format=json'
	cvVolumeResults = json.load(urllib.urlopen(volumeURL))
	volumeName = cvVolumeResults['results']['name']
	return volumeName

def readCBI(dir, filename):
	# read the meta data from the zipfiles comment field
	cbzComment = readComment(dir, filename)
	if len(cbzComment) == 0:
		print 'No comment in zip file.'
		comicBookInfo =  blankCBI()
	else:
		try:
			comicBookInfo = json.loads(cbzComment)
		except: 
			comicBookInfo = blankCBI()
	return comicBookInfo

def getSeries(comicBookInfo, directory, filename):
	try: thisSeries = comicBookInfo['ComicBookInfo/1.0']['series']
	except: thisSeries = ''

	thisSeriesId = 0
	readSeriesId = thisSeriesId
	if useSeriesCacheFile == True:
		if os.path.exists(os.path.join(directory, 'seriesId.txt')) == True:
			print 'Found a seriesId.txt file in this directory'
			with open(os.path.join(directory, 'seriesId.txt'), 'r') as cacheFile:
				readSeriesId = cacheFile.readline()
			if readSeriesId == '':	
				readSeriesId = 0
			else:
				print 'Read series Id is %s' % readSeriesId		
			thisSeriesId = readSeriesId

			if thisSeriesId != '' and thisSeriesId != 0:
				thisSeries = getVolumeNameFromID(thisSeriesId)
				print 'That series is %s' % thisSeries

	if thisSeries == '' and assumeDirIsSeries == True :
		thisSeries = os.path.basename(directory)
		print 'Assuming series name is [%s]' % thisSeries

	if thisSeriesId == 0 and interactiveMode == True and promptSeriesNameIfBlank == False and promptSeriesIdIfBlank == True :
		print 'Processing %s:' % os.path.join(directory, filename)
		thisSeriesId = raw_input('No series name found.  Enter the series Id:\t')

	if thisSeries == '' and thisSeriesId ==0 and interactiveMode == True and promptSeriesNameIfBlank == True :
		print 'Processing %s:' % os.path.join(directory, filename)
		thisSeries = raw_input('No series name found.  Enter the series name:\t')
	
	if interactiveMode == True and thisSeriesId == 0:	
		seriesResults = searchForSeries(thisSeries)
		if len(seriesResults) == 0:
			'No series with that name found.'
			thisSeriesId = 0

		if len(seriesResults) == 1:
			'Found the series'
			for id in seriesResults:
				thisSeriesId = id
		if len(seriesResults) > 1:
			displaySeriesInfo(seriesResults)
			thisSeriesId = raw_input('Enter the Series ID fo %s from the list above:\t' % filename)
		
	# if we've got a new series Id, we should update the cacheFile
	if thisSeriesId != readSeriesId and thisSeriesId != 0 and useSeriesCacheFile == True:
		print 'caching the series id...'
		with open(os.path.join(directory, 'seriesId.txt'), 'w') as cacheFile:
			cacheFile.write(str(thisSeriesId))
		print 'done caching the series id'
	return thisSeries, thisSeriesId

def getIssueNumber(comicBookInfo, directory, filename):
	try:thisIssue = comicBookInfo['ComicBookInfo/1.0']['issue']
	except: thisIssue = ''
	
	if thisIssue == '':
		# try the parsing function
		thisIssue = parseIssueNumberFromName(filename)
		print 'Assuming issue number is ' + thisIssue + ' based on the filename.'
	if thisIssue == '':
		# try a regex
		issnum = re.search('(?<=[_#\s-])(\d+[a-zA-Z]|\d+\.\d|\d+)', filename)
		if issnum:
			thisIssue = issnum.group()
			print 'Got the issue from filename. Issue is ' + thisIssue + '.'

	if thisIssue == '' and interactiveMode == True:
		thisIssue = raw_input('No issue number found.  Enter the issue number:\t')
	# strip leading zeroes from issue number
	thisIssue = thisIssue.lstrip("0")
	if len(thisIssue) == 0:
		thisIssue = "0"
	return thisIssue

def getCredits(issueCredits, cvIssueResults):
	for person in cvIssueResults['results']['person_credits']:
		for role in person['roles']:
			issueCredit = {}
			issueCredit['person'] = person['name']
			issueCredit['role'] = role['role'].title()
			issueCredits.append(issueCredit)
	return issueCredits

def getIssueId(thisSeries, thisIssue, cvSearchResults):
	issueId = 0
	resultCount = cvSearchResults['number_of_page_results']		

	#with open('searchJSON.txt', mode='w') as f:
	#	json.dump(cvSearchResults,f, indent = 2)

	if resultCount == 1:
		issueId = cvSearchResults['results'][0]['id']
		print 'Only one match found.  Issue ID is: ' + str(issueId)

	if resultCount > 1:
		print 'Found ' + str(resultCount) + ' matches.  Going to try and find the correct issue...'
		# probably a better way to keep track of how many loops we've done...
		index = 0

		matchingIssues = []
		for k in cvSearchResults['results']:
			currentSeries = str(cvSearchResults['results'][index]['volume']['name']).rstrip()
			currentIssue = cvSearchResults['results'][index]['issue_number']
			# messy gyrations to make the issue number that's expressed as a decimal expressed as a whole number 
			currentIssueD = decimal.Decimal(str(cvSearchResults['results'][index]['issue_number']))
			currentIssueI = int(currentIssueD)
			currentIssue = str(currentIssueI).rstrip()
			if currentIssue  == thisIssue and currentSeries  == thisSeries:
				#issueId = cvSearchResults['results'][index]['id']
				matchingIssues.append(k)
			index = index + 1
		
		# we don't want to automatically remove all the matches so 
		# let the user deal with them if we can't narrow them down to one.
		if len(matchingIssues) == 0:
			for k in cvSearchResults['results']:
				matchingIssues.append(k)

		if len(matchingIssues) == 1:
			print 'Only one issue had the same series name and issue number, must be it...'
			issueId = matchingIssues[0]['id']
			print issueId
		else:
			if resultCount != len(matchingIssues):
				print 'First pass narrowed it down to ' + str(len(matchingIssues))  + ' matches found'
			if interactiveMode == True:
				for j in matchingIssues:
					currentVolume = getVolumeDataFromURL(j['volume']['api_detail_url'])
					# print currentVolume['results']['start_year']
					print "####################################\n\n"			
					print "Issue ID:\t%s" % j['id']
					print "Issue:\t%s" % j['issue_number']
					print "Issue Name:\t%s" % j['name']
					print "Issue URL:\t%s" % j['api_detail_url']
					print "Volume Name:\t%s" % j['volume']['name']
					print "Volume First Published:\t%s" % currentVolume['results']['start_year']
					print "Volume URL:\t%s" % j['volume']['api_detail_url']
					if displaySeriesDescriptionOnDupe == True:
						volumeDescription = remove_html_tags(currentVolume['results']['description'])
						volumeDescription = volumeDescription[:maxDescriptionLength]
						print "Volume Description:\t%s" % volumeDescription
					publishDate = str(j['publish_month']) + '/' + str(j['publish_year'])
					print "Issue Published:\t %s" % publishDate
					if displayIssueDescriptionOnDupe == True:
						issueDescription = remove_html_tags(j['description']) 
						issueDescription = issueDescription[:maxDescriptionLength]
						print "Issue Description:\t%s\n" % issueDescription 

 				print "####################################\n\n"			
				issueId = raw_input('Enter the Issue ID from the list above: ')
			else:
				print 'Unable to find Issue ID and we are in non-interactive mode'


	if issueId == '':
		issueId = 0 

	return issueId

def writeComicBookInfo(comicBookInfo, dir, filename):
	# mark the comment as last-edited-by this app
	cbi = comicBookInfo['ComicBookInfo/1.0']
	comicBookInfo['ComicBookInfo/1.0'] = cbi
	comicBookInfo['lastModified'] = time.strftime("%Y-%m-%d %H:%M%S +0000", time.gmtime())
	comicBookInfo['appID'] = __program__ + '/' + __version__

	#write JSON object to a file
	jsonFile = os.path.join(dir, filename) + '.json'
	with open(jsonFile , mode='w') as f:
		json.dump(comicBookInfo,f,indent=0)

	#TODO: if the JSON is too big, trim it
	#TODO: if the JSON is zero length, log an error
	jsonLength = len(json.dumps(comicBookInfo,indent=0))
	#print jsonLength
	#pauseHere = raw_input('Press Enter')

	print 'Writing back updated ComicBookInfo for ' + filename

	cmdLine = zipCommand + ' "' + os.path.join(dir, filename) + '" -z < "' + jsonFile + '"'
	#print cmdLine
	subprocess.Popen(cmdLine, shell=True, stdout = open(os.devnull, 'w'))

	#process = subprocess.Popen(['/usr/bin/zip', os.path.join(dir, filename), '-z' ], shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
	# need a short wait so zip can get ready for our comment
	time.sleep(3)
	## dumping without an indent value seems to cause problems unless you've recompiled zip with longer line support
	#json.dump(comicBookInfo, process.stdin, indent=0)

	#delete the JSON file
	os.remove(jsonFile)


def displayIssueInfo(matchingIssues):
	for issue in matchingIssues:
		print '##################################\n'
		print 'Issue ID:\t%s' % matchingIssues[issue]['id']
		print 'Issue Name:\t%s' % matchingIssues[issue]['name']
		if displaySeriesDescriptionOnDupe == True:
			issueDescription = remove_html_tags(matchingIssues[issue]['description'])
			print 'Issue Description:\t%s\n' % issueDescription



def processFile(dir, filename, thisSeriesId):

	print 'Processing :' + filename

	thisSeries = ''		
	seriesId = thisSeriesId
	#seriesId = 0
	comicBookInfo = readCBI(dir, filename)

	#TODO:  Add a check that will lookup the issue/series based on the pre-existing
	#	metadata if it exists before trying the filename
	# try to lookup the issue based on the filename
	# this will only return non-zero values if only one match is found
	issueId, seriesId, thisSeries, thisIssue = searchByFileName(filename)

	

	if seriesId == 0 or seriesId == '':
		thisSeries, seriesId  = getSeries(comicBookInfo, dir, filename)

	if seriesId == 0 or seriesId == '':
		print 'No Series Id Found'
		if logLevel >= 2:
			logFile = open(logFileName, 'a')
			logFile.write('No Series Id Found: ' + dir + '/' + filename + '\n')
			logFile.close()
			return
		if logLevel >= 1:
			logFile = open(logFileName, 'a')
			logFile.write(dir + '/' + filename + '\n')
			logFile.close()
			return
		return

	if thisSeries == 0 and thisSeries == '':
		print 'No Series Found'
		if logLevel >= 2:
			logFile = open(logFileName, 'a')
			logFile.write('No Series Found: ' + dir + '/' + filename + '\n')
			logFile.close()
			return
		if logLevel >= 1:
			logFile = open(logFileName, 'a')
			logFile.write(dir + '/' + filename + '\n')
			logFile.close()
			return
		return

	# if we don't know the issue number, try to look it up
	if issueId == 0:
		thisIssue = getIssueNumber(comicBookInfo, dir, filename)
		issueResults = searchForIssue(thisSeries, thisIssue, seriesId)
		if len(issueResults) == 0 :
			'Unable to find that issue.'
			return
		if len(issueResults) == 1 :
			for id in issueResults:
				issueId = id
		if len(issueResults) > 1:
			displayIssueInfo(issueResults)
			issueId = raw_input('Enter the Issue ID from the list above: ')

	#issueId = getIssueId(thisSeries, thisIssue, cvSearchResults)
	if issueId == 0:
		print 'Unable to find the issue id.  Sorry'
		if logLevel >= 2:
			logFile = open(logFileName, 'a')
			logFile.write('No Issue Id Found: ' + dir + '/' + filename + '\n')
			logFile.close()
			return
		if logLevel >= 1:
			logFile = open(logFileName, 'a')
			logFile.write(dir + '/' + filename + '\n')
			logFile.close()
			return
		return

	else: 
		cvIssueResults = getIssueData(issueId)
		resultCount = cvIssueResults['number_of_total_results']

		cvVolumeURL = cvIssueResults['results']['volume']['api_detail_url'] + '?api_key=' + APIKEY + '&format=json'
		cvVolumeResults = json.load(urllib.urlopen(cvVolumeURL))

		# update our JSON object with the CV data
		comicBookInfo['ComicBookInfo/1.0']['series'] = cvIssueResults['results']['volume']['name']
		comicBookInfo['ComicBookInfo/1.0']['issue'] = thisIssue
		if useSeriesWhenNoTitle == True and cvIssueResults['results']['name'].rstrip(cvIssueResults['results']['name']) == '':
			while len(thisIssue) < padIssueNumber:
				thisIssue = '0' + thisIssue
			comicBookInfo['ComicBookInfo/1.0']['title'] = cvIssueResults['results']['volume']['name'] + " " + thisIssue
		else:
			comicBookInfo['ComicBookInfo/1.0']['title'] = cvIssueResults['results']['name']
		#print cvVolumeResults

		try:
			comicBookInfo['ComicBookInfo/1.0']['publisher'] = cvVolumeResults['results']['publisher']['name']
		except:
			print 'No Publisher in metadata'

		if cvIssueResults['results']['publish_year'] == None:
			print 'No Publication Year found.  Skipping the year and month'
		else:
			if cvIssueResults['results']['publish_month'] == None:
				print 'No Publication Month found.  Defaulting to January'
				comicBookInfo['ComicBookInfo/1.0']['publicationMonth']  = 1
			else:
				comicBookInfo['ComicBookInfo/1.0']['publicationMonth']  = cvIssueResults['results']['publish_month']

			comicBookInfo['ComicBookInfo/1.0']['publicationYear'] = cvIssueResults['results']['publish_year']

		if includeDescriptionAsComment == True:
			issueDescription = remove_html_tags(cvIssueResults['results']['description'])
			issueDescription = issueDescription[:maxDescriptionLength]
			if len(issueDescription) > 0:
				comicBookInfo['ComicBookInfo/1.0']['comments'] = issueDescription

		# personal perference to make volume the year the volume started


		if useStartYearAsVolume == True and cvVolumeResults['results']['start_year'] != None :
			comicBookInfo['ComicBookInfo/1.0']['volume'] = cvVolumeResults['results']['start_year']
		else:
			try: del comicBookInfo['ComicBookInfo/1.0']['volume']
			except: pass

		if purgeExistingCredits == True:
			issueCredits = []
		else:
			issueCredits = comicBookInfo['ComicBookInfo/1.0']['credits']

		if updateCredits == True:
			comicBookInfo['ComicBookInfo/1.0']['credits'] = getCredits(issueCredits, cvIssueResults)
			
		if purgeExistingTags == True:
			tags = []
		else:
			tags = comicBookInfo['ComicBookInfo/1.0']['tags']

		if updateTags == True:

			if includeStoryArcAsTags == True:
				# add story arcs to the tags
				for k in cvIssueResults['results']['story_arc_credits']:
					tag = {}
					tags.append(k['name'])

			if includeCharactersAsTags == True:			
				# add characters to the tags
				for k in cvIssueResults['results']['character_credits']:
					tag = {}
					tags.append(k['name'])

			if includeItemsAsTags == True:
				# add items to the tags
				for k in cvIssueResults['results']['object_credits']:
					tag = {}
					tags.append(k['name'])

			comicBookInfo['ComicBookInfo/1.0']['tags'] = tags

		writeComicBookInfo(comicBookInfo, dir, filename)
		# Clean up JSON file if it's still there.  
		# For some reason it's not always deleted properly
		jsonFile = os.path.join(dir, filename) + '.json'
		if os.path.exists(jsonFile) == True:
			os.remove(jsonFile)

	print 'Done with ' + filename

def processDir(dir):

	(fileList, dirList) = getfiles(dir)
	# initialize the seriesId number
	thisSeriesId = 0

	# if this folder has a cached seriesId and we've turned on the option to use it
	# read the series Id and we'll pass that along.
	if useSeriesCacheFile == True:
		if os.path.exists(os.path.join(dir, 'seriesId.txt')) == True:
			print 'Found a seriesId.txt file in this directory.'
			with open(os.path.join(dir, 'seriesId.txt'), 'r') as cacheFile:
				readSeriesId = cacheFile.readline()
			if readSeriesId == '':	
				readSeriesId = 0
			else:
				print 'Read series Id is %s' % readSeriesId		
			thisSeriesId = readSeriesId

	for filename in fileList:
		# skip any files that start with a ._
		if filename[:2] != "._":
			processFile(dir, filename, thisSeriesId)
	for subdir in dirList:
		processDir(os.path.join(dir, subdir))

def makehash():
	return collections.defaultdict(makehash)



def main():
	usage() 
	readConfig()
	global useSeriesCacheFile
	if len(sys.argv) == 1 or sys.argv[1] == 'autoset' :  
		dir = os.getcwd()
		processDir(dir)
	else:
		if sys.argv [1] in ("set" , "get"):
			action = sys.argv[1]
			argv = sys.argv[2:]
		else:
			argv = sys.argv
			action=""
		try:
			if action == "set":
				opts, args = getopt.getopt(argv,"zhf:p:t:s:i:v:d:",["zerocache","help","version","file=","publisher=","title=","series=", "issue=", "volume=", "date="])
			else:
				opts, args = getopt.getopt(argv,"hf:ptsivdc",["help","version","file=","publisher","title","series", "issue", "volume", "date","credits"])

		except getopt.GetoptError:
			print getopt.GetoptError
			usage()
			sys.exit(2)

		tags = { "publisher":"", \
						"title":"",  \
						"series":"",  \
						"issue":"",  \
						"volume":"", \
						"date":"",
						"lastModified":"", \
						"rating":"",\
						"publicationYear":"" , \
						"publicationMonth":"" ,
						"country":"", \
						"genre":"" ,\
						"language":"", \
						"appID" : "" , \
						"credits":"",\
						"tags":""
					}

		# set to blank for now
		file = ""

		for opt , arg in opts:
			if opt in ("-h","--help"):
				usage()
				sys.exit()
			elif opt in ("-z", "--zerocache"):
				useSeriesCacheFile = False
			elif opt == "--version":
				print sys.argv[0] + " " + __version__
				sys.exit()
			elif opt in ("-p", "--publisher", "publisher"):
				if action == "get":
					tags["publisher"] = "1"
				else:
					tags["publisher"] =  arg
			elif opt in ("-t", "--title"):
				if action == "get":
					tags["title"] = "1"
				else:
					tags["title"] =  arg
			elif opt in ("-s", "--series"):
				if action == "get":
					tags["series"] = "1"
				else:
					tags["series"] =  arg
			elif opt in ("-i", "--issue"):
				if action == "get":
					tags["issue"] = "1"
				else:
					tags["issue"] =  arg
			elif opt in ("-v","--volume"):
				if action == "get":
					tags["volume"] = "1"
				else:
					tags["volume"] =  arg
			elif opt in ("-d","--date"):
				if action == "get":
					tags["date"] = "1"
				else:
					tags["date"] =  arg
			elif opt in ("-c","--credits"):
				if action == "get":
					tags["credits"] = "1"
			elif opt in ("-f","--file"):
				if os.path.isfile(arg) :
					if not zipfile.is_zipfile (arg)  :
						print arg +": Not a (cbz) zip file."
						sys.exit(2)
					else:
						file = arg # we've got it
				else:
					print file + ": no such file"
					sys.exit(2)

		if file == "" : # it is still blank and all futher work needs it
			if action != "":
				print "No target file specified"
			sys.exit(2)

		# this is neded both for readin and writing nad we know file is zip file at this point
		cbzfile = zipfile.ZipFile(file)

		if action == "get" :
			requestedTags = [];
			for t in tags:
				if tags[t] == "1":
					requestedTags.append(t)
			print "Getting CBI from " + file
			cbzcomment = cbzfile.comment
			try:
				cbinfo = readComment(os.getcwd(),file)
				#cbinfo = json.loads(cbzcomment)
			except:
				print 'No CBI found in file'
				sys.exit(2)
			for k  in cbinfo:
				if k in ('lastModified' , 'appID'):
					if tags[k] or len(requestedTags) == 0 :
						print k + ": " + cbinfo[k]
				elif k == 'ComicBookInfo/1.0':
					for kk  in cbinfo[k]:
						if kk in ('series' , 'title' , 'publisher' , 'publicationMonth' , 'publicationYear' , 'issue' ,'numberOfIssues' , 'volume' , 'numberOfVolumes' , 'rating' , 'genre' , 'language' , 'country' ):
							if tags[kk] or len(requestedTags) == 0 :
								print  kk + ": " + str(cbinfo[k][kk])
						elif kk == 'credits':
							if tags[kk] or len(requestedTags) == 0 :
								for kkk  in cbinfo[k][kk]:
									if kkk['primary'] :
										primary_str  ="*"
									else:
										primary_str = ""
									print  kkk["role"] + primary_str + ": " +  kkk['person']
						elif kk == 'tags':
							print "tags: " + kk
				elif k[:2] == "x-":
					print "Custom tags are not yet implemented"

		elif action == "set":
			print "Setting CBI for " + file
			dir = os.getcwd()
			processFile(dir, file)

		#	for tag in tags:
		#		print tag + ": " + tags[tag]


if __name__ == "__main__":
	main()



