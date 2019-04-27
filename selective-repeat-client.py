import sys
import socket
import time
import struct
import threading

TIMEOUT_TIMER = 0.2
lock = threading.Lock()
window = {}
maxseq_number = -1

class Sender(threading.Thread):
	def __init__(self, host, port, file, n, MSS, socket_client, receiver):
		threading.Thread.__init__(self)
		self.host = host				
		self.port = int(port)			
		self.file = file				
		self.n    = int(n)			
		self.MSS  = int(MSS)
		self.sock = socket_client
		self.r = receiver
		self.start()		

	def carry_around_add(self, x, y):
		return ((x+y) & 0xffff) + ((x + y) >> 16)

	def checksum_computation(self, message):
		add = 0
		for i in range(0, len(message) - len(message) % 2, 2):
			message = str(message)
			w = ord(message[i]) + (ord(message[i + 1]) << 8)
			add = self.carry_around_add(add, w)
		return ~add & 0xffff								
				
	def create_packet(self, data, seq):
		data_packet = struct.pack('=H',21845)
		seq_number = struct.pack('=I',seq)
		checksum_val = self.checksum_computation(data)
		checksum = struct.pack('=H',checksum_val)
		packet = seq_number + checksum + data_packet + bytes(data,'UTF-8')
		return packet
		
	def run(self):
		self.rdt_send()	
		
	def retransmitter(self, host, port):
		global window
		global lock
		
		lock.acquire()
		for packet in window:
			if window[packet][2] == 0 and time.time() - window[packet][1] > TIMEOUT_TIMER:
				print('Timeout, sequence number = '+str(packet))
				window[packet] = (window[packet][0], time.time(), 0)
				self.sock.sendto(window[packet][0],(host, port))
		lock.release()
	
	def rdt_send(self):
		global window
		global maxseq_number

		fileHandle = open(self.file,'rb')
		current_sequence = 0
		data_sent = ''
		
		b = True
		while b:
			b = fileHandle.read(1)
			data_sent += str(b,'UTF-8')
			if len(data_sent) == self.MSS or (not b):		
				while len(window) >= self.n:
					self.retransmitter(self.host,self.port)
				lock.acquire()
				data_packet = struct.pack('=H',21845)
				seq_number = struct.pack('=I',current_sequence)
				checksum_val = self.checksum_computation(data_sent)
				checksum = struct.pack('=H',checksum_val)
				packet = seq_number+checksum+data_packet+bytes(data_sent,'UTF-8')
				# packet = self.create_packet(data_sent, current_sequence)				
				window[current_sequence] = (packet, time.time(), 0)
				self.sock.sendto(packet,(self.host, self.port))
				lock.release()
				current_sequence += 1
				data_sent = ''
						
		data_sent = '0101end0101'
		lock.acquire()
		data_packet = struct.pack('=H',21845)
		seq_number = struct.pack('=I',current_sequence)
		checksum_val = self.checksum_computation(data_sent)
		checksum = struct.pack('=H',checksum_val)
		packet = seq_number+checksum+data_packet+bytes(data_sent,'UTF-8')
		# packet = self.create_packet(data_sent, current_sequence)				
		window[current_sequence] = (packet, time.time(), 0)
		self.sock.sendto(packet,(self.host, self.port))
		lock.release()
		maxseq_number = current_sequence
		while len(window) > 0:
			self.retransmitter(self.host,self.port)
		fileHandle.close()	
		
class receiver(threading.Thread):
	def __init__(self, host, port, file, n, MSS, socket_client):		
		threading.Thread.__init__(self)
		self.host = host				
		self.port = int(port)			
		self.file = file				
		self.n    = int(n)				
		self.MSS  = int(MSS)			
		self.socket_client = socket_client
		self.start()
	
	def message_from_sender(self, msg):
		null = struct.unpack('=H', msg[4:6])				
		identifier = struct.unpack('=H', msg[6:])			
		seq_number = struct.unpack('=I', msg[0:4])			
		return seq_number, null, identifier
		
	def run(self):
		global lock	
		global window
		try:
			while True or len(window) > 0:			
				ackReceived, server_addr = self.socket_client.recvfrom(2048)
				seq_number , null, identifier = self.message_from_sender(ackReceived)
				if int(null[0]) > 0:
					print('Receiver Terminated')
					break
				if int(identifier[0]) == 43690 and int(seq_number[0]) in window:
					lock.acquire()					
					del window[int(seq_number[0])]
					lock.release()
		except:
			print('Server closed its connection - Receiver')
			self.socket_client.close()

def main():
	host = sys.argv[1]
	port = int(sys.argv[2])
	socket_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)	
	client_port = 4443
	socket_client.bind(('',client_port)) 
	host = sys.argv[1]
	port = sys.argv[2]
	file = sys.argv[3]
	n = sys.argv[4]
	MSS = sys.argv[5]
	startTime = time.time()
	ACKs = receiver(host, port, file, n, MSS, socket_client)					
	transmitted_data = Sender(host, port, file, n, MSS, socket_client, ACKs) 
	transmitted_data.join()
	ACKs.join()
	endTime = time.time()
	socket_client.close()

	print('Total Time Taken (Delay):'+str(endTime-startTime))	
	
if __name__ == '__main__':	
	main()	


