def get_request_company(user):
    """Resolve the tenant (Company) a request is acting on behalf of."""
    if user is None or not getattr(user, 'is_authenticated', False):
        return None
    admin = getattr(user, 'admin', None)
    if admin is not None:
        return admin.company
    worker = getattr(user, 'worker', None)
    if worker is not None:
        return worker.admin.company
    return None
