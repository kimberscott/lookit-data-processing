from announcements import send_announcement_emails

# WORDS AND OBJECTS
ageRangeDays = (9 * 30, 365 + 7 * 30 + 6)
logfilename = '/Users/kms/lookit-v2/scripts/logs/sentwordsobjectsannouncement.txt'
expId = '0574c4e1-2d0a-444d-9225-082d58d7ad7e'
studyName = 'Words and Objects'
studyMessage = "This study from the Stanford Language and Cognition Lab is about how babies form categories of objects. We're interested whether hearing verbal labels ('look, a doggie!') influences this learning process. your baby will see eight objects along with either beeps or words. Then, we will measure his or her looking time to objects from that new category vs. familiar objects. By examining which objects babies choose to look at during this study, we can start to uncover how babies find structure in the world around them - and how what you say to them helps! You will receive a $5 Amazon gift card to thank you for your participation.<br><br>To learn more or get started, visit <a href='https://lookit.mit.edu/studies/0574c4e1-2d0a-444d-9225-082d58d7ad7e/' target=_blank>the study</a> on Lookit!<br><br>Happy experimenting! <br><br>The Lookit team<br><br> P.S. Do you have any friends with kids who are also 9 - 18 months old? We'd be grateful for any help spreading the word about this study!<br><br><hr>"
maxToSend = 200
emails = 'all' # 'all'/list of emails

send_announcement_emails(emails, ageRangeDays, logfilename, expId, studyName, studyMessage, maxToSend)

# GEOMETRY
# ageRangeDays = (198, 229)
# logfilename = '/Users/kms/lookit-v2/scripts/logs/sentgeometryannouncement.txt'
# expId = 'c7001e3a-cfc5-4054-a8e0-0f5e520950ab'
# studyName = 'Baby Euclid'
# studyMessage = "This study for 7-month-olds (6 1/2 to 7 1/2 months) looks at babies' perception of shapes: we're interested in whether infants pick up on features essential to Euclidean geometry, like relative lengths and angles, even across changes in a shape's size and orientation. <br><br> In this 10-minute study, your baby watches short videos of two changing streams of triangles, one on each side of the screen. On one side, the triangles will be changing in shape and size, and on the other side, they will be changing in size alone. We measure how long your baby looks at each of the two streams of triangles to see which changes he or she finds more noticeable and interesting.            <br><br> To learn more or get started, visit <a href='https://lookit.mit.edu/studies/c7001e3a-cfc5-4054-a8e0-0f5e520950ab/' target=_blank>the study</a> on Lookit!<br><br>Happy experimenting! <br><br>The Lookit team<br><br><hr>"
# maxToSend = 200
# emails = 'all' # 'all'/list of emails
#
# send_announcement_emails(emails, ageRangeDays, logfilename, expId, studyName, studyMessage, maxToSend)

# BABY LAUGHTER
ageRangeDays = (88, 915)
logfilename = '/Users/kms/lookit-v2/scripts/logs/sentlaughterannouncement.txt'
expId = 'd4cbfabc-ea53-4877-bc55-c701426fd13b'
studyName = 'Baby Laughter Games'
studyMessage = "In this study from Caspar Addyman's group at Goldsmiths, University of London, you and your baby will perform a series of short games, including \"Peekaboo.\" We are interested in the different kinds of things that make babies laugh at different ages. Smiles and laughter transcend barriers of age, language and culture. Babies know this better than anyone -- they even began smiling in the womb!<br><br>To learn more or get started, visit <a href='https://lookit.mit.edu/studies/d4cbfabc-ea53-4877-bc55-c701426fd13b/' target=_blank>the study</a> on Lookit!<br><br>Happy experimenting! <br><br>The Lookit team<br><br> P.S. Do you have any friends with kids around the same age? We'd be grateful for any help spreading the word about this study!<br><br><hr>"
maxToSend = 200
emails = 'all' # 'all'/list of emails

send_announcement_emails(emails, ageRangeDays, logfilename, expId, studyName, studyMessage, maxToSend)

# FLURPS AND ZAZZES
ageRangeDays = (2192, 2916)
logfilename = '/Users/kms/lookit-v2/scripts/logs/sentflurpsannouncement.txt'
expId = '13fb90d9-af38-43d1-999b-7e079019b75a'
studyName = 'Flurps and Zazzes'
studyMessage = "This study for 3- through 7-year-olds looks at how young children expect social groups to affect people's behavior. In this 15-minute study, your child will see and hear a story about two groups of kids building towers. Then we'll ask him or her to guess how the kids will behave towards others in their own group and the opposite group, and how much the kids will have in common with their group members. Your child's responses can help teach scientists about how moral and social reasoning develop. <br><br> You'll earn a $5 Amazon gift card for participating (one gift card per child)! <br><br>To learn more or get started, visit <a href='https://lookit.mit.edu/studies/13fb90d9-af38-43d1-999b-7e079019b75a/' target=_blank>the study</a> on Lookit!<br><br>Happy experimenting! <br><br>The Lookit team<br><br> P.S. Do you have any friends with kids around the same age? We'd be grateful for any help spreading the word about this study!<br><br><hr>"
maxToSend = 200
emails = 'all' # 'all'/list of emails

send_announcement_emails(emails, ageRangeDays, logfilename, expId, studyName, studyMessage, maxToSend)

# POLITENESS
# ageRangeDays = (730, 1461)
# logfilename = '/Users/kms/lookit-v2/scripts/logs/sentpolitenessannouncement.txt'
# expId = 'b40b6731-2fec-4df4-a12f-d38c7be3015e'
# studyName = 'Mind and Manners'
# studyMessage = "This study for 2- through 4-year-olds looks at how kids learn what it means to be polite. <br><br> In this 15-minute study, your child will listen to short stories where people make requests, and answer questions about the characters by pointing. <br><br> To learn more or get started, visit <a href='https://lookit.mit.edu/studies/b40b6731-2fec-4df4-a12f-d38c7be3015e/' target=_blank>the study</a> on Lookit!<br><br> You'll earn a $4 Amazon gift card for participating (one gift card per child)! <br><br>Happy experimenting! <br><br>The Lookit team<br><br> P.S. Do you have any friends with kids around the same age? We'd be grateful for any help spreading the word about this study!<br><br><hr>"
# maxToSend = 200
# emails = 'all' # 'all'/list of emails
#
# send_announcement_emails(emails, ageRangeDays, logfilename, expId, studyName, studyMessage, maxToSend)

# PHYSICS
# ageRangeDays = (6*30, 11*30) # advertise in slightly narrower age range than need, so we don't prompt everyone to start at 4mo
# logfilename = '/Users/kms/lookit-v2/scripts/logs/sentphysicsannouncement.txt'
# expId = 'cfddb63f-12e9-4e62-abd1-47534d6c4dd2'
# studyName = 'Your baby, the physicist'
# studyMessage = "This study for 4- to 12-month-olds looks at how babies intuitively expect physical forces to work. During each study session, your baby watches pairs of short videos of physical events. On one side, something pretty normal happens: e.g., a ball rolls off a table and falls to the ground. On the other side, something surprising happens: e.g., the ball rolls off a table and falls UP! <br><br>This study will be one of the first to look in detail not just at infants' abilities collectively, but at individual differences in their expectations and styles of responding.<br><br>To better understand individual children's responses, we especially need dedicated families to complete multiple experiment sessions (up to 12). After each session, we'll email you a $5 Amazon gift card as a thank-you! (One gift card per child per session, up to 12 sessions; $5 bonus for 12th session. Child must be in the age range for the study and be visible in the consent video, so that we don't go broke paying random adults on the internet.) <br><br> Although every session helps, if you complete at least 12 sessions over the course of 2 months, we'll also be able to send you a personalized report about your child's looking patterns once video coding for the study is complete. (Sad note about how long careful science takes: this is likely to be in a few years.)<br><br>To learn more or get started, visit <a href='https://lookit.mit.edu/studies/13fb90d9-af38-43d1-999b-7e079019b75a/' target=_blank>the study</a> on Lookit!<br><br>Happy experimenting! <br><br>The Lookit team<br><br> P.S. Do you have any friends with babies around the same age? We'd be grateful for any help spreading the word about this study!<br><br><hr>"
# maxToSend = 200
# emails = 'all' # 'all'/list of emails
#
# send_announcement_emails(emails, ageRangeDays, logfilename, expId, studyName, studyMessage, maxToSend)
