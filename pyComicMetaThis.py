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
__version__ = '0.2i'
__author__ = "Andre (andre.messier@gmail.com)"
__date__ = "2011-02-07"
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
try: import simplejson as json
except ImportError: import json


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

searchSubFolders = False
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
useSeriesWhenNoTitle = True
padIssueNumber = 3

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

def blankCBI():
	emptyCBIContainer = {}
	emptyCBI = {}
	emptyCBI['series'] = ''
	emptyCBI['issue'] = ''
	emptyCBI['volume'] = ''
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
	cvBaseSearchURL = searchURL + '?api_key=' + APIKEY + '&query=' + urllib.quote(seriesName + ' ' + issueNumber) + '&resources=issue' 
	#TODO: after this is working, limit the results to the fields we use
	#cvBaseSearchURL = cvBaseSearchURL + '&field_list=name,start_year,id,description,issue_number'
	cvBaseSearchURL = cvBaseSearchURL + '&format=json'
	offset = 0
	resultCount = 20
	cvSearchURL = cvBaseSearchURL
	print 'Querying ComicVine for the Issue...'
	i = 0
	while resultCount >= 20:
		cvSearchResults = json.load(urllib.urlopen(cvSearchURL))
		resultCount = cvSearchResults['number_of_page_results']
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
				volume['id'] = series['id']
				volume['name'] = series['name']
				volume['start_year'] = series['start_year']
				volume['description'] =  remove_html_tags(series['description'])
				seriesList[series['id']] = volume					
		offset = offset + resultCount
		cvSearchURL = cvBaseSearchURL + '&offset=' + str(offset)
	return seriesList
	

def displaySeriesInfo(seriesList):
	sortedList = []
	for key in seriesList:
		sortedList.append((seriesList[key]['start_year'], seriesList[key]['id'], seriesList[key]['name'], seriesList[key]['description']))
	import operator
	index = operator.itemgetter(0)
	sortedList.sort(key=index)

	for volume in sortedList:
		print 'Series Id"\t%s' % volume[1]
		print 'Name:\t%s' % volume[2]
		if displaySeriesDescriptionOnDupe == True:
			print 'Description:\t%s' % volume[3]
		print 'First Published:\t%s' % volume[0]
		print '****'

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
	if thisSeries == '' and interactiveMode == True and promptSeriesNameIfBlank == True :
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
			thisSeriesId = raw_input('Enter the Series ID from the list above:\t')
		
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

def getCredits(credits, cvIssueResults):
	for person in cvIssueResults['results']['person_credits']:
		for role in person['roles']:
			credit = {}
			credit['person'] = person['name']
			credit['role'] = role['role'].title()
			credits.append(credit)
	return credits

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

	if thisSeries == 0 or thisSeries == '':
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
		if useSeriesWhenNoTitle == True and str.rstrip(cvIssueResults['results']['name']) == '':
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
			comicBookInfo['ComicBookInfo/1.0']['volume'] = ''

		if purgeExistingCredits == True:
			credits = []
		else:
			credits = comicBookInfo['ComicBookInfo/1.0']['credits']

		if updateCredits == True:
			comicBookInfo['ComicBookInfo/1.0']['credits'] = getCredits(credits, cvIssueResults)
			
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
		processFile(dir, filename, thisSeriesId)
	for subdir in dirList:
		processDir(os.path.join(dir, subdir))

def makehash():
	return collections.defaultdict(makehash)



def main():
	usage() 
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



