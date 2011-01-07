#!/usr/bin/env python

from subprocess import Popen, PIPE, STDOUT
import re, httplib, urllib, json, os, sys, time
import threading, SimpleHTTPServer, SocketServer, socket

#sudo tcpdump -i mon0 -s 0 -e link[25] != 0x80
#sudo aa-complain /usr/sbin/tcpdump

json_map={}

http_running=True

class httpRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
  def do_GET(self):
    try:
      if self.path.endswith(".json"):

	self.send_response(200)
	self.send_header('Content-type','application/x-javascript')
	self.end_headers()
	self.wfile.write(json.dumps(json_map))
	return
	
      elif self.path=='/' or self.path.endswith(".html"):
	f = open(os.curdir + os.sep + 'html' + os.sep + 'wilocate.html')
	self.send_response(200)
	self.send_header('Content-type','text/html')
	self.end_headers()
	self.wfile.write(f.read())
	f.close()
	return
	
    except IOError:
      self.send_error(404, 'File not found: %s' % self.path)
      
    #return SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)

class httpHandler ( threading.Thread ):
  
   def run ( self ):
    
      
      http_timeout = 5
      socket.setdefaulttimeout(http_timeout)

      server_address = ('127.0.0.1', 8000)
      httpd = SocketServer.TCPServer(('', 8000), httpRequestHandler)
      sa = httpd.socket.getsockname()
      print "Serving HTTP on", sa[0], "port", sa[1], "..."
      while http_running:
	  httpd.handle_request()
      httpd.socket.close()
	

def usage():
  print '\n  Usage:\n\n' + sys.argv[0] + '\t\t\tLocate actual position using WiFi scanning\n' + sys.argv[0] + ' <MAC address>\tLocate given MAC address position\n' + sys.argv[0] + ' --help|-h\t\tThis help\n\n  Progress symbols:\n\n* new wifi AP detected\n. incomplete geographic data returned, retry\n+ complete geographic data returned\n- geographic data request failed, skipping address\n! connection error, retry'

class macHandler:
  
  def macHandler(self):
    pass

  def getAddresses(self):
    
    addr=[]
    
    for i in range(3):
      newaddr=[]
      
      cmd = 'iwlist scan'
      p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
      newaddr = re.findall('Address: ((?:[0-9A-Z][0-9A-Z]:?){6})', p.stdout.read())
      
      if len(set(addr + newaddr)) > len(addr):
	print '* '*(len(set(addr + newaddr))-len(addr)),
      
      addr = list(set(addr + newaddr))
      
      return addr


  def getLocation(self,addr):

    jsons=[]

    for a in addr:

      done=False

      for r in range(3):
	
	sys.stdout.flush()
	
	params = "{ \"version\": \"1.1.0\", \"host\": \"maps.google.com\", \"request_address\": \"true\", \"address_language\":\"en_GB\", \"wifi_towers\": [ { \"mac_address\": " + a.replace(':','-') + ", \"signal_strength\": 8, \"age\": 0 } ] }"
	headers = { "Pragma" : "no-cache", "Cache-control" : "no-cache" }
	conn = httplib.HTTPConnection("www.google.com:80")
	try:
	  conn.request("POST", "/loc/json", params, headers)
	  response = conn.getresponse()
	except Exception, e:
	  print '!', e
	  continue
	
	try:
	  j = json.loads(response.read())
	except ValueError, e:
	  print '!', e
	  continue
	
	if 'location' in j:
	  j = j['location'].copy()
	  if 'address' in j:
	    print '+',
	    j['mac_address']=a
	    jsons.append(j)
	    done=True
	    break
	else:
	  print '.',
	  continue
	
      if not done:
	print '-',

    print ''

    jsons.sort(key=lambda j: j['accuracy'], reverse=True)
    return jsons


  def calcLocation(self,jsons):

    weightedsumm=[0.0,0.0]
    summ=[0.0,0.0]
    summweight=0
    numlocated=0

    json_block={}

    for j in jsons:

      latitude=0
      longitude=0

      print ''
      
      if 'mac_address' in j:
	
	numlocated=numlocated+1
	
	print j['mac_address'],
	
	if 'accuracy' in j:
	  weight = j['accuracy']
	  summweight = summweight + weight

	  print '(accuracy: ' + str(j['accuracy']) + ')', 
	
	if 'latitude' in j:
	    latitude = j['latitude']
	    summ[0]=summ[0]+j['latitude']
	    weightedsumm[0]=weightedsumm[0]+j['latitude']*weight

	
	if 'longitude' in j:
	    longitude = j['longitude']
	    summ[1]=summ[1]+j['longitude']
	    weightedsumm[1]=weightedsumm[1]+j['longitude']*weight
	    
	if 'address' in j:
	  
	  if 'country' in j['address']:
	    print j['address']['country'],
	    
	  if 'country_code' in j['address']:
	    print '(' + j['address']['country_code'] + ')',
	    
	  if 'region' in j['address']:
	    print j['address']['region'],

	  if 'postal_code' in j['address']:
	    print j['address']['postal_code'],

	  if 'county' in j['address']:
	    county = j['address']['county']
		  
	  if 'city' in j['address']:
	    city = j['address']['city']

	  if county != city:
	    print city, county,
	  elif not city:
	    print county,
	  else:
	    print city, 


	  if 'street' in j['address']:
	    print j['address']['street'],

	  if 'street_number' in j['address']:
	    print j['address']['street_number'],
	    
	  #print '                  http://maps.google.it/maps?q=' + str(latitude) + ',' + str(longitude)

	if 'APs' not in json_block:
	  json_block['APs']={}
	  
	json_block['APs'][j['mac_address']]=j.copy()


    timestamp = int(time.time())
    if numlocated>0 and weightedsumm>0:
      print '\n' + str(timestamp) + ' position: http://maps.google.it/maps?q=' + str(summ[0]/numlocated) + ',' + str(summ[1]/numlocated)
      
      if 'position' not in json_block:
	json_block['position'] = [ summ[0]/numlocated, summ[1]/numlocated ]

    json_map[timestamp]=json_block
    print json_map

      #print '\nWeighted average: http://maps.google.it/maps?q=' + str(weightedsumm[0]/summweight) + ',' + str(weightedsumm[1]/summweight)

     

  

def main():
  
  if len(sys.argv) == 2:
    
    if(sys.argv[1]=='--help' or sys.argv[1]=='-h'):
      usage()
      sys.exit(0)
    
    elif not re.match("(?:[0-9A-Z][0-9A-Z](:|-)?){6}", sys.argv[1]):
      print '! Error: \'' + sys.argv[1] + '\' is not a MAC address with AA:BB:CC:DD:EE:FF format. Exiting.'
      sys.exit(1)
      
  elif len(sys.argv) == 1:
    
    if os.getuid() != 0:
      
      print '+ Warning: triggered scan needs root privileges. Restart with \'sudo ' + sys.argv[0] + '\' to get more results.'
    
    try:
      httpHandler().start()
    except:
      print '! Error running HTTP web server on port :8000, exiting.'
      sys.exit(0)
      
    while http_running:  
      machandler=macHandler()
      addr = machandler.getAddresses()
      if len(addr)==0:
	print '! No AP founded while scanning.'
      
      jsons = machandler.getLocation(addr)
      if len(jsons)==0:
	print '! No mapped WiFi MAC address founded in Google API database. Exiting.'
      
      machandler.calcLocation(jsons)
      
      time.sleep(5)
      

  else:
      usage()


if __name__ == "__main__":

  print '+ WiLocate		Version 0.1'
  
  try:
    main()
    while True: 
      time.sleep(100)
  except (KeyboardInterrupt, SystemExit):
    print '\n! Received keyboard interrupt, quitting threads.\n'
    http_running=False
      

