#!/usr/bin/env python

from subprocess import Popen, PIPE, STDOUT
import re, httplib, urllib, json, os, sys, time, pprint,math, stat
import threading, SimpleHTTPServer, SocketServer, socket, webbrowser, privilege

#sudo tcpdump -i mon0 -s 0 -e link[25] != 0x80
#sudo aa-complain /usr/sbin/tcpdump  

# sincronizzare data.json_map

http_running=False


def touch(p): 
  open(p,'w').close() 

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
  http_running = False
  
  if data.f and not data.f.closed:
      data.f.close()
      
  if data.lock and data.lock.locked():
    data.lock.release()
  
  sys.exit(r)

class dataHandler:
  json_map={}
  f=None
  lock=None
  
  def __init__(self):
    pass
  
  def openfile(self):
    
    dirr = 'log'
    if not os.path.exists(dirr):
      run_as_user(os.makedirs,dirr)
    
    i=0
    tm = time.strftime("%d-%b-%Y", time.gmtime())
    
    path = 'log/' +  tm + '-' + str(i) + '.log' 
    while(os.path.exists(path)):
      i+=1
      path = 'log/' +  tm + '-' + str(i) + '.log' 
    
    run_as_user(touch,path)
    
    created=False
    for i in range(10):
      if not os.path.exists(path):
	time.sleep(1)
      else:
	created=True
	break

    if not created:
      print '+ Error creating', path, 'with dropped privileges.'

    print '+ Saving AP datas in', path 
    self.f = open(path,'w')
      
    self.lock = threading.Lock()
    
  def pprint(self,j,m):
    
    blockprint=''
    
    if 'reliable' in j:
      blockprint += '+ ' 
    else:
      blockprint += '- ' 
    
    blockprint += m + ' ' + j['essid'] + ' (' + str(j['latitude']) + ',' + str(j['longitude']) + ') ' 
  
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
    self.lock.acquire()
    toret = json_map.copy()
    self.lock.release()
    return toret
    
  
  def insert(self,jsons):

    blockprint=''

    json_block={}

    print '\n## Snapshot at ' + time.strftime("%d-%b-%Y-%H:%M:%S", time.gmtime()) + ':'
    
    for a in jsons:

      j= jsons[a]
      
      if 'accuracy' in j and 'latitude' in j and 'longitude' in j:
	
	if 'APs' not in json_block:
	  json_block['APs']={}
	  
	json_block['reliable']=0  
	json_block['APs'][a]=j.copy()

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
      if json_block['APs'][f]['accuracy'] < 22000:  
	if json_block['APs'][f]['latitude'] >= media_lat-sd_lat and json_block['APs'][f]['latitude'] <= media_lat+sd_lat:
	  sum_lat+=json_block['APs'][f]['latitude']
	  if json_block['APs'][f]['longitude'] >= media_lng-sd_lng and json_block['APs'][f]['longitude'] <= media_lng+sd_lng:
	    sum_lng+=json_block['APs'][f]['longitude']
	    summ_num+=1
	    json_block['APs'][f]['reliable']=1
    
    for f in json_block['APs']:
      self.pprint(json_block['APs'][f],f)
    
    if summ_num>0 and sum_lat>0 and sum_lng>0:
      print  '+ Position: http://maps.google.it/maps?q=' + str(sum_lat/summ_num) + ',' + str(sum_lng/summ_num)
      
      json_block['position'] = [ sum_lat/summ_num, sum_lng/summ_num ]

      self.lock.acquire()
      self.json_map[timestamp]=json_block
      self.lock.release()

      self.f.write(pprint.pformat(json_block) + '\n')
      self.f.flush()


class StoppableHttpServer (SocketServer.TCPServer):

    def serve_forever (self):
	global http_running
	http_running = True
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
	self.wfile.write(json.dumps(data.json_map))
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
  
   global http_running
   httpd = None
   
   def run ( self ):
    
      global http_running

      try:
	httpd = StoppableHttpServer(('', 8000), httpRequestHandler)
      except Exception, e:
	print '!', e
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

  def getAddresses(self):
    
    newaddr=[]
    
    cmd = 'iwlist scan'
    p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
    
    newaddr = re.findall('Address: ((?:[0-9A-Z][0-9A-Z]:?){6})[\s\S]*?ESSID:"(.*)"', p.stdout.read())
    
    print '* '*(len(newaddr)),
    return newaddr


  def getLocation(self,addr):

    jsons={}

    for a in addr:

      done=False
      
      for r in range(3):
	
	sys.stdout.flush()
	
	params = "{ \"version\": \"1.1.0\", \"host\": \"maps.google.com\", \"request_address\": \"true\", \"address_language\":\"en_GB\", \"wifi_towers\": [ { \"mac_address\": " + a[0].replace(':','-') + ", \"signal_strength\": 8, \"age\": 0 } ] }"
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
	    
	    j['essid']=a[1]
	    jsons[a[0]]=j
	    
	    done=True
	    break
	else:
	  print '.',
	  continue
	
      if not done:
	print '-',

    print ''
    return jsons

data = dataHandler()
machandler=macHandler()

def main():
  
  global http_running,data,machandler

  single=False
  if len(sys.argv) == 2:
    
    if(sys.argv[1]=='--help' or sys.argv[1]=='-h'):
      usage()
      exit(0)
    
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

  data.openfile()

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
  print '+ + If map web page doesn\'t open automatically on your browser, point it to http://localhost:8000'

  while http_running:  
    
    if single is True:
      addr = [sys.argv[1]]  
    else:
      addr = machandler.getAddresses()
      if len(addr)==0:
	print '! No AP founded while scanning.'
    
    jsons = machandler.getLocation(addr)
    if len(jsons)==0:
      print '! No  MAC address founded in Google API database.'
    else:
      data.insert(jsons)
  
    if single is not True:
      time.sleep(5)
    else:
      break



if __name__ == "__main__":

  print '+ WiLocate		Version 0.1'
  
  try:
    main()
  except (KeyboardInterrupt):
    http_running = False
    print '! Quitting in few seconds...\n'
    exit(0)  

