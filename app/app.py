#!/usr/bin/env python3

import paramiko
from flask import Flask, make_response, jsonify, request
import time
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone
from queue import Queue
import threading
import multiprocessing
import re
import json

app = Flask(__name__)
logs = {'reg':{}, 'unr':{}, 'par-reg':{}, 'rej':{}, 'exp-unr':{}}
suscriber = json.load(open('./data/suscriber.json',))

def logging(error):
	open('./data/log.txt', 'a').write(f"{datetime.now().strftime('%d/%m/%Y, %H:%M:%S')}-{error['t']}-{error['d']}\n")	
		
def HtmlParser():
	'''Email message constructor'''
	t = HtmlParser.__name__
	with open(os.getcwd() + '/template.html', 'r', encoding='utf-8') as f:
		html = f.read()
	for log in list(logs.keys())[1:]:
		index = html.find('<!--' + log + '-begin-->')
		html_content = ''
		for k, v in logs[log].items():
			seq = '<td>' + k + '</td>'
			for i in range(2):
				seq = seq + '<td>' + v[i] + '</td>'
			seq = seq + '<td>' + str(datetime.fromtimestamp(int(v[2]), timezone.utc).astimezone()) + '</td>'
			html_content = html_content + '<tr class="underlined-row">' + seq + '</tr>'
			seq = ''
		html = html[:index] + html_content + html[index:]
	return html


def EmailReport():
	'''Send email report to administrators'''
	t = EmailReport.__name__
	settings = json.load(open('./data/settings.json',))
	logging({'t': t, 'd': f'Init sending email'})
	from_addr = 'no-reply@fsw.edu'
	msg = MIMEMultipart('alternative')
	msg['Subject'] = 'CUCM Registration Phones Report'
	msg['From'] = from_addr
	msg.attach(MIMEText(HtmlParser(), 'html'))
	s = smtplib.SMTP(host = settings['smtp']['url'], port = settings['smtp']['port'])
	logging({'t': t, 'd': f'Connected to SMTP server'})
	for to_addr in settings['to_addrs']:
		msg['To'] = to_addr
		s.sendmail(from_addr, to_addr, msg.as_string())
	logging({'t': t, 'd': f'End sending email'})
	s.quit()

def Validator():
	'''Check every category againg the registered category finding duplicates'''
	t = Validator.__name__
	for logType in list(logs.keys())[1:]:
		macList = list(logs[logType].keys())
		if macList: 
			for mac in macList:
				if mac in logs['reg']:
					logs[logType].pop(mac)

def DeviceConnector(q):
	t = DeviceConnector.__name__
	while True:
		ip = q.get()
		greeting = ''
		output = ''
		timeout = 5
		ssh_client = paramiko.SSHClient()
		ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		ssh_client.connect(hostname = ip, username = os.environ.get('USERNAME'), password = os.environ.get('PASSWORD'))
		remote_connection = ssh_client.invoke_shell()
		while not('admin:' in greeting) and timeout != 0:
			time.sleep(1)
			timeout = timeout - 1
			greeting = remote_connection.recv(65535).decode('utf-8')
		if timeout != 0:
			timeout = 5
			logging({'t': t, 'd': f'Successful connection to host {ip}'})
			remote_connection.send('show risdb query phone\n')
			while not('admin:' in output) and timeout != 0:				
				time.sleep(1)
				output = output + remote_connection.recv(655350).decode('utf-8')
				timeout = timeout - 1						
			if timeout != 0:
				logging({'t': t, 'd': f'Processing host {ip} data'})
				items = re.findall(r'SEP([A-F0-9]{12}), (.+?(?=,)), (.+?(?=,)){5}, (.+?(?=,)), (.+?(?=,)){5}, (.+?(?=,)), (.+?(?=,)){1}, (\d*).+', output)
				for i in items:
					if i[3] in list(logs.keys()):
						logs[i[3]][i[0]] = [i[1], i[5], i[7]]
					else:
						logging({'t': t, 'd': f'Problem processing data: {i}'})			
			else:
				logging({'t': t, 'd': f'Problem processing data host {ip} data'})
		else:
			logging({'t': t, 'd': f'Problem with the SSH connection to host {ip}'})
		ssh_client.close()
		q.task_done()

#localhost:32000/status?send=true
@app.route("/status")
def status():
	for key in list(logs.keys()):
		logs[key].clear()
	settings = json.load(open('./data/settings.json',))
	if request.args:
		req = request.args
		res = {}
		for key, value in req.items():
			res[key] = value
	for ipaddr in suscriber['ipaddrs']:
		queue.put(ipaddr)
	queue.join()
	Validator()
	if res['send'] == 'true':
		EmailReport()
	res = make_response(jsonify(logs), 200)
	return res


if __name__ == "__main__":
	queue = Queue()
	for i in range(len(suscriber['ipaddrs']) if multiprocessing.cpu_count() > len(suscriber['ipaddrs']) else multiprocessing.cpu_count()):
		thread = threading.Thread(target = DeviceConnector, args = (queue,))
		thread.setDaemon(True)
		thread.start()
	app.run(host = '0.0.0.0', port = os.environ.get('PORT'))