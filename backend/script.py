import dataclasses


@dataclasses.dataclass
class Script:
    title: str
    description: str
    audio: bytes
    hero: bytes
    qr_code: bytes
    footer_1: str
    footer_2: str
    narrator: str
