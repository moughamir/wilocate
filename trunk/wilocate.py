#!/usr/bin/env python

from subprocess import Popen, PIPE, STDOUT
import re, httplib, urllib, json, os, sys
from itertools import groupby

print '+ WiLocator		Version 0.1'


if len(sys.argv) == 2:
  
  if not re.match("(?:[0-9A-Z][0-9A-Z](:|-)?){6}", sys.argv[1]):
    print '! Error: \'' + sys.argv[1] + '\' is not a MAC address with AA:BB:CC:DD:EE:FF format. Exiting.'
    sys.exit(1)
    
  addr = [ sys.argv[1] ]

elif len(sys.argv) == 1:
  cmd = 'iwlist scan'
  p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
  rawaddr = re.findall('Address: ((?:[0-9A-Z][0-9A-Z]:?){6})', p.stdout.read())
  addr = [ a.replace(':','-') for a in rawaddr]

else:
  print '+ Usage:\n+ ' + sys.argv[0] + '\t\tLocate actual position using WiFi scanning\n+ ' + sys.argv[0] + ' <MAC address>\t\tLocate given MAC address position'
  sys.exit(0)


if os.getuid() != 0:
  print '! Warning: triggered scans needs high privileges. Execute as root to get more accurate results.'

jsons=[]

for a in addr:

  params = "{ \"version\": \"1.1.0\", \"host\": \"maps.google.com\", \"request_address\": \"true\", \"address_language\":\"en_GB\", \"wifi_towers\": [ { \"mac_address\": " + a.replace(':','-') + ", \"signal_strength\": 8, \"age\": 0 } ] }"
  headers = { "Pragma" : "no-cache", "Cache-control" : "no-cache" }
  conn = httplib.HTTPConnection("www.google.com:80")
  conn.request("POST", "/loc/json", params, headers)
  response = conn.getresponse()
  j = json.loads(response.read())
  j['mac_address']=a
  jsons.append(j)

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
      print '                  http://maps.google.it/maps?q=' + str(longitude) + ',' + str(latitude)