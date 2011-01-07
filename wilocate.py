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

	
	print json_map
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
    
      
      http_timeout = 30
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
	  print '!', 
	  continue
	
	j = json.loads(response.read())
	
	if not ('location' in j and 'address' in j['location']):
	  print '.',
	  continue
	else:
	  print '+',
	  j['mac_address']=a
	  jsons.append(j)
	  done=True
	  break
      
      if not done:
	print '-',

    print ''

    jsons.sort(key=lambda j: j['location']['accuracy'], reverse=True)
    return jsons


  def calcLocation(self,jsons):

    weightedsumm=[0.0,0.0]
    summ=[0.0,0.0]
    summweight=0
    numlocated=0

    for j in jsons:

      latitude=0
      longitude=0

      print ''
      
      if 'mac_address' in j:
	print j['mac_address'],

      if 'location' in j:
	
	
	numlocated=numlocated+1
	
	if 'accuracy' in j['location']:
	  weight = j['location']['accuracy']
	  summweight = summweight + weight

	  print '(accuracy: ' + str(j['location']['accuracy']) + ')', 
	
	if 'latitude' in j['location']:
	    latitude = j['location']['latitude']
	    summ[0]=summ[0]+j['location']['latitude']
	    weightedsumm[0]=weightedsumm[0]+j['location']['latitude']*weight

	
	if 'longitude' in j['location']:
	    longitude = j['location']['longitude']
	    summ[1]=summ[1]+j['location']['longitude']
	    weightedsumm[1]=weightedsumm[1]+j['location']['longitude']*weight
	    
	if 'address' in j['location']:
	  
	  if 'country' in j['location']['address']:
	    print j['location']['address']['country'],
	    
	  if 'country_code' in j['location']['address']:
	    print '(' + j['location']['address']['country_code'] + ')',
	    
	  if 'region' in j['location']['address']:
	    print j['location']['address']['region'],

	  if 'postal_code' in j['location']['address']:
	    print j['location']['address']['postal_code'],

	  if 'county' in j['location']['address']:
	    county = j['location']['address']['county']
		  
	  if 'city' in j['location']['address']:
	    city = j['location']['address']['city']

	  if county != city:
	    print city, county,
	  elif not city:
	    print county,
	  else:
	    print city, 


	  if 'street' in j['location']['address']:
	    print j['location']['address']['street'],

	  if 'street_number' in j['location']['address']:
	    print j['location']['address']['street_number'],
	    
	  print '                  http://maps.google.it/maps?q=' + str(latitude) + ',' + str(longitude)

	if 'mac_addresses' not in json_map:
	  json_map['mac_addresses']={}
	if j['mac_address'] not in json_map['mac_addresses']:
	  json_map['mac_addresses'][j['mac_address']]=[ latitude, longitude ]
	  
	 
    if numlocated>0 and weightedsumm>0:
      print '\nPoint: http://maps.google.it/maps?q=' + str(summ[0]/numlocated) + ',' + str(summ[1]/numlocated)
      
      if 'actual_position' not in json_map:
	json_map['actual_position'] = [ summ[0]/numlocated, summ[1]/numlocated ]
      
      print 'AAAAAAAAAA', str(len(json_map))
      #print '\nWeighted average: http://maps.google.it/maps?q=' + str(weightedsumm[0]/summweight) + ',' + str(weightedsumm[1]/summweight)

    for j in jsons:
      print str(j['location']['latitude']) + ',' + str(j['location']['longitude'])
      

  

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
      
      time.sleep(10)
      

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
      

