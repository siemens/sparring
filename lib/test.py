import stats

#from pudb import set_trace; set_trace()

s = stats.Stats()
cats = s.categories
#cats['Servers'] = [ ('192.168.1.2', 80, '') ]
#cats['Servers'] += [ ('134.34.166.66', 80, '192.168.1.100:3128') ]
cats['Servers'] = {}
cats['Servers']['192.168.1.2'] = [ 80, False]
cats['Filez'] = {}
cats['Filez']['EXE'] = 'foobar.exe'

print s
