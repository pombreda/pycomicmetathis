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
"""

APIKEY="e75dd8dd18cfdd80e1638de4262ed47ed890b96e"

updateTags = True
updateCredits = True
# setting purgeExistingTags or purgeExistingCredits to False 
# could be dangerous if you run this on the same files 
# repeatedly as the tags will be duplicated
purgeExistingTags = True
purgeExistingTags = True
includeCharactersAsTags = True
includeItemsAsTags = True
# interactiveMode will prompt the user for series and issue info 
# if it can't be determined automatically.  
interactiveMode = False
# if interactiveMode is disabled, any issues that can't be
# identified automatically will be logged to this file.
# The file is appended to.
logFileName = 'pyComicMetaThis.log'

baseURL="http://api.comicvine.com/"
searchURL = baseURL + 'search'
issueURL = baseURL + 'issue'

# maybe we'll add .cbr support?
fileExtList = [".cbz"]

__program__ = 'pyComicMetaThis.py'
__version__ = '0.1f'
__author__ = "Andre (andre.messier@gmail.com); Sasha (sasha@goldnet.ca)"
__date__ = "2010-12-05"
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
try: import simplejson as json
except ImportError: import json

def usage ():
	print __program__ + " " +__version__+ " (" + __date__ + ")"
	print __copyright__
	print __doc__

def blankCBI():
	emptyCBIContainer = {}
	emptyCBIContainer['appID'] = __program__ + '/' + __version__
	emptyCBIContainer['lastModified'] = time.strftime("%Y-%m-%d %H:%M%S +0000", time.gmtime())
	emptyCBI = {}
	emptyCBI['series'] = ''
	emptyCBI['issue'] = ''
	emptyCBIContainer['ComicBookInfo/1.0'] = emptyCBI
	return emptyCBIContainer

def stripTags(text): 
     finished = 0 
     while not finished: 
         finished = 1 
         start = text.find("<") 
         if start >= 0: 
             stop = text[start:].find(">") 
             if stop >= 0: 
                 text = text[:start] + text[start+stop+1:] 
                 finished = 0 
     return text 

def getfiles(directory):
	entries = os.listdir(directory)
	fileList = [f for f in entries if os.path.splitext(f)[1].lower() in fileExtList and len(os.path.splitext(f)[0]) and os.path.isfile(os.path.join(directory, f))]
	fileList.sort()
	return (fileList)

def readComment(filename):
	archivefile = file(filename)
	cbz = zipfile.ZipFile(archivefile)
	cbzComment = cbz.comment
	cbz.close()
	return cbzComment	

def searchForIssue(seriesName, issueNumber):
	cvSearchURL = searchURL + '?api_key=' + APIKEY + '&query=' + urllib.quote(seriesName + ' ' + issueNumber) + '&resources=issue' 
	#cvSearchURL = cvSearchURL + '&field_list=name,start_year,id'
	cvSearchURL = cvSearchURL + '&format=json'
	cvSearchResults = json.load(urllib.urlopen(cvSearchURL))
	return cvSearchResults

def getIssueData(issueId):
	cvIssueURL = issueURL + '/' + str(issueId) + '/' +  '?api_key=' + APIKEY + '&format=json'
	cvIssueResults = json.load(urllib.urlopen(cvIssueURL))
	return cvIssueResults

def getVolumeDataFromURL(volumeURL):
	volumeURL = volumeURL + '?api_key=' + APIKEY  + '&format=json'
	cvVolumeResults = json.load(urllib.urlopen(volumeURL))
	return cvVolumeResults

def readCBI(filename):
	# read the meta data from the zipfiles comment field
	cbzComment = readComment(filename)
	if len(cbzComment) == 0:
		print 'No comment in zip file.'
		comicBookInfo =  blankCBI()
	else:
		if len(cbzComment) > 0 and cbzComment.startswith('{') == False:
			print 'No ComicBookInfo header found.  We should create one, but what should it contain?'
		comicBookInfo = json.loads(cbzComment)
	return comicBookInfo

def getSeriesName(comicBookInfo):
	thisSeries = comicBookInfo['ComicBookInfo/1.0']['series']
	if thisSeries == '' and interactiveMode == True:
		thisSeries = raw_input('No series name found.  Enter the series name:\t')
	return "Green Lantern"
	return thisSeries

def getIssueNumber(comicBookInfo):
	thisIssue = comicBookInfo['ComicBookInfo/1.0']['issue']
	if thisIssue == '' and interactiveMode == True:
		thisIssue = raw_input('No issue number found.  Enter the issue number:\t')
	thisIssue = '5'
	return thisIssue

def getCredits(cvIssueResults):
	credits = []
	for person in cvIssueResults['results']['person_credits']:
		for role in person['roles']:
			credit = {}
			credit['person'] = person['name']
			credit['role'] = role['role']
			credits.append(credit)
	return credits

def getIssueId(thisSeries, thisIssue, cvSearchResults):
	issueId = 0
	resultCount = cvSearchResults['number_of_page_results']		

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
		if len(matchingIssues) == 1:
			print 'Only one issue had the same series name and issue number, must be it...'
			issueId = matchingIssues[0]['id']
			print issueId
		else:
			print 'First pass narrowed it down to ' + str(len(matchingIssues))  + ' matches found'
			if interactiveMode == True:
				for j in matchingIssues:
					currentVolume = getVolumeDataFromURL(j['volume']['api_detail_url'])
					print currentVolume['results']['start_year']
					print "####################################\n\n"			
					print "Issue ID:\t%s" % j['id']
					print "Volume Name:\t%s" % j['volume']['name']
					print "Volume First Published:\t%s" % currentVolume['results']['start_year']
					print "Volume:\t%s" % j['volume']
					print "Volume Description:\t%s" % stripTags(currentVolume['results']['description'])
					publishDate = str(j['publish_month']) + '/' + str(j['publish_year'])
					print "Issue Published:\t %s" % publishDate
					print "Issue Description:\t%s\n------------------------------------" % j['description'] 
					print "Issue Description:\t%s\n------------------------------------" % stripTags(j['description']) 
 				print "####################################\n\n"			
				issueId = raw_input('Enter the Issue ID from the list above: ')
			else:
				print 'Unable to find Issue ID and we are in non-interactive mode'


	if issueId == '':
		issueId = 0 

	return issueId

def processDir(dir):

	(fileList) = getfiles(dir)

	for filename in fileList:
		print 'Processing :' + filename
		
		comicBookInfo = readCBI(filename)

		thisSeries = getSeriesName(comicBookInfo)
		thisIssue = getIssueNumber(comicBookInfo)

		cvSearchResults = searchForIssue(thisSeries, thisIssue)
		issueId = getIssueId(thisSeries, thisIssue, cvSearchResults)
		if issueId == 0:
			print 'Unable to find the issue id.  Sorry'
			if interactiveMode != True:
				logFile = open(logFileName, 'a')
				logFile.write(dir + '/' + filename + '\n')
				logFile.close()
			#break
		else: 
			cvIssueResults = getIssueData(issueId)
			resultCount = cvIssueResults['number_of_total_results']

			cvVolumeURL = cvIssueResults['results']['volume']['api_detail_url'] + '?api_key=' + APIKEY + '&format=json'
			cvVolumeResults = json.load(urllib.urlopen(cvVolumeURL))

			# update our JSON object with the CV data
			comicBookInfo['ComicBookInfo/1.0']['series'] = thisSeries
			comicBookInfo['ComicBookInfo/1.0']['issue'] = thisIssue
			comicBookInfo['ComicBookInfo/1.0']['title'] = cvIssueResults['results']['name']
			comicBookInfo['ComicBookInfo/1.0']['publisher'] = cvVolumeResults['results']['publisher']['name']
			comicBookInfo['ComicBookInfo/1.0']['publicationMonth']  = cvIssueResults['results']['publish_month']
			comicBookInfo['ComicBookInfo/1.0']['publicationYear'] = cvIssueResults['results']['publish_year']
			# personal perference to make volume the year the volume started
			comicBookInfo['ComicBookInfo/1.0']['volume'] = cvVolumeResults['results']['start_year']

			if updateCredits == True:
				comicBookInfo['ComicBookInfo/1.0']['credits'] = getCredits(cvIssueResults)
			
			if purgeExistingTags == True:
				tags = []
			else:
				tags = comicBookInfo['ComicBookInfo/1.0']['tags']

			if updateTags == True:
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

			# mark the comment as last-edited-by this app
			comicBookInfo['lastModified'] = time.strftime("%Y-%m-%d %H:%M%S +0000", time.gmtime())
			comicBookInfo['appID'] = __program__ + '/' + __version__
	    	        print 'Writing back updated ComicBookInfo for ' + filename
			process = subprocess.Popen(['/usr/bin/zip', filename, '-z' ], shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
			# need a short wait so zip can get ready for our comment
			time.sleep(1)
			# dumping without an indent value seems to cause problems...
			#print comicBookInfo
			json.dump(comicBookInfo, process.stdin, indent=0)
			print 'Done with ' + filename


def makehash():
	return collections.defaultdict(makehash)



def main():
	usage() 
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
				opts, args = getopt.getopt(argv,"hf:p:t:s:i:v:d:",["help","version","file=","publisher=","title=","series=", "issue=", "volume=", "date="])
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
				cbinfo = json.loads(cbzcomment)
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
			print "Setting CBI"

		#	for tag in tags:
		#		print tag + ": " + tags[tag]


if __name__ == "__main__":
	main()



