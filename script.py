import dataclasses


@dataclasses.dataclass
class Script:
    display_text: str
    audio_file: str
    image_file: str