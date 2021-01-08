import os

def processPhysicsCoding(codingRecord, expData):
	'''Additional processing when updating coding for the physics study.

	Meant to be given as a processingFunction argument to Experimenter.updatecoding.

	codingRecord: a value in the Experiment.coding dictionary

	expData: corresponding session['attributes']['expData'] field for this session; dictionary of frameId: frameData pairs.

	Returns codingRecord, edited in place with the following fields added:
		videosExpected: list of videoIds for any frames in expData with a videoId field. These are not the full filename with timestamp & random string: they just have the study ID, frame ID, and session ID, e.g.,
			'583c892ec0d9d70082123d94_11-pref-phys-videos_58474acfc0d9d70082123db6'
		showedAlternate: corresponding to videosExpected, a list of whether the alternate test video was shown during this trial. True/False for pref-phys-videos frames; None for other frames with video (e.g. consent, video-preview)
		endedEarly: corresponding to videosExpected, a list of whether the trial was ended early, determined as either not having a 'startTestVideo'/'startAlternateVideo' event OR the alternate video was paused OR video was paused but alternate not started.
		videosShown: corresponding to videosExpected, a list of videos shown. If alternate video was shown, the alternate is stored here. Filename (without path/extension) is stored: e.g. u'sbs_stay_near_mostly-on_hammer_c2_green_NN'
	'''

	codingRecord['videosExpected'] = []
	codingRecord['showedAlternate'] = []
	codingRecord['endedEarly'] = []
	codingRecord['videosShown'] = []

	def eventsContain(eNameFrag, eventNames):
	    return any([eNameFrag in name for name in eventNames])

	for (frameId, frameData) in expData.iteritems():
		if 'videoId' in frameData.keys() and not frameId=='32-32-pref-phys-videos':
			if 'pref-phys-videos' in frameId:

				# Check events: was the video paused?
				events = [e['eventType'] for e in frameData['eventTimings']]
				showAlternate = eventsContain('startAlternateVideo', events)

				if events:
				    eventPrefix = events[0].split(':')[0] # 'exp-physics' or 'exp-video-physics' depending on recorder
				else:
				    eventPrefix = 'exp-physics' # doesn't matter, no events anyway, just define it to avoid errors

				# Was the alternate video also paused, if applicable?
				# TODO: once we have an F1 event, add this as a way the study could be ended early
				# Ended early if we never saw either test or alternate video (check
				# for alternate b/c of rare case where due to lots of pausing only
				# alternate is shown)
				# Just check for startTestVideo/startAlternateVideo in event name,
				# as events are now exp-video-physics:EVENTNAME instead of exp-physics:EVENTNAME
				# in line with all other frames
				endedEarly = not(eventsContain('startTestVideo', events)) and not(eventsContain('startAlternateVideo', events))
				# Check that the alternate video wasn't paused
				if showAlternate:
					lastAlternateEvent = len(events) - events[::-1].index(eventPrefix + ':startAlternateVideo') - 1
					endedEarly = endedEarly or ('pauseVideo' in events[lastAlternateEvent:])
				# Check we didn't pause test video, but never get to alternate (e.g. F1)
				if not endedEarly and eventsContain('pauseVideo', events) and eventsContain('startTestVideo', events):
					lastPause = len(events) - events[::-1].index(eventPrefix + ':pauseVideo') - 1
					firstTest = events.index(eventPrefix + ':startTestVideo')
					endedEarly = endedEarly or (lastPause > firstTest and not showAlternate)

				# Which video file was actually shown?
				thisVideo = ''
				if 'videosShown' in frameData.keys() and len(frameData['videosShown']):
					videos = frameData['videosShown']
					thisVideo = os.path.splitext(os.path.split(videos[0 + showAlternate])[1])[0]

			else:
				showAlternate = None
				thisVideo = None
				endedEarly = None

			codingRecord['videosExpected'].append(frameData['videoId'])
			codingRecord['showedAlternate'].append(showAlternate)
			codingRecord['videosShown'].append(thisVideo)
			codingRecord['endedEarly'].append(endedEarly)

	return codingRecord

def processPhysicsConcat(codingRecord, vidData):
	'''Updates a coding record based on the vidData structure used in concatenate_session_videos.
	Meant to be used as a processingFunction argument to concatenate_session_videos.

	vidData: list of video data; each element is a list
		[vidName, vidInd, vidTimestamp, useWhole].
		vidInd gives the index of this video in codeRecord['videosFound']

	codeRecord: value from coding dictionary, corresponding to this video list.

	Saves concatShowedAlternate and concatVideosShown fields, lists of whether video shown
	was the alternate test video and the video name, respectively, corresponding to the list
	of concatenated videos in vidData.

	updates codeRecord in place and returns.'''

	vidsShown = [codingRecord['videosShown'][vid[1]] for vid in vidData]
	codingRecord['concatShowedAlternate'] = [codingRecord['showedAlternate'][i] for (vidName, i, t, useW) in vidData]
	codingRecord['concatVideosShown'] = vidsShown
	return codingRecord

def skipIfEndedEarly(vidData, codeRecord):
	'''Selects vidData elements correpsonding to only frames that didn't end early.
	Meant to be given as an argument to concatenate_session_videos.

	vidData: list of video data; each element is a list
		[vidName, vidInd, vidTimestamp, useWhole].
		vidInd gives the index of this video in codeRecord['videosFound']

	codeRecord: value from coding dictionary, corresponding to this video list.

	Returns a sublist of vidData, where the corresponding element of codeRecord['endedEarly']
	is False.'''

	return [vid for vid in vidData if not codeRecord['endedEarly'][vid[1]]]

# List of current coder names. coding.py will only create/commit coding for coders on this list. Removing an inactive coder will not affect existing data.
CODERS = ['Kim', 'Coder1']

# Allow usage of study 'nicknames' when calling coding.py or reminder_emails.py
studyNicknames = {'physics': 'cfddb63f-12e9-4e62-abd1-47534d6c4dd2',
				  'geometry': 'c7001e3a-cfc5-4054-a8e0-0f5e520950ab',
				  'politeness': 'b40b6731-2fec-4df4-a12f-d38c7be3015e',
				  'flurps': '1e9157cd-b898-4098-9429-a599720d0c0a',
				  'geometry2': '849b547f-5199-4aa0-892d-a96262080dc8',
				  'laughter': 'd4cbfabc-ea53-4877-bc55-c701426fd13b'}

# Which studies do we want to fetch video from when doing an update? Can manually set a list
# of IDs (e.g. to just do physics, ['cfddb63f-12e9-4e62-abd1-47534d6c4dd2']), or use
# 'all' to get video from all studies you have access to.
whichStudiesVideo = [] #studyNicknames.values()

# Don't show/count these user IDs when making coding spreadsheets
ignoreProfiles = []

# Default list of fields endings to include in coding sheets, beyond basic
# headers. For each session, any field ENDING in a string in this list will
# be included. The original field name will be removed and the
# corresponding data stored under this partial name, so they should
# be unique endings within sessions. (Using just the ending allows
# for variation in which segment the field is associated with.)
standardFields = [	     'exit-survey.withdrawal',
						 'exit-survey.useOfMedia',
						 'exit-survey.databraryShare',
						 'exit-survey.feedback',
						 'instructions.confirmationCode',
						 'mood-survey.active',
						 'mood-survey.childHappy',
						 'mood-survey.rested',
						 'mood-survey.healthy',
						 'mood-survey.doingBefore',
						 'mood-survey.lastEat',
						 'mood-survey.napWakeUp',
						 'mood-survey.nextNap',
						 'mood-survey.usualNapSchedule',
						 'mood-survey.ontopofstuff',
						 'mood-survey.parentHappy',
						 'mood-survey.energetic']

# Default list of field ENDINGS to exclude. For each session, any field ENDING
# in a string in this list will excluded from consent/codesheets. May want to put fields
# that are redundant or that have super long strings here.
standardExclude = [		 'allEventTimings',
						 '.links.related',
						 'type',
						 'consentFormText']

# Default study settings; overridden by any values in settingsByStudy.
settings = {
		'onlyMakeConcatIfConsent': True, # Don't concatenate video unless consent field is 'yes'
		'nVideosExp': 0, # Study videos to expect; for summary display only
		'videoFrameNames': [], # Frame substrings we expect video for; these videos will be trimmed
		'trimLength': False, #For videos we do trimming of: False (default) not to do any trimming of video file, or a number of seconds, or an event name suffix (string). If a number of seconds is given: positive numbers indicate how much to trim from the START of the video; negative numbers indicate where to start relative to the END of the video (counted from the end of the shortest stream - generally video rather than audio; if the video is shorter than that, the entire video will be kept). If a string is given, then we look for the FIRST occurrence of an even ending in that string during this video and start from that streamTime (or from the start of the video if the event isn't found).
		'excludeFields': standardExclude,
		'studyFields': [], # List of exact field names to include in codesheets, beyond basic headers
		'includeFields': standardFields,
		'extraCodingFields': [], # Additional fields to add to coding records
		'codingProcessFunction': None, # Function for additional coding processing - see Experiment.update_coding
		'concatProcessFunction': None, # Function for additional coding processing after video concatenation - see Experiment.concatenate_session_videos
		'concatSkipFunction': None, # Function to select videos for concatenation - see Experiment.concatenate_session_videos
		'eventsToAnnotate': [] # list of event types that should be annotated in bottom left of videos (any events ending in any of these will be annotated)
	}

showUsername = True # Whether to show usernames (email addresses) in account CSV files, if you have permissions to see these directly

# For each study using coding.py, add a dictionary entry with studyId/studyNickname:settings here. settings (defined above) are the default values; anything here overrides those.
settingsByStudy = {
		'physics': {
			'onlyMakeConcatIfConsent': True,
			'nVideosExp': 24,
			'videoFrameNames': ['pref-phys-videos'],
			'trimLength': -24,
			'excludeFields': standardExclude + ['eventTimings'],
			'studyFields': ['videosShown', 'showedAlternate', 'endedEarly'],
			'includeFields': standardFields,
			'extraCodingFields': {
				'concatShowedAlternate': None,
				'concatVideosShown': None,
				'videosExpected': [],
				'showedAlternate': [],
				'endedEarly': [],
				'videosShown': []
				},
			'codingProcessFunction': processPhysicsCoding,
			'concatProcessFunction': processPhysicsConcat,
			'concatSkipFunction': skipIfEndedEarly,
			'eventsToAnnotate': []
		},
		'geometry': {
			'onlyMakeConcatIfConsent': False,
			'nVideosExp': 4,
			'videoFrameNames': ['alt-trials'],
			'trimLength': -72,
			'excludeFields': ['eventTimings'] + standardExclude,
			'studyFields': ['uniqueEventsOrdered'],
			'includeFields': standardFields,
			'eventsToAnnotate': ['exp-alternation:pauseVideo',
				'exp-alternation:unpauseVideo',
				'exp-alternation:startIntro',
				'exp-alternation:startCalibration',
				'exp-alternation:startTestTrial',
				'exp-alternation:enteredFullscreen',
				'exp-alternation:leftFullscreen',
				'exp-alternation:stoppingCapture']
		}
	}
