#!/usr/bin/python

import os
import json
import urllib
import subprocess
import zipfile
import time
import decimal 

APIKEY="ENTER_YOUR_API_KEY_HERE"

__program__ = 'pyComicMetaThis.py'
__version__ = '0.1c'

baseURL="http://api.comicvine.com/"
searchURL = baseURL + 'search'
issueURL = baseURL + 'issue'

# maybe we'll add .cbr support?
fileExtList = [".cbz"]

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
		print 'No comment in zip file.  Creating a blank ComicBookInfo structure.'
		comicBookInfo =  blankCBI()
	else:
		if len(cbzComment) > 0 and cbzComment.startswith('{') == False:
			print 'No ComicBookInfo header found.  We should create one, but what should it contain?'
		comicBookInfo = json.loads(cbzComment)
	return comicBookInfo

def getSeriesName(comicBookInfo):
	thisSeries = comicBookInfo['ComicBookInfo/1.0']['series']
	if thisSeries == '':
		thisSeries = raw_input('No series name found.  Enter the series name:\t')
	return thisSeries

def getIssueNumber(comicBookInfo):
	thisIssue = comicBookInfo['ComicBookInfo/1.0']['issue']
	if thisIssue == '':
		thisIssue = raw_input('No issue number found.  Enter the issue number:\t')
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
			if issueId == '':
				issueId = 0 
			print issueId

	return issueId

def processDir(dir):

	(fileList) = getfiles(dir)

	for filename in fileList:
		print 'Processing :' + filename
		
		comicBookInfo = readCBI(filename)

		thisSeries = getSeriesName(comicBookInfo)
		thisIssue = getIssueNumber(comicBookInfo)

		cvSearchResults = searchForIssue(thisSeries, thisIssue)
		print 'foo'
		issueId = getIssueId(thisSeries, thisIssue, cvSearchResults)


		#resultCount = cvSearchResults['number_of_page_results']		

		#issueId = 0

		#if resultCount == 1:
		#	issueId = cvSearchResults['results'][0]['id']
		#	print 'Only one match found.  Issue ID is: ' + str(issueId)

		#if resultCount > 1:
		#	print 'Found ' + str(resultCount) + ' matches.  Going to try and find the correct issue...'
		#	# probably a better way to keep track of how many loops we've done...
		#	index = 0

		#	matchingIssues = []
		#	for k in cvSearchResults['results']:
		#		currentSeries = str(cvSearchResults['results'][index]['volume']['name']).rstrip()
		#		currentIssue = cvSearchResults['results'][index]['issue_number']
		#		# messy gyrations to make the issue number that's expressed as a decimal expressed as a whole number 
		#		currentIssueD = decimal.Decimal(str(cvSearchResults['results'][index]['issue_number']))
		#		currentIssueI = int(currentIssueD)
		#		currentIssue = str(currentIssueI).rstrip()
		#		if currentIssue  == thisIssue and currentSeries  == thisSeries:
		#			issueId = cvSearchResults['results'][index]['id']
		#			matchingIssues.append(k)
		#		index = index + 1
		#	if len(matchingIssues) == 1:
		#		print 'Only one issue had the same series name and issue number, must be it...'
		#		issueId = matchingIssues[0]['id']
		#		print issueId
		#	else:
		#		print 'First pass narrowed it down to ' + str(len(matchingIssues))  + ' matches found'
		#		for j in matchingIssues:
		#			currentVolume = getVolumeDataFromURL(j['volume']['api_detail_url'])
		#			print currentVolume['results']['start_year']
 		#			print "####################################\n\n"			
		#			print "Issue ID:\t%s" % j['id']
		#			print "Volume Name:\t%s" % j['volume']['name']
		#			print "Volume First Published:\t%s" % currentVolume['results']['start_year']
		#			print "Volume:\t%s" % j['volume']
		#			print "Volume Description:\t%s" % stripTags(currentVolume['results']['description'])
		#			publishDate = str(j['publish_month']) + '/' + str(j['publish_year'])
		#			print "Issue Published:\t %s" % publishDate
		#			print "Issue Description:\t%s\n------------------------------------" % j['description'] 
		#			print "Issue Description:\t%s\n------------------------------------" % stripTags(j['description']) 
 		#		print "####################################\n\n"			
		#		issueId = raw_input('Enter the Issue ID from the list above: ')
		#		if issueId == '':
		#			issueId = 0 
		#		print issueId

		if issueId == 0:
			print 'Unable to find the issue id.  Sorry'
			break
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

			#credits = []
			#for person in cvIssueResults['results']['person_credits']:
			#	for role in person['roles']:
			#		credit = {}
			#		credit['person'] = person['name']
			#		credit['role'] = role['role']
			#		credits.append(credit)
			#comicBookInfo['ComicBookInfo/1.0']['credits'] = credits
			comicBookInfo['ComicBookInfo/1.0']['credits'] = getCredits(cvIssueResults)
		


			# it is possible to preserve the existing tags if we want to
			# but right now we're wiping them clean
			tags = []
			#tags = comicBookInfo['ComicBookInfo/1.0']['tags']
			
			# add characters to the tags
			for k in cvIssueResults['results']['character_credits']:
				tag = {}
				tags.append(k['name'])

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
			print comicBookInfo
			json.dump(comicBookInfo, process.stdin, indent=0)
			print 'Done with ' + filename

def main():
	dir = os.getcwd()
	processDir(dir)
	
if __name__ == "__main__":
	main()



