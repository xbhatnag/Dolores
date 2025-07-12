import dataclasses


@dataclasses.dataclass
class Script:
    title: str
    audio_text: str
    audio_data: bytes
    image_data: bytes