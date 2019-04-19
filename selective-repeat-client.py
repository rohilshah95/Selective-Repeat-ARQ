import sys
import socket
import time
import struct
import threading

TIMEOUT_TIMER = 0.2
sendingLock = threading.Lock()
window = {}
closeFlag = True
maxSeqNum = -1

class fileReader(threading.Thread):
	def __init__(self, host, port, file, n, MSS, cSock, receiver):
		threading.Thread.__init__(self)
		self.host = host				#SERVER IP ADDRESS
		self.port = int(port)			#SERVER PORT
		self.file = file				#FILE TO TRANSMIT
		self.n    = int(n)				#WINDOW SIZE
		self.MSS  = int(MSS)			#MAXIMUM SEGMENT SIZE
		self.sock = cSock
		self.r = receiver
		self.start()		

	def computeChecksum(self, data):
		sum = 0
		for i in range(0, len(data), 2):
			if i+1 < len(data):
				data16 = ord(data[i]) + (ord(data[i+1]) << 8)		#To take 16 bits at a time
				interSum = sum + data16
				sum = (interSum & 0xffff) + (interSum >> 16)		#'&' to ensure 16 bits are returned
		return ~sum & 0xffff										#'&' to ensure 16 bits are returned
				
	def formPacket(self, data, seq):
		#32 bit sequence number
		#16 bit check of the data part
		#16 bit 0101010101010101 -- Indicates data packet(in int 21845)
		dataIndicator = struct.pack('=H',21845)
		seqNum = struct.pack('=I',seq)
		checksum_val = self.computeChecksum(data)
		checksum = struct.pack('=H',checksum_val)
		packet = seqNum+checksum+dataIndicator+bytes(data,'UTF-8')
		return packet
		
	def run(self):
		self.rdt_send()	
		
	def retransmitter(self, host, port):
		global window
		global sendingLock
		
		sendingLock.acquire()
		for packet in window:
			if window[packet][2] == 0 and time.time() - window[packet][1] > TIMEOUT_TIMER:
				print('TIMEOUT, SEQUENCE NUMBER = '+str(packet))
				window[packet] = (window[packet][0], time.time(), 0)
				self.sock.sendto(window[packet][0],(host, port))
		sendingLock.release()
	
	def rdt_send(self):
		global window
		global maxSeqNum

		fileHandle = open(self.file,'rb')
		currSeq = 0
		sendMsg = ''
		
		b = True
		while b:
			b = fileHandle.read(1)
			sendMsg += str(b,'UTF-8')
			if len(sendMsg) == self.MSS or (not b):		
				while len(window) >= self.n:
					#pass
					self.retransmitter(self.host,self.port)
				#sender(self.sock, self.host, self.port, sendMsg, currSeq)    #Thread spawned to handle a single packet
				sendingLock.acquire()
				packet = self.formPacket(sendMsg, currSeq)				#Packets are created here
				window[currSeq] = (packet, time.time(), 0)
				self.sock.sendto(packet,(self.host, self.port))
				sendingLock.release()
				currSeq += 1
				sendMsg = ''
						
		sendMsg = '00000end11111'
		sendingLock.acquire()
		packet = self.formPacket(sendMsg, currSeq)				#Packets are created here
		window[currSeq] = (packet, time.time(), 0)
		self.sock.sendto(packet,(self.host, self.port))
		sendingLock.release()
		#sender(self.sock, self.host, self.port, sendMsg,currSeq)		#Thread spawned to send the end packet
		maxSeqNum = currSeq
		while len(window) > 0:
			self.retransmitter(self.host,self.port)
		fileHandle.close()	
		
#Thread Class to receive the ACK Packets from the Server
class receiver(threading.Thread):
	def __init__(self, host, port, file, n, MSS, cSock):		
		threading.Thread.__init__(self)
		self.host = host				#SERVER IP ADDRESS
		self.port = int(port)			#SERVER PORT
		self.file = file				#FILE TO TRANSMIT
		self.n    = int(n)				#WINDOW SIZE
		self.MSS  = int(MSS)			#MAXIMUM SEGMENT SIZE
		self.sockAddr = cSock
		self.start()
	
	def parseMsg(self, msg):
		zero16 = struct.unpack('=H', msg[4:6])				#16 bit field with all 0's
		identifier = struct.unpack('=H', msg[6:])			#16 bit field to identify the ACK packets
		seq_number = struct.unpack('=I', msg[0:4])			#Sequence Number Acked by the server
		return seq_number, zero16, identifier
		
	def run(self):
		global sendingLock	
		global window
		global closeFlag

		closeFlag = True
		try:
			while closeFlag == True or len(window) > 0:			
				ackReceived, server_addr = self.sockAddr.recvfrom(2048)			#Receives the ACK packets 
				seq_number , zero16, identifier = self.parseMsg(ackReceived)
				if int(zero16[0]) > 0:
					print('Receiver Terminated')
					break
				#16 bit identifier field to identify the ACK packets - 1010101010101010 [in int 43690]		
				if int(identifier[0]) == 43690 and int(seq_number[0]) in window:
					sendingLock.acquire()
					setTime = window[int(seq_number[0])][1]
					window[int(seq_number[0])] = (window[int(seq_number[0])][0],setTime, 1)					
					del window[int(seq_number[0])]
					sendingLock.release()
		except:
			print('Server closed its connection - Receiver')
			self.sockAddr.close()

def main():
	host = sys.argv[1]
	port = int(sys.argv[2])
	cliSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)	
	cliPort = int(input('Client Port ='))
	cliSocket.bind(('',cliPort)) 
	
	startTime = time.time()
	ackReceiver = receiver(sys.argv[1], sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5],cliSocket)					#Thread that receives ACKs from the Server
	fileHandler = fileReader(sys.argv[1], sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5],cliSocket, ackReceiver) 	#Thread that reads the file and sending of packets
	fileHandler.join()
	ackReceiver.join()
	endTime = time.time()
	cliSocket.close()

	print('Total Time Taken (Delay):'+str(endTime-startTime))	
	
if __name__ == '__main__':	
	main()	


