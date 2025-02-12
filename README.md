# Nintendo Clients
Python package to communicate with Nintendo servers

To import this into your code, run `python setup.py install` or place the `nintendo` folder somewhere Python can find it.

You might need to adjust your scripts if you pull new commits from this package (it may receive backwards compatibility breaking changes at any time).

### Documentation
https://github.com/Kinnay/NintendoClients/wiki

### Requirements
* Python 3 (tested with 3.6.4)
* Python requests (http://docs.python-requests.org)
* BeautifulSoup4 and lxml
* For `nintendo.pia.lan`:
    * PyCryptodome
    * netifaces

### Example scripts
| Name | Platform | Description |
| --- | --- | --- |
| example_donkeykong.py | Wii U | Downloads DKC Tropical Freeze rankings and the replay file of the world record. |
| example_mariokart.py | Wii U | Downloads Mario Kart 8 rankings and the replay file of whoever is in 500th place. |
| example_miis.py | Wii U | Requests all kinds of information about the primary mii associated with a NNID. |
| example_friend_list.py | Wii U | Requests your friend list, incoming and outgoing friend requests, and blacklist. |
| example_friend_notifications.py | Wii U | Listens for friend notifications (a friend starting a game for example). |
| example_createroom.py | Wii U | Shows how to create a friend room in Mario Kart 8. You'll get an error if you try to join it on a real Wii U though, because this package doesn't support P2P connections yet. |
| example_mariokartdeluxe.py | Switch | Downloads Mario Kart 8 Deluxe rankings. This script logs in as guest, so you don't need to dump any keys or other information from your Switch. |
| example_lan_mode.py | Switch | Searches for a Splatoon 2 LAN session and prints information about it. |
| example_server.py | Custom | Shows how to create a simple game server with both an authentication server and a secure server. |
| example_server_login.py | Custom | Logs in on a game server and disconnects immediately. This can be used to test custom servers (such as example_server.py). |
