import os
from videotools import *
import sys

# Bare-bones script to create cute grids of participant videos.
# If using for physics study : First run coding.py --export physics
# and in addition to exporting the concatenated videos to the physics export directory,
# it'll make directories for each participant with just calibration videos (looking
# L-R-L-R or reverse). Choose the directories you want to make grids for and put them
# in the baseDir below. Or just set the baseDir to the whole export directory.

if __name__ == "__main__":

	# --------------- REPLACE THESE ------------------------------------------------------

	usePublicOnly = False # True to select only the 'Public' privacy level clips to
	# include in grids. So if a participant has some private, some scientific, some public
	# clips, you can get a grid that you can share for publicity. If you choose false,
	# all clips will be included, and the resulting grid will have in its filename
	# a privacy level at the end of its filename a privacy level which corresponds to the
	# MOST RESTRICTIVE privacy level. I.e., if you see 'scientific' in the grid filename,
	# it's okay to use for scientific purposes.

	# Directory that contains collections of participant videos to make grids of. Each
	# subdirectory is for one participant.
	baseDir = '/Users/kms/Dropbox (MIT)/Examples, free/Consent collage/'
	# Where to put the grids that are created
	collageDir = '/Users/kms/Dropbox (MIT)/Examples, free/Consent collage/'
	# Where to
	exportDir = '/Users/kms/Dropbox (MIT)/Examples, free/Consent collage export/'

	# ------------------------------------------------------------------------------------

	participantDirs = [os.path.join(baseDir, d) for d in os.listdir(baseDir) if os.path.isdir(os.path.join(baseDir, d))]

	make_sure_path_exists(collageDir)
	make_sure_path_exists(exportDir)

	for partDir in participantDirs:

		vids = [f for f in os.listdir(partDir) if (not(os.path.isdir(os.path.join(partDir, f))) and f[-4:]=='.mp4')]
		if usePublicOnly:
			vids = [f for f in vids if 'public' in f]

		privacy = 'public' if all(['public' in f for f in vids]) else ('scientific' if all([('public' in f) or ('scientific' in f) for f in vids]) else 'private')

		collageName = os.path.split(partDir)[1] + '_' + privacy

		if len(vids):

			print('Making ' + collageName)
			print(vids)

			doSound = True
			make_collage(partDir, vids, min(3, len(vids)), os.path.join(collageDir, collageName), doSound, 0)

			print('Exporting compressed')
			make_mp4(os.path.join(collageDir, collageName + '.mp4'), exportDir, width=min(1920, 480*len(vids)))
