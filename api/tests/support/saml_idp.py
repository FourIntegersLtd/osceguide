"""A SAML identity provider for tests: a real key, a real certificate, and a signed response.

Signed with `python3-saml`'s own signer, so the platform's verification is
exercised against the XML-DSig it will meet from Entra or Okta, not a stub.
"""

from __future__ import annotations

import base64
import uuid
from datetime import UTC, datetime, timedelta

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from onelogin.saml2.constants import OneLogin_Saml2_Constants
from onelogin.saml2.utils import OneLogin_Saml2_Utils

IDP_ENTITY_ID = "https://sts.windows.net/test-tenant/"
IDP_SSO_URL = "https://login.microsoftonline.com/test-tenant/saml2"
EMAIL_CLAIM = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress"
GIVEN_CLAIM = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname"
SURNAME_CLAIM = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname"


class TestIdentityProvider:
    """One IdP signing key and its self-signed certificate."""

    __test__ = False  # not a pytest test class

    def __init__(self) -> None:
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Test IdP")])
        now = datetime.now(UTC)
        certificate = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=1))
            .not_valid_after(now + timedelta(days=365))
            .sign(key, hashes.SHA256())
        )
        self.key_pem = key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
        ).decode()
        self.cert_pem = certificate.public_bytes(serialization.Encoding.PEM).decode()

    def response(
        self,
        *,
        acs_url: str,
        audience: str,
        in_response_to: str,
        email: str,
        subject: str = "entra-object-id-123",
        given_name: str = "Ana",
        surname: str = "Lee",
        issuer: str = IDP_ENTITY_ID,
    ) -> str:
        """A base64 SAMLResponse, signed by this IdP, as a browser would post it."""
        now = datetime.now(UTC)

        def stamp(moment: datetime) -> str:
            return moment.strftime("%Y-%m-%dT%H:%M:%SZ")

        response_id, assertion_id = f"_{uuid.uuid4().hex}", f"_{uuid.uuid4().hex}"
        xml = f"""<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
 xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion" ID="{response_id}" Version="2.0"
 IssueInstant="{stamp(now)}" Destination="{acs_url}" InResponseTo="{in_response_to}">
<saml:Issuer>{issuer}</saml:Issuer>
<samlp:Status><samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/></samlp:Status>
<saml:Assertion ID="{assertion_id}" Version="2.0" IssueInstant="{stamp(now)}">
<saml:Issuer>{issuer}</saml:Issuer>
<saml:Subject>
<saml:NameID Format="urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified">{subject}</saml:NameID>
<saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">
<saml:SubjectConfirmationData InResponseTo="{in_response_to}"
 NotOnOrAfter="{stamp(now + timedelta(minutes=5))}" Recipient="{acs_url}"/>
</saml:SubjectConfirmation>
</saml:Subject>
<saml:Conditions NotBefore="{stamp(now - timedelta(minutes=1))}"
 NotOnOrAfter="{stamp(now + timedelta(minutes=5))}">
<saml:AudienceRestriction><saml:Audience>{audience}</saml:Audience></saml:AudienceRestriction>
</saml:Conditions>
<saml:AuthnStatement AuthnInstant="{stamp(now)}" SessionIndex="{assertion_id}">
<saml:AuthnContext><saml:AuthnContextClassRef>urn:oasis:names:tc:SAML:2.0:ac:classes:Password</saml:AuthnContextClassRef></saml:AuthnContext>
</saml:AuthnStatement>
<saml:AttributeStatement>
<saml:Attribute Name="{EMAIL_CLAIM}"><saml:AttributeValue>{email}</saml:AttributeValue></saml:Attribute>
<saml:Attribute Name="{GIVEN_CLAIM}"><saml:AttributeValue>{given_name}</saml:AttributeValue></saml:Attribute>
<saml:Attribute Name="{SURNAME_CLAIM}"><saml:AttributeValue>{surname}</saml:AttributeValue></saml:Attribute>
</saml:AttributeStatement>
</saml:Assertion>
</samlp:Response>"""
        signed = OneLogin_Saml2_Utils.add_sign(
            xml,
            self.key_pem,
            self.cert_pem,
            sign_algorithm=OneLogin_Saml2_Constants.RSA_SHA256,
            digest_algorithm=OneLogin_Saml2_Constants.SHA256,
        )
        return base64.b64encode(signed if isinstance(signed, bytes) else signed.encode()).decode()
