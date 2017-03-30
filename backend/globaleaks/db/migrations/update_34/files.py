# -*- coding: utf-8 -*-
# Included here to archive File model based function calls used in migration 34

import base64

from storm.locals import Unicode, Storm

from globaleaks.utils.utility import uuid4


class File_v_36(Storm):
    """
    Class used for storing files
    """
    id = Unicode(primary=True, default_factory=uuid4)

    data = Unicode()


def db_add_file(store, data, key = None):
    file_obj = None
    if key is not None:
        file_obj = store.find(File_v_36, File_v_36.id == key).one()

    if file_obj is None:
        file_obj = File_v_36()
        if key is not None:
            file_obj.id = key
        store.add(file_obj)

    file_obj.data = base64.b64encode(data)


def db_get_file(store, key):
    file_obj = store.find(File_v_36, File_v_36.id == key).one()

    if file_obj is None:
        return ''

    return file_obj.data
