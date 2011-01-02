import unittest
import atomic_charge

try:
    import libtorrent
except ImportError:
    raise ImportError("please install python-libtorrent-rasterbar")

import threading
import time
import os
import tempfile

class SingleFileTest2(unittest.TestCase):
    TORRENT = "single2.torrent"
    TIMEOUT = 30
    STEP = 1
    @property
    def torrent(self):
        return os.path.join(os.path.dirname(__file__), self.TORRENT)
    def setUp(self):
        # need to keep reference to session() to prevent GC picking it up
        self.session = session = libtorrent.session()
        session.listen_on(6883, 6884)
        torrent = libtorrent.bdecode(open(self.torrent, 'rb').read())
        info = libtorrent.torrent_info(torrent)
        self.transfer = session.add_torrent(info, tempfile.gettempdir())

    def test_transfer(self):
        charge_func = self.charge
        class ChargeThread(threading.Thread):
            def run(self):
                charge_func()
        ChargeThread().run()
        timeout = self.TIMEOUT
        while timeout > 0:
            if self.transfer.is_seed() \
                    or self.transfer.status().state in (4, 5):
                break
            timeout -= self.STEP
            time.sleep(self.STEP)

        assert self.transfer.is_seed() \
            or self.transfer.status().state in (4, 5)
                                # downloading, finished, or seeding
        self.transfer.pause()

    def charge(self):
        charger = atomic_charge.Charger(self.torrent,
                os.path.join(os.path.dirname(__file__), "seed", "lorem2.txt"),
                                        "localhost", self.session.listen_port())
        charger.begin()

    def tearDown(self):
        for entry in self.transfer.get_torrent_info().files():
            os.remove(os.path.join(tempfile.gettempdir(), entry.path))
        del self.session


if __name__ == '__main__':
    unittest.main()
