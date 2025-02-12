
from nintendo.nex import account, authentication, common, datastore, \
	friends, kerberos, matchmaking, notification, ranking, secure, \
	service, nattraversal
from nintendo.settings import Settings

import logging
logger = logging.getLogger(__name__)


class LoginResult:
	def __init__(self, pid, ticket, secure_station):
		self.pid = pid
		self.ticket = ticket
		self.secure_station = secure_station


class BackEndClient:
	def __init__(self, access_key, version, settings=None):
		if settings:
			self.settings = settings.copy()
		else:
			self.settings = Settings()
		self.settings.set("server.access_key", access_key)
		self.settings.set("server.version", version)
		
		self.auth_client = service.RMCClient(self.settings)
		self.secure_client = service.RMCClient(self.settings)
		
		self.auth_proto = authentication.AuthenticationClient(self.auth_client)
		self.secure_proto = secure.SecureConnectionClient(self.secure_client)
		
		if self.settings.get("kerberos.key_derivation") == 0:
			self.key_derivation = kerberos.KeyDerivationOld(65000, 1024)
		else:
			self.key_derivation = kerberos.KeyDerivationNew(1, 1)
			
		self.my_pid = None
		self.local_station = None
		self.public_station = None
		
	def connect(self, host, port):
		# Connect to authentication server
		if not self.auth_client.connect(host, port, 1):
			raise ConnectionError("Couldn't connect to authentication server")
		
	def close(self):
		self.auth_client.close()
		self.secure_client.close()
		
	def login(self, username, password, auth_info=None, login_data=None):
		if self.settings.get("server.version") < 40500:
			result = self.login_normal(username, auth_info)
		else:
			result = self.login_with_param(username, auth_info)
		
		self.pid = result.pid
		
		secure_station = result.secure_station
		
		# Derive kerberos key from password
		kerberos_key = self.key_derivation.derive_key(
			password.encode("ascii"), self.pid
		)
		
		# Decrypt ticket from login response
		ticket = kerberos.ClientTicket()
		ticket.decrypt(result.ticket, kerberos_key, self.settings)
		
		if ticket.target_pid != secure_station["PID"]:
			# Request ticket for secure server
			response = self.auth_proto.request_ticket(
				self.pid, secure_station["PID"]
			)
			
			# Check for errors and decrypt ticket
			response.result.raise_if_error()
			ticket = kerberos.ClientTicket()
			ticket.decrypt(response.ticket, kerberos_key, self.settings)
			
		ticket.source_pid = self.pid
		ticket.target_cid = secure_station["CID"]

		# The secure server may reside at the same
		# address as the authentication server
		host = secure_station["address"]
		port = secure_station["port"]
		if host == "0.0.0.1":
			host, port = self.auth_client.remote_address()

		# Connect to secure server
		server_sid = secure_station["sid"]
		if not self.secure_client.connect(host, port, server_sid, ticket):
			raise ConnectionError("Couldn't connect to secure server")
		
		# Create a stationurl for our local client address
		client_addr = self.secure_client.local_address()
		self.local_station = common.StationURL(
			address=client_addr[0], port=client_addr[1],
			sid=self.secure_client.stream_id(),
			natm=0, natf=0, upnp=0, pmp=0
		)
		
		# Register urls on secure server
		if login_data:
			response = self.secure_proto.register_ex([self.local_station], login_data)
		else:
			response = self.secure_proto.register([self.local_station])

		# Check for errors and update urls
		response.result.raise_if_error()
		self.public_station = response.public_station
		self.public_station["RVCID"] = response.connection_id
		self.local_station["RVCID"] = response.connection_id
		
	def login_normal(self, username, auth_info):
		if auth_info:
			response = self.auth_proto.login_ex(username, auth_info)
		else:
			response = self.auth_proto.login(username)			
		response.result.raise_if_error()
		return LoginResult(
			response.pid, response.ticket, response.connection_data.main_station
		)
		
	def login_with_param(self, username, auth_info):
		param = authentication.ValidateAndRequestTicketParam()
		param.username = username
		if auth_info:
			param.data = auth_info
		else:
			param.data = common.NullData()
		param.nex_version = self.settings.get("server.version")
		response = self.auth_proto.login_with_param(param)
		return LoginResult(
			response.pid, response.ticket, response.server_url
		)
		
	def login_guest(self):
		self.login("guest", "MMQea3n!fsik")
		
	def get_pid(self):
		return self.pid
