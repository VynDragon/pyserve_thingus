#!/bin/env python3

import http.server
import re
import os.path
import io
import mimetypes
import shutil

errorPath = "./data/error/"
check_path = re.compile("([\w\/\.%](?!(?<=\.)\.))*")

class RequestHandler(http.server.BaseHTTPRequestHandler):
	def handleHeaders(self, response):
		self.send_response(response)
		self.end_headers()

	def handleError(self, error):
		self.handleHeaders(error)
		with open(errorPath+str(error)+".html", 'rb') as  filee:
					shutil.copyfileobj(filee, self.wfile)
					self.wfile.flush()

	def parseStream(self, stream):
		return stream.read()

	def do_GET(self):
		if self.path.startswith("/api"):
			return
		else:
			try:
				if self.path == "/":
					self.path = "/index.html"
				if not check_path.fullmatch(self.path):
					self.handleError(400)
					return
				with io.open("./client"+self.path, 'rb') as  filee:
					filetype, encoding = mimetypes.guess_type("./client"+self.path, strict=False)
					self.send_response(200)
					self.send_header("Content-Type", filetype)
					self.end_headers()
					if self.path.endswith("html"):
						self.wfile.write(self.parseStream(filee))
					else:
						shutil.copyfileobj(filee, self.wfile)
					self.wfile.flush()
			except FileNotFoundError:
				self.handleError(404)

if __name__ == '__main__':
	server = http.server.HTTPServer(("", 8000), RequestHandler)
	server.serve_forever()
	
