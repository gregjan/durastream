# Settings
The default configuration is in default_config.py. Instead of
modifying that file directly, here is the preferred way to configure:

1. Make your own copy of the file someplace safely outside of the application, like /etc/durastream_config.py.
+ Modify that file as needed.
+ Add that file to your CM tool, if applicable.
+ Set the "DURASTREAM_SETTINGS" environment variable to the location of the new file.

    export DURASTREAM_SETTINGS=/etc/durastream_config.py
