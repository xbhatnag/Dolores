import dataclasses_json
import dataclasses
from datetime import datetime

@dataclasses_json.dataclass_json
@dataclasses.dataclass
class Article:
    source: str
    title: str
    author: str
    content: str
    url: str
    pub_date: datetime
    
@dataclasses_json.dataclass_json
@dataclasses.dataclass
class Script:
    article: Article
    voice: str
    script_text: str
    script_audio: str