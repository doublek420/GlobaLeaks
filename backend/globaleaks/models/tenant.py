from storm.locals import Bool, Int, Reference, ReferenceSet, Unicode, Storm, JSON

from globaleaks.models import Model, ShortURL
from globaleaks.models.validators import shorttext_v
from globaleaks.utils.utility import log


class Tenant(Model):
    """
    Class used to implement multi tenancy.
    """
    id = Int(primary=True) # TODO Note may become text again
    label = Unicode(validator=shorttext_v)

    unicode_keys = ['label']


def db_create_tenant(store, desc, use_single_lang=False):
    # NOTE Invalidates memory_var cache but does not refresh it
    tenant = Tenant(desc)
    store.add(tenant)
    store.commit()

    log.debug("Creating tenant:%d" % tenant.id)

    # Note an example of a tenant resource
    sh = ShortURL({'shorturl':'/s/exampleres', 'longurl':'/exampleres'})
    sh.tid = tenant.id
    store.add(sh)

    return tenant


def db_get_tenant_list(store):
    return store.find(Tenant)


def db_delete_tenant(store, tenant_id):
    tenant = store.find(Tenant, Tenant.id == tenant_id).one()
    if tenant is not None:
        store.remove(tenant)
