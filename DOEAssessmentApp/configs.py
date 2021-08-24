import sys
import os
import konfig

_HERE = os.path.dirname(__file__)

_SETTINGS_FILE = os.path.join(_HERE, 'settings.ini')

CONFS = konfig.Config(_SETTINGS_FILE)

if sys.platform == 'linux':
    db_settings_map = CONFS.get_map('dbforlinux')

elif sys.platform == 'win32':
    db_settings_map = CONFS.get_map('dbforwin32')

elif sys.platform == 'darwin':
    db_settings_map = CONFS.get_map('dbformac')
else:
    db_settings_map = CONFS.get_map('default')

email_settings_map = CONFS.get_map('emailtriggercredentials')
licensing_limitations_map = CONFS.get_map('licensinglimitations')
dev_configs_from_file = [db_settings_map, email_settings_map, licensing_limitations_map]
