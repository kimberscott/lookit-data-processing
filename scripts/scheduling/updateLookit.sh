source venv/bin/activate
say "Updating Lookit version 2 studies and sending reminder emails"

now=$(date +"%m_%d_%Y")
timestamp=$(date +"%Y_%m_%d_%H_%M_%S")
mv /Users/kms/lookit-v2/scripts/logs/autoSync.out /Users/kms/lookit-v2/scripts/logs/autoSync_$timestamp.out
mv /Users/kms/lookit-v2/scripts/logs/autoSync.err /Users/kms/lookit-v2/scripts/logs/autoSync_$timestamp.err

python coding.py updateaccounts

python coding.py update --study physics
python reminder_emails.py --study physics --emails all --feedback
python coding.py fetchconsentsheet --coder Kim --study physics
python coding.py exportaccounts --study physics

python coding.py update --study flurps
python coding.py exportaccounts --study flurps

python send_current_announcements.py

aws s3 cp /Users/kms/lookitcodingv2/coding/accountsprod_1e9157cd-b898-4098-9429-a599720d0c0a.csv s3://lookit-data/ --grants read=emailaddress=lisa.chalik@gmail.com full=emailaddress=lookit@mit.edu
