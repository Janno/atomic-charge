import atomic_charge
import libtorrent
import unittest
import thread
import time
import os

class SingleFileTest(unittest.TestCase):
    def setUp(self):
        # need to keep reference to session() to prevent GC picking it up
        self.session = session = libtorrent.session()
        session.listen_on(6881, 6882)
        torrent = libtorrent.bdecode(open("single.torrent", 'rb').read())
        info = libtorrent.torrent_info(torrent)
        self.transfer = session.add_torrent(info, "/tmp")

    def test_transfer(self):
        thread.start_new_thread(self.charge, ())
        time.sleep(1)
        assert self.transfer.is_seed() \
            or self.transfer.status().state in (3, 4, 5)
                                # downloading, finished, or seeding

    def charge(self):
        charger = atomic_charge.Charger("single.torrent", "./seed/lorem.txt",
                                        "localhost", 6881)
        charger.begin()

    def tearDown(self):
        try:
            os.remove("/tmp/lorem.txt")
        except OSError:
            pass # we did not finish at all?


#states = ('queued', 'checking', 'downloading metadata',
#          'downloading', 'finished', 'seeding', 'allocating')
#while not transfer.is_seed():
#        s = transfer.status()
#        print '%.2f%%, % 2d peers (%s)' % (
#            s.progress * 100, s.num_peers, states[s.state])
if __name__ == '__main__':
    unittest.main()
