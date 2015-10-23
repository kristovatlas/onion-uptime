# onion-uptime
Checking the status of onion sites in the Tor network

# Dependencies

Requires the SocksiPy module. This can be installed using `pip` with the following command:
```pip install SocksiPy-branch```

If you receive an error such as:
```
	File "/usr/local/lib/python2.7/dist-packages/socks.py", line 165, in sendall
	socket.socket.sendall(self, bytes) 
	
	RuntimeError: maximum recursion depth exceeded
```

You may need to download the 'socks' library for Python. This can be done in Linux with these two commands:
```
	wget http://sourceforge.net/projects/socksipy/files/latest/download
	unzip download
```
