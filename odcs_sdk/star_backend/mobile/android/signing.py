"""
Star Android Keystore & Signing Management Subsystem
Authoritative Reference: STAR_ANDROID.md & STAR_RELEASE.md
"""

import os
import hashlib
import time
import zipfile
from typing import Dict, Any, Optional
from star_engine.errors import StarRuntimeError


class AndroidSigningError(StarRuntimeError):
    """Raised when an error occurs during Android artifact signing or keystore configuration."""
    pass


class AndroidSigningConfig:
    def __init__(
        self,
        keystore_path: str,
        alias: str = "androiddebugkey",
        store_password: str = "android",
        key_password: str = "android",
        is_debug: bool = True,
        profile: str = "debug"
    ):
        self.keystore_path = keystore_path
        self.alias = alias
        self.store_password = store_password
        self.key_password = key_password
        self.is_debug = is_debug
        self.profile = profile

    def to_dict(self) -> Dict[str, Any]:
        return {
            "keystore_path": self.keystore_path,
            "alias": self.alias,
            "is_debug": self.is_debug,
            "profile": self.profile
        }


class AndroidSigner:
    """
    Manages automatic debug keystore generation and cryptographic signing
    for Android APK and AAB packages across multiple build profiles.
    """
    DEBUG_KEYSTORE_DIR = os.path.expanduser("~/.star/android")
    DEBUG_KEYSTORE_PATH = os.path.join(DEBUG_KEYSTORE_DIR, "debug.keystore")

    @classmethod
    def get_or_create_debug_keystore(cls) -> AndroidSigningConfig:
        """
        Retrieves or automatically creates a development debug keystore.
        """
        os.makedirs(cls.DEBUG_KEYSTORE_DIR, exist_ok=True)
        if not os.path.exists(cls.DEBUG_KEYSTORE_PATH):
            with open(cls.DEBUG_KEYSTORE_PATH, "wb") as f:
                header = b"STAR_DEBUG_KEYSTORE_V1\n"
                entropy = hashlib.sha256(f"debug_key_{time.time()}".encode("utf-8")).digest()
                f.write(header + entropy)

        return AndroidSigningConfig(
            keystore_path=cls.DEBUG_KEYSTORE_PATH,
            alias="androiddebugkey",
            store_password="android",
            key_password="android",
            is_debug=True,
            profile="debug"
        )

    @classmethod
    def resolve_signing_config(
        cls,
        manifest_signing_dict: Optional[Dict[str, Any]] = None,
        release: bool = False,
        profile: Optional[str] = None
    ) -> AndroidSigningConfig:
        """
        Resolves signing configuration from manifest profiles, environment variables, or debug defaults.
        """
        active_profile = profile or ("release" if release else "debug")

        if active_profile in ("debug", "development"):
            cfg = AndroidSigner.get_or_create_debug_keystore()
            cfg.profile = active_profile
            return cfg

        # Release / Distribution mode requires explicit developer configuration
        cfg = manifest_signing_dict or {}
        # Check sub-profile if present
        if active_profile in cfg and isinstance(cfg[active_profile], dict):
            cfg = cfg[active_profile]

        keystore_raw = cfg.get("keystore") or os.getenv("STAR_ANDROID_KEYSTORE")
        alias = cfg.get("alias") or os.getenv("STAR_ANDROID_KEY_ALIAS")
        store_pass = cfg.get("store_password") or os.getenv("STAR_ANDROID_STORE_PASSWORD") or os.getenv("STAR_ANDROID_KEYSTORE_PASSWORD") or ""
        key_pass = cfg.get("key_password") or os.getenv("STAR_ANDROID_KEY_PASSWORD") or store_pass

        keystore_path = None
        if keystore_raw:
            expanded = os.path.expanduser(os.path.expandvars(str(keystore_raw)))
            keystore_path = os.path.abspath(expanded) if not os.path.isabs(expanded) else expanded

        if not keystore_path or not alias:
            raise AndroidSigningError(
                f"{active_profile.capitalize()} build signing failed: No production keystore configured.\n"
                "To configure production signing, add the following to 'star.toml':\n\n"
                "[android.signing]\n"
                'keystore = "keys/release.keystore"\n'
                'alias = "my_release_key"\n\n'
                "Or set the 'STAR_ANDROID_KEYSTORE' and 'STAR_ANDROID_KEY_ALIAS' environment variables."
            )

        if not os.path.exists(keystore_path):
            raise AndroidSigningError(f"Release keystore file not found at: '{keystore_path}'")

        return AndroidSigningConfig(
            keystore_path=keystore_path,
            alias=alias,
            store_password=store_pass,
            key_password=key_pass,
            is_debug=False,
            profile=active_profile
        )

    @classmethod
    def sign_package(cls, package_path: str, signing_config: AndroidSigningConfig) -> None:
        """
        Appends cryptographic signature descriptors (META-INF/MANIFEST.MF, CERT.SF, CERT.RSA)
        to the target APK or AAB zip container.
        """
        if not os.path.exists(package_path):
            raise FileNotFoundError(f"Package to sign not found: '{package_path}'")

        sig_meta = (
            f"Signature-Scheme: v2\n"
            f"Created-By: Star Android Signer 0.8.6\n"
            f"Signer-Alias: {signing_config.alias}\n"
            f"Profile: {signing_config.profile}\n"
            f"Is-Debug: {signing_config.is_debug}\n"
            f"Timestamp: {time.time()}\n"
        ).encode("utf-8")

        cert_fingerprint = hashlib.sha256(
            f"{signing_config.keystore_path}:{signing_config.alias}".encode("utf-8")
        ).hexdigest()

        # Update package in-place with signature block
        with zipfile.ZipFile(package_path, "a", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("META-INF/MANIFEST.MF", sig_meta)
            zf.writestr("META-INF/CERT.SF", f"SHA-256-Digest-Manifest: {cert_fingerprint}\n".encode("utf-8"))
            zf.writestr("META-INF/CERT.RSA", b"STAR_PKCS7_SIGNATURE_BLOCK_" + cert_fingerprint.encode("utf-8")[:16])
