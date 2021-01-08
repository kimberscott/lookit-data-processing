import os
import subprocess as sp
import math
import sys
import errno
from sets import Set
import warnings
import numpy as np
import re
import shlex
import json
from videoutils import get_video_details

ORIGEXT = ['.mov', '.mp4']
VIDEXT = '.mp4'

def make_sure_path_exists(path):
	try:
		os.makedirs(path)
		return 1
	except OSError as exception:
		return 0
		if exception.errno != errno.EEXIST:
			raise

def make_mp4(inputpath, mp4dir, width='original', overwrite=True, rate=1000):
	"""Export an mp4 version of a video for the web.

	Arguments:
	inputpath - the full path to the video file to export
	mp4dir - the directory where the new file should go

	Keyword arguments:
	width - either 'original' to keep width of input file, or width in pixels

	The mp4 version will have the same filename as the input video, but
	with an mp4 extension. Aspect ratio is preserved if changing width."""

	(shortname, ext) = os.path.splitext(os.path.basename(inputpath))
	command = ["ffmpeg", "-i", inputpath, "-c:v", "libx264", "-preset", "slow",
			"-b:v", str(rate) + "k", "-maxrate", str(rate) + "k", "-bufsize", str(2*rate) + "k",
			"-c:a", "libfdk_aac", "-b:a", "128k"]
	if not(width=='original'):
		command = command + ['-vf', "scale=" + str(width) + ":-2"]

	outpath = os.path.join(mp4dir, shortname + '.mp4')
	if not(overwrite) and os.path.exists(outpath):
		return
	else:
		sp.check_call(command + [outpath])


def make_webm(inputpath, webmdir, width='original', overwrite=True, rate=1000):
	"""Export an webm version of a video for the web.

	Arguments:
	inputpath - the full path to the video file to export
	webmdir - the directory where the new file should go

	Keyword arguments:
	width - either 'original' to keep width of input file, or width in pixels

	The webm version will have the same filename as the input video, but
	with an webm extension. Aspect ratio is preserved if changing width."""

	(shortname, ext) = os.path.splitext(os.path.basename(inputpath))
	command = ["ffmpeg", "-i", inputpath, "-c:v", "libvpx",
			"-b:v", str(rate) + "k", "-maxrate", str(rate) + "k", "-bufsize", str(2*rate) + "k",
			"-c:a", "libvorbis", "-b:a", "128k", "-speed", "2"]
	if not(width=='original'):
		command = command + ['-vf', "scale=" + str(width) + ":-2"]
	outpath = os.path.join(webmdir, shortname + '.webm')
	if not(overwrite) and os.path.exists(outpath):
		return
	else:
		sp.check_call(command + [outpath])

def prep_mp4_and_webm(inputpath, width='original', overwrite=True):
	"""Export all video files in a directory to both webm and mp4 for the web.

	Arguments:
	inputpath - the video directory to process

	Keyword arguments:
	width - either 'original' to keep width of input file, or width in pixels (applied to
		all files)

	mp4 and webm versions will have the same filenames as the originals, but appropriate
	extensions. Aspect ratio is preserved if changing width."""

	if not(os.path.isdir(inputpath)):
		raise ValueError('prep_mp4_and_webm requires a path to a directory with videos')

	(parent, child) = os.path.split(inputpath)
	webmdir = os.path.join(parent, child, 'webm')
	mp4dir = os.path.join(parent, child, 'mp4')

	make_sure_path_exists(webmdir)
	make_sure_path_exists(mp4dir)

	videoExts = ['.mov', '.mp4', '.flv', '.webm', '.ogv', '.avi']
	for f in os.listdir(inputpath):
		if not(os.path.isdir(os.path.join(inputpath, f))):
			(shortname, ext) = os.path.splitext(f)
			if ext in videoExts:
				make_mp4(os.path.join(inputpath, f), mp4dir, width, overwrite)
				make_webm(os.path.join(inputpath, f), webmdir, width, overwrite)


def make_collage(videoDir, videoList, nCols, outPath, doSound, exportWidth, vidHeight=[], cropSquare=False):
	"""Make a grid of videos (mp4 format).

	Arguments:
	videoDir - directory where the input videos are (use '/' to just give full paths
		in videoList
	videoList - list of videos to include in the grid. They will appear in reading order.
		Videos should all be the same size! (But any aspect ratio is fine.)
	nCols - number of columns for the grid. The number of rows will be set accordingly.
	outPath - where to put the collage (full path and filename, excluding extension)
	doSound - boolean, whether to include sound in the collage.
	exportWidth - 0 not to export, otherwise width in pixels of mp4 & webm to create

	If doing sound, this creates a few temporary files in the same directory as the final
	collage, named (if the final output is collage.mp4) collage_silent.mp4 and
	collage_sound.wav.

	Sizes of input videos is unchanged, so final collage size is (originalWidth * nCols) x
	(originalHeight * nRows). """

	if doSound:
		(outPathDir, outPathFname) = os.path.split(outPath)
		outPathSilent = os.path.join(outPathDir, outPathFname + '_silent.mp4')
		outPathSound = os.path.join(outPathDir, outPathFname + '.wav')
	else:
		outPathSilent = outPath + '.mp4'

	outPath = outPath + '.mp4'

	# Step 1: make a silent collage

	nRows = int(math.ceil(len(videoList) / nCols))

	inputList = []
	for (iV, vidName) in enumerate(videoList):
		inputList = inputList + ['-i', os.path.join(videoDir, vidName)]

	command = ['ffmpeg'] + inputList

	# for control, change ih, h to 696

	border = 10
	# In general, use 'ih' and 'h'; if heights vary, input here.
	if vidHeight:
		vidHeight = str(vidHeight)
		vidHeightOverlay = vidHeight
	else:
		vidHeight = 'ih'
		vidHeightOverlay = 'h'

	filterStr = '[0:v]pad=' + str(border*(nCols-1)) + '+' + 'iw*' + str(nCols) + ':'  + str(border*(nRows-1)) + '+' + vidHeight + '*' + str(nRows) + '[x0];'
	for iVid in range(1, len(videoList)):
		if iVid==(len(videoList)-1):
			outStr = '[out]'
		else:
			outStr = '[x' + str(iVid) + ']'

		thisY = iVid / nCols
		thisX = iVid % nCols

		if cropSquare:
			filterStr = filterStr + '[' + str(iVid) + ':v]crop=iw:iw:0:0[y' + str(iVid-1) + '];'

			filterStr = filterStr + '[x' + str(iVid-1) + '][y' + str(iVid-1) + \
						']overlay=x=' + str(border*(thisX)) + "+(" + str(thisX) + '*w):y=' + str(border*(thisY)) + "+(" + str(thisY) + \
						'*' + vidHeightOverlay + '):repeatlast=1:shortest=0:eof_action=repeat' + \
						outStr + ';'
		else:
			filterStr = filterStr + '[x' + str(iVid-1) + '][' + str(iVid) + \
						':v]overlay=x=' + str(border*(thisX)) + "+(" + str(thisX) + '*w):y=' + str(border*(thisY)) + "+(" + str(thisY) + \
						'*' + vidHeightOverlay + '):repeatlast=1:shortest=0:eof_action=repeat' + \
						outStr + ';'


	command = command + ['-filter_complex', filterStr[:-1],
						 "-c:v", "libx264", '-map', '[out]', outPathSilent]

	sp.check_call(command)

	if doSound:

		# Step 2: make sound mix

		filterStr = 'amix=inputs=' + str(len(videoList)) + \
					':duration=first:dropout_transition=3'

		command = ['ffmpeg'] + inputList + ['-filter_complex', filterStr, \
				  outPathSound]

		sp.check_call(command)

		command = ['ffmpeg', '-i', outPathSilent, '-i', outPathSound, \
				   '-c:v', 'copy', '-c:a', 'libfdk_aac', '-shortest', \
				   outPath]
		sp.check_call(command)

		# Clean up intermediate files

		sp.call(['rm', outPathSilent])
		sp.call(['rm', outPathSound])

	if exportWidth != 0:
		(exportDir, baseFilename) = os.path.split(outPath)
		exportDir = os.path.join(exportDir, 'export')
		make_sure_path_exists(exportDir)
		make_mp4(outPath, exportDir, exportWidth, rate=2000)
		make_webm(outPath, exportDir, exportWidth, rate=2000)

def make_dummies(outDir, blankVideoPath, vidNames):
	'''Make blank labeled videos.

	outDir: directory to put the blank videos in
	blankVideoPath: full path to the mp4 video to use as the starting point
	vidNames: array of video filenames (no extension). One mp4 video will be created for
		each; it will just be the blank video with the vidName written on it. '''

	make_sure_path_exists(outDir)

	for vidName in vidNames:

		sp.call(["ffmpeg", "-i", blankVideoPath, "-ar", "22050", \
			"-q:v", "1", "-vf", "drawtext='fontfile=/Library/Fonts/Arial Black.ttf:text=\'" + \
				vidName+"\':fontsize=40:fontcolor=white:x=100:y=40'", os.path.join(outDir, vidName)])

# function to find the resolution of the input video file
# http://stackoverflow.com/a/34356719
def findVideoResolution(pathToInputVideo):
    cmd = "ffprobe -v quiet -print_format json -show_streams"
    args = shlex.split(cmd)
    args.append(pathToInputVideo)
    # run the ffprobe process, decode stdout into utf-8 & convert to JSON
    ffprobeOutput = sp.check_output(args).decode('utf-8')
    ffprobeOutput = json.loads(ffprobeOutput)

    # find height and width
    height = ffprobeOutput['streams'][0]['height']
    width = ffprobeOutput['streams'][0]['width']

    return height, width



def parse_video_filename(filename, orderDict):
	shortfilename = filename.split('.')
	shortfilename = shortfilename[0]
	pieces = shortfilename.split('_')
	camera = pieces[orderDict['camera']]
	event = pieces[orderDict['event']]
	object = pieces[orderDict['object']]
	if 'outcome' in orderDict.keys():
		outcome = pieces[orderDict['outcome']]
	else:
		outcome = ''
	if 'background' in orderDict.keys():
		background = pieces[orderDict['background']]
	else:
		background = ''
	return (event, outcome, object, camera, background)

def flipVideos(rawVideoDir, origVideoDir, unflippedOrderDict):
	print "Flipping:"
	vidLengths = {'apple':66, 'cup':86, 'lotion':68, 'orangeball':76, 'spray':90, 'whiteball':64}
	fadeFrames = 10

	make_sure_path_exists(origVideoDir)
	for f in os.listdir(rawVideoDir):
		if not(os.path.isdir(os.path.join(rawVideoDir, f))):
			(shortname, ext) = os.path.splitext(f)
			if ext in ORIGEXT:
				(event, outcome, object, camera, background) = parse_video_filename(shortname, unflippedOrderDict)
				print (event, outcome, object, camera, background)
				if outcome == 'up':
					continue


				sp.call(["ffmpeg", "-i", os.path.join(rawVideoDir, f), \
					"-vf", """vflip,fade=type=in:start_frame=1:nb_frames={}:color=0x009EFC,fade=type=out:start_frame={}:color=0x009EFC""".format(fadeFrames, vidLengths[object]-fadeFrames), "-loglevel", "error", \
					os.path.join(origVideoDir, event + '_up_' + object + '_' + background + '_' + camera + '.mp4')])
				sp.call(["ffmpeg", "-i", os.path.join(rawVideoDir, f), \
					"-vf", """fade=type=in:start_frame=1:nb_frames={}:color=0x009EFC,fade=type=out:start_frame={}:color=0x009EFC""".format(fadeFrames, vidLengths[object]-fadeFrames), "-loglevel", "error", \
					os.path.join(origVideoDir, event + '_down_' + object + '_' + background + '_' + camera + '.mp4')])
	return 0

### Crops and rescales 640px wide.
def cropVideos(origVideoDir, croppedVideoDir, regularOrderDict, originalSizes=[],
	cropStrings=[], which=[], cropByName=[], timecrop=[], fadeParams=[], doCrossFade=False):
	'''TODO: docstring
	timecrop: list of (ID, start, stop, padStart, padStop) tuples.
		ID: dict containing any keys in ['object', 'event', 'outcome', 'camera', 'background'] and values.
			This time cropping will be applied to any videos that match the values for all
			the specified keys.
		start, stop: start and stop times in s.
		padStart, padStop: amount of time to extend first and last frames by, in s.
	fadeParams: (fadeFrames, fadeColor)
	'''

	print "Cropping:"
	make_sure_path_exists(croppedVideoDir)
	for f in os.listdir(origVideoDir):
		if not(os.path.isdir(os.path.join(origVideoDir, f))):
			(shortname, ext) = os.path.splitext(f)
			if ext in ORIGEXT:
				if regularOrderDict:
					(event, outcome, object, camera, background) = parse_video_filename(shortname, regularOrderDict)
					thisID = {'event': event, 'outcome': outcome, 'object': object,
							  'camera': camera, 'background': background}
					if len(which)==2 and not (object, event) == which:
						continue
					if len(which)==3 and not (object, event, outcome) == which:
						continue
					print (event, outcome, object, camera, background)

					timecropCommand = []
					doTimeCrop = False
					if timecrop:
						for (ID, s, e, pS, pE) in timecrop:
							if all([thisID[key] == val for (key, val) in ID.items()]):
								startTime = s
								endTime = e
								padStart = pS
								padEnd = pE
								doTimeCrop = True
						if doTimeCrop:
							if not startTime == -1:
								timecropCommand = ["-ss", str(startTime)]
								if not endTime == -1:
									timecropCommand = timecropCommand + ["-t", str(endTime - startTime)]
						else:
							warnings.warn("No time cropping for this video")


				if cropByName:
					for (vidNames, cropStrForNames) in cropByName:
						if f in vidNames:
							cropStr = cropStrForNames

				else:
					if originalSizes == "*":
						cropStr = cropStrings[0]
					else:
						res = findVideoResolution(os.path.join(origVideoDir, f))
						if res in originalSizes:
							cropStr = cropStrings[originalSizes.index(res)]
						else:
							cropStr = """scale=640:-2"""

				cropStr = cropStr + ',setpts=PTS-STARTPTS'

				if doTimeCrop:
					croppedVid = os.path.join(croppedVideoDir, shortname + '_middle.mp4')
					croppedVidFinal = os.path.join(croppedVideoDir, shortname + '.mp4')
				else:
					croppedVid = os.path.join(croppedVideoDir, shortname + '.mp4')
					croppedVidFinal = croppedVid

				command = ["ffmpeg", "-i", os.path.join(origVideoDir, f), \
					"-vf", cropStr] + timecropCommand + ["-loglevel", "error", \
					croppedVid]

				sp.call(command)

				if doTimeCrop:
					firstImg = os.path.join(croppedVideoDir, shortname + '_first.png')
					lastImg = os.path.join(croppedVideoDir, shortname + '_last.png')
					firstVid = os.path.join(croppedVideoDir, shortname + '_first.mp4')
					lastVid = os.path.join(croppedVideoDir, shortname + '_last.mp4')

					sp.call(["ffmpeg", "-i", croppedVid,
						"-vframes", "1", "-f", "image2", firstImg, "-loglevel", "error"])
					[nF, dur, x, y] = get_video_details(croppedVid, ['nframes', 'vidduration', "width", "height"])
					sp.call(["ffmpeg", "-i", croppedVid,
						"-vf", "select='eq(n,{})'".format(nF-1), "-vframes", "1", "-f",
						"image2", lastImg, "-loglevel", "error"])
					sp.call(["ffmpeg", "-loop", "1", "-i", firstImg, "-t", str(padStart),
						firstVid, "-loglevel", "error"])
					sp.call(["ffmpeg", "-loop", "1", "-i", lastImg, "-t", str(padEnd),
						lastVid, "-loglevel", "error"])

					if not doCrossFade:
						concat_mp4s(croppedVidFinal, [firstVid, croppedVid, lastVid])

					else:
						unfaded = os.path.join(croppedVideoDir, shortname + '_beforecrossfade.mp4')
						concat_mp4s(unfaded, [croppedVid, lastVid])
						# see crossfade advice at http://superuser.com/a/778967
						sp.call(["ffmpeg", "-i", unfaded, "-i", firstVid, "-f", "lavfi",
							 "-i", "color=white:s={}x{}".format(int(x),int(y)), "-filter_complex",
							"[0:v]format=pix_fmts=yuva420p,fade=t=out:st={}:d={}:alpha=1,setpts=PTS-STARTPTS[va0];\
							[1:v]format=pix_fmts=yuva420p,fade=t=in:st=0:d={}:alpha=1,setpts=PTS-STARTPTS+{}/TB[va1];\
							[2:v]scale={}x{},trim=duration={}[over];\
							[over][va0]overlay=format=yuv420[over1];\
							[over1][va1]overlay=format=yuv420[outv]".format(dur+padEnd, padEnd, padEnd, dur, int(x), int(y), dur+padStart+padEnd),
							"-vcodec", "libx264", "-map", "[outv]", croppedVidFinal, "-loglevel", "error"])
						os.remove(unfaded)



					os.remove(firstImg)
					os.remove(lastImg)
					os.remove(firstVid)
					os.remove(lastVid)
					os.remove(croppedVid)

				if fadeParams:
					(fadeFrames, fadeColor) = fadeParams
					nF = get_video_details(croppedVidFinal, 'nframes')
					unfaded = os.path.join(croppedVideoDir, shortname + '_unfaded.mp4')
					os.rename(croppedVidFinal, unfaded)

					sp.call(["ffmpeg", "-i", unfaded, \
					"-vf", """fade=type=in:start_frame=1:nb_frames={}:color={},fade=type=out:start_frame={}:color={}""".format(fadeFrames, fadeColor, nF-fadeFrames, fadeColor),
					"-loglevel", "error", croppedVidFinal])

					os.remove(unfaded)



def combineVideos(croppedVideoDir, sidebysideDir, regularOrderDict, whichVersions, minimal=False):
	print "Joining:"
	make_sure_path_exists(sidebysideDir)
	commands = ["""[0:v]setpts=PTS-STARTPTS,pad=iw*3:ih:color=white[a];[1:v]setpts=PTS-STARTPTS[z];[a][z]overlay=x=2*w:repeatlast=1:shortest=1:eof_action=repeat[out]""", \
				"""[0:v]setpts=PTS-STARTPTS,hflip,pad=iw*3:ih:color=white[b];[1:v]setpts=PTS-STARTPTS[z];[b][z]overlay=x=2*w:repeatlast=1:shortest=1:eof_action=repeat[out]""", \
				"""[0:v]setpts=PTS-STARTPTS,pad=iw*3:ih:color=white[b];[1:v]setpts=PTS-STARTPTS[z];[z]hflip[c];[b][c]overlay=x=2*w:repeatlast=1:shortest=1:eof_action=repeat[out]""", \
				"""[0:v]setpts=PTS-STARTPTS,hflip,pad=iw*3:ih:color=white[b];[1:v]setpts=PTS-STARTPTS[z];[z]hflip[c];[b][c]overlay=x=2*w:repeatlast=1:shortest=1:eof_action=repeat[out]"""]
	suffixes = ['NN', 'RN', 'NR', 'RR']

	allfiles = os.listdir(croppedVideoDir)

	for iVid1, video1 in enumerate(allfiles):
		(shortname1, ext1) = os.path.splitext(video1)
		if not(os.path.isdir(os.path.join(croppedVideoDir, video1))) and ext1 == VIDEXT:
			for iVid2 in range(len(allfiles)):
				if iVid2 == iVid1:
					continue
				if minimal and iVid2 <= iVid1:
					continue
				else:
					video2 = allfiles[iVid2]
					(shortname2, ext2) = os.path.splitext(video2)
					if not(os.path.isdir(os.path.join(croppedVideoDir, video2))) and ext2 == VIDEXT:
						labels = [parse_video_filename(v, regularOrderDict) for v in [video1, video2]]
						if labels[0][0] == labels[1][0] and \
							labels[0][2] == labels[1][2] and \
							labels[0][3] == labels[1][3] and \
							labels[0][4] == labels[1][4]:

							print '%s %s %s %s: %s and %s' % (labels[0][0], labels[0][2], labels[0][3], labels[0][4], \
								labels[0][1], labels[1][1])

							outfilenameBase = 'sbs_' + labels[0][0] + '_' + labels[0][1] + '_' + labels[1][1] + '_'  + \
								labels[0][2] + '_' + labels[0][3] + '_' + labels[0][4] + '_'

							for iVid in range(len(commands)):
								if suffixes[iVid] in whichVersions:
									print suffixes[iVid]
									sp.call(["ffmpeg", "-i", os.path.join(croppedVideoDir, video1), \
												   "-i", os.path.join(croppedVideoDir, video2), \
												   "-filter_complex", \
												   commands[iVid], \
												"-map", """[out]""", "-loglevel", "error", \
												os.path.join(sidebysideDir, outfilenameBase + suffixes[iVid] + '.mp4')])

def reverse(sidebysideDir, reversedDir, regularOrderDict):
	print "Reversing/concating:"
	make_sure_path_exists(sidebysideDir)
	make_sure_path_exists(reversedDir)
	command = """[1:v]reverse[secondhalf];[0:v][secondhalf]concat[out]"""

	allfiles = os.listdir(sidebysideDir)

	for iVid1, video1 in enumerate(allfiles):
		(shortname1, ext1) = os.path.splitext(video1)
		if not(os.path.isdir(os.path.join(sidebysideDir, video1))) and ext1 == VIDEXT:

			labels = parse_video_filename(video1, regularOrderDict)

			print '%s %s %s %s' % (labels[0], labels[2], labels[3], labels[4])

			outfilenameBase = video1 + '_reversed'


			sp.call(["ffmpeg", "-i", os.path.join(sidebysideDir, video1), \
						   "-i", os.path.join(sidebysideDir, video1), \
						   "-filter_complex", \
						   command,
						"-map", """[out]""", "-loglevel", "error", \
						os.path.join(reversedDir, outfilenameBase + '.mp4')])

def concat_mp4s(concatPath, vidPaths):
	'''Concatenate a list of mp4s into a single new mp4, video only.

	concatPath: full path to the desired new mp4 file, including
		extension
	vidPaths: full paths to the videos to concatenate.

	Videos will be concatenated in the order they appear in this list.'''

	concat = ["ffmpeg"]
	inputList = ''

	# If there are no files to concat, immediately return 0.
	if not len(vidPaths):
		return 0

	# Build the concatenate command
	for (iVid, vid) in enumerate(vidPaths):
		concat = concat + ['-i', vid]
		inputList = inputList + '[{}:0]'.format(iVid)

	# Concatenate the videos
	concat = concat + ['-filter_complex', inputList + 'concat=n={}:v=1:a=0'.format(len(vidPaths)) + '[out]',
		'-map', '[out]', concatPath, '-loglevel', 'error', "-c:v", "libx264", "-preset", "slow",
		"-b:v", "1000k", "-maxrate", "1000k", "-bufsize", "2000k"]

	sp.call(concat)
