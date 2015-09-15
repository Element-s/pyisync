#Pyisync
pyinotofy+rsync for real-time sync files

* License          : MIT
* Project URL      : [https://github.com/Element-s/pyisync](http://github.com/Element-s/pyisync)

##Dependencies

* Linux ≥ 2.6.13
* Python ≥ 2.4
* Pyinotify
* rsync

##Watch a directory
#Just unzip and do:
Modify sync_list.xml in syncconf directory, add your watch directories or files.

##Installation Instructions

#To start pyisync there is NO NEED to install it. Just  do:

#start server:
python isync.py --type server --host 192.168.1.2
#start client:
python isync.py --type client --host 192.168.1.1

That's it!!!






