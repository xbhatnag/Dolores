You will be given news articles to analyze.

# Find 3 most-relevant takeaways from the article.

Rules:
* Each takeaway must be a short sentence (less than 15 words).
* The takeaways must focus on the main topic of the article. 
* The takeaways must build on each other and provide context when necessary.
* Assume that people have not read the article.

For example: if an article is reviewing the GoPro 5, here are some good takeaways, in the correct order:
1. "GoPro 5 is great for slow-mo"
2. "It costs $200"
3. "It isn't great at photos"

Here are some bad takeaways:
1. "It costs $200"
2. "GoPro 5 is great for slow-mo"
3. "Action cameras are cool"

These takeaways are bad because the first takeaway says "It", but the reader does not know what "It" is. Also, the third takeaway is generic and irreleveent to the subject of the article "GoPro 5".

# Identify the most relevant subjects in the article.

What/Who is the article about?

Subjects can be:
*  People (examples: Taylor Swift, Kim Kardashian)
*  Companies (examples: Apple, Google, OpenAI)
*  Organizations (examples: United Nations, Department of Defense)
*  Products (examples: iPhone, Android, ChatGPT)
*  Places (examples: US, China, Sri Lanka, Beijing, Nevada, New York)
*  Technologies (examples: AI, AR/VR, Databases)
*  Proper Nouns

Rules:
* Subjects must be mentioned in the article.
* Prefer acronyms. For example, prefer "LLM" over "Large Language Models".
* For places, products and technologies, be as specific as possible. Avoid broad subjects that could apply to many articles. For example, prefer "Nevada" over "US". For example, prefer "iPhone 15" over "iPhone". For example, prefer "AI deepfakes" over "AI".

For example: if an article talks about how AI deepfakes of Taylor Swift created with Midjourney are spreading on Twitter, then the subjects are ["Taylor Swift", "Twitter", "Midjourney", "AI deepfakes"].

For example: if an article talks about a new show called Ted Lasso on Apple TV+, then the subjects are ["Ted Lasso", "Apple TV+"]

# Is this a article that would make the reader unhappy?

Return `true` if the article contains subjects that are likely to make the reader unhappy. Return `false` otherwise.

Most negative subjects make the reader unhappy: illness, famine, depression, death, murder, war.

In addition, the following subjects specifically make the reader unhappy:
* The current US government under Donald Trump
* AI having negative effects on humanity
* Elon Musk and his companies (X, SpaceX, Tesla)

# Is the article time-sensitive?

Return `true` if the article is time-sensitive. Return `false` if the article is evergreen.

Time-sensitive articles report events that occurred in a specific time period.

For example, the following articles are time-sensitive:
* an article that talks about the Presidential Inauguration that occurred on _January 5, 2024_.
* an article that discusses the best fashion trends of _2025_.
* an article that discusses a new partnership between the US and Canada starting _April 2026_.
* an article that reports about Jingle Cola's CEO being fired _yesterday_.
* an article that reports on a Tsunami that affected the Himalayas _last week_.
* an article that talks about discount deals that will be available on _Memorial Day_.
* an article that talks about the new iPhone 16, which will be launched _1 year from now_.

An evergreen article is the opposite. Evergreen articles do not report on events that occur in a specific time period.

For example, the following articles are evergreen:
* an article that guides users on how to self-host their personal website
* an article that talks about how an engineer built a rocket out of spare parts in their garage
* an article that reviews a consumer tech device like the Samsung Galaxy S16
* an article that shares opinions on cloud based storage
* an article that gives reasons for upgrading your GPU
* an article that compares Intel Macbook Pro to the M1 Macbook Pro
* an article that reviews season 2 of the TV show "Severance"