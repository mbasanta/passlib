"""passlib.handlers.digests - plain hash digests
"""
#=============================================================================
# imports
#=============================================================================
# core
from base64 import b64encode, b64decode
from hashlib import md5, sha1
import logging; log = logging.getLogger(__name__)
import re
from warnings import warn
# site
# pkg
from passlib.handlers.misc import plaintext
from passlib.utils import to_native_str, unix_crypt_schemes, \
                          classproperty, to_unicode
from passlib.utils.compat import b, bytes, uascii_to_str, unicode, u
import passlib.utils.handlers as uh
# local
__all__ = [
    "ldap_plaintext",
    "ldap_md5",
    "ldap_sha1",
    "ldap_salted_md5",
    "ldap_salted_sha1",

    ##"get_active_ldap_crypt_schemes",
    "ldap_des_crypt",
    "ldap_bsdi_crypt",
    "ldap_md5_crypt",
    "ldap_sha1_crypt"
    "ldap_bcrypt",
    "ldap_sha256_crypt",
    "ldap_sha512_crypt",
]

#=============================================================================
# ldap helpers
#=============================================================================
class _Base64DigestHelper(uh.StaticHandler):
    """helper for ldap_md5 / ldap_sha1"""
    # XXX: could combine this with hex digests in digests.py

    ident = None # required - prefix identifier
    _hash_func = None # required - hash function
    _hash_regex = None # required - regexp to recognize hash
    checksum_chars = uh.PADDED_BASE64_CHARS

    @classproperty
    def _hash_prefix(cls):
        """tell StaticHandler to strip ident from checksum"""
        return cls.ident

    def _calc_checksum(self, secret):
        if isinstance(secret, unicode):
            secret = secret.encode("utf-8")
        chk = self._hash_func(secret).digest()
        return b64encode(chk).decode("ascii")

class _SaltedBase64DigestHelper(uh.HasRawSalt, uh.HasRawChecksum, uh.GenericHandler):
    """helper for ldap_salted_md5 / ldap_salted_sha1"""
    setting_kwds = ("salt", "salt_size")
    checksum_chars = uh.PADDED_BASE64_CHARS

    ident = None # required - prefix identifier
    checksum_size = None # required
    _hash_func = None # required - hash function
    _hash_regex = None # required - regexp to recognize hash
    _stub_checksum = None # required - default checksum to plug in
    min_salt_size = max_salt_size = 4

    # NOTE: openldap implementation uses 4 byte salt,
    # but it's been reported (issue 30) that some servers use larger salts.
    # the semi-related rfc3112 recommends support for up to 16 byte salts.
    min_salt_size = 4
    default_salt_size = 4
    max_salt_size = 16

    @classmethod
    def from_string(cls, hash):
        hash = to_unicode(hash, "ascii", "hash")
        m = cls._hash_regex.match(hash)
        if not m:
            raise uh.exc.InvalidHashError(cls)
        try:
            data = b64decode(m.group("tmp").encode("ascii"))
        except TypeError:
            raise uh.exc.MalformedHashError(cls)
        cs = cls.checksum_size
        assert cs
        return cls(checksum=data[:cs], salt=data[cs:])

    def to_string(self):
        data = (self.checksum or self._stub_checksum) + self.salt
        hash = self.ident + b64encode(data).decode("ascii")
        return uascii_to_str(hash)

    def _calc_checksum(self, secret):
        if isinstance(secret, unicode):
            secret = secret.encode("utf-8")
        return self._hash_func(secret + self.salt).digest()

#=============================================================================
# implementations
#=============================================================================
class ldap_md5(_Base64DigestHelper):
    """This class stores passwords using LDAP's plain MD5 format, and follows the :ref:`password-hash-api`.

    The :meth:`~passlib.ifc.PasswordHash.encrypt` and :meth:`~passlib.ifc.PasswordHash.genconfig` methods have no optional keywords.
    """
    name = "ldap_md5"
    ident = u("{MD5}")
    _hash_func = md5
    _hash_regex = re.compile(u(r"^\{MD5\}(?P<chk>[+/a-zA-Z0-9]{22}==)$"))

class ldap_sha1(_Base64DigestHelper):
    """This class stores passwords using LDAP's plain SHA1 format, and follows the :ref:`password-hash-api`.

    The :meth:`~passlib.ifc.PasswordHash.encrypt` and :meth:`~passlib.ifc.PasswordHash.genconfig` methods have no optional keywords.
    """
    name = "ldap_sha1"
    ident = u("{SHA}")
    _hash_func = sha1
    _hash_regex = re.compile(u(r"^\{SHA\}(?P<chk>[+/a-zA-Z0-9]{27}=)$"))

class ldap_salted_md5(_SaltedBase64DigestHelper):
    """This class stores passwords using LDAP's salted MD5 format, and follows the :ref:`password-hash-api`.

    It supports a 4-16 byte salt.

    The :meth:`~passlib.ifc.PasswordHash.encrypt` and :meth:`~passlib.ifc.PasswordHash.genconfig` methods accept the following optional keyword:

    :type salt: bytes
    :param salt:
        Optional salt string.
        If not specified, one will be autogenerated (this is recommended).
        If specified, it may be any 4-16 byte string.

    :type salt_size: int
    :param salt_size:
        Optional number of bytes to use when autogenerating new salts.
        Defaults to 4 bytes for compatibility with the LDAP spec,
        but some systems use larger salts, and Passlib supports
        any value between 4-16.

    :type relaxed: bool
    :param relaxed:
        By default, providing an invalid value for one of the other
        keywords will result in a :exc:`ValueError`. If ``relaxed=True``,
        and the error can be corrected, a :exc:`~passlib.exc.PasslibHashWarning`
        will be issued instead. Correctable errors include
        ``salt`` strings that are too long.

        .. versionadded:: 1.6

    .. versionchanged:: 1.6
        This format now supports variable length salts, instead of a fix 4 bytes.
    """
    name = "ldap_salted_md5"
    ident = u("{SMD5}")
    checksum_size = 16
    _hash_func = md5
    _hash_regex = re.compile(u(r"^\{SMD5\}(?P<tmp>[+/a-zA-Z0-9]{27,}={0,2})$"))
    _stub_checksum = b('\x00') * 16

class ldap_salted_sha1(_SaltedBase64DigestHelper):
    """This class stores passwords using LDAP's salted SHA1 format, and follows the :ref:`password-hash-api`.

    It supports a 4-16 byte salt.

    The :meth:`~passlib.ifc.PasswordHash.encrypt` and :meth:`~passlib.ifc.PasswordHash.genconfig` methods accept the following optional keyword:

    :type salt: bytes
    :param salt:
        Optional salt string.
        If not specified, one will be autogenerated (this is recommended).
        If specified, it may be any 4-16 byte string.

    :type salt_size: int
    :param salt_size:
        Optional number of bytes to use when autogenerating new salts.
        Defaults to 4 bytes for compatibility with the LDAP spec,
        but some systems use larger salts, and Passlib supports
        any value between 4-16.

    :type relaxed: bool
    :param relaxed:
        By default, providing an invalid value for one of the other
        keywords will result in a :exc:`ValueError`. If ``relaxed=True``,
        and the error can be corrected, a :exc:`~passlib.exc.PasslibHashWarning`
        will be issued instead. Correctable errors include
        ``salt`` strings that are too long.

        .. versionadded:: 1.6

    .. versionchanged:: 1.6
        This format now supports variable length salts, instead of a fix 4 bytes.
    """
    name = "ldap_salted_sha1"
    ident = u("{SSHA}")
    checksum_size = 20
    _hash_func = sha1
    _hash_regex = re.compile(u(r"^\{SSHA\}(?P<tmp>[+/a-zA-Z0-9]{32,}={0,2})$"))
    _stub_checksum = b('\x00') * 20

class ldap_plaintext(plaintext):
    """This class stores passwords in plaintext, and follows the :ref:`password-hash-api`.

    This class acts much like the generic :class:`!passlib.hash.plaintext` handler,
    except that it will identify a hash only if it does NOT begin with the ``{XXX}`` identifier prefix
    used by RFC2307 passwords.

    The :meth:`~passlib.ifc.PasswordHash.encrypt`, :meth:`~passlib.ifc.PasswordHash.genhash`, and :meth:`~passlib.ifc.PasswordHash.verify` methods all require the
    following additional contextual keyword:

    :type encoding: str
    :param encoding:
        This controls the character encoding to use (defaults to ``utf-8``).

        This encoding will be used to encode :class:`!unicode` passwords
        under Python 2, and decode :class:`!bytes` hashes under Python 3.

    .. versionchanged:: 1.6
        The ``encoding`` keyword was added.
    """
    # NOTE: this subclasses plaintext, since all it does differently
    # is override identify()

    name = "ldap_plaintext"
    _2307_pat = re.compile(u(r"^\{\w+\}.*$"))

    @classmethod
    def identify(cls, hash):
        # NOTE: identifies all strings EXCEPT those with {XXX} prefix
        hash = uh.to_unicode_for_identify(hash)
        return bool(hash) and cls._2307_pat.match(hash) is None

#=============================================================================
# {CRYPT} wrappers
# the following are wrappers around the base crypt algorithms,
# which add the ldap required {CRYPT} prefix
#=============================================================================
ldap_crypt_schemes = [ 'ldap_' + name for name in unix_crypt_schemes ]

def _init_ldap_crypt_handlers():
    # NOTE: I don't like to implicitly modify globals() like this,
    #       but don't want to write out all these handlers out either :)
    g = globals()
    for wname in unix_crypt_schemes:
        name = 'ldap_' + wname
        g[name] = uh.PrefixWrapper(name, wname, prefix=u("{CRYPT}"), lazy=True)
    del g
_init_ldap_crypt_handlers()

##_lcn_host = None
##def get_host_ldap_crypt_schemes():
##    global _lcn_host
##    if _lcn_host is None:
##        from passlib.hosts import host_context
##        schemes = host_context.schemes()
##        _lcn_host = [
##            "ldap_" + name
##            for name in unix_crypt_names
##            if name in schemes
##        ]
##    return _lcn_host

#=============================================================================
# eof
#=============================================================================
