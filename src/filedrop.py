# init howto
# https://www.digitalocean.com/community/tutorials/how-to-set-up-uwsgi-and-nginx-to-serve-python-apps-on-ubuntu-14-04
# ststemd howto:
# https://www.digitalocean.com/community/tutorials/how-to-set-up-uwsgi-and-nginx-to-serve-python-apps-on-centos-7
# S3 upload howto
# https://devcenter.heroku.com/articles/s3-upload-python
from flask import Flask, render_template, request, redirect, Response, url_for, session, abort
import time, os, json, base64, hmac, urllib
from hashlib import sha1
from ConfigParser import SafeConfigParser
from logging import Formatter
import requests


application = Flask(__name__)

##
## Set debugging and logging
# application.debug = True
application.debug = False

if application.debug is not True:   
	import logging
	from logging.handlers import RotatingFileHandler
	loglevel = logging.ERROR
#	loglevel = logging.DEBUG
	logFormatStr = '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
	logFilename = 'filedrop.log'
	logging.basicConfig(format = logFormatStr, filename = logFilename, level=loglevel)
	application.logger.info("Logging started.")

##
## Read configuration
config = SafeConfigParser()
config.read ('filedrop-config.ini')
application.secret_key = config.get('flask','secret_key')

##
## Process Flask routes

@application.route("/reCAPTCHA", methods=['GET', 'POST'])
def reCAPTCHA():
	application.logger.info("in reCAPTCHA")
	if request.method == 'POST':
		application.logger.info("checking capcha.")
		r = requests.post("https://www.google.com/recaptcha/api/siteverify",
			data = {"secret":config.get('reCAPTCHA','secret_key'), "response":request.form['g-recaptcha-response']})
		if 'success' in r.json() and r.json()['success']:
			session['reCAPTCHA'] = True
			session['s3_numsigs'] = 0
			application.logger.info("capcha successful.")
			return redirect(url_for('index'))

	if 'reCAPTCHA' not in session or not session['reCAPTCHA']:
		application.logger.info("reCAPTCHA: 'reCAPTCHA' not in session.")
		return (render_template('reCAPTCHA.html', reCAPTCHA_site_key = config.get('reCAPTCHA','site_key')))

	application.logger.info("reCAPTCHA: 'reCAPTCHA' IS in session.")
	return (redirect(url_for('index')))


@application.route("/", methods=['GET'])
def index():
	application.logger.info("in index")

#	resp = []
#	resp.append("<pre>")
#	for key in os.environ.keys():
#		resp.append ("%30s %s \n" % (key, os.environ[key]))
#	resp.append("</pre>")
	if 'reCAPTCHA' not in session or not session['reCAPTCHA']:
		application.logger.info("index: 'reCAPTCHA' not in session.")
		return (redirect(url_for('reCAPTCHA')))

	application.logger.info("index: not a robot")
	return (render_template('index.html'))


# Listen for GET requests to yourdomain.com/sign_s3/
@application.route('/sign_s3/', methods=['GET', 'POST'])
def sign_s3():
	application.logger.info("in sign_s3")

	if 'reCAPTCHA' not in session or not session['reCAPTCHA']:
		application.logger.info("sign_s3: 'reCAPTCHA' not in session.")
		abort (401)

	if session['s3_numsigs'] > int(config.get('flask','max_session_sigs')):
		application.logger.info("sign_s3: max_session_sigs exceeded")
		session.pop('reCAPTCHA', None)
		session.pop('s3_numsigs', None)
		abort (401)
	

	application.logger.info("sign_s3: not a robot: {}/{} sigs in this session".format (session['s3_numsigs'],config.get('flask','max_session_sigs')))

	# Load necessary information into the application:
	aws_access_key = config.get('S3', 'aws_access_key')
	aws_secret_access_key = config.get('S3', 'aws_secret_access_key')
	s3_bucket = config.get('S3', 'bucket')
	
	# Collect information on the file from the GET parameters of the request:
	object_name = urllib.quote_plus(request.args.get('file_name'))
	mime_type = request.args.get('file_type')

	application.logger.info("signing request to put {} in {}.".format (request.args.get('file_name'),s3_bucket))


	# Set the expiry time of the signature (in seconds) and declare the permissions of the file to be uploaded
	expires = int(time.time()+60*60*24)
	# amz_headers = "x-amz-acl:public-read"
	amz_headers = "x-amz-acl:private"
 
	# Generate the StringToSign:
	string_to_sign = "PUT\n\n%s\n%d\n%s\n/%s/%s" % (mime_type, expires, amz_headers, s3_bucket, object_name)

	# Generate the signature with which the StringToSign can be signed:
	signature = base64.encodestring(hmac.new(aws_secret_access_key, string_to_sign.encode('utf8'), sha1).digest())
	# Remove surrounding whitespace and quote special characters:
	signature = urllib.quote_plus(signature.strip())

	# Build the URL of the file in anticipation of its imminent upload:
	url = 'https://%s.s3.amazonaws.com/%s' % (s3_bucket, object_name)

	
	content = json.dumps({
		'signed_request': '%s?AWSAccessKeyId=%s&Expires=%s&Signature=%s' % (url, aws_access_key, expires, signature),
		'url': url,
	})

	if 's3_numsigs' in session:
		session['s3_numsigs'] += 1
	else:
		session['s3_numsigs'] = 1

	return content



@application.errorhandler(Exception)
def internal_error(error):
	application.logger.error(error)
	return (repr(error))
#	return render_template('500.html', error)


if __name__ == "__main__":
	application.run(host='0.0.0.0')
