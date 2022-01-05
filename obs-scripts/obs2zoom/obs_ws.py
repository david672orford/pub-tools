# A simple OBS Websocket client library

import websocket
import json
import base64
import hashlib
import logging

logger = logging.getLogger(__name__)

class ObsEventReader:
	def __init__(self, hostname="localhost", port=4444, password="secret"):
		logger.debug("Connecting to OBS...")
		self.ws = websocket.WebSocket()
		self.ws.connect("ws://%s:%d" % (hostname, port))
		self.id = 1

		logger.debug("Logging in...")
		response = self.request({"request-type": "GetAuthRequired"})
		assert response['status'] == 'ok', response

		if response.get('authRequired'):
			secret = base64.b64encode(hashlib.sha256((password + response['salt']).encode('utf-8')).digest())
			auth = base64.b64encode(hashlib.sha256(secret + response['challenge'].encode('utf-8')).digest()).decode('utf-8')
			response = self.request({"request-type": "Authenticate", "auth": auth})
			assert response['status'] == 'ok', response

		logger.debug("Ready to receive messages from OBS.")

	# Send a request to OBS-Websocket. Wait for the response. Discard any
	# events which may come in before the response.
	def request(self, data, wait=True):
		data["message-id"] = str(self.id)
		self.id += 1
		logger.debug("request: %s", json.dumps(data, indent=2, ensure_ascii=False))
		self.ws.send(json.dumps(data))
		if not wait:
			return None
		while True:
			response = json.loads(self.ws.recv())
			logger.debug("response: %s", json.dumps(response, indent=2, ensure_ascii=False))
			if response.get('message-id') == data['message-id']:
				break
		return response

	# We use this to receive events.
	def recv_message(self):
		return json.loads(self.ws.recv())

	def get_virtualcam_active(self):
		response = self.request({"request-type": "GetVirtualCamStatus"})
		assert response['status'] == 'ok', response
		return response['isVirtualCam']

	def get_current_sources(self):
		response = self.request({"request-type": "GetCurrentScene"})
		assert response['status'] == 'ok', response
		return response['sources']

