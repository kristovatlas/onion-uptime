'''
Description: Checks the status of a .onion site. Sends notification email if site is down. Logs status over time and collects uptime stats.
Author: kristovatlas [at-symbol] gmail [period] com
'''

#url fetching through Tor SOCKS proxy
import socks #pip install SocksiPy-branch
import socket
import urllib2

#timestamp
import time
import datetime

#generating email alerts
import smtplib
from email.mime.text import MIMEText

#logging
import os.path

#configuration
import ConfigParser

#set the current working directory to the location of the script
os.chdir(os.path.dirname(os.path.realpath(__file__)))

#################
# CONFIGURATION #
#################

#modify the contents of this configuration file in order to configure the script's behavior
config_filename = 'check-onion-status.cfg'

config = ConfigParser.RawConfigParser()

try:
	config.readfp(open(config_filename))
except ConfigParser.Error:
	sys.exit("Could not read or parse '%s'" % config_filename)

config.read(config_filename)

####################
# GENERAL SETTINGS #
####################

target_url = config.get('Settings','target_url')
site_descriptor = config.get('Settings','site_descriptor')
site_down_substring = config.get('Settings','site_down_substring')
log_filename = config.get('Settings','log_filename')
timestamp_format = config.get('Settings','timestamp_format')
tor_proxy_ip_address = config.get('Settings','tor_proxy_ip_address')
tor_proxy_port = int(config.get('Settings','tor_proxy_port'))

###########
# OPTIONS #
###########

LOGGING_ON  = config.get('Options','LOGGING_ON')	#Log all status to file
EMAILING_ON = config.get('Options','EMAILING_ON')	#Send email when down

##################
# EMAIL SETTINGS #
##################

email_address_from = config.get('Email','email_address_from')
email_address_to = config.get('Email','email_address_to')
email_server = config.get('Email','email_server')
email_username = config.get('Email','email_username')
email_password = config.get('Email','email_password')
send_email_not_more_than_n_seconds = int(config.get('Email','send_email_not_more_than_n_seconds'))

####################
# GLOBAL VARIABLES #
####################

uptime_stats_str = ''
is_time_to_send_email = True

#############
# FUNCTIONS #
#############

def print_results(is_quota_exceeded, is_exception, exception, timestamp):
	global uptime_stats_str
	if (is_quota_exceeded):
		print("[%s] Quota exceeded" % timestamp)
	elif (is_exception):
		print("[%s] Unable to reach site: %s" % (timestamp, exception))
	else:
		print("[%s] Page is up" % timestamp)
	print(uptime_stats_str)

#appends a newline at the end when writing to log
def write_to_log(message):
	with open(log_filename, "a") as logfile:
		logfile.write("%s\n" % message)

def write_to_log_with_timestamp(message):
	timestamp = datetime.datetime.fromtimestamp(time.time()).strftime(timestamp_format)
	write_to_log("[%s] %s" % (timestamp, message))

def log_results(is_quota_exceeded, is_exception, exception, timestamp):
	if (LOGGING_ON):
		with open(log_filename, "a") as logfile:
			if (is_quota_exceeded): 	   
				write_to_log_with_timestamp("Quota exceeded")
			elif (is_exception):
				write_to_log_with_timestamp("Unable to reach site: %s" % exception)
			else:
				write_to_log_with_timestamp("Page is up")

#TODO: refactor this ugly function
def uptime_stats():
	global is_time_to_send_email
	current_epoch = time.time()

	total_num_times_up = 0
	total_num_times_exceeded = 0
	total_num_times_unreachable = 0

	last_hour_times_up = 0
	last_hour_times_exceeded = 0
	last_hour_times_unreachable = 0

	last_day_times_up = 0
	last_day_times_exceeded = 0
	last_day_times_unreachable = 0

	last_week_times_up = 0
	last_week_times_exceeded = 0
	last_week_times_unreachable = 0

	time_last_email_sent = 0

	if (os.path.isfile(log_filename)):
		with open(log_filename, "r") as logfile:
			for line in logfile:
				line_timestamp = line[1:20]
				line_epoch = int(time.mktime(time.strptime(line_timestamp, timestamp_format)))

				if ('Quota exceeded' in line):
					total_num_times_exceeded += 1
				elif ('Page is up' in line):			
					total_num_times_up += 1
				elif ('Unable to reach site' in line):			
					total_num_times_unreachable += 1
				elif ('Alert email has been sent' in line):
					time_last_email_sent = line_epoch

				if (line_epoch >= current_epoch - (60 * 60)):
					#this entry happened in the last hour

					if ('Page is up' in line):
						last_hour_times_up += 1
					elif ('Quota exceeded' in line):
						last_hour_times_exceeded += 1
					elif ('Unable to reach site' in line):
						last_hour_times_unreachable += 1

				if (line_epoch >= current_epoch - (60 * 60 * 24)):
					#this entry happened in the last 24 hours

					if ('Page is up' in line):
						last_day_times_up += 1
					elif ('Quota exceeded' in line):
						last_day_times_exceeded += 1
					elif ('Unable to reach site' in line):
						last_day_times_unreachable += 1

				if (line_epoch >= current_epoch - (60 * 60 * 24 * 7)):
					#this entry happened in the last week

					if ('Page is up' in line):
						last_week_times_up += 1
					elif ('Quota exceeded' in line):
						last_week_times_exceeded += 1
					elif ('Unable to reach site' in line):
						last_week_times_unreachable += 1
	#end 'with' statement	
	else:
		print("Warning: Log file doesn't appear to exist yet?")
		return ""	
	total_uptime = 0
	week_uptime = 0
	day_uptime = 0
	hour_uptime = 0
	
	if (total_num_times_up + total_num_times_exceeded + total_num_times_unreachable > 0):
		total_uptime = int(round(total_num_times_up * 100.0 / (total_num_times_up + total_num_times_exceeded + total_num_times_unreachable), 0))
	if (last_week_times_up + last_week_times_exceeded + last_week_times_unreachable > 0):
		week_uptime = int(round(last_week_times_up * 100.0 / (last_week_times_up + last_week_times_exceeded + last_week_times_unreachable), 0))
	if (last_day_times_up + last_day_times_exceeded + last_day_times_unreachable > 0):
		day_uptime = int(round(last_day_times_up * 100.0 / (last_day_times_up + last_day_times_exceeded + last_day_times_unreachable), 0))
	if (last_hour_times_up + last_hour_times_exceeded + last_hour_times_unreachable > 0):
		hour_uptime = int(round(last_hour_times_up * 100.0 / (last_hour_times_up + last_hour_times_exceeded + last_hour_times_unreachable), 0))

	#evaluate whether it's too soon to send another alert email based on the threshold set by 'send_email_not_more_than_n_seconds'
	#print("DEBUG: current_epoch = %i time_last_email_sent = %i send_email_not_more_than_n_seconds = %i" % (current_epoch, time_last_email_sent, send_email_not_more_than_n_seconds))
	if (current_epoch - time_last_email_sent < send_email_not_more_than_n_seconds):		
		is_time_to_send_email = False

	return "Uptime Stats: All-Time (" + str(total_uptime) + "%) Week (" + str(week_uptime) + "%) Day (" + str(day_uptime) + "%) Hour (" + str(hour_uptime) + "%)"

#based on: https://docs.python.org/2/library/email-examples.html
def send_email(message):
	msg = MIMEText(message)
	msg['Subject'] = 'WARNING: ' + site_descriptor + ' is down'
	msg['From'] = email_address_from
	msg['To'] = email_address_to

	s = smtplib.SMTP(email_server)
	try:
		s.login(email_username, email_password)
	except:
		print("Error: Trouble logging in... check your mail server, username, and password?")
	s.sendmail(msg['From'], msg['To'], msg.as_string())
	s.quit()

def email_results(is_quota_exceeded, is_exception, exception, timestamp):
	global is_time_to_send_email
	global uptime_stats_str
	if (EMAILING_ON):
		'''if (is_time_to_send_email):
			print "DEBUG: True"
		else:
			print "DEBUG: False"'''
		if (is_time_to_send_email and (is_quota_exceeded or is_exception)):
			print("Sending alert email to %s..." % email_address_to)
			timestamp = datetime.datetime.fromtimestamp(time.time()).strftime(timestamp_format)
			send_email("The .onion site '%s' is currently down as of %s with exception '%s'. %s" % (target_url, timestamp, exception, uptime_stats_str))
			write_to_log_with_timestamp("Alert email has been sent.")
		else:
			print("Email sent too recently for threshold, will not send now.")

def process_results(is_quota_exceeded, is_exception, exception):
	global uptime_stats_str
	#this function is called only after the current status of the website has been evaluated, and expressed through
	# the function params
	timestamp = datetime.datetime.fromtimestamp(time.time()).strftime(timestamp_format)

	#calculate uptime stats and determine whether the number of recently sent emails exceeds the threshold
	uptime_stats_str = uptime_stats()

	#present restults on stdout, logfile, and email where appropriate
	print_results(is_quota_exceeded, is_exception, exception, timestamp)
	log_results(is_quota_exceeded, is_exception, exception, timestamp)
	email_results(is_quota_exceeded, is_exception, exception, timestamp)

#From: https://stackoverflow.com/questions/5148589/python-urllib-over-tor

def create_connection(address, timeout=None, source_address=None):
    sock = socks.socksocket()
    sock.connect(address)
    return sock

###########################################
# Begin script to fetch status of website #
###########################################

socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, tor_proxy_ip_address, tor_proxy_port)

# patch the socket module
socket.socket = socks.socksocket
socket.create_connection = create_connection

# Now you can go ahead and scrape those shady darknet .onion sites
is_exception = False
is_quota_exceeded = False
exception = ''
page = ''

try:
	page = urllib2.urlopen(target_url).read()

except Exception as e:
	is_exception = True
	exception = str(e) #report the Exception as a string

#Determine whether quota has been exceeded due to DoS or high traffic volume
if (site_down_substring in page):
	is_quota_exceeded = True

#inform script user of the results of the query
process_results(is_quota_exceeded, is_exception, exception)

print("Done.")
