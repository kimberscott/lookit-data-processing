import os
import argparse
from dotenv import load_dotenv

parser = argparse.ArgumentParser()
parser.add_argument('-c', '--config', type=str)
args, _ = parser.parse_known_args()

default_env = '.env-prod'
dotenv_path = os.path.join(os.path.dirname(__file__), args.config or default_env)
load_dotenv(dotenv_path)

VERSION=(args.config or default_env).split('-')[-1]

SENDGRID_KEY = os.environ.get('SENDGRID_KEY')
LOOKIT_ACCESS_TOKEN = os.environ.get('LOOKIT_ACCESS_TOKEN')
LOOKIT_HOST = os.environ.get('LOOKIT_URL')
