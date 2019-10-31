import random, asyncio, aiofiles, socket, json, datetime, requests as rq, keyboard, argparse
from colorama import init, Fore, Back, Style

# todo:
# count attempts
# iterative & random ip generation
# if a player is online, add it to a seperate (surveillance) list of servers
# 	sort ip by country


class ServerScan:
	def __init__(self, address, port, timeout=0.3):
		self.address = address
		self.port = port
		self.timeout = timeout

		self.raw = None
		self.online = True


	def jsonify(self):
		if self.online:
			server = {
				"host": str(self.address) + ":" + str(self.port),
				"version": self.version,
				"latency": self.latency,
				"players": self.current_players,
				"maxPlayers": self.max_players,
				"motd": self.motd,
				"time": "{}".format(datetime.datetime.now().strftime("%x - %X"))
			}
			return json.dumps(server)
		else:
			return False


	def prettify(self):
		if self.online:
			string = f"{Style.BRIGHT}{Fore.GREEN}{self.version}  {Fore.BLUE}{self.latency}ms  {Fore.YELLOW}{self.current_players}/{self.max_players}  {Fore.MAGENTA}{self.motd}{Style.RESET_ALL}"
		
		return "offline" if not string else string


	async def analyze(self):
		await self.getData()
		await self.parseData()


	async def getData(self):
		packet = bytearray([0xFE, 0x01])
		start_time = datetime.datetime.now()
		try:
			r, w = await asyncio.wait_for(asyncio.open_connection(self.address, self.port), self.timeout)

			self.latency = int(round((datetime.datetime.now() - start_time).total_seconds() * 1000))

			# handshake with mc server to aquire data
			w.write(packet)
			self.raw = await asyncio.wait_for(r.read(1024), self.timeout)

			w.close()

		except:
			self.online = False


	async def parseData(self):
		if not self.raw:
			self.online = False
		elif self.online:
			try:
				data = self.raw.decode('cp437').split('\x00\x00\x00')
				if len(data) >= 6:
					self.online = True
					self.version = data[2].replace("\x00", "")
					try:
						self.motd = data[3].encode('utf-8').replace(b"\x00", b"").decode()
					except:
						self.motd = data[3].encode('utf-8').replace(b"\x00", b"")
					self.current_players = data[4].replace("\x00", "")
					self.max_players = data[5].replace("\x00", "")
				else:
					self.online = False
			except:
				self.online = False



def getIP(iter=False, ip=None):
	newIP = [
		random.choice(list(range(2, 254))), 
		random.choice(list(range(2, 254))), 
		random.choice(list(range(2, 254))), 
		random.choice(list(range(2, 254)))
	]
	# some ips may be invalid, but this is less than a minor issue
	# 	(one invalid IP will have an impact of less than 1ms delay if default timeout)
	
	formatted = ""
	for num in newIP:
		formatted += str(num) + "."
	
	return formatted[:len(formatted)-1] # remove a dot


async def portOpen(ip, port, timeout):
	try:
		r, w = await asyncio.wait_for(asyncio.open_connection(ip, port), timeout)
		w.close()
		return True
	except:
		return False


async def worker(name, portList, timeout, minecraftMode, toBot=False, stopKey="F9"):
	while not keyboard.is_pressed(stopKey):
		ip = getIP()

		for port in portList:
			portStatus = await portOpen(ip, port, timeout)
			if portStatus:
				statString = Fore.CYAN+ip+Style.RESET_ALL + ":" + str(port) + " "*(24-len(ip)-len(str(port)))
				statString = "[{}] ".format(datetime.datetime.now().strftime("%x - %X")) + statString

					
				if minecraftMode:
					stats = ServerScan(ip, port, timeout)
					await stats.analyze()

					statString += "Online: " if stats.online else "Offline"
					if stats.online:
						# SERVER IS ONLINE

						if toBot:
							try:
								# send to discord bot
								rq.get("http://litago.xyz:23086", params={"server": stats.jsonify()}, timeout=2)
							except Exception as e:
								print(e)

						statString += stats.prettify()
						print(statString)

				else:
					print(statString)



async def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("ports", help="comma separated integers", type=lambda i: list(map(int, i.split(","))))
	parser.add_argument("-t", "--timeout", help="Default: 0.3", type=float)
	parser.add_argument("-w", "--workers", help="Default: 400", type=int)
	parser.add_argument("-d", "--discord", help="Default: True", type=lambda i: not "false" in i.lower())
	parser.add_argument("-m", "--minecraft", help="Default: False. Whether to scan for a minecraft server or not", type=lambda i: not "true" in i.lower())

	args = parser.parse_args()

	if args.timeout is None:
		args.timeout = 0.3
	if args.workers is None:
		args.workers = 400
	if args.discord is None:
		args.discord = True
	if args.minecraft is None:
		args.minecraft = False

	#async with aiofiles.open(str(datetime.datetime.now().strftime("%x")).replace("/", "-"), mode="a+") as fs:
	
	# make a lot of workers, each doing the same thing
	tasks = []
	for i in range(args.workers):
		tasks.append(asyncio.create_task(worker(str(i), args.ports, args.timeout, args.minecraft, toBot=args.discord, stopKey="F9")))

	# initiate the workers
	print("Started searching at " + datetime.datetime.now().strftime("%x - %X"), end="\n\n")
	await asyncio.gather(*tasks)


if __name__ == "__main__":
	init() # colorama
	asyncio.run(main())

