import dataclasses


@dataclasses.dataclass
class Script:
    title: str
    description: str
    hero: bytes
    audio: str
    qr_code: str
    footer_1: str
    footer_2: str
