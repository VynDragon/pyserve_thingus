#!/bin/env python

import http.server
import threading
import time
import re
import urllib
import datetime
from server import RequestHandler as  ServerDefaultRequestHandler

def failedJobNameList():
	global dataset
	out = ""
	for job in dataset["failed_jobs"]:
		culprit = ("build #" + str(job["custom_data"]["firstFailedBuid"]["number"])) if job["custom_data"]["firstFailedBuid"] is not None else "forever as far as jenkins remember"
		if job["custom_data"]["firstFailedBuid"]:
			if job["custom_data"]["firstFailedBuid"]["changeSet"]:
				changeset_set_name = set([i["author"]["fullName"] for i in job["custom_data"]["firstFailedBuid"]["changeSet"]["items"]])
				itemlen = len(changeset_set_name)
				if itemlen > 1:
					culprit += ". Suspected culprits are "
				else:
					culprit += ". Suspected culprit is "
				for idx, item in enumerate(changeset_set_name):
					culprit += item
					if not idx == itemlen - 1:
						culprit += ", "
		if job["name"] in [i["name"] for i in dataset["building_jobs"]]:
			out += "<div class=\"icon building\">"
		else:
			out += "<div class=\"icon\">"
		out += job["name"] + "<br><div class=\"culprit\">Failed since " + culprit  + "</div></div>"
	return out

def failedJobs():
	global dataset
	out = ""
	if len(dataset["failed_jobs"]) > 0:
			return "true"
	return "false"

def hour():
	now = datetime.datetime.now()
	return str(now.hour).zfill(2) + ":" + str(now.minute).zfill(2)

def latestFixedJob():
	out = ""
	if len(dataset["fixed_jobs"]) < 1:
		return out
	job = dataset["fixed_jobs"][0]
	culprit = ""
	if job["custom_data"]["firstSuceededBuild"]:
			if job["custom_data"]["firstSuceededBuild"]["changeSet"]:
				changeset_set_name = set([i["author"]["fullName"] for i in job["custom_data"]["firstSuceededBuild"]["changeSet"]["items"]])
				itemlen = len(changeset_set_name)
				for idx, item in enumerate(changeset_set_name):
					culprit += item
					if not idx == itemlen - 1:
						culprit += ", "
	out += "Latest fixed job is " + job["name"]
	if len(culprit) > 0:
		out +=  ", fixed by " + culprit
	return out

def failedJobs_displayifnotfailed():
	global dataset
	if len(dataset["failed_jobs"]) > 0:
			return "hidden"
	return "visible"

class ParsingRequestHandler(ServerDefaultRequestHandler):
	datasetmatcher = re.compile(r'\@\!\>(.*?)\<\!\@')
	datasetHandlers = {"failedJobNameList": failedJobNameList,
					"failedJobs": failedJobs,
					"failedJobs_displayifnotfailed": failedJobs_displayifnotfailed,
					"hour": hour,
					"latestFixedJob": latestFixedJob}
	def parseStream(self, stream):
		out = ""
		for line in stream:
			linedec = line.decode()
			matches = self.datasetmatcher.finditer(linedec)
			for match in matches:
				if match is not None:
					if match.lastindex:
						for m in range(1, match.lastindex + 1):
							if match.group(m) in self.datasetHandlers:
								linedec = linedec.replace("@!>" + match.group(m) + "<!@", self.datasetHandlers[match.group(m)]())
			out += linedec
		return out.encode()
	def setData(self, dataset):
		self.dataset = dataset

server = http.server.HTTPServer(("", 8000), ParsingRequestHandler)
#server.serve_forever()

serverThread = threading.Thread(target=server.serve_forever)
serverThread.start()
print('Starting data update loop...')

import jenkins

dataset = dict()

jenkinsServer = jenkins.Jenkins('http://192.168.5.4', username='Anonymous')
version = jenkinsServer.get_version()
print('Jenkins server version:' + str(version))
while True:
	dataset_new = dict()
	dataset_new["job_list"] = jenkinsServer.get_jobs(view_name="dashboard")
	dataset_new["jobs"] = list()
	dataset_new["failed_jobs"] = list()
	dataset_new["building_jobs"] = list()
	dataset_new["fixed_jobs"] = list()
	for job in dataset_new["job_list"]:
		dataset_new["jobs"].append(jenkinsServer.get_job_info(job["name"]))
	for job in dataset_new["jobs"]:
		if job["lastSuccessfulBuild"] is not None and job["lastCompletedBuild"] is not None:
			if job["lastSuccessfulBuild"]["number"] != job["lastCompletedBuild"]["number"] and job["buildable"] :
				dataset_new["failed_jobs"].append(job)
		elif job["buildable"]:
			dataset_new["failed_jobs"].append(job)
		if job["lastCompletedBuild"] is not None:
			if job["lastCompletedBuild"]["number"] != job["lastBuild"]["number"] :
				dataset_new["building_jobs"].append(job)
	for job in dataset_new["failed_jobs"]:
		job["custom_data"] = dict()
		if job["lastSuccessfulBuild"]:
			try:
				job["custom_data"]["firstFailedBuid"] = jenkinsServer.get_build_info(job["name"], int(job["lastSuccessfulBuild"]["number"]) + 1)
			except jenkins.NotFoundException:
				job["custom_data"]["firstFailedBuid"] = None
		elif job["lastFailedBuild"]:
			job["custom_data"]["firstFailedBuid"] = jenkinsServer.get_build_info(job["name"], 1)
		else:
			job["custom_data"]["firstFailedBuid"] = None
	try:
		failed_job_names = set([job["name"] for job in dataset_new["failed_jobs"]])
		previous_failed_job_names = set([job["name"] for job in dataset["failed_jobs"]])
		fixed_job_names  = previous_failed_job_names.difference(failed_job_names)
		dataset_new["fixed_jobs"] = [job for job in dataset["jobs"] if (job["name"] in fixed_job_names)]
		if len(dataset_new["fixed_jobs"]) < 1:
			dataset_new["fixed_jobs"] = dataset["fixed_jobs"]
		else:
			for job in dataset_new["fixed_jobs"]:
				if job["custom_data"] is None:
					job["custom_data"] = dict()
				job["custom_data"]["firstSuceededBuild"] =  jenkinsServer.get_build_info(job["name"], int(job["lastSuccessfulBuild"]["number"]))
	except:
		print("Well there was an exception in a place where it can happen, I need to put something in there.")
	dataset = dataset_new
	time.sleep(30)

