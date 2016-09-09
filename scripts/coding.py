import os
import errno
import pickle
from client import Account, ExperimenterClient
#from sendgrid_client import SendGrid
from utils import make_sure_path_exists, indent, timestamp, printer, backup_and_save, flatten_dict, backup, backup_and_save_dict
import uuid
import subprocess as sp
import sys
import videoutils
from warnings import warn
import datetime
import lookitpaths as paths
from updatefromlookit import sync_S3, pull_from_wowza, update_account_data, show_all_experiments, update_session_data
import csv
import random
import string
import argparse
import unittest
import numpy as np
import vcode

class Experiment(object):
    '''TODO: DOC'''

    # TODO: for backup_and_save, allow hold flag in init that says whether to wait until
    # explicitly instructed to save data. Also make fn to backup/save all, and allow
    # tagging the backups (e.g. "FNNAME - before commit Kim").

    # TODO: clear UI & docs for coders, future self. Set up to do basic updates
    # automatically.

    # Don't have ffmpeg tell us everything it has ever thought about.
    loglevel = 'quiet'

    # Coder-specific fields to create/expect in coding data. If FIELDNAME is one
    # of these fields, then codingrecord[FIELDNAME] is a dict with keys = coder
    # names. New fields will be added to coding records the next time coding is
    # updated. If an existing codesheet is committed before coding is updated OR a
    # new coder sheet is created, a warning will be displayed that an expected field is
    # missing.
    coderFields = ['coderComments']
    videoData = {}
    accounts = {}

    @classmethod
    def find_session(cls, sessionData, sessionKey):
        for sess in sessionData['sessions']:
            if sess['id'] == sessionKey:
                return sess
        return -1

    @classmethod
    def load_batch_data(cls, expId):
        '''Return saved batch data for this experiment. Empty if no data.'''
        batchFile = paths.batch_filename(expId)
        if os.path.exists(batchFile):
            with open(batchFile,'rb') as f:
                batches = pickle.load(f)
            return batches
        else:
            return {}

    @classmethod
    def load_session_data(cls, expId):
        '''Return saved session data for this experiment. Error if no saved data.'''
        with open(paths.session_filename(expId),'rb') as f:
            exp = pickle.load(f)
        return exp

    @classmethod
    def load_coding(cls, expId):
        '''Return saved coding data for this experiment, or empty dict if none saved.'''
        codingFile = paths.coding_filename(expId)
        if os.path.exists(codingFile):
            with open(codingFile,'rb') as f:
                coding = pickle.load(f)
        else:
            coding = {}
        return coding

    @classmethod
    def load_video_data(cls):
        '''Return video data, or empty dict if none saved.'''
        if os.path.exists(paths.VIDEO_FILENAME):
            with open(paths.VIDEO_FILENAME,'rb') as f:
                videoData = pickle.load(f)
        else:
            videoData = {}
        cls.videoData = videoData
        return videoData

    @classmethod
    def load_account_data(cls):
        '''Return saved account data, or empty dict if none saved.'''
        if os.path.exists(paths.ACCOUNT_FILENAME):
            with open(paths.ACCOUNT_FILENAME,'rb') as f:
                accountData = pickle.load(f)
        else:
            accountData = {}
        cls.accounts = accountData
        return accountData

    @classmethod
    def make_mp4s(cls, sessDirRel, vidNames, display=False, trimming=False, suffix='', replace=False):
        '''	Convert flvs in VIDEO_DIR to mp4s organized in SESSION_DIR for a
		particular session

        	sessDirRel: relative path to session directory where mp4s
        		should be saved. mp4s will be created in
        		paths.SESSION_DIR/sessDirRel.

        	vidNames: list of video names (flv filenames within
        		VIDEO_DIR, also keys into videoData) to convert

        	display: whether to display information about progress

        	trimming: False (default) not to do any trimming of video
        		file, or a maximum clip duration in seconds. The last
        		trimming seconds (counted from the end of the
        		shortest stream--generally video rather than audio)
        		will be kept, or if the video is shorter than
        		trimming, the entire video will be kept.

        	suffix: string to append to the mp4 filenames (they'll be
        		named as their originating flv filenames, plus
        		"_[suffix]") and to the fields 'mp4Path_[suffix]' and
        		'mp4Dur_[suffix]' in videoData. Default ''.

        	replace: False (default) to skip making an mp4 if (a) we
        		already have the correct filename and (b) we have a
        		record of it in videoData, True to make anyway.

        	To make the mp4, we first create video-only and
        		audio-only files from the original flv file. Then we
        		put them together and delete the temporary files. The
        		final mp4 has a duration equal to the length of the
        		video stream (technically it has a duration equal to
        		the shorter of the audio and video streams, but
        		generally video is shorter, and we pad the audio
        		stream with silence in case it's shorter). Trimming,
        		however, is done (to the best of my understanding)
        		from the end of the longest stream. This is
        		appropriate since it is possible for audio to
        		continue to the end of a recording period, while
        		video gets cut off earlier due to the greater
        		bandwidth required.

        	mp4s have a text label in the top left that shows
        		[segment]_[session]_[timestamp and randomstring] from
        		the original flv name.

        	Returns a dictionary with keys = vidNames. Each value is
        		a dict with the following fields: 'mp4Dur_[suffix]':
        		0 if no video was able to be created, due to missing
        		video or a missing video stream. It is also possible
        		for video not to be created if there is a video
        		stream, but it stops and then the audio stream
        		continues for at least trimming seconds after that.
        		'mp4Path_[suffix]': Relative path (from
        		paths.SESSION_DIR) to mp4 created, or '' if as above
        		mp4 was not created.

        	(Does NOT save anything directly to videoData, since this
        		may be called many times in short succession!)'''


        vidData = {}
        concat = [paths.FFMPEG]

        # Get full path to the session directory
        sessionDir = os.path.join(paths.SESSION_DIR, sessDirRel)

        # Keep track of whether we
        madeAnyFiles = False

        # Convert each flv clip to mp4 & get durations
        for (iVid, vid) in enumerate(vidNames):
            vidPath = os.path.join(paths.VIDEO_DIR, vid)

            # If not replacing: check that we haven't already (tried to) make this mp4
            mergedFilename = vid[:-4] + '_' + suffix + '.mp4'
            mergedPath = os.path.join(sessionDir, mergedFilename)
            if not replace and os.path.exists(mergedPath) and vid in cls.videoData.keys() and ('mp4Dur_' + suffix) in cls.videoData[vid].keys() and ('mp4Path_' + suffix) in cls.videoData[vid].keys():
                if display:
                    print "Already have {} mp4 for video {}, skipping".format(suffix, vid)
                continue

            # Add this to the video data file, with default values in case we can't
            # actually create the mp4 file (video data missing).
            vidData[vid] = {}
            vidData[vid]['mp4Dur' + '_' + suffix] = 0
            vidData[vid]['mp4Path' + '_' + suffix] = ''

            # Check that we actually have any video data in the original
            height, origDur = videoutils.get_video_details(vid, ['height', 'duration'])
            if height == 0:
                warn('No video data for file {}'.format(vid))
                continue

            trimStrVideo = ''
            trimStrAudio = ''
            if trimming:
                startTimeVideo = max(0, origDur - trimming)
                startTimeAudio = max(0, origDur - trimming)
                trimStrVideo = ",trim=" + str(startTimeVideo)+":,setpts=PTS-STARTPTS"
                trimStrAudio = "asetpts=PTS-STARTPTS,atrim="+ str(startTimeAudio)+':,'

            # Make video-only file
            (_, frameId, sessStr, timestamp, _) = paths.parse_videoname(vid)
            filterComplexVideo = "[0:v]drawtext='fontfile=/Library/Fonts/Arial Black.ttf':text='"+frameId + '_' + '_' + sessStr + '_' + timestamp + "':fontsize=12:fontcolor=red:x=10:y=10,setpts=PTS-STARTPTS" + trimStrVideo + "[v0]"
            noAudioPath = os.path.join(sessionDir, vid[:-4] + '_video.mp4')
            sp.call([paths.FFMPEG, '-i', vidPath, '-filter_complex',
    filterComplexVideo, '-map', '[v0]', '-c:v', 'libx264', '-an', '-vsync', 'cfr', '-r', '30', '-crf', '18', noAudioPath, '-loglevel', cls.loglevel])
            madeAnyFiles = True

            # Check that the last N seconds contain video
            videoOnlyDur = videoutils.get_video_details(noAudioPath, ['duration'], fullpath=True)

            if videoOnlyDur > 0:
                if display:
                    print "Making {} mp4 for vid: {}".format(suffix, vid)

                # Make audio-only file
                filterComplexAudio = '[0:a]' + trimStrAudio + 'asetpts=PTS-STARTPTS,apad=pad_len=100000'
                audioPath = os.path.join(sessionDir, vid[:-4] + '_audio.m4a')
                sp.call([paths.FFMPEG, '-i', vidPath, '-vn', '-filter_complex', filterComplexAudio, '-c:a', 'libfdk_aac', '-loglevel', cls.loglevel, audioPath])

                # Put audio and video together
                sp.call([paths.FFMPEG, '-i', noAudioPath,  '-i', audioPath, '-c:v', 'copy', '-c:a', 'copy', '-shortest', '-loglevel', cls.loglevel, mergedPath])

                # Check the duration of the newly created clip
                (dur, startTime) = videoutils.get_video_details(mergedPath, ['duration', 'starttime'],  fullpath=True)

                # Save the (relative) path to the mp4 and its duration
                vidData[vid] = {}
                vidData[vid]['mp4Dur' + '_' + suffix] = dur
                vidData[vid]['mp4Path' + '_' + suffix] = os.path.join(sessDirRel, mergedFilename)


        # Clean up intermediate audio/video-only files
        if madeAnyFiles:
            sp.call('rm ' + os.path.join(sessionDir, '*_video.mp4'), shell=True)
            sp.call('rm ' + os.path.join(sessionDir, '*_audio.m4a'), shell=True)

        return vidData

    @classmethod
    def concat_mp4s(cls, concatPath, vidPaths):
        '''Concatenate a list of mp4s into a single new mp4.

        concatPath: full path to the desired new mp4 file, including
        	extension vidPaths: relative paths (within paths.SESSION_DIR) to
        	the videos to concatenate. Videos will be concatenated in the
        	order they appear in this list.

        Return value: vidDur, the duration of the video stream of the
        	concatenated mp4 in seconds. vidDur is 0 if vidPaths is empty,
        	and no mp4 is created.'''

        concat = [paths.FFMPEG]
        inputList = ''

        # If there are no files to concat, immediately return 0.
        if not len(vidPaths):
            return 0

        # Build the concatenate command
        for (iVid, vid) in enumerate(vidPaths):
            concat = concat + ['-i', os.path.join(paths.SESSION_DIR, vid)]
            inputList = inputList + '[{}:0][{}:1]'.format(iVid, iVid)

        # Concatenate the videos
        concat = concat + ['-filter_complex', inputList + 'concat=n={}:v=1:a=1'.format(len(vidPaths)) + '[out]', '-map', '[out]', concatPath, '-loglevel', 'error']
        sp.call(concat)

        # Check and return the duration of the video stream
        vidDur = videoutils.get_video_details(concatPath, 'vidduration', fullpath=True)
        return vidDur

    @classmethod
    def batch_id_for_filename(cls, expId, batchFilename):
        '''Returns the batch ID for a given experiment & batch filename.'''

        batches = load_batch_data(expId)
        if not len(batchFilename):
            raise ValueError('remove_batch: must provide either batchId or batchFilename')
        for id in batches.keys():
            if batches[id]['batchFile'] == batchFilename:
                return id
        raise ValueError('remove_batch: no batch found for filename {}'.format(batchFilename))

    @classmethod
    def export_accounts(cls):
        '''Create a .csv sheet showing all account data.

        All fields except password and profiles will be included. Instead of the list of child
        profile dicts under 'profiles', the individual dicts will be expanded as
        child[N].[fieldname] with N starting at 0.
        '''
        cls.load_account_data() # since this may be called without initializing an instance

        accs = []
        headers = set()
        allheaders = set()
        for (userid, acc) in cls.accounts.items():
            thisAcc = acc['attributes']
            thisAcc['username'] = userid
            profiles = thisAcc['profiles']
            del thisAcc['profiles']
            del thisAcc['password']
            headers = headers | set(thisAcc.keys())
            iCh = 0
            for pr in profiles:
                for (k,v) in pr.items():
                    thisAcc['child' + str(iCh) + '.' + k] = v
                iCh += 1
            for k in thisAcc.keys():
                if type(thisAcc[k]) is unicode:
                    thisAcc[k] = thisAcc[k].encode('utf-8')
            accs.append(thisAcc)
            allheaders = allheaders | set(thisAcc.keys())

        # Order headers in the file: initial list, then regular, then child-profile
        initialHeaders = [u'username']
        childHeaders = allheaders - headers
        headers = list(headers - set(initialHeaders))
        headers.sort()
        childHeaders = list(childHeaders)
        childHeaders.sort()
        headerList = initialHeaders + headers + childHeaders
        headerList = [h.encode('utf-8') for h in headerList]

        # Back up any existing accounts csv file by the same name
        accountsheetPath = paths.accountsheet_filename()
        backup_and_save_dict(accountsheetPath, accs, headerList)


    def __init__(self, expId):
        self.expId = expId
        self.batchData = self.load_batch_data(expId)
        self.coding = self.load_coding(expId)
        self.sessions = self.load_session_data(expId)
        self.videoData = self.load_video_data()
        self.accounts = self.load_account_data()
        print 'initialized study {}'.format(expId)

    def update_session_data(self):
        '''Pull updated session data from server, save, and load into this experiment.'''
        update_session_data(self.expId, display=False)
        self.sessions = self.load_session_data(self.expId)

    def update_video_data(self, newVideos=[], reprocess=False, resetPaths=False,
        display=False):
        '''Updates video data file for this experiment.

        keyword args:

        newVideos: If [] (default), process all video
            names in the video directory that are not already in the video
            data file. Otherwise process only the list newVideos. Should be
            a list of filenames to find in VIDEO_DIR. If 'all', process all
            video names in the video directory.

        reprocess: Whether to
            reprocess filenames that are already in the data file. If true,
            recompute framerate/duration (BUT DO NOT CLEAR BATCH DATA).
            Default false (skip filenames already there). Irrelevant if
            newVideos==[].

        resetPaths: Whether to reset mp4Path/mp4Dur
            fields (e.g. mp4Path_whole, mp4Path_trimmed) to ''/-1 (default
            False)

        Returns: (sessionsAffected, improperFilenames, unmatchedVideos)

        sessionsAffected: list of sessionIds (as for indexing into
            coding)

        improperFilenames: list of filenames skipped because
            they couldn't be parsed

        unmatchedFilenames: list of filenames
            skipped because they couldn't be matched to any session data

        '''

        # Get current list of videos
        videoFilenames = paths.get_videolist()

        # Parse newVideos input
        if len(newVideos) == 0:
            newVideos = list(set(videoFilenames) - set(self.videoData.keys()))
        elif newVideos=="all":
            newVideos = videoFilenames

        print "Updating video data. Processing {} videos.".format(len(newVideos))

        sessionData = self.sessions['sessions']

        sessionsAffected = []
        improperFilenames = []
        unmatchedFilenames = []

        for vidName in newVideos:
            # Parse the video name and check format
            try:
                (expId, frameId, sessId, timestamp, shortname) = paths.parse_videoname(vidName)
            except AssertionError:
                print "Unexpected videoname format: " + vidName
                improperFilenames.append(vidName)
                continue
            key = paths.make_session_key(expId, sessId)

            # Skip videos for other studies
            if expId != self.expId:
                continue

            # Don't enter videos from the experimenter site, since we don't have
            # corresponding session/coding info
            if sessId == 'PREVIEW_DATA_DISREGARD':
                if display:
                    print "Preview video - skipping"
                continue;

            # Check that we can match this to a session
            if key not in [s['id'] for s in sessionData]:
                print """ Could not find session!
                    vidName: {}
                    sessId from filename: {}
                    key from filename: {}
                    actual keys (examples): {}
                    """.format(
                      vidName,
                      sessId,
                      key,
                      [s['id'] for s in sessionData[:10]]
                    )
                unmatchedFilenames.append(vidName)
                continue

            # Update info if needed (i.e. if replacing or don't have this one yet)
            alreadyHaveRecord = (vidName in self.videoData.keys())
            if (not alreadyHaveRecord) or (reprocess or resetPaths):

                sessionsAffected.append(key) # Keep track of this session

                # Start from either existing record or any default values that need to be added
                if alreadyHaveRecord:
                    thisVideo = self.videoData[vidName]
                else:
                    thisVideo = {'inBatches': {}}

                # Add basic attributes
                thisVideo['shortname'] = shortname
                print shortname # TODO: remove
                thisVideo['sessionKey'] = key
                thisVideo['expId'] = expId

                # Add framerate/etc. info if needed
                if reprocess or not alreadyHaveRecord:
                    (nFrames, dur, bitRate) = videoutils.get_video_details(vidName, ['nframes', 'duration', 'bitrate'])
                    thisVideo['framerate'] = nFrames/dur
                    thisVideo['duration'] = dur
                    thisVideo['bitRate'] = bitRate

                # Add default path values if needed
                if resetPaths or not alreadyHaveRecord:
                    thisVideo['mp4Dur_whole'] = -1
                    thisVideo['mp4Path_whole'] = ''
                    thisVideo['mp4Dur_trimmed'] = -1
                    thisVideo['mp4Path_trimmed'] = ''

                if display:
                    print "Processed {}: framerate {}, duration {}".format(vidName,
                        thisVideo['framerate'], thisVideo['duration'])

                self.videoData[vidName] = thisVideo

        # Save the video data file
        backup_and_save(paths.VIDEO_FILENAME, self.videoData)

        return (sessionsAffected, improperFilenames, unmatchedFilenames)

    def update_videos_found(self):
        '''Use coding & video data to match expected videoname fragments to received videos for this experiment.

        Uses partial filenames in coding[sessKey]['videosExpected'] and searches for
        videos in the videoData that match the expected pattern. The field
        coding[sessKey]['videosFound'] is created or updated to correspond to
        coding[sessKey]['videosExpected']. ...['videosFound'][i] is a list of
        video filenames within VIDEO_DIR that match the pattern in
        ...['videosExpected'][i].

        Currently this is very inefficient--rechecks all sessions in the experiment.
        Note that this does not update the coding or video data; these should
        already be up to date.'''

        print "Updating videos found for study {}", self.expId

        # Process each session...
        for sessKey in self.coding.keys():
            # Process the sessKey and check this is the right experiment
            (expIdKey, sessId) = paths.parse_session_key(sessKey)

            # Which videos do we expect? Skip if none.
            shortNames = self.coding[sessKey]['videosExpected']
            self.coding[sessKey]['nVideosExpected'] = len(shortNames)
            if len(shortNames) == 0:
                continue;


            # Which videos match the expected patterns? Keep track & save the list.
            self.coding[sessKey]['videosFound'] = []
            for (iShort, short) in enumerate(shortNames):
                theseVideos = [k for (k,v) in self.videoData.items() if (v['shortname']==short) ]
                if len(theseVideos) == 0:
                    warn('update_videos_found: Expected video not found for {}'.format(short))
                self.coding[sessKey]['videosFound'].append(theseVideos)

            self.coding[sessKey]['nVideosFound'] = len([vList for vList in self.coding[sessKey]['videosFound'] if len(vList) > 0])

        # Save coding & video data
        backup_and_save(paths.coding_filename(self.expId), self.coding)

    def make_mp4s_for_study(self, sessionsToProcess='missing', display=False,
        trimming=False, suffix=''):
        '''Convert flvs to mp4s for sessions in a particular study.

        expId: experiment id, string (ex.: 574db6fa3de08a005bb8f844)

        sessionsToProcess: 'missing', 'all', or a list of session keys (as
        	used to index into coding). 'missing' creates mp4s only if they
        	don't already exist (both video file and entry in videoData).
        	'all' creates mp4s for all session flvs, even if they already
        	exist.

        display: (default False) whether to print out information about
        	progress

        trimming: False (default) not to do any trimming of video file, or a
        	maximum clip duration in seconds. The last trimming seconds
        	(counted from the end of the shortest stream--generally video
        	rather than audio) will be kept, or if the video is shorter than
        	trimming, the entire video will be kept. As used by make_mp4s.

        suffix: string to append to the mp4 filenames (they'll be named as
        	their originating flv filenames, plus "_[suffix]") and to the
        	fields 'mp4Path_[suffix]' and 'mp4Dur_[suffix]' in videoData.
        	Default ''. As used by make_mp4s.

        Calls make_mp4s to actually create the mp4s; see documentation there.

        The following values are set in videoData[video]: 'mp4Dur_[suffix]':
        	0 if no video was able to be created, due to missing video or a
        	missing video stream. It is also possible for video not to be
        	created if there is a video stream, but it stops and then the
        	audio stream continues for at least trimming seconds after that.
        	'mp4Path_[suffix]': Relative path (from paths.SESSION_DIR) to mp4
        	created, or '' if as above mp4 was not created.'''

        print "Making {} mp4s for study {}".format(suffix, self.expId)

        if sessionsToProcess in ['missing', 'all']:
            sessionKeys = self.coding.keys()
        else:
            # Make sure list of sessions is unique
            sessionKeys = list(set(sessionsToProcess))


        # Process each session...
        for sessKey in sessionKeys:
            # Process the sessKey and check this is the right experiment
            (expIdKey, sessId) = paths.parse_session_key(sessKey)
            if not expIdKey == self.expId:
                print "Skipping session not for this ID: {}".format(sessKey)
                continue

            # Which videos do we expect? Skip if none.
            shortNames = self.coding[sessKey]['videosExpected']
            if len(shortNames) == 0:
                continue;

            # Expand the list of videos we'll need to process
            vidNames = []
            for vids in self.coding[sessKey]['videosFound']:
                vidNames = vidNames + vids

            # Choose a location for the concatenated videos
            sessDirRel = os.path.join(self.expId, sessId)
            sessionDir = os.path.join(paths.SESSION_DIR, sessDirRel)
            make_sure_path_exists(sessionDir)

            # Convert each flv clip to mp4 & get durations

            if display:
                print 'Session: ', sessId

            replace = sessionsToProcess == 'all'

            mp4Data = self.make_mp4s(sessDirRel, vidNames, display, trimming=trimming, suffix=suffix, replace=replace)

            for vid in mp4Data.keys():
                # Save the (relative) path to the mp4 and its duration in video data
                # so we can use it when concatenating these same videos into another
                # file
                self.videoData[vid]['mp4Path' + '_' + suffix] = mp4Data[vid]['mp4Path' + '_' + suffix]
                self.videoData[vid]['mp4Dur' + '_' + suffix] = mp4Data[vid]['mp4Dur' + '_' + suffix]


        # Save coding & video data
        backup_and_save(paths.VIDEO_FILENAME, self.videoData)

    def concatenate_session_videos(self, sessionKeys, replace=False, display=False):
        '''Concatenate videos within the same session for the specified sessions.

        Should be run after update_videos_found as it relies on videosFound
        	in coding. Does create any missing _whole mp4s but does not
        	replace existing ones.

        expId: experiment ID to concatenate videos for. Any sessions
        	associated with other experiments will be ignored (warning
        	shown).

        sessionKeys: 'all', 'missing', or a list of session keys
        	to process, e.g. as returned by update_video_data. Session keys
        	are the IDs in session data and the keys for the coding data.

        replace: whether to replace existing concatenated files (default
        	False)

        display: whether to show debugging output (default False)

        For each session, this: - uses videosFound in the coding file to
        	locate (after creating if necessary) single-clip mp4s (untrimmed)
        	with text labels - creates a concatenated mp4 with all video for
        	this session (in order) in SESSION_DIR/expId/sessId/, called
        	expId_sessId.mp4

        Does not save any coding or video data. '''

        print "Making concatenated session videos for study {}".format(self.expId)

        if sessionKeys in ['missing', 'all']:
            sessionKeys = self.coding.keys()
        else:
            # Make sure list of sessions is unique
            sessionKeys = list(set(sessionKeys))

        self.make_mp4s_for_study(sessionsToProcess=sessionKeys, display=display, trimming=False, suffix='whole')

        # Process each session...
        for sessKey in sessionKeys:

            # Process the sessKey and check this is the right experiment
            (expIdKey, sessId) = paths.parse_session_key(sessKey)
            if not expIdKey == self.expId:
                print "Skipping session not for this ID: {}".format(sessKey)
                continue

            if display:
                print 'Session: ', sessKey

            # Choose a location for the concatenated videos
            sessDirRel = os.path.join(self.expId, sessId)
            sessionDir = os.path.join(paths.SESSION_DIR, sessDirRel)
            make_sure_path_exists(sessionDir)
            concatFilename = self.expId + '_' +  sessId + '.mp4'
            concatPath = os.path.join(sessionDir, concatFilename)

            # Skip if not replacing & file exists
            if not replace and os.path.exists(concatPath):
                print "Skipping, already have concat file: {}".format(concatFilename)
                continue

            # Which videos match the expected patterns? Keep track & save the list.
            vidNames = []
            for vids in self.coding[sessKey]['videosFound']:
                vidNames = vidNames + vids

            # Sort the vidNames found by timestamp so we concat in order.
            withTs = [(paths.parse_videoname(v)[3], v) for v in vidNames]
            vidNames = [tup[1] for tup in sorted(withTs)]
            vidNames = [v for vid in vidNames if len(self.videoData[vid]['mp4Path_whole'])] # TODO: this assumes we have mp4Path_whole in all cases

            if len(vidNames) == 0:
                warn('No video data for session {}'.format(sessKey))
                continue

            totalDur = 0
            for (iVid, vid) in enumerate(vidNames):
                totalDur = totalDur + self.videoData[vid]['mp4Dur_whole']

            # Concatenate mp4 videos

            vidDur = self.concat_mp4s(concatPath, [os.path.join(paths.SESSION_DIR, self.videoData[vid]['mp4Path_whole']) for vid in vidNames])

            if display:
                print 'Total duration: expected {}, actual {}'.format(totalDur, vidDur)
                # Note: "actual total dur" is video duration only, not audio or standard "overall" duration. This is fine for our purposes so far where we don't need exactly synchronized audio and video in the concatenated files (i.e. it's possible that audio from one file might appear to occur during a different file (up to about 10ms per concatenated file), but would need to be fixed for other purposes!

            # Warn if we're too far off (more than one video frame at 30fps) on
            # the total duration
            if abs(totalDur - vidDur) > 1./30:
                warn('Predicted {}, actual {}'.format(totalDur, vidDur))

    def batch_videos(self, batchLengthMinutes=5, codingCriteria={'consent':['yes'], 'usable':['yes']},
        includeIncompleteBatches=True):
        ''' Create video batches for a study.

        expId: experiment id, string (ex.: 574db6fa3de08a005bb8f844)

        batchLengthMinutes: minimum batch length in minutes. Videos will be
        	added to one batch until they exceed this length.

        codingCriteria: a dictionary of requirements on associated coding
        	data for videos to be included in a batch. keys are keys within a
        	coding record (e.g. 'consent') and values are lists of acceptable
        	values. Default {'consent':['yes'], 'usable':['yes']}. Values are
        	insensitive to case and leading/trailing whitespace.

        includeIncompleteBatches: whether to create a batch for the
        	"leftover" files even though they haven't gotten to
        	batchLengthMinutes long yet.

        Trimmed mp4s (ending in _trimmed.mp4) are used for the batches. These
        	must already exist--call make_mp4s_for_study first. Only videos
        	not currently in any batch will be added to a batch.

        Batch mp4s are named [expId]_[short random code].mp4 and are stored
        	in paths.BATCH_DIR. Information about the newly created batches
        	is stored in two places: - batch data: adds new mapping batchKey
        	: {'batchFile': batchFilename, 'videos': [(sessionKey, flvName,
        	duration), ...] } - videoData: add
        	videoData[flvName]['inBatches'][batchId] = index in batch

        '''

        print "Making video batches for study {}".format(self.expId)

        vidsToProcess = []

        # First, find all trimmed, not-currently-in-batches videos for this study.
        for sessKey in self.coding.keys():
            for vidList in self.coding[sessKey]['videosFound']:
                for vid in vidList:
                    if 'mp4Path_trimmed' in self.videoData[vid].keys():
                        mp4Path = self.videoData[vid]['mp4Path_trimmed']
                        mp4Dur  = self.videoData[vid]['mp4Dur_trimmed']
                        if len(mp4Path) and mp4Dur and not len(self.videoData[vid]['inBatches']):
                            vidsToProcess.append((sessKey, vid))

        # Check for coding criteria (e.g. consent, usable)
        for (criterion, values) in codingCriteria.items():
            values = [v.lower().strip() for v in values]
            vidsToProcess = [(sessKey, vid) for (sessKey, vid) in vidsToProcess if self.coding[sessKey][criterion].lower().strip() in values]

        # Separate list into batches; break off a batch whenever length exceeds
        # batchLengthMinutes
        batches = []
        batchDurations = []
        currentBatch = []
        currentBatchLen = 0
        for (iVid, (sessKey, vid)) in enumerate(vidsToProcess):
            dur = self.videoData[vid]['mp4Dur_trimmed']
            currentBatch.append((sessKey, vid, dur))
            currentBatchLen += dur

            # Check if size of videos changes between this & next video
            sizeMismatch = False
            if (iVid + 1) < len(vidsToProcess):
                currentBatchWidth = videoutils.get_video_details(vid, 'width')
                nextBatchWidth = videoutils.get_video_details(vidsToProcess[iVid+1][1], 'width')
                sizeMismatch = nextBatchWidth != currentBatchWidth

            if sizeMismatch or (currentBatchLen > batchLengthMinutes * 60):
                batches.append(currentBatch)
                batchDurations.append(currentBatchLen)
                currentBatch = []
                currentBatchLen = 0

        # If anything's left in the last batch, include it
        if len(currentBatch):
            if includeIncompleteBatches:
                batches.append(currentBatch)
                batchDurations.append(currentBatchLen)
            else:
                warn('Some videos not being batched because they are not long enough for a complete batch')

        for [iBatch, batchList] in enumerate(batches):
            # Name the batch file
            done = False
            while not done:
                concatFilename = self.expId + '_' + ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(5)) + '.mp4'
                done = concatFilename not in paths.get_batchfiles()
            concatPath = os.path.join(paths.BATCH_DIR, concatFilename)
            print concatPath

            # Get full paths to videos
            batchPaths = [os.path.join(paths.SESSION_DIR, self.videoData[vid]['mp4Path_trimmed']) for (sessKey, vid, dur) in batchList]

            # Create the batch file
            batchDur = self.concat_mp4s(concatPath, batchPaths)

            print "Batch duration -- actual: {}, expected: {}".format(batchDur, batchDurations[iBatch])
            durDiff = batchDur - batchDurations[iBatch]
            if durDiff > 0.033: # Greater than one frame at 30fps
                warn('Difference between predicted and actual batch length, batch filename {}'.format(concatFilename))

            # Add the batch to the videoData file
            self.add_batch(concatFilename, batchList)

    def add_batch(self, batchFilename, videos):
        '''Add a batched video to data files.

        expId: experiment id, string (ex.: 574db6fa3de08a005bb8f844)
        	batchFilename: filename of batch video file within batch dir (not
        	full path)

        videos: ordered list of (sessionId, videoFilename,
        	duration) tuples. sessionId is an index into the coding
        	directory, videoFilename is the individual filename (not full
        	path).

        The batch data file for this experiment will be updated to include
        	this batch (see bat definition) and the videoData for all
        	included videos will be updated with their positions within this
        	batch: videoData[videoname]['inBatches'][batId] = iVid (index in
        	this batch) '''

        batchDur = videoutils.get_video_details(os.path.join(paths.BATCH_DIR, batchFilename),
             'vidduration', fullpath=True)

        # Create a batch dict for this batch
        bat = { 'batchFile': batchFilename,
                'videos': videos,
                'duration': batchDur,
                'expected': sum([v[2] for v in videos]),
                'addedOn': '{:%Y-%m-%d%H:%M:%S}'.format(datetime.datetime.now()),
                'codedBy': [] }

        # Add this batch to the existing batches
        batId = uuid.uuid4().hex
        self.batchData[batId] = bat

        # Add references to this batch in each videoData record affected
        for (iVid, (sessionId, videoname, dur)) in enumerate(videos):
            self.videoData[videoname]['inBatches'][batId] = iVid

        # Save batch and video data
        backup_and_save(paths.batch_filename(self.expId), self.batchData)
        backup_and_save(paths.VIDEO_FILENAME, self.videoData)

    def remove_batch(self, batchId='', batchFilename='', deleteVideos=False):
        '''Remove a batched video from the data files (batch and video data).

        Either batchId or batchFilename must be provided. batchId is the ID
        	used as a key in the batch data file for this experiment;
        	batchFilename is the filename within the batch directory. If both
        	are provided, only batchId is used.

        If batchId is 'all', all batches for this study are removed from the
        	batch and video data files.

        deleteVideos (default false): whether to remove the specified batch
        	videos in the batch dir as well as records of them

        Batch data will be removed from the batch file for this experiment
        	and from each included video in videoData.'''

        # First handle special case of removing all batches for this experiment
        if batchId == 'all':
            # Remove references to batches in all videoData for this study
            for (vid, vidData) in self.videoData.items():
                vidExpId = paths.parse_videoname(vid)[0]
                if vidExpId == self.expId:
                    self.videoData[vid]['inBatches'] = {}
            backup_and_save(paths.VIDEO_FILENAME, self.videoData)
            # Empty batch data file
            backup_and_save(paths.batch_filename(self.expId), {})
            # Remove batch videos
            if deleteVideos:
                for batchVideoname in paths.get_batchfiles():
                    vidExpId = batchVideoname.split('_')[0]
                    if vidExpId == self.expId:
                        sp.call('rm ' + os.path.join(paths.BATCH_DIR, batchVideoname), shell=True)

            return

        # Use filename if provided instead of batchId
        if not batchId:
            batchId = self.batch_id_for_filename(self.expId, batchFilename)

        # Remove this batch from batch data
        videos = self.batchData[batchId]['videos']
        vidName = self.batchData[batchId]['batchFile']
        del self.batchData[batchId]

        # Remove references to this batch in each videoData record affected
        for (iVid, (sessionId, videoname, dur)) in enumerate(videos):
            del self.videoData[videoname]['inBatches'][batchId]

        # Backup and save batch and video data
        backup_and_save(paths.batch_filename(expId), self.batchData)
        backup_and_save(paths.VIDEO_FILENAME, self.videoData)
        print 'Removed batch from batch and video data'

        # Delete video
        if deleteVideos:
            batchPath = os.path.join(paths.BATCH_DIR, vidName)
            if os.path.exists(batchPath):
                sp.call('rm ' + batchPath, shell=True)
                print 'Deleted batch video'

    def empty_coding_record(self):
        '''Return a new instance of an empty coding dict'''
        emptyRecord = {'consent': 'orig',
                'usable': '',
                'feedback': '',
                'videosExpected': [],
                'videosFound': []}
        for field in self.coderFields:
            emptyRecord[field] = {} # CoderName: 'comment'
        return emptyRecord

    def update_coding(self, display=False):
        '''Update coding data with empty records for any new sessions in saved session
        data.'''

        updated = False

        # If any existing coding records are missing expected fields, add them
        for (sessId, code) in self.coding.iteritems():
            empty = self.empty_coding_record()
            for missingKey in set(empty.keys()) - set(code.keys()):
                code[missingKey] = empty[missingKey]
                updated = True

        sessIds = [self.sessions['sessions'][iSess]['id'] for iSess in \
                        range(len(self.sessions['sessions']))]
        newIds = list(set(sessIds) - set(self.coding.keys()))
        newCoding = dict((k, self.empty_coding_record()) for k in newIds)

        self.coding.update(newCoding)

        for iSess in range(len(self.sessions['sessions'])):
            sessId = self.sessions['sessions'][iSess]['id']
            expData = self.sessions['sessions'][iSess]['attributes']['expData']
            self.coding[sessId]['videosExpected'] = []
            for (frameId, frameData) in expData.iteritems():
                if 'videoId' in frameData.keys():
                  self.coding[sessId]['videosExpected'].append(frameData['videoId'])

        backup_and_save(paths.coding_filename(self.expId), self.coding)

        if display:
            printer.pprint(self.coding)

        print "Updated coding with {} new records for experiment: {}".format(len(newCoding), self.expId)

    def generate_batchsheet(self, coderName):
        '''Create a .csv sheet for a coder to mark whether batches are coded.

        coderName: coder in paths.CODERS (e.g. 'Kim') or 'all' to display
        	coding status for all coders. Error raised if unknown coder used.

        Fields will be id, minutes (duration of batch in minutes, estimated
        	from sum of individual files), batchFile (filename of batch) and
        	codedBy-coderName.'''

        if coderName != 'all' and coderName not in paths.CODERS:
            raise ValueError('Unknown coder name', coderName)

        if coderName == 'all':
            coders = paths.CODERS
        else:
            coders = [coderName]

        batchList = []
        for (batchId, bat) in self.batchData.items():

            batchEntry = {  'id': batchId,
                            'minutesSum': sum([v[2] for v in bat['videos']])/60,
                            'minutesActual': bat.get('duration', -60)/60,
                            'addedOn': bat['addedOn'],
                            'batchFile': bat['batchFile']}

            for c in coders:
                batchEntry['codedBy-' + c] = 'yes' if c in bat['codedBy'] else 'no'

            batchList.append(batchEntry)

        headers = ['batchFile', 'addedOn', 'id', 'minutesSum', 'minutesActual']
        for c in coders:
            headers.append('codedBy-' + c)

        for b in batchList:
            for k in b.keys():
                if type(b[k]) is unicode:
                    b[k] = b[k].encode('utf-8')

        batchList.sort(key=lambda b: b['addedOn'])

        # Back up any existing batch file by the same name & save
        batchsheetPath = paths.batchsheet_filename(self.expId, coderName)
        backup_and_save_dict(batchsheetPath, batchList, headers)

    def commit_batchsheet(self, coderName):
        '''Update codedBy in the batch file based on a CSV batchsheet.

        Raises IOError if the CSV batchsheet is not found.

        Batch keys are used to match CSV to pickled data records. Only
        	whether this coder has completed coding is updated, based on
        	the codedBy-[coderName] column. '''

        batchsheetPath = paths.batchsheet_filename(self.expId, coderName)

        field = 'codedBy-' + coderName

        if not os.path.exists(batchsheetPath):
            raise IOError('Batch sheet not found: {}'.format(codesheetPath))

        # Read each row of the coder CSV. 'rU' is important for Mac-formatted CSVs
        # saved in Excel.
        with open(batchsheetPath, 'rU') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                id = row['id']
                if id in self.batchData.keys(): # Match to the actual batch
                    if field in row.keys():
                        coded = row[field].strip().lower() # Should be 'yes' or 'no'
                        if coded == 'yes':
                            if coderName not in self.batchData[id]['codedBy']:
                                self.batchData[id]['codedBy'].append(coderName)
                        elif coded == 'no':
                            if coderName in self.batchData[id]['codedBy']:
                                self.batchData[id]['codedBy'].remove(coderName)
                        else:
                            raise ValueError('Unexpected value for whether coding is done for batch {} (should be yes or no): {}'.format(id, coded))
                    else:
                        warn('Missing expected row header in batch CSV: {}'.format(field))
                else: # Couldn't find this batch ID in the batch dict.
                    warn('ID found in batch CSV but not in batch file, ignoring: {}'.format(id))

        # Actually save coding
        backup_and_save(paths.batch_filename(self.expId), self.batchData)

    def generate_codesheet(self, coderName, showOtherCoders=True, showAllHeaders=False,
    includeFields=[], filter={}):
        '''Create a .csv coding sheet for a particular study and coder

        csv will be named expID_coderName.csv and live in the CODING_DIR.

        coderName: name of coder; must be in paths.CODERS. Use 'all' to show
        	all coders.

        showOtherCoders: boolean, whether to display columns for other
        	coders' coder-specific data

        showAllHeaders: boolean, whether to include all headers or only the
        	basics

        includeFields: list of field ENDINGS to include beyond basic headers.
        	For each session, any field ENDING in a string in this list will
        	be included. The original field name will be removed and the
        	corresponding data stored under this partial name, so they should
        	be unique endings within sessions. (Using just the ending allows
        	for variation in which segment the field is associated with.)

        filter: dictionary of header:value pairs that should be required in
        	order for the session to be included in the codesheet. (Most
        	common usage is {'consent':'yes'} to show only records we have
        	already confirmed consent for.)

        '''

        if coderName != 'all' and coderName not in paths.CODERS:
            raise ValueError('Unknown coder name', coderName)

        # Make coding into a list instead of dict
        codingList = []
        headers = set() # Keep track of all headers

        for (key,val) in self.coding.items():
            # Get session information for this coding session
            sess = self.find_session(self.sessions, key)

            # Combine coding & session data
            val = flatten_dict(val)
            sess = flatten_dict(sess)
            val.update(sess)

            # Find which account/child this session is associated with
            profile = val['attributes.profileId']
            pieces = profile.split('.')
            username = pieces[0]
            child = pieces[1]

            # Get the associated account data and add it to the session
            acc = self.accounts[username]
            childData = [pr for pr in acc['attributes']['profiles'] if pr['profileId']==profile]
            childDataLabeled = {}
            for (k,v) in childData[0].items():
                childDataLabeled['child.' + k] = v
            val.update(childDataLabeled)

            # Look for fields that end in any of the suffixes in includeFields.
            # If one is found, move the data from that field to the corresponding
            # member of includeFields.
            for fieldEnd in includeFields:
                for field in val.keys():
                    if field[-len(fieldEnd):] == fieldEnd:
                        val[fieldEnd] = val[field]
                        del val[field]

            # Add any new headers from this session
            headers = headers | set(val.keys())

            codingList.append(val)

        # Organize the headers we actually want to put in the file - headerStart will come
        # first, then alphabetized other headers if we're using them
        headerStart = ['id', 'meta.created-on', 'child.profileId', 'consent', 'usable', 'feedback']

        # Insert this and other coders' data here if using
        if coderName == 'all':
            for field in self.coderFields:
                headerStart = headerStart + [h for h in headers if h[:len(field + '.')] == field + '.']
        else:
            for field in self.coderFields:
                headerStart = headerStart + [field + '.' + coderName]
                if showOtherCoders:
                    headerStart = headerStart + [h for h in headers if h[:len(field + '.')] == field + '.' and h != field + '.' + coderName]

        # Continue predetermined starting list
        headerStart = headerStart + ['attributes.feedback',
            'attributes.hasReadFeedback',
            'attributes.completed', 'nVideosExpected', 'nVideosFound', 'videosExpected', 'videosFound',
            'child.birthday', 'child.deleted', 'child.gender', 'child.profileId',
            'child.additionalInformation'] + includeFields

        # Add remaining headers from data if using
        if showAllHeaders:
            headerList = list(headers - set(headerStart))
            headerList.sort()
            headerList = headerStart + headerList
        else:
            headerList = headerStart

        # Filter to show only data that should go in sheet
        for (key, val) in filter.items():
            codingList = [sess for sess in codingList if key in sess.keys() and sess[key]==val]

        # Reencode anything in unicode
        for record in codingList:
            for k in record.keys():
                if type(record[k]) is unicode:
                    record[k] = record[k].encode('utf-8')

        codingList.sort(key=lambda b: b['meta.created-on'])

        # Back up any existing coding file by the same name & save
        codesheetPath = paths.codesheet_filename(self.expId, coderName)
        backup_and_save_dict(codesheetPath, codingList, headerList)

    def commit_coding(self, coderName):
        '''Update the coding file for expId based on a CSV edited by a coder.

        Raises IOError if the CSV file is not found.

        Session keys are used to match CSV to pickled data records. Only
        	coder fields for this coder (fields in coderFields +
        	.[coderName]) are updated.

        Fields are only *added* to coding records if there is a nonempty
        	value to place. Fields are *updated* in all cases (even to an
        	empty value).'''

        # Fetch coding information: path to CSV, and which coder fields
        codesheetPath = paths.codesheet_filename(self.expId, coderName)
        thisCoderFields = [f + '.' + coderName for f in self.coderFields]

        if not os.path.exists(codesheetPath):
            raise IOError('Coding sheet not found: {}'.format(codesheetPath))

        # Read each row of the coder CSV. 'rU' is important for Mac-formatted CSVs
        # saved in Excel.
        with open(codesheetPath, 'rU') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                id = row['id']
                if id in self.coding.keys(): # Match to a sessionKey in the coding dict.
                    # Go through each expected coder-specific field, e.g.
                    # coderComments
                    for field in thisCoderFields:
                        if field in row.keys():
                            # Parse the CSV field name. It's been flattened, so what
                            # would be ...[fieldName][coderName] is now
                            # fieldName.coderName. Using this for more generalizability
                            # later if we want to be able to edit other coder names in
                            # addition--can manipulate thisCoderFields.
                            fieldParts = field.split('.')
                            if len(fieldParts) != 2:
                                warn('Bad coder field name {}, should be of the form GeneralField.CoderName'.format(field))
                                continue
                            genField, coderField = fieldParts

                            # Field isn't already there
                            if genField not in self.coding[id].keys() or coderField not in self.coding[id][genField].keys():
                                if len(row[field]):
                                    print('Adding field {} to session {}: "{}"'.format(field, id, row[field]))
                                    self.coding[id][genField][coderField] = row[field]

                            # Field is already there and this value is new
                            elif self.coding[id][genField][coderField] != row[field]:
                                print('Updating field {} in session {}: "{}" ->  "{}"'.format(field, id, self.coding[id][genField][coderField], row[field]))
                                self.coding[id][genField][coderField] = row[field]
                        else:
                            warn('Missing expected row header in coding CSV: {}'.format(field))
                else: # Couldn't find this sessionKey in the coding dict.
                    warn('ID found in coding CSV but not in coding file, ignoring: {}'.format(id))

        # Actually save coding
        backup_and_save(paths.coding_filename(self.expId), self.coding)

    def commit_global(self, coderName, commitFields):
        '''Update the coding file for expId based on a CSV edited by a coder;
        edit global fields like consent/usable rather than coder-specific fields.

        expId: experiment id, string
            (ex.: 574db6fa3de08a005bb8f844)

        coderName: name of coder to use CSV file from. Raises IOError if the CSV
            file is not found.

        commitFields: list of headers to commit.

        Session keys are used to match CSV to pickled data records. Fields are
        updated in all cases (even to an empty value).'''

        codesheetPath = paths.codesheet_filename(self.expId, coderName)

        if not os.path.exists(codesheetPath):
            raise IOError('Coding sheet not found: {}'.format(codesheetPath))

        # Read each row of the coder CSV. 'rU' is important for Mac-formatted CSVs
        # saved in Excel.
        with open(codesheetPath, 'rU') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                id = row['id']
                if id in self.coding.keys(): # Match to a sessionKey in the coding dict.
                    for field in commitFields:
                        if field not in row.keys():
                            raise ValueError('Bad commitField name, not found in CSV')

                        if field not in self.coding[id].keys():
                            print 'Adding field {} to session {}: "{}"'.format(field, id, row[field])
                        elif row[field] != self.coding[id][field]:
                            print 'Updating field {} for session {}: "{}" to "{}"'.format(field, id, self.coding[id][field], row[field])
                        self.coding[id][field] = row[field]

                else: # Couldn't find this sessionKey in the coding dict.
                    warn('ID found in coding CSV but not in coding file, ignoring: {}'.format(id))

        # Actually save coding
        backup_and_save(paths.coding_filename(self.expId), self.coding)

    def send_feedback(self):
        '''Send feedback back to JamDB to show to participants from coding data.

        First updates session data from server so we know what feedback is new.

        Does not update feedback based on a coder CSV - need to first run
        commit_global(expId, coderName, ['feedback']) to save feedback to the
        coding file.

        '''

        # Update session data
        update_session_data(self.expId)
        self.sessions = self.load_session_data(self.expId)

        # Set up connection to JamDB
        client = ExperimenterClient(access_token=paths.OSF_ACCESS_TOKEN).authenticate()

        # For each session, look at old and new feedback; update if needed
        for sessKey in self.coding.keys():

            thisSession = self.find_session(self.sessions, sessKey)
            existingFeedback = thisSession['attributes']['feedback']

            newFeedback = self.coding[sessKey]['feedback']

            if newFeedback != existingFeedback:
                print 'Updating feedback for session {}. Existing: {}, new: {}'.format(sessKey, existingFeedback, newFeedback)
                client.set_session_feedback({'id': sessKey}, newFeedback)

        print "Sent updated feedback to server for exp {}".format(self.expId)

    def read_batch_coding(self):
        '''TODO: DOC'''
        for (batchID, batch) in self.batchData.items():
            theseCoders = batch['codedBy']
            printer.pprint([batch['batchFile'], theseCoders])
            # Extract list of lengths to use for demarcating trials
            vidLengths = [v[2] for v in batch['videos']]
            for coderName in theseCoders:
                vcodeFilename = paths.vcode_filename(batch['batchFile'], coderName)
                # Check that the VCode file exists
                if not os.path.isfile(vcodeFilename):
                    warn('Expected Vcode file {} for coder {} not found'.format(os.path.basename(vcodeFilename), coderName))
                    continue
                # Read in file
                (durations, leftLookTime, rightLookTime, oofTime) = \
                    vcode.read_preferential(vcodeFilename, interval=[], videoLengths=vidLengths)
                # Save data
                vcodeData = {'durations': durations, 'leftLookTime': leftLookTime,
                    'rightLookTime': rightLookTime, 'oofTime': oofTime}

                if 'vcode' in batch.keys():
                    batch['vcode'][coderName] = vcodeData
                else:
                    batch['vcode'] = {coderName: vcodeData}
                self.batchData[batchID] = batch

        # Save batch and video data
        backup_and_save(paths.batch_filename(self.expId), self.batchData)







def get_batch_info(expId='', batchId='', batchFilename=''):
        '''Helper: Given either a batchId or batch filename, return batch data for this
        batch. Must supply either expId or batchFilename.

        Returns the dictionary associated with this batch, with field:
        	batchFile - filename of batch, within BATCH_DIR videos - list of
        	(sessionKey, videoFilename, duration) tuples in order videos
        	appear in batch codedBy - list of coders who have coded this
        	batch'''

        # Load the batch data for this experiment
        if len(expId):
            batches = load_batch_data(expId)
        elif len('batchFilename'):
            expId = batchFilename.split('_')[0]
            batches = Experiment.load_batch_data(expId)
        else:
            raise ValueError('get_batch_info: must supply either batchFilename or expId')

        # Use filename if provided instead of batchId
        if not len(batchId):
            batchId = Experiment.batch_id_for_filename(expId, batchFilename)

        return batches[batchId]

helptext = '''
You'll use the program coding.py to create spreadsheets with updated data for you to work
with, and to 'commit' or save the edits you make in those spreadsheets to the underlying
data structures. Note that the spreadsheets you interact with are TEMPORARY files: they
are created, you edit them, and you commit them. Simply saving your spreadsheet from Excel
does NOT commit your work, and it may be overwritten.

In the commands below, YOURNAME is the name we have agreed on for you, generally your
first name with a capital first letter (e.g. 'Audrey'). So if you were told to type
python coding.py --coder YOURNAME
you would actually type
python coding.py --coder Audrey

STUDY is the study name, which can be either the full ID (found in the URL if you find the
correct study on Lookit) or a nickname you'll be told (e.g. 'physics'). Coding/batch sheets
and video data are always stored under the full ID.

To get an updated coding sheet for a particular study:
    python coding.py fetchcodesheet --coder YOURNAME --study STUDY

    This creates a coding spreadsheet named STUDYID_YOURNAME.csv in the coding directory.
    Do not move or rename it. Do not edit the first column, labeled id.

    All other fields are okay to edit/delete/hide,
    but only the ones with a .YOURNAME ending (e.g. coderComments.Audrey) will actually
    be saved when you commit the sheet. Only sessions where consent and usability have
    already been confirmed will be displayed on your sheet. Sessions are sorted by
    date/time.

To commit your coding sheet:
    python coding.py commitcodesheet --coder YOURNAME --study STUDY

    This updates the stored coding data to reflect changes you have made in any fields
    with a .YOURNAME ending in your coder sheet. Your coder sheet must exist and be in the
    expected location/filename for this to work.

To get an updated batch sheet for a particular study:
    python coding.py fetchbatchsheet --coder YOURNAME --study STUDY

    This creates a batch spreadsheet named STUDYID_batches_YOURNAME.csv in the coding
    directory so you can mark which batches you have coded. Each row is a batch; batches
    are sorted by date created. batchFile gives the filename of the batch within the
    batches directory.

    Do NOT edit the 'id' column or move/rename your spreadsheet. When you have coded a
    batch, change the value in the 'codedBy-YOURNAME' field from 'no' to 'yes'.

To commit your batch sheet:
    python coding.py commitbatchsheet --coder YOURNAME --study STUDY

    This updates the stored batch data to reflect changes you have made in the
    codedBy-YOURNAME field of your batch sheet. Your batch sheet must exist and be in the
    expected location/filename for this to work.

----------------- Advanced users & consent coders only -----------------------------------

To do a regular update:
    python coding.py update --study STUDY

    Standard full update. Updates account data, gets new videos, updates sessions, and
    processes video for this study.

To get an updated consent sheet:
    python coding.py fetchconsentsheet --coder YOURNAME --study STUDY

    This works exactly like fetching a coding sheet (and creates the same filename)
    but (a) all sessions (not just those with consent/usability already confirmed) will
    be shown and (b) all fields will be shown.

To commit data from a consent sheet:
    python coding.py commitconsentsheet --coder YOURNAME --study STUDY [--fields a b c ..]

    This commits global (not coder specific) data only from your consent sheet to the
    coding data. Fields committed are 'consent' and 'feedback' unless specified using
    fields (e.g. --fields feedback usable).

To send feedback to users:
    python coding.py sendfeedback --study STUDY

    This sends feedback currently in the coding data to the site, where it will be
    displayed to users. Feedback must first be updated, e.g. using commitconsentsheet.

To view all current coding/batches:
    python coding.py fetchcodesheet --coder all
    python coding.py fetchconsentsheet --coder all
    python coding.py fetchbatchsheet --coder all

    Using --coder all will show coder-specific fields from all coders.

To change the list of coders:
    change in .env file. You won't be able to generate a new coding or batch sheet for
    a coder removed from the list, but existing data won't be affected.

To change what fields coders enter in their coding sheets:
    edit coderFields in Experiment (in coding.py), then update coding.
    (python coding.py updatesessions --study study)

    New fields will be added to coding records the next time coding is
    updated. If an existing codesheet is committed before coding is updated OR a
    new coder sheet is created, a warning will be displayed that an expected field is
    missing.

To create batches of video:
    python coding.py makebatches --study STUDY

    Using any video not already in a batch, forms batches of approximately batchLengthMinutes
    (defined in coding.py) long and adds them to batch data. These will show up on
    batch sheets. Only videos from sessions with usability & consent confirmed are included.

To remove a video batch:
    python coding.py removebatch --study STUDY [--batchID batchID] [--batchFile batchFile]

    Remove the .mp4 and the record of a particular batch. Must provide either batch ID
    (from a batch sheet) or filename within the batch directory. Use --batchID all to
    remove all batches from a given study.

To check for missing video:
    Look at a coding sheet -- can see nVideosExpected and nVideosFound fields.

To check for issues with batch concatenation, where total file length != sum of individual
    file lengths:
    Look at a batch sheet -- compare minutesSum (sum of individual file lengths) and
    minutesActual (duration of video stream of batch mp4).

To look for and process VCode files for batch videos:
    python coding.py updatevcode --study STUDY

Partial updates:

    To get updated account data:
        python coding.py updateaccounts

        This gets updated account information from the server and creates a file
        accounts.csv in the coding directory. It is recommended to update account data *before*
        updating study data since new accounts may have participated.

    To get updated videos for all studies:
        python coding.py getvideos

        This fetches videos only from the S3 bucket, pulling from wowza to get any very new
        data, and puts them in the video directory directly.

    To get updated session data:
        python coding.py updatesessions --study STUDY

        This fetches session data from the database on the server and updates the coding data
        accordingly.

    To process videos for this study:
        python coding.py processvideo --study STUDY

        This will do some basic video processing on any new videos (not already processed)
        and store the results in the video data file (checking duration & bitrate). It
        checks that there are no video filenames that can't be matched to a session. The coding
        data is updated to show all videos found for each session, matched to the expected videos,
        and videos are converted to mp4 and concatenated by session, with the results stored
        under sessions/STUDYID. (Existing videos are not overwritten.)'''



if __name__ == '__main__':



    studyNicknames = {'phys': '57a212f23de08a003c10c6cb',
                      'test': '57adc3373de08a003fb12aad'}
    # TODO: select fields to display
    includeFieldsByStudy = {'57a212f23de08a003c10c6cb': [],
                            '57adc3373de08a003fb12aad': []}

    trimLength = 20
    batchLengthMinutes = 5

    actions = {'fetchcodesheet': ['coder', 'study'],
               'commitcodesheet': ['coder', 'study'],
               'fetchconsentsheet': ['coder', 'study'],
               'commitconsentsheet': ['coder', 'study'],
               'sendfeedback': ['study'],
               'fetchbatchsheet': ['coder', 'study'],
               'commitbatchsheet': ['coder', 'study'],
               'updateaccounts': [],
               'getvideos': [],
               'updatesessions': ['study'],
               'processvideo': ['study'],
               'update': ['study'],
               'makebatches': ['study'],
               'removebatch': ['study'],  # must provide batchID or batchFile
               'exportmat': ['study'],
               'updatevcode': ['study'],
               'tests': []}

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Coding operations for Lookit data',
        epilog=helptext, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('action',
        choices=actions.keys(),
        help='Action to take')
    parser.add_argument('--coder', choices=paths.CODERS + ['all'],
        help='Coder name to create sheet or commit coding for')
    parser.add_argument('--study', help='Study ID')
    parser.add_argument('--fields', help='Fields to commit (used for commitconsentsheet only)',
        action='append', default=['consent', 'feedback'])
    parser.add_argument('--batchID', help='Batch ID to remove, or "all" (used for removebatch only)')
    parser.add_argument('--batchFile', help='Batch filename to remove (used for removebatch only)')

    args = parser.parse_args()

    # Additional input-checking for fields required for specific actions
    if 'study' in actions[args.action] and not args.study:
        raise ValueError('Must supply a study ID to use this action.')
    if 'coder' in actions[args.action] and not args.coder:
        raise ValueError('Must supply a coder name to use this action.')

    # Process any study nicknames
    if args.study:
        args.study = studyNicknames.get(args.study, args.study)
        exp = Experiment(args.study)
        includeFields = includeFieldsByStudy.get(args.study, [])

    ### Process individual actions

    if args.action == 'sendfeedback':
        print 'Sending feedback...'
        exp.send_feedback()

    elif args.action == 'fetchcodesheet':
        print 'Fetching codesheet...'
        exp.generate_codesheet(args.coder, filter={'consent':'yes'}, showAllHeaders=False,
            includeFields=includeFields)

    elif args.action == 'fetchconsentsheet':
        print 'Fetching consentsheet...'
        exp.generate_codesheet(args.coder, filter={}, showAllHeaders=True)

    elif args.action == 'commitcodesheet':
        print 'Committing codesheet...'
        exp.commit_coding(args.coder)

    elif args.action == 'commitconsentsheet':
        print 'Committing consentsheet...'
        exp.commit_global(args.coder, args.fields)

    elif args.action == 'fetchbatchsheet':
        print 'Making batchsheet...'
        exp.generate_batchsheet(args.coder)

    elif args.action == 'commitbatchsheet':
        print 'Committing batchsheet...'
        exp.commit_batchsheet(args.coder)

    elif args.action == 'updateaccounts':
        print 'Updating accounts...'
        update_account_data()
        Experiment.export_accounts()

    elif args.action == 'getvideos':
        print 'Syncing videos with server...'
        newVideos = sync_S3(pull=True)

    elif args.action == 'updatesessions':
        print 'Updating session and coding data...'
        exp.update_session_data()
        exp.update_coding(display=False)

    elif args.action == 'processvideo':
        print 'Processing video...'
        sessionsAffected, improperFilenames, unmatched = exp.update_video_data(reprocess=False, resetPaths=False, display=False)
        assert len(unmatched) == 0
        exp.update_videos_found()
        exp.concatenate_session_videos('all', display=True, replace=False)

    elif args.action == 'update':
        print 'Starting Lookit update, {:%Y-%m-%d%H:%M:%S}'.format(datetime.datetime.now())
        update_account_data()
        exp.accounts = exp.load_account_data()
        newVideos = sync_S3(pull=True)
        exp.update_session_data()
        exp.update_coding(display=False)
        sessionsAffected, improperFilenames, unmatched = exp.update_video_data(reprocess=False, resetPaths=False, display=False)
        assert len(unmatched) == 0
        exp.update_videos_found()
        exp.concatenate_session_videos('all', display=True, replace=False)
        print 'update complete'

    elif args.action == 'makebatches': # TODO: update criteria
        print 'Making batches...'
        exp.make_mp4s_for_study(sessionsToProcess='missing', display=True, trimming=trimLength, suffix='trimmed')
        exp.batch_videos(batchLengthMinutes=batchLengthMinutes, codingCriteria={'consent':['orig'], 'usable':['']})

    elif args.action == 'removebatch':
        print 'Removing batch(es)...'
        exp.remove_batch(batchId=args.batchID, batchFilename=args.batchFile, deleteVideos=True)

    elif args.action == 'exportmat':
        coding_export = {}
        for k in exp.coding.keys():
            safeKey = k.replace('.', '_')
            coding_export[safeKey] = exp.coding[k]
        scipy.io.savemat(os.path.join(paths.DATA_DIR, exp.expId + '_coding.mat'), coding_export)

        batches_export = {}
        for k in exp.batchData.keys():
            safeKey = 'b' + k
            batches_export[safeKey] = exp.batchData[k]
        scipy.io.savemat(os.path.join(paths.DATA_DIR, exp.expId + '_batches.mat'), batches_export)

    elif args.action == 'updatevcode':
        exp.read_batch_coding()
