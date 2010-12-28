import unittest
import atomic_charge

try:
    import libtorrent
except ImportError:
    raise ImportError("please install python-libtorrent-rasterbar")

import thread
import time
import os
import tempfile

class SingleFileTest(unittest.TestCase):
    TORRENT = "single.torrent"
    @property
    def torrent(self):
        return os.path.join(os.path.dirname(__file__), self.TORRENT)
    def setUp(self):
        # need to keep reference to session() to prevent GC picking it up
        self.session = session = libtorrent.session()
        session.listen_on(6881, 6882)
        torrent = libtorrent.bdecode(open(self.torrent, 'rb').read())
        info = libtorrent.torrent_info(torrent)
        self.transfer = session.add_torrent(info, tempfile.gettempdir())

    def test_transfer(self):
        thread.start_new_thread(self.charge, ())
        time.sleep(1)
        assert self.transfer.is_seed() \
            or self.transfer.status().state in (3, 4, 5)
                                # downloading, finished, or seeding
        self.transfer.pause()

    def charge(self):
        charger = atomic_charge.Charger(self.torrent,
                os.path.join(os.path.dirname(__file__), "seed", "lorem.txt"),
                                        "localhost", 6881)
        charger.begin()

    def tearDown(self):
        for entry in self.transfer.get_torrent_info().files():
            os.remove(os.path.join(tempfile.gettempdir(), entry.path))

if __name__ == '__main__':
    unittest.main()
