#!/usr/bin/env python

from subprocess import Popen, PIPE, STDOUT
import re, httplib, urllib, json, os, sys, time, pprint,math, stat
import threading, SimpleHTTPServer, SocketServer, socket, webbrowser, privilege

#sudo tcpdump -i mon0 -s 0 -e link[25] != 0x80
#sudo aa-complain /usr/sbin/tcpdump  


http_running=False


def touch(files): 
  for f in files:
    open(f,'w').close() 

def run_as_user(function, *args):
  pid = os.fork() 
  if pid == 0: # son
    #print os.getuid(), os.getgid(), privilege.getresuid(), privilege.getresgid()
    if os.geteuid() == 0:
	useruid=int(os.getenv("SUDO_UID")) 
	usergid=int(os.getenv("SUDO_GID"))
	if usergid and useruid:
	  privilege.drop_privileges_permanently(useruid, usergid, [1])
	  function( *args )
    else:
      function( *args )
      
    #print os.getuid(), os.getgid(), privilege.getresuid(), privilege.getresgid()
    sys.exit(0)

#print 'root', os.getuid(), os.getgid()
  
def standard_deviation(sequence):
  med = sum(sequence) / len(sequence)
  variance = sum([(x-med)**2 for x in sequence]) / len(sequence)
  return math.sqrt(variance)
    

def exit(r=0):
  global http_running
  
  http_running = False
  print '! Quitting.\n'
      
  jsondata.close()    
  #if jsondata.flocation and not jsondata.flocation.closed:
      #jsondata.flocation.close()

  #if jsondata.fwifi and not jsondata.fwifi.closed:
      #jsondata.fwifi.close()

  #if jsondata.locklocation and jsondata.locklocation.locked():
    #jsondata.locklocation.release()
  
  #if jsondata.lockwifi and jsondata.lockwifi.locked():
    #jsondata.lockwifi.release()
  
  urllib.urlopen('http://localhost:8000/')
  
  sys.exit(r)

class jsondataHandler:
  locations={}
  wifis={}
  
  flocation=None
  fwifi=None
  locklocation=None
  lockwifi=None
  
  def __init__(self):
    pass
  
  def close(self):
    
    if self.flocation:
      self.flocation.close()
    if self.fwifi:
      self.fwifi.close()
    if self.lockwifi and self.lockwifi.locked():
      self.lockwifi.release()
    if self.lockwifi and self.lockwifi.locked():
      self.lockwifi.release()
    
  def openfile(self):
    
    dirr = 'log'
    if not os.path.exists(dirr):
      run_as_user(os.makedirs,dirr)
    
    i=0
    tm = time.strftime("%d-%b-%Y", time.gmtime())
    
    path = 'log/' +  tm + '-' + str(i)
    while os.path.exists(path + '.loc') and os.path.exists(path + '.wifi'):
      i+=1
      path = 'log/' +  tm + '-' + str(i)
      
    run_as_user(touch, [ path + '.loc', path + '.wifi'])
    
    created=False
    for i in range(10):
      if not os.path.exists(path + '.loc') and os.path.exists(path + '.wifi'):
	time.sleep(1)
      else:
	created=True
	break

    if not created:
      print '+ Error creating', path, 'with dropped privileges.'

    print '+ Saving AP datas in', path 
    self.flocation = open(path,'w')
      
    self.locklocation = threading.Lock()
    self.lockwifi = threading.Lock()
    
  def pprint(self,j,m):
    
    blockprint=''
    
    if 'reliable' in j:
      blockprint += '+ ' 
    else:
      blockprint += '- ' 
    
    blockprint += m + ' '
    if 'ESSID' in self.wifis[m]:
      blockprint += self.wifis[m]['ESSID'] 
    
    if 'latitude' and 'longitude':
      blockprint += ' (' + str(j['latitude']) + ',' + str(j['longitude']) + ') ' 
  
    if 'address' in j:
      if 'country' in j['address']:
	blockprint += j['address']['country'] + ' ' 
	
      if 'country_code' in j['address']:
	blockprint +=  '(' + j['address']['country_code'] + ') '
	
      if 'region' in j['address']:
	blockprint +=  j['address']['region'] + ' '

      if 'postal_code' in j['address']:
	blockprint +=  j['address']['postal_code'] + ' '

      if 'county' in j['address']:
	county = j['address']['county'] + ' '
	      
      if 'city' in j['address']:
	city = j['address']['city'] + ' '

      if county != city:
	blockprint +=  city + ' ' + county + ' '
      elif not city:
	blockprint +=  county + ' '
      else:
	blockprint +=  city + ' '

      if 'street' in j['address']:
	blockprint +=  j['address']['street'] + ' '

      if 'street_number' in j['address']:
	blockprint +=  j['address']['street_number'] + ' '
	
  
      blockprint += '(' + str(j['accuracy']) + ') '
       
    print blockprint
      

  def extract(self):
    self.locklocation.acquire()
    toret = locations.copy()
    self.locklocation.release()
    return toret
    
  
  def insertLocation(self,aps,jsons):

    blockprint=''
    json_block={}

    print '+ + + Snapshot at ' + time.strftime("%d-%b-%Y-%H:%M:%S", time.gmtime()) + ':'
    
    l = len(self.wifis)
    self.wifis.update(aps)
    diff = len(self.wifis)-l
    if diff>0:
      print '+ New', str(diff), 'Access Points', '(' + str(len(self.wifis)) + ')'
    
    for loc in jsons:

      j= jsons[loc]
      
      if 'accuracy' in j and 'latitude' in j and 'longitude' in j:
	
	if 'APs' not in json_block:
	  json_block['APs']={}
	  
	json_block['reliable']=0 
	json_block['APs'][loc]=j.copy()

    timestamp = int(time.time())  
    tot_lat=[]
    tot_lng=[]
    
    
    for f in json_block['APs']:
      tot_lat.append(json_block['APs'][f]['latitude'])
      tot_lng.append(json_block['APs'][f]['longitude'])
    
    sd_lat=standard_deviation(tot_lat)*1.1
    sd_lng=standard_deviation(tot_lng)*1.1
    media_lat = sum(tot_lat) / len(tot_lat)
    media_lng = sum(tot_lng) / len(tot_lng)
    
    sum_lat=0
    sum_lng=0
    summ_num=0
    for f in json_block['APs']:
	if json_block['APs'][f]['latitude'] >= media_lat-sd_lat and json_block['APs'][f]['latitude'] <= media_lat+sd_lat:
	  sum_lat+=json_block['APs'][f]['latitude']
	  if json_block['APs'][f]['longitude'] >= media_lng-sd_lng and json_block['APs'][f]['longitude'] <= media_lng+sd_lng:
	    sum_lng+=json_block['APs'][f]['longitude']
	    summ_num+=1
	    json_block['APs'][f]['reliable']=1
	    
	
	if json_block['APs'][f]['accuracy'] > 22000:  
	  print 'Ho rifiutato', f, 'con', json_block['APs'][f]['accuracy']
	  reliable=0
    
    for f in json_block['APs']:
      self.pprint(json_block['APs'][f],f)
    
    if summ_num>0 and sum_lat>0 and sum_lng>0:
      print  '+ Position: http://maps.google.it/maps?q=' + str(sum_lat/summ_num) + ',' + str(sum_lng/summ_num)
      
      json_block['position'] = [ sum_lat/summ_num, sum_lng/summ_num ]

      self.locklocation.acquire()
      self.locations[timestamp]=json_block
      self.locklocation.release()

      self.flocation.write(pprint.pformat(json_block) + '\n')
      self.flocation.flush()


class StoppableHttpServer (SocketServer.TCPServer):

    def serve_forever (self):
	global http_running
        while http_running:
            self.handle_request()
            
    
class httpRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
   
   
  def log_request(self, code='-', size='-'):
    pass
  
  def do_GET(self):
    try:
      if self.path.endswith(".json"):

	self.send_response(200)
	self.send_header('Content-type','application/x-javascript')
	self.end_headers()
	
	merged={ 'locations' : jsondata.locations, 'wifi' : jsondata.wifis }
	
	self.wfile.write(json.dumps(merged))
	return
	
      elif self.path=='/' or self.path.endswith(".html"):
	f = open(os.curdir + os.sep + 'html' + os.sep + 'wilocate.html')
	self.send_response(200)
	self.send_header('Content-type','text/html')
	self.end_headers()
	self.wfile.write(f.read())
	f.close()
	return
	
      elif self.path.endswith(".png"):
	f = open(os.curdir + os.sep + 'html' + self.path) 
	
	self.send_response(200)
	self.send_header('Content-type','image/png')
	self.end_headers()
	self.wfile.write(f.read())
	f.close()
	return

    except IOError:
      self.send_error(404, 'File not found: %s' % self.path)
      
    #return SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)

class httpHandler ( threading.Thread ):
  
   httpd = None
   
   def run ( self ):
    
      global http_running

      try:
	httpd = StoppableHttpServer(('', 8000), httpRequestHandler)
      except Exception, e:
	print '! Error running HTTP server', e
	http_running=False
      else:
	http_running=True
	sa = httpd.socket.getsockname()
	print "+ Running HTTP server on", sa[0], "port", sa[1], "..."
	httpd.serve_forever()
	

def usage():
  print '\n  Usage:\n\n' + sys.argv[0] + '\t\t\tLocate actual position using WiFi scanning\n' + sys.argv[0] + ' <MAC address>\tLocate given MAC address position\n' + sys.argv[0] + ' --help|-h\t\tThis help\n\n  Progress symbols:\n\n* new wifi AP detected\n. incomplete geographic data returned, retry\n+ complete geographic data returned\n- geographic data request failed, skipping address\n! connection error, retry'

class macHandler:
  
  def __init__(self):
    pass

  def getScan(self):
	
    data = {}
    lastcell=''
    lastauth=''

    cmd = 'iwlist scan'
    pop = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)

    for l in pop.stdout.read().split('\n'):
      p = l.strip()
      spa = [x.strip() for x in p.split(' ')]
      sp = [x.strip(':') for x in spa]
      
      # If Cell i create new key with mac address
      if sp[0] == 'Cell' and sp[3] == 'Address':
	lastcell=sp[4]
	data[lastcell]={}
	
      elif sp[0].startswith('Channel') or sp[0].startswith('Frequency') or sp[0].startswith('Mode') or sp[0].startswith('ESSID'):
	splitted = sp[0].split(':') + sp[1:]
	data[lastcell][splitted[0]]=splitted[1].strip('"') # For ESSID
	#append
	if sp[0].startswith('Frequency') and len(splitted)==5 and splitted[3]=='(Channel':
	  data[lastcell][splitted[0]]+=splitted[2]
	  data[lastcell]['Channel']=splitted[4][0]
      elif sp[0].startswith('Quality') and sp[2] == 'Signal':
	if '=' in sp[0] and len(sp[0])==2:
	  quality = sp[0].split('=')[1]
	  data[lastcell]['Quality'] = quality
	if '=' in sp[3] and len(sp[0])==4:
	  level = sp[3].split('=')[1]
	  data[lastcell]['Level'] = level
      elif sp[0] == 'Encryption' and sp[1].startswith('key'):
	if sp[1].split(':')[1] == 'on':
	  if 'Encryption' not in data[lastcell]:
	    data[lastcell]['Encryption']= {}
	    
	    #Traceback (most recent call last):
	    #File "wilocate.py", line 486, in <module>
	      #main()
	    #File "wilocate.py", line 464, in main
	      #aps = machandler.getScan()
	    #File "wilocate.py", line 348, in getScan
	      #data[lastcell]['Encryption'][lastauth][sp[0]]=value
	  #KeyError: 'WPA Version 1'

      elif sp[0] == 'IE' and sp[1] != 'Unknown':
	lastauth=' '.join(sp[1:])
	if 'Encryption' not in data[lastcell]:
	  data[lastcell]['Encryption']= {}
	data[lastcell]['Encryption'][lastauth]={}
      elif sp[0] == 'Group' or sp[0] == 'Pairwise' or sp[0] == 'Authentication':
	# The separator is '' (void array slot), because i stripped out :
	value=''
	if '' in sp:
	  where = sp.index('')
	  value=' '.join(sp[where:]).strip()
	
	if 'Encryption' not in data[lastcell]:
	  data[lastcell]['Encryption']= {}
	data[lastcell]['Encryption'][lastauth][sp[0]]=value
	
    return data

  #def getAddresses(self):
    
    #newaddr=[]
    
    #cmd = 'iwlist scan'
    #p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
    
    #newaddr = re.findall('Address: ((?:[0-9A-Z][0-9A-Z]:?){6})[\s\S]*?ESSID:"(.*)"', p.stdout.read())
    
    #print '* '*(len(newaddr)),
    #return newaddr


  def getLocation(self,addr):

    jsons={}

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
	  print '! Error querying Google for',a, e
	  continue
	
	try:
	  j = json.loads(response.read())
	except ValueError, e:
	  print '! Error decoding JSON:', e
	  continue
	
	if 'location' in j:
	  j = j['location'].copy()
	  if 'address' in j:
	    print '+',
	    
	    jsons[a]=j
	    
	    done=True
	    break
	else:
	  print '.',
	  continue
	
      if not done:
	print '-',

    print ''
    return jsons

jsondata = jsondataHandler()
machandler=macHandler()

def main():
  
  global http_running,jsondata,machandler

  single=False
  if len(sys.argv) == 2:
    
    if(sys.argv[1]=='--help' or sys.argv[1]=='-h'):
      usage()
      jsondata.exit(0)
    
    elif not re.match("(?:[0-9A-Z][0-9A-Z](:|-)?){6}", sys.argv[1]):
      print '! Error: \'' + sys.argv[1] + '\' is not a MAC address with AA:BB:CC:DD:EE:FF format. Exiting.'
      exit(1)
  
    single=True
      
  elif len(sys.argv) == 1:
    
    if os.getuid() != 0:
      
      print '+ Warning: triggered scan needs root privileges. Restart with \'sudo ' + sys.argv[0] + '\' to get more results.'

  else:
      usage()
      exit(0)

  jsondata.openfile()

  try:
    httpHandler().start()
  except Exception, e:
    print '! Error running HTTP thread. Quitting.'
    http_running=False
    exit(0)
  
  time.sleep(1)
  if not http_running:
    print '! Error opening HTTP server.'
    exit(0)

  run_as_user(webbrowser.open,'http://localhost:8000')
  print '+ + + If map web page doesn\'t open automatically on your browser, point it to http://localhost:8000'

  while http_running:  
    
    if single is True:
      aps = { sys.argv[1] : {} }  
    else:
      aps = machandler.getScan()
      if len(aps)==0:
	print '! No AP founded while scanning.'
    
    locs = machandler.getLocation(aps.keys())
    if len(locs)==0:
      print '! No  MAC address founded in Google API database.'
    else:
      jsondata.insertLocation(aps,locs)
  
    if single is True:
      break
    time.sleep(5)
    


if __name__ == "__main__":

  print '+ WiLocate		Version 0.1'
  
  try:
    main()
  except (KeyboardInterrupt):
    exit(0)  
  except (SystemExit):
    sys.exit(0)

