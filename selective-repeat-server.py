import sys
import socket
import struct
import random
import threading

def message_from_sender(message):						
	seq_num = struct.unpack('=I',message[0:4])		
	checksum = struct.unpack('=H',message[4:6])
	data_identifier = struct.unpack('=H',message[6:8])
	data = message[8:].decode('UTF-8')	
	return seq_num, checksum, data_identifier, data
	
def generate_ack_packets(seqAcked, type):
	seq_num = struct.pack('=I', seqAcked)
	if type != 0:
		null = struct.pack('=H', 1)
	else:
		null = struct.pack('=H', 0)
	data_packet = struct.pack('=H',43690)		
	ackPacket = seq_num + null + data_packet
	return ackPacket

def carry_around_add(self, x, y):
		return ((x+y) & 0xffff) + ((x + y) >> 16)

def checksum_computation(data, checksum):
	sum = 0
	
	for i in range(0, len(data), 2):
		if i+1 < len(data):
			data16 = ord(data[i]) + (ord(data[i+1]) << 8)		
			interSum = sum + data16
			sum = (interSum & 0xffff) + (interSum >> 16)
	currChk = sum & 0xffff 
	result = currChk & checksum
	
	if result != 0:
		return False
	else:
		return True
	
def main():
	port = int(sys.argv[1])		
	filename = sys.argv[2]		
	probability = float(sys.argv[3])	
	buffer = {}			
	flag = True
	maxseq_num = 0
	
	server_socket  = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)	
	host = socket.gethostname()
	server_socket.bind((host,port)) 
	
		
	while flag or len(buffer) < maxseq_num:
		receivedMsg, sender_addr = server_socket.recvfrom(1024)
		seq_num, checksum, data_identifier, data = message_from_sender(receivedMsg) 
		if random.random() <= probability:
			print('Packet loss, sequence number = '+str(seq_num[0]))
		else:
			chksumVerification = checksum_computation(data, int(checksum[0]))
			if chksumVerification == True:
				if data == '0101end0101':
					flag = False
					maxseq_num = int(seq_num[0])
				elif data != '0101end0101' and int(seq_num[0]) not in buffer:
						buffer[int(seq_num[0])] = data						
				ackPacket = generate_ack_packets(int(seq_num[0]),0)
				server_socket.sendto(ackPacket,sender_addr)
	
	ackPacket = generate_ack_packets(maxseq_num+1,1)
	server_socket.sendto(ackPacket,sender_addr)
	fileHandler = open(filename,'a')
	for i in range(0, maxseq_num):
		fileHandler.write(buffer[i])
	fileHandler.close()
	print('File Received Successfully at the Server')
	server_socket.close()	
	
if __name__ == '__main__':	
	main()