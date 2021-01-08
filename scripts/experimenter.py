"""
Functions to access/edit Lookit data via API.

Make sure to install requirements (`pip install requests`).
"""
from __future__ import print_function
from utils import printer, backup_and_save
import lookitpaths as paths

import argparse
import copy
import datetime
import json
import os
import pprint
import re
import sys
import random
import requests
import conf
import time


########
# Basic client logic
class ExperimenterClient(object):
	"""
	Base class for experimenter requests
	"""

	def __init__(self, jam_token=None, url=None, namespace=None):
		self.BASE_URL = conf.LOOKIT_HOST
		self.TOKEN = conf.LOOKIT_ACCESS_TOKEN
		self.session = requests.Session()
		self.session.headers.update({'Authorization': 'Token ' + self.TOKEN})

	def _url_for_collection(self, collection):
		return '{}/api/v1/{}/'.format(
			self.BASE_URL,
			collection
		)

	def fetch_single_record(self, url):
		res = self.session.get(url)
		if res.status_code == 404:
			print('No results found for specified collection!')
			return []
		res = res.json()
		data = res['data']
		return data

	def fetch_child(self, childId):
		childUrl = self._url_for_collection('children') + childId + '/'
		childData = self.fetch_single_record(childUrl)
		return childData

	def fetch_user(self, userId):
		userUrl = self._url_for_collection('users') + userId + '/'
		userData = self.fetch_single_record(userUrl)
		return userData

	def fetch_collection_records(self, collection):
		"""Fetch all records that are a member of the specified collection"""
		if collection.startswith('https://'):
			url = collection
		else:
			url = self._url_for_collection(collection)
		res = self.session.get(url)
		if res.status_code == 404:
			return []
		res = res.json()
		respLink = res['links']['next']
		hasMore = respLink is not None
		data = res['data']
		while hasMore:
			res = self.session.get(respLink).json()
			data = data + res['data']
			respLink = res['links']['next']
			hasMore = respLink is not None
		return data

	def add_response(self, study_id, child_id, data):
		'''data is e.g.
			"conditions": {
				"3-video-stim": {
					"conditionNum": 1,
					"parameterSet": {
						"RESTPIC": "http://d1xha8gpb1dx7d.cloudfront.net/img/rest.png",
						"REST-AUD": "http://d1xha8gpb1dx7d.cloudfront.net/mp3/rest-normalized-loop5.mp3",
						"STIM-AUD": "http://d1xha8gpb1dx7d.cloudfront.net/mp3/mo-normalized.mp3",
						"STIM-PIC": "http://d1xha8gpb1dx7d.cloudfront.net/img/go.png",
						"STIM-VID": "https://bayetlab-neonatal.s3.us-east-2.amazonaws.com/mp4/MouthOpening.mp4",
						"INSTRUCTION": "Open your mouth",
						"REST-AUD-OGG": "http://d1xha8gpb1dx7d.cloudfront.net/ogg/rest-normalized-loop5.ogg",
						"STIM-AUD-OGG": "http://d1xha8gpb1dx7d.cloudfront.net/ogg/mo-normalized.ogg",
						"STIM-AUD-REPEAT": "http://d1xha8gpb1dx7d.cloudfront.net/mp3/mo-normalized-loop5.mp3",
						"STIM-AUD-REPEAT-OGG": "http://d1xha8gpb1dx7d.cloudfront.net/ogg/mo-normalized-loop5.ogg"
					}
				}
			},
			"global_event_timings": [
				{
					"exit_type": "browserNavigationAttempt",
					"timestamp": "2017-09-05T14:33:41.322Z",
					"event_type": "exitEarly",
					"last_page_seen": 0
				}
			],
			"exp_data": {},
			"sequence": [
				"0-video-config",
				"1-consent-form",
				"2-video-quality",
				"3-video-stim",
				"4-video-stim",
				"5-video-stim",
				"6-video-stim",
				"7-video-stim",
				"8-video-stim",
				"9-video-stim",
				"10-video-stim",
				"11-video-stim",
				"12-video-stim",
				"13-video-stim",
				"14-video-stim",
				"15-are-mother-survey",
				"16-PSS-survey",
				"17-RLEQ-survey",
				"18-father-present-survey",
				"20-exit-survey"
			],
			"completed": true,
			"completed_consent_frame": true,
			"created_on": "2020-01-08T20:37:58.344491-05:00",
			"pk": 1036,
			"withdrawn": null
		'''
		url = self._url_for_collection('responses')
		post_data = {
			"data": {
				"attributes": data,
				"relationships": {
				  "child": {
					"data": {
					  "type": "children",
					  "id": child_id
					}
				  },
				  "study": {
					"data": {
					  "type": "studies",
					  "id": study_id
					}
				  }
				},
			"type": "responses"
			}
		}
		return self.session.post(
			url,
			headers = {'Content-type': "application/vnd.api+json"},
			json = post_data
		).json()

	def add_session_feedback(self, session, feedback):
		"""Add session feedback.
		session: dict, {'id': SESSIONID}
		feedback: string

		if successful, returns dict with structure:
		{
			'attributes': {'comment': feedback},
			'id': [feedback ID, new],
			'links': {'self': [feedback URL]},
			'relationships': {
				'researcher': { 'links': { 'related': [researcher URL]}},
				'response':	  { 'links': { 'related': [response URL]}},
			'type': 'feedback'
		}
		"""

		url = self._url_for_collection('feedback')

		feedbackdata = {
			"data": {
				"attributes": {
					 "comment": feedback
				},
			   "relationships": {
				 "response": {
				   "data": {
					 "type": "responses",
					 "id": session['id']
				   }
				 }
			   },
			   "type": "feedback"
			}
		}

		return self.session.post(
			url,
			headers = {'Content-type': "application/vnd.api+json"},
			json = feedbackdata
		).json()['data']

	def update_feedback(self, feedbackID, feedback):
		"""Update feedback.
		feedbackID: string (uuid)
		feedback: string

		if successful, returns dict with structure:
		{
			'attributes': {'comment': feedback},
			'id': [feedback ID, new],
			'links': {'self': [feedback URL]},
			'relationships': {
				'researcher': { 'links': { 'related': [researcher URL]}},
				'response':	  { 'links': { 'related': [response URL]}},
			'type': 'feedback'
		}
		"""

		url = self._url_for_collection('feedback') + feedbackID + '/'

		feedbackdata = {
			"data": {
				"attributes": {
					 "comment": feedback
				},
			   "type": "feedback",
			   "id": feedbackID
			}
		}

		return self.session.patch(
			url,
			headers = {'Content-type': "application/vnd.api+json"},
			json = feedbackdata
		).json()['data']



def get_all_feedback(): # TODO: DOC
	client = ExperimenterClient()
	feedback = client.fetch_collection_records('feedback')
	allFeedback = {paths.get_collection_from_url(fb['relationships']['response']['links']['related']) : {'id': fb['id'], 'comment': fb['attributes']['comment']} for fb in feedback}
	return allFeedback

def update_session_data(experimentId, display=False):
	'''Get session data from the server for this experiment ID and save'''
	client = ExperimenterClient()
	exp = client.fetch_collection_records(
		'studies/{}/responses'.format(experimentId)
	)
	backup_and_save(paths.session_filename(experimentId), exp)
	if display:
		printer.pprint(exp)
	print("Synced session data for experiment: {}".format(experimentId))

def update_child_data():
	client = ExperimenterClient()

	childData = client.fetch_collection_records('children')
	allChildren = {acc[u'id']: acc for acc in childData}

	print('Child data download complete. Found {} records'.format(len(childData)))
	backup_and_save(paths.CHILD_FILENAME, allChildren)

def update_account_data(): # TODO: doc
	client = ExperimenterClient()

	start = time.time()
	accountData = client.fetch_collection_records('users')
	end = time.time()
	print('Fetched account data; took {} seconds'.format(end - start))
	allAccounts = {acc[u'id']: acc for acc in accountData}

	for (id, acc) in allAccounts.iteritems():
		allAccounts[id] = expandAccount(acc)

	print('Account data download complete. Found {} records'.format(len(accountData)))
	backup_and_save(paths.ACCOUNT_FILENAME, allAccounts)

def fetch_single_account(userId): # TODO: doc
	'''Fetch single account data from server, don't update local storage'''
	client = ExperimenterClient()

	accountData = client.fetch_user(userId)

	return expandAccount(accountData)

def user_from_child(childId): # TODO: DOC
	client = ExperimenterClient()
	if childId.startswith('https://'):
		url = childId
	else:
		url = client._url_for_collection('children/' + childId)
	childRecord = client.fetch_single_record(url)
	user = paths.get_collection_from_url(childRecord['relationships']['user']['links']['related'])
	return user


def expandAccount(acc):
	'''Add to a user account dict information about children and demographics'''
	client = ExperimenterClient()
	children = client.fetch_collection_records(acc['relationships']['children']['links']['related'])
	childDict = {child['id']: child['attributes'] for child in children}

	demographics = client.fetch_collection_records(acc['relationships']['demographics']['links']['related'])
	demographics.sort(key=lambda d:d['attributes']['date_created'])

	acc['attributes']['demographics'] = demographics[-1]['attributes'] if demographics else {}
	acc['attributes']['children'] = childDict
	return acc

if __name__ == '__main__':
	print("testing")

