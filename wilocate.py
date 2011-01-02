#!/usr/bin/env python

from subprocess import Popen, PIPE, STDOUT
import re, httplib, urllib, json, os, sys

def usage():
  print '\n  Usage:\n\n' + sys.argv[0] + '\t\t\tLocate actual position using WiFi scanning\n' + sys.argv[0] + ' <MAC address>\tLocate given MAC address position\n' + sys.argv[0] + ' --help|-h\t\tThis help\n\n  Progress symbols:\n\n* new wifi AP detected\n. incomplete geographic data returned, retry\n+ complete geographic data returned\n- geographic data request failed, skipping address\n! connection error, retry'

print '+ WiLocate		Version 0.1'


addr=[]

if len(sys.argv) == 2:
  
  if(sys.argv[1]=='--help' or sys.argv[1]=='-h'):
    usage()
    sys.exit(0)
  
  elif not re.match("(?:[0-9A-Z][0-9A-Z](:|-)?){6}", sys.argv[1]):
    print '! Error: \'' + sys.argv[1] + '\' is not a MAC address with AA:BB:CC:DD:EE:FF format. Exiting.'
    sys.exit(1)
    
  addr = [ sys.argv[1] ]

elif len(sys.argv) == 1:
  
  if os.getuid() != 0:
    print '+ Warning: triggered scan needs root privileges. Restart with \'sudo ' + sys.argv[0] + '\' to get more results.'


  for i in range(3):
    newaddr=[]
    
    cmd = 'iwlist scan'
    p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
    newaddr = re.findall('Address: ((?:[0-9A-Z][0-9A-Z]:?){6})', p.stdout.read())
    
    if len(set(addr + newaddr)) > len(addr):
      print '* '*(len(set(addr + newaddr))-len(addr)),
    
    addr = list(set(addr + newaddr))
    
    sys.stdout.flush()

else:
  usage()
  sys.exit(0)


if len(addr)==0:
  print '! No AP founded while scanning. Exiting.'
  sys.exit(0)

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

if len(jsons)==0:
  print '! No mapped WiFi MAC address founded in Google API database. Exiting.'
  sys.exit(0)

jsons.sort(key=lambda j: j['location']['accuracy'], reverse=True)

for j in jsons:

  latitude=longitude=0.0
  
  print ''
  
  if 'mac_address' in j:
    print j['mac_address'],

  if 'location' in j:
    if 'accuracy' in j['location']:
      print '(accuracy: ' + str(j['location']['accuracy']) + ')', 
    
    if 'latitude' in j['location']:
	latitude = j['location']['latitude']
    
    if 'longitude' in j['location']:
	longitude = j['location']['longitude']
	
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
	
      print ''
      print '                  http://maps.google.it/maps?q=' + str(latitude) + ',' + str(longitude)
