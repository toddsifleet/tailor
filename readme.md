Tailor
=============

A simple way to tail and combine the output of multiple logs.  The logs can be local or on server[s] you have ssh access to.

Features
-------

-Tail multiple files locally or remotely

-Tail the same file across multiple servers

-Combine and color code the output into one terminal


Installation
-------

git clone https://github.com/toddsifleet/tailor.git

Usage
-------

To tail local files:

    python tailor/main.py file_1_to_tail,file_2_to_tail

To tail remote files:

    python tailor/main.py file_1_to_tail,file_2_to_tail bob@barker.com

To tail remote files on multiple servers:

    python tailor/main.py file_1_to_tail,file_2_to_tail bob@barker.com,drew@carey.com

Note
-------

For ssh access you must be using public key auth, and have already connected to the server before.  I did not add any authentication functionality.

License:
-------

See LICENSE