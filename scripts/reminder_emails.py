from sendgrid_client import EmailPreferences, SendGrid
from coding import *
from utils import printer
from experimenter import update_account_data, user_from_child, get_all_feedback
import datetime
import numpy as np
import lookitpaths as paths
import donotsend

'''Reminder emails for the Lookit physics study. Can also use as starting point to set up reminders for other studies.'''

def get_email(user):
	return exp.accounts[user]['attributes']['username']

def getFeedbackToSend(allFeedback, theseSessions, child):

	# Get list of feedback that's been given on any sessions
	theseFeedback = [ {
						'sessionId': sess['id'],
						'feedback': allFeedback[sess['id']]['comment'],
						'sessDate': datetime.datetime.strftime(datetime.datetime.strptime(sess['attributes']['created_on'], '%Y-%m-%dT%H:%M:%S.%fZ'), '%B %d'),
						'progress': len([segment for segment in sess['attributes']['exp_data'].keys() if 'pref-phys-videos' in segment])
					}
					for sess in theseSessions if sess['id'] in allFeedback.keys()]

	# But only send feedback that hasn't been sent in previous emails
	feedbackToSend = [f for f in theseFeedback if not any([f['sessionId'] in e['feedbackKeys'] for e in exp.email.get(child, [])])]

	return feedbackToSend

def generate_email(allFeedback, allSessions, child, message, nCompleted, justFeedback=False):
	feedbackToSend = getFeedbackToSend(allFeedback, allSessions, child)

	# Get username, email address, & names to use in email generation
	participant = user_from_child(child)
	acc =  exp.accounts[participant]
	name = acc['attributes']['nickname']
	childProfile = acc['attributes']['children'][child]
	childName = childProfile.get('given_name', 'your child')

	# Generate email text to send
	body = 'Hi ' + (name if name else participant) + ',<br><br>'
	if justFeedback:
		body += message + "<br> "
	else:
		body += message + "This study will be one of the first to look in detail not just at infants' abilities collectively, but at individual differences in their expectations and styles of responding. But to do that, we need families to keep coming back so we can gather enough data from each child.<br><br>Our goal--unprecedented in cognitive development research--is to observe as many participants as possible over at least " + str(idealSessions) + " sessions each. Will you and " + childName + " <a href='https://lookit.mit.edu' target=_blank>come back to Lookit</a> to help out? We're ready if you are, and you can participate any time that's convenient for you!<br><br> "


	if len(feedbackToSend):
		body += "Here's some new feedback from the research team on your recent sessions: <br><br>"
	for feedback in feedbackToSend:
		body += ' * ' + feedback['sessDate'] + ' ('
		if feedback['progress'] >= 24:
			body += 'complete): '
		else:
			body += str(feedback['progress']) + ' of 24 videos): '
		body += '"' + feedback['feedback'] + '"<br><br>'

    if nCompleted > 0:
        body += 'Our records indicate that you have already completed ' + str(nCompleted) + ' of the 12 sessions'
        if (idealSessions+1)/2 < nCompleted < (idealSessions - 4):
            body += ' (more than halfway done)!'
        elif (idealSessions - 4) <= nCompleted < idealSessions:
            body += ' (so close)!'
        elif nCompleted >= idealSessions:
            body += ' (all done)!'
        else:
            body += '!'

	if nCompleted >= idealSessions:
		body += ' Thank you so much for all the time you have put in. We will send a personalized report about ' + childName + "'s looking patterns once video coding is ready!<br><br>--The Lookit team<br><br><hr>"
	else:
		body += ' Thank you for all the time you have already put in. If you complete all ' + str(idealSessions) + ' sessions, we will be able to send a personalized report about ' + childName + "'s looking patterns once video coding is ready.<br><br>--The Lookit team<br><br><hr>"
	return (body, feedbackToSend)

# Email timing
emailsScheduled = {
	'started2': {
		'success': True,
		'days': 2,
		'subject': 'Ready for another "Your baby the physicist" session?',
		'message': "Thank you so much for participating in the study 'Your baby the physicist' on Lookit a few days ago with your child! "},
	'started4': {
		'success': True,
		'days': 4,
		'subject': "Ready for another 'Your baby the physicist' session?",
		'message': "Thank you so much for participating in the study 'Your baby the physicist' on Lookit this week with your child! "},
	'started7': {
		'success': True,
		'days': 7,
		'subject': "It's been a week since your last 'Your baby the physicist' session - ready to come back?",
		'message': "Thank you so much for participating in the study 'Your baby the physicist' on Lookit last week with your child! "},
	'started14': {
		'success': True,
		'days': 14,
		'subject': "It's been a few weeks since your last 'Your baby the physicist' session - ready to come back?",
		'message': "Thank you so much for participating in the study 'Your baby the physicist' on Lookit with your child! "}}

idealSessions = 12
maxDaysSinceLast = 60

if __name__ == '__main__':

	# Parse command-line arguments
	parser = argparse.ArgumentParser(description='Send reminder emails for a Lookit study')
	parser.add_argument('--study', help='Study ID')
	parser.add_argument('--feedback', action='store_true')
	parser.add_argument('--emails', help='Only send emails to these addresses (enter "all" to send to all eligible)',	 action='append', default=['kimber.m.scott@gmail.com'])

	args = parser.parse_args()
	study = coding_settings.studyNicknames.get(args.study, args.study)

	#update_account_data()
	exp = Experiment(study)
	exp.update_saved_sessions()
	accounts = Experiment.load_account_data()
	allFeedback = get_all_feedback()

	# Get list of all unique participants

	children = list(set([paths.get_context_from_session(sess)['child'] for sess in exp.sessions]))

	print("Sending reminder emails. All children participating in this study:")
	print(", ".join(children))

	print("Not sending emails to these users:")
	print(", ".join(donotsend.users))

	# Get SendGrid object & unsubscribe group for notifications
	sg = SendGrid()

	# Date/time to use for determining whether to send email yet
	td = datetime.datetime.today()

	for child in children:

		print "***********	" + child

		# Get list of all sessions completed by this child
		allSessions = [sess for sess in exp.sessions if paths.get_context_from_session(sess)['child'] == child]

		# Sort by time completed
		allSessions = sorted(allSessions, key=lambda sess:datetime.datetime.strptime(sess['attributes']['created_on'], '%Y-%m-%dT%H:%M:%S.%fZ'))

		# Figure out how many "real" sessions to count & when last was.

		# 1. Require at least one pref-phys-videos segment
		theseSessions = [sess for sess in allSessions if any(['pref-phys-videos' in segment for segment in sess['attributes']['exp_data'].keys()])]

		# 2. Don't include sessions within 6 hrs of a previous session
		anyTooClose = True
		while anyTooClose:
			sessDatetimes = [datetime.datetime.strptime(sess['attributes']['created_on'], '%Y-%m-%dT%H:%M:%S.%fZ') for sess in theseSessions]
			daysSinceSession = [ float((td - sd).total_seconds())/86400 for sd in sessDatetimes]

			dayDiffs = np.subtract(daysSinceSession[:-1], daysSinceSession[1:])
			tooClose = [i for i, diff in enumerate(dayDiffs) if diff < 1./4]
			anyTooClose = len(tooClose) > 0

			if anyTooClose:
				del theseSessions[tooClose[0] + 1]

		# A. Has only unsuccessfully tried to participate, FIRST trial was N days ago...
		anySuccess = len(theseSessions) > 0
		if not anySuccess:
			firstSessionDate = datetime.datetime.strptime(allSessions[0]['attributes']['created_on'], '%Y-%m-%dT%H:%M:%S.%fZ')
			sincePrev = float((td - firstSessionDate).total_seconds())/86400

		# B. Has successfully participated at least once; LAST successful trial was N days ago...
		else:
			sincePrev = daysSinceSession[-1]

		sessDatetimes = [datetime.datetime.strptime(sess['attributes']['created_on'], '%Y-%m-%dT%H:%M:%S.%fZ') for sess in theseSessions]
		lastSession = max(sessDatetimes) if sessDatetimes else 0

		# Has it been long enough to send each scheduled email?
		eligible = sorted([(emailName, emailDesc) for (emailName, emailDesc) in emailsScheduled.items() if sincePrev > emailDesc['days'] and anySuccess == emailDesc['success']], key=lambda e:e[1]['days'])
		# Make sure subject has participated and NOT completed the study! Also require time since last participation isn't already too long
		sendEmail = len(eligible) > 0 and len(theseSessions) < idealSessions and sincePrev < maxDaysSinceLast

		# Also send an email if we	have feedback to send, even if it hasn't been long enough to trigger a reminder
		feedbackToSend = getFeedbackToSend(allFeedback, allSessions, child)
		justFeedback = not sendEmail and len(feedbackToSend)
		if justFeedback and args.feedback:
			eligible = [('thanks', {
				'success': True,
				'days': 0,
				'subject': "Thanks for participating in the 'Your baby the physicist' study on Lookit!",
				'message': "Thank you so much for participating in the study 'Your baby the physicist' on Lookit with your child! "})]
			sendEmail = True

		# Go ahead and send the email!
		if sendEmail:
			(emailName, emailDesc) = eligible[-1] # send most-recently triggered
			message = emailDesc['message']

			# Have we already sent this reminder to this child? - *with no new session since then*?
			alreadySent = any([(emailName == e['emailName']) and e['dateSent'] > lastSession for e in exp.email.get(child, [])])


			user = user_from_child(child)
			recipient = get_email(user)
			acc = accounts[user]

			if user in donotsend.users:
			    print("Skipping email for user on donotsend list: {}".format(user))
			    continue

			if ((not alreadySent) or emailName == 'thanks') and user not in donotsend.users:

				(body, feedbackToSend) = generate_email(allFeedback, allSessions, child, message, len(theseSessions), justFeedback=justFeedback)

				if (recipient in args.emails or 'all' in args.emails) and acc['attributes']['email_next_session']:
					print "Actually sending email:"
					print (recipient, body)
					status = sg.send_email_to(
						recipient,
						emailDesc['subject'],
						body
					)
					if status == 200:
						# Record in list of emails sent to this child
						emailRecord = {'emailName': emailName,
									   'message': emailDesc['message'],
									   'dateSent': td,
									   'daysPastToSend': emailDesc['days'],
									   'actualDaysPast': sincePrev,
									   'success': emailDesc['success'],
									   'feedbackKeys': [f['sessionId'] for f in feedbackToSend]}
					if child in exp.email.keys():
						exp.email[child].append(emailRecord)
					else:
						exp.email[child] = [emailRecord]
					backup_and_save(paths.email_filename(study), exp.email)

			if not anySuccess:
				print "Has never successfully participated; first session was {} days ago.".format(sincePrev)
			else:
				print "Has successfully participated {} times; last session was {} days ago.".format(len(theseSessions), sincePrev)

			print 'Recipient is unsubscribed from this list: {}'.format(
				not acc['attributes']['email_next_session'])

			if sendEmail:
				print 'Time to send email ({})'.format(emailName)
				print "Already sent: {}".format(alreadySent)
			else:
				print 'No email to send at this time'
