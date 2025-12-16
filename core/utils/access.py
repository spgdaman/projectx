def user_has_access(user):
    if not user.is_authenticated:
        return False
    return user.userprofile.has_access()
