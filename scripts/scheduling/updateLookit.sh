source venv/bin/activate
say "Updating Lookit version 2 studies"

now=$(date +"%m_%d_%Y")
timestamp=$(date +"%Y_%m_%d_%H_%M_%S")
mv /Users/kms/lookit-v2/scripts/logs/autoSync.out /Users/kms/lookit-v2/scripts/logs/autoSync_$timestamp.out
mv /Users/kms/lookit-v2/scripts/logs/autoSync.err /Users/kms/lookit-v2/scripts/logs/autoSync_$timestamp.err

python coding.py updateaccounts

say "Updated accounts."

python coding.py update --study physics
python coding.py fetchconsentsheet --coder Kim --study physics
python coding.py exportaccounts --study physics

say "Updated physics."

# python send_current_announcements.py

# say "Sent announcements"
