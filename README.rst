Atomic Charge
=============

**Atomic Charge** is a seeding-only BitTorrent client.

The torrent protocol is designed to negotiate peers for file transfer (via
trackers or DHT) dynamically.   This guarantees a fair distribution of the
pieces among *all* peers.  Atomic Charge sends to a single peer *exclusively.*

Say you have downloaded a file from a torrent and want a friend of yours to
receive it too.  Instead of initiating a direct connection to your friend you
can augment her torrent download -- and *hers only.*  Thereby she will fetch
the file from your uplink *and* the swarm.  All you need for this to work is a
common torrent file, its finished files, your friend's IP and her listening
port.

The unfair game resulting from this behaviour stems directly from a flaw in the
torrent protocol:  peers announce their download status to other peers in a
private connection.  The swarm does not necessarily receive full, let alone
consistent, data;  clients accept pieces (parts of a file) from any interesting
peer.  The peer to peer nature of the torrent protocol allows you to
communicate with a single peer *only* if you chose so.
