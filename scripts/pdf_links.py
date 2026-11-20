"""Portable PDF destinations; local source locators remain visible text."""
import ipaddress
from urllib.parse import urlsplit


def portable_target(target):
    if target.startswith("#"):
        return True
    parsed = urlsplit(target)
    if parsed.scheme.lower() == "mailto":
        return True
    if parsed.scheme.lower() not in ("https", "http") or not parsed.hostname:
        return False
    host = parsed.hostname.lower().rstrip(".")
    if host == "localhost" or host.endswith(".localhost"):
        return False
    try:
        return ipaddress.ip_address(host).is_global
    except ValueError:
        return True


def inspect_pdf(path):
    from pypdf import PdfReader
    from common import sha
    errors, external = [], []
    internal = 0
    for number, page in enumerate(PdfReader(path).pages, 1):
        for reference in page.get("/Annots", []):
            annotation = reference.get_object()
            if annotation.get("/Dest") is not None:
                internal += 1
            action = annotation.get("/A")
            if not action:
                continue
            action = action.get_object()
            kind = action.get("/S")
            if kind == "/GoTo":
                internal += 1
            elif kind == "/URI":
                target = str(action.get("/URI", ""))
                if portable_target(target):
                    external.append({"page": number, "target": target})
                else:
                    errors.append({"page": number, "action": kind, "target": target})
            else:
                # Includes remote-document navigation and launching a local file.
                errors.append({"page": number, "action": str(kind)})
    return {"passed": not errors, "sha256": sha(path), "internal_links": internal,
            "external_links": external, "errors": errors}
