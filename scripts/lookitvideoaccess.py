import os
from utils import indent, printer
import subprocess as sp
import lookitpaths as paths
from utils import backup_and_save
import conf
import experimenter
from coding_settings import whichStudiesVideo

def sync_S3():
	'''Download any new or modified video files from S3 for studies we can access.

	This only gets the video files; details are not stored in the video database.'''

    # Get a list of studies we have access to via Lookit API..
    # TODO: allow passing a study argument to fetch videos from just one study
	client = experimenter.ExperimenterClient()
	if whichStudiesVideo == 'all':
	    studies = client.fetch_collection_records('studies')
	    studyIds = [s['id'] for s in studies]
	    studyIds += ['b30602f0-89b7-4441-a644-a9f81ef34313'] # manually included from old system
	else:
	    studyIds = whichStudiesVideo
	# Create a list of include options to add to the aws sync call to
	# get only video from these studies
	includeStudiesCommand = sum([['--include', '*_' + ID + '_*'] for ID in studyIds], [])

	origVideos = paths.get_videolist()
	awsCommand = ['aws', 's3', 'sync', 's3://mitLookit', paths.VIDEO_DIR, '--only-show-errors', '--metadata-directive', 'COPY', '--exclude', '*'] + includeStudiesCommand
	sp.check_call(awsCommand)

	allVideos = paths.get_videolist()
	newVideos = list(set(allVideos)-set(origVideos))
	print "Downloaded {} videos:".format(len(newVideos))
	print(indent(printer.pformat(newVideos), 4))
	return newVideos

#def pull_from_wowza():
#	'''Sync wowza data with S3 so we get up-to-date data from S3'''
#	thisDir = os.path.dirname(os.path.realpath(__file__))
#	sp.call(['ssh', '-i', os.path.join(thisDir, 'lookit2016.pem'), 'ec2-user@lookit-streaming.mit.edu', 'aws', 's3', 'sync', '/home/ec2-user/content', 's3://mitLookit'])

