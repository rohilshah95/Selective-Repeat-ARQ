import sys
import socket
import struct
import random
import threading

def unpack_message(msg):					#Parsing the Message received from client
	header = msg[0:8]
	data = msg[8:]	
	sequenceNum = struct.unpack('=I',header[0:4])		
	checksum = struct.unpack('=H',header[4:6])
	identifier = struct.unpack('=H',header[6:])
	dataDecoded = data.decode('UTF-8')	
	return sequenceNum, checksum, identifier, dataDecoded
	
def generate_ack_packets(seqAcked, type):
	seqNum 		 = struct.pack('=I', seqAcked)	#SEQUENCE NUMBER BEING ACKED	
	if type != 0:
		zero16 	 = struct.pack('=H', 1)
	else:
		zero16 	 = struct.pack('=H', 0)
	ackIndicator = struct.pack('=H',43690)		#ACK INDICATOR - 1010101010101010[INT 43690]
	ackPacket = seqNum+zero16+ackIndicator
	return ackPacket

def verifyChecksum(data, checksum):
	sum = 0
	
	for i in range(0, len(data), 2):
		if i+1 < len(data):
			data16 = ord(data[i]) + (ord(data[i+1]) << 8)		#To take 16 bits at a time
			interSum = sum + data16
			sum = (interSum & 0xffff) + (interSum >> 16)		#To ensure 16 bits
	currChk = sum & 0xffff 
	result = currChk & checksum
	
	if result != 0:
		return False
	else:
		return True
	
def main():
	port = int(sys.argv[1])		#PORT ON WHICH SERVER WILL ACCEPT UDP PACKETS
	filename = sys.argv[2]		#NAME OF THE NEW FILE CREATED
	prob = float(sys.argv[3])	#PACKET DROP PROBABILITY
	buffer = {}			
	flag = True
	maxSeqNum = 0
	
	server_socket  = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)	
	host = socket.gethostname()
	server_socket.bind((host,port)) 
	
		
	while flag or len(buffer) < maxSeqNum:
		receivedMsg, sender_addr = server_socket.recvfrom(1024)
		sequenceNum, checksum, identifier, data = unpack_message(receivedMsg) 
		if random.uniform(0,1) <= prob:
			print('PACKET LOSS, SEQUENCE NUMBER = '+str(sequenceNum[0]))
		else:
			chksumVerification = verifyChecksum(data, int(checksum[0]))
			if chksumVerification == True:
				if data == '00000end11111':
					flag = False
					maxSeqNum = int(sequenceNum[0])
				elif data != '00000end11111' and int(sequenceNum[0]) not in buffer:
						buffer[int(sequenceNum[0])] = data						
				ackPacket = generate_ack_packets(int(sequenceNum[0]),0)
				server_socket.sendto(ackPacket,sender_addr)
	
	ackPacket = generate_ack_packets(maxSeqNum+1,1)
	server_socket.sendto(ackPacket,sender_addr)
	fileHandler = open(filename,'a')
	for i in range(0, maxSeqNum):
		fileHandler.write(buffer[i])
	# fileHandler.close()
	# print('File Received Successfully at the Server')
	# server_socket.close()	
	
if __name__ == '__main__':	
	main()