import os
from utils import make_sure_path_exists, printer
import conf
import coding_settings

BASE_DIR=os.environ.get("BASE_DIR")
VIDEO_DIR = os.path.join(BASE_DIR, os.environ.get("VIDEO_DIR"))
DATA_DIR = os.path.join(BASE_DIR, os.environ.get("DATA_DIR"))
CODING_DIR = os.path.join(BASE_DIR, os.environ.get("CODING_DIR"))
SESSION_DIR = os.path.join(BASE_DIR, os.environ.get("SESSION_DIR"))
EXPORT_DIR = os.path.join(BASE_DIR, os.environ.get("EXPORT_DIR"))
FIG_DIR = os.path.join(CODING_DIR, 'figs')
FFMPEG = os.environ.get("FFMPEG_PATH")
FFPROBE = os.path.join(os.path.split(FFMPEG)[0], 'ffprobe')

make_sure_path_exists(VIDEO_DIR)
make_sure_path_exists(DATA_DIR)
make_sure_path_exists(CODING_DIR)
make_sure_path_exists(SESSION_DIR)
make_sure_path_exists(EXPORT_DIR)

VIDEO_FILENAME = os.path.join(DATA_DIR, 'video_data.bin')
ACCOUNT_FILENAME = os.path.join(DATA_DIR, 'accounts' + conf.VERSION + '.bin')
CHILD_FILENAME = os.path.join(DATA_DIR, 'children' + conf.VERSION + '.bin')

def session_filename(expId):
	'''Return full path to the session data filename for experiment expId'''
	return os.path.join(DATA_DIR, 'session_data_' + expId + '.bin')

def email_filename(expId):
	'''Return full path to the email data filename for experiment expId'''
	return os.path.join(DATA_DIR, 'email_data_' + expId + conf.VERSION + '.bin')

def coding_filename(expId):
	'''Return full path to the coding data filename for experiment expId'''
	return os.path.join(DATA_DIR, 'coding_data_' + expId + '.bin')

def vcode_filename(sessKey, coderName, short=False):
	'''Return full path to expected VCode file for a given study, session & coder. short=True to use just the session ID instead of exp + session.'''
	(expId, shortSess) = parse_session_key(sessKey)
	if short:
		return os.path.join(CODING_DIR, coderName, shortSess + '-evts.txt')
	else:
		return os.path.join(CODING_DIR, coderName, expId + '_' + shortSess + '-evts.txt')

def codesheet_filename(expId, coderName):
	'''Return full path to the .csv coding file for experiment expId & coderName'''
	return os.path.join(CODING_DIR, expId + '_' + coderName + '.csv')

def accountsheet_filename(expId='all'):
	'''Return full path to the .csv account file'''
	if expId=='all':
		return os.path.join(CODING_DIR, 'accounts' + conf.VERSION + '.csv')
	else:
		return os.path.join(CODING_DIR, 'accounts' + conf.VERSION + '_' + expId + '.csv')

def childsheet_filename():
	'''Return full path to the .csv children file'''
	return os.path.join(CODING_DIR, 'children' + conf.VERSION + '.csv')

def make_session_key(expId, sessId):
	#if conf.VERSION == 'prod':
	#	 return 'lookit.session' + expId + 's.' + sessId
	#else:
	#	 return 'experimenter.session' + expId + 's.' + sessId
	return sessId

def parse_session_key(sessKey):
	#if conf.VERSION == 'staging':
	#	 prefix = 'experimenter.session'
	#elif conf.VERSION == 'prod':
	#	 prefix = 'lookit.session'
	#assert sessKey[:len(prefix)] == prefix
	#sessKey = sessKey[len(prefix):]
	#(expId, sessId) = sessKey.split('.')
	#assert expId[-1] == 's'
	#expId = expId[:-1]
	#return (expId, sessId)
	return (None, sessKey)

def parse_expId(expId): # TODO
	'''parse an experiment id of the form *.ACTUALID'''
	pieces = expId.split('.')
	id = pieces[-1]
	# prefix = '.'.join(pieces[:-1])
	return id

def make_long_expId(expId): # TODO
	'''move from experiment ID to collection name'''
	return 'session' + expId + 's'

def parse_videoname(vidName):
	'''Extracts meaningful pieces of video name.

	videos are named
	videoStream_video-record-<experiment.id>-<frame.id>-
	   <session.id>_<timestamp>.EXT, e.g.
		  videoStream_video-consent-574db6fa3de08a005bb8f844-0-video-consent-574f62863de08a005bb8f8b8_1464820374637_240.flv
		  videoStream_57586a553de08a005bb8fb7f_1-video-consent_PREVIEW_DATA_DISREGARD_1465935820244_351.flv

	'''

	assert vidName[-4:] in ['.flv', '.mp4']
	fname = vidName[:-4]
	pieces = fname.split('_')

	assert len(pieces) >= 4

	expId = pieces[1]
	frameId = pieces[2]
	if vidName.find('PREVIEW_DATA_DISREGARD') > 0:
		sessId = 'PREVIEW_DATA_DISREGARD'
	else:
		sessId = pieces[3]
	timestamp = '_'.join(pieces[-2:])

	# shortname is what's recorded in the session data as the video expected.
	# It's missing the videoStream_ prefix and the timestamp_random.EXT.
	# ex:
	# video-record-57472c903de08a0054472a02-2-video-1-574f693f3de08a005bb8f8e2
	shortnamePieces = fname.split('_')
	assert len(shortnamePieces) > 2
	shortname = '_'.join(shortnamePieces[1:-2])

	return (expId, frameId, sessId, timestamp, shortname)

def get_videolist():
	'''Return the list of .flv/.mp4 files in the video directory'''
	return [f for f in os.listdir(VIDEO_DIR) if \
					not(os.path.isdir(os.path.join(VIDEO_DIR, f))) and \
					f[-4:] in ['.flv', '.mp4'] ]

def session_video_path(expId, child, sessId):
	'''Return relative path within SESSION_DIR for a given session for this experiment, childID, & session ID.'''
	return os.path.join(expId, child + '_' + sessId)

def get_collection_from_url(url): # TODO: DOC
	return url.strip('/').split('/')[-1]

def get_context_from_session(sessData): # TODO: DOC
	rels = sessData['relationships']
	child = get_collection_from_url(rels['child']['links']['related'])
	study = get_collection_from_url(rels['study']['links']['related'])
	return {'child': child, 'study': study}
