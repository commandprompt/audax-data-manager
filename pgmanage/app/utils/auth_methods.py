"""How a database connection authenticates."""


def uses_iam_auth(credentials_extra) -> bool:
    """
    Tells if a connection authenticates with an IAM token.

    The AWS region is necessary to sign a token and it is not a secret, thus it
    stays readable and shows that IAM is configured.
    """
    if not credentials_extra:
        return False
    return bool(credentials_extra.get("aws_region"))
