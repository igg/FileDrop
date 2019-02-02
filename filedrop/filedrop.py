from flask import Flask, render_template, request, redirect, Response, url_for, session, abort
import time, os, json, base64, hmac, urllib, random, string, datetime
from hashlib import sha1
from ConfigParser import SafeConfigParser
from logging import Formatter
import requests
import boto3

application = Flask(__name__)

##
## Set debugging and logging
# application.debug = True
application.debug = False

if application.debug is not True:
	import logging
	from logging.handlers import RotatingFileHandler
	loglevel = logging.INFO
#	loglevel = logging.DEBUG

	logFormatStr = '%(asctime)s %(levelname)s: %(message)s'
# 	if loglevel == logging.DEBUG:
# 		logFormatStr += ' [in %(pathname)s:%(lineno)d]'

	logFilename = 'filedrop.log'
	logging.basicConfig(format = logFormatStr, filename = logFilename, level=loglevel)
	application.logger.info("Logging started.")

##
## Read configuration
config = SafeConfigParser()
config_file_path = os.path.join (os.path.dirname(__file__),'filedrop-config.ini')
application.logger.info("Reading config from: {}".format(config_file_path))
config.read ( config_file_path )

application.secret_key = config.get('flask','secret_key')

##
## Process Flask routes

@application.route("/reCAPTCHA", methods=['GET', 'POST'])
def reCAPTCHA():
	application.logger.debug("in reCAPTCHA")
	if request.method == 'POST':
		application.logger.debug("checking capcha.")
		r = requests.post("https://www.google.com/recaptcha/api/siteverify",
			data = {"secret":config.get('reCAPTCHA','secret_key'), "response":request.form['g-recaptcha-response']})
		if 'success' in r.json() and r.json()['success']:
			session['reCAPTCHA'] = True
			session['s3_numsigs'] = 0
			application.logger.debug("capcha successful.")
			return redirect(url_for('index'))

	if 'reCAPTCHA' not in session or not session['reCAPTCHA']:
		application.logger.debug("reCAPTCHA: 'reCAPTCHA' not in session.")
		return (render_template('reCAPTCHA.html', reCAPTCHA_site_key = config.get('reCAPTCHA','site_key')))

	application.logger.debug("reCAPTCHA: 'reCAPTCHA' IS in session.")
	return (redirect(url_for('index')))


@application.route("/", methods=['GET'])
def index():
	application.logger.debug("in index")

#	resp = []
#	resp.append("<pre>")
#	for key in os.environ.keys():
#		resp.append ("%30s %s \n" % (key, os.environ[key]))
#	resp.append("</pre>")
	if 'reCAPTCHA' not in session or not session['reCAPTCHA']:
		application.logger.debug("index: 'reCAPTCHA' not in session.")
		return (redirect(url_for('reCAPTCHA')))

	application.logger.debug("index: not a robot")
	return (render_template('index.html'))


# Listen for GET requests to yourdomain.com/sign_s3/
@application.route('/sign_s3/', methods=['GET', 'POST'])
def sign_s3():
	application.logger.debug("in sign_s3")

	if 'reCAPTCHA' not in session or not session['reCAPTCHA']:
		application.logger.debug("sign_s3: 'reCAPTCHA' not in session.")
		abort (401)

	if session['s3_numsigs'] > int(config.get('flask','max_session_sigs')):
		application.logger.debug("sign_s3: max_session_sigs exceeded")
		session.pop('reCAPTCHA', None)
		session.pop('s3_numsigs', None)
		abort (401)

	application.logger.debug("sign_s3: not a robot: {}/{} sigs in this session".format (session['s3_numsigs'],config.get('flask','max_session_sigs')))
	application.logger.info("sign_s3: request remote addr: {}".format (request.remote_addr))

	folder = "{} {}".format (str(request.remote_addr), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

	# Get the application credentials and set a policy for the S3 bucket
	sts = boto3.client(
		'sts',
		aws_access_key_id=config.get('S3', 'aws_access_key'),
		aws_secret_access_key=config.get('S3', 'aws_secret_access_key'),
		region_name=config.get('S3', 'region')
	)
	policy = json.dumps({ "Version":"2012-10-17",
		"Statement"    : [{
			"Effect"   : "Allow",
			"Action"   : "s3:*",
			"Resource" : ["arn:aws:s3:::{}/{}/*".format(config.get('S3', 'bucket'), folder)]
		}]
	})

	# Get a federation token (temporary credentials based on application credentials + policy)
	credentials = sts.get_federation_token(
		Name='filedrop',
		Policy=policy,
		DurationSeconds= 60 * 60,
	)
	application.logger.debug("sign_s3: sts credentials")
	application.logger.debug("  AccessKeyId = {}".format (credentials['Credentials']['AccessKeyId']))
#	application.logger.debug("  SessionToken = {}".format (credentials['Credentials']['SessionToken']))
#	application.logger.debug("  SecretAccessKey = {}".format (credentials['Credentials']['SecretAccessKey']))
	application.logger.debug("Bucket = {}".format (config.get('S3', 'bucket')))
	application.logger.debug("Folder = {}".format (folder))

	# Send the federation token back to the caller:	
	content = json.dumps({
		'AccessKeyId': credentials['Credentials']['AccessKeyId'],
		'SessionToken': credentials['Credentials']['SessionToken'],
		'SecretAccessKey': credentials['Credentials']['SecretAccessKey'],
		'Region': config.get('S3', 'region'),
		'Bucket': config.get('S3', 'bucket'),
		'Folder': folder,
	})

	if 's3_numsigs' in session:
		session['s3_numsigs'] += 1
	else:
		session['s3_numsigs'] = 1

	return (content)


@application.errorhandler(Exception)
def internal_error(error):
	application.logger.error(error)
	return (repr(error))
#	return render_template('500.html', error)


if __name__ == "__main__":
	application.run(host='0.0.0.0')
