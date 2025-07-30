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

# Create search terms for the article

What are the words that can be put into a Google Search to find this article again?

Rules:
* Balance precision with conciseness. You want to be as descriptive as possible in as few words as possible.
* Prefer acronyms.
* Do not repeat yourself.

Here are some example search terms:
* an article about how AI deepfakes of Taylor Swift created with Midjourney are spreading on Twitter should return the search terms ["Taylor Swift", "Twitter", "Midjourney", "AI deepfakes"].
* an article about a new cast member Jack Black on the show "Ted Lasso" should return ["Ted Lasso", "Jack Black"]

# Is this a article that would make the reader unhappy?

On a scale of 1 (most unhappy) to 5 (most happy), rate the article based on how likely it is to make the reader happy or unhappy.

The following subjects are rated 1 by the reader:
* Physical harm: famine, illness, death, murder, war, homelessness, drug abuse.
* Mental health issues: depression, anxiety.
* The current US government under Donald Trump
* AI having negative effects on humanity (stealing jobs, energy crisis)
* Elon Musk and his companies (X, SpaceX, Tesla, Neuralink)
* Environmental degradation (especially point-of-no-return)
* AI hype/fear-mongering, usually done by CEOs (e.g - Sam Altman) or people who don't code

The following subjects are rated 5 by the reader:
* Announcements of new TV shows, movies, consumer products, games or features
* Computer projects, prototypes and hacks
* Consumer product reviews or comparisons

# Would the article impact the reader?

On a scale of 1 (least) to 5 (most), rate how likely it is to directly impact the reader.

The reader is:
* living in San Francisco, California
* of Indian descent
* a Canadian citizen
* working for Google
* an LGBTQ individual
* left-leaning when it comes to political viewpoints

# Is this breaking news?

Return `true` if the article is breaking news, `false` otherwise.

Breaking news is an important real-world event that has occurred or will occur in the future.

Here are some examples that are breaking news (notice the emphasis on dates):
* an article that talks about the Presidential Inauguration that occurred on _January 5, 2024_.
* an article that discusses a new partnership between the US and Canada starting _April 2026_.
* an article that reports on a Tsunami that affected the Himalayas _last week_.
* an article that talks about new features announced _today_ for Adobe Photoshop.
* an article that talks about discount deals that will be available on _Memorial Day_.
* an article that talks about the new iPhone 16, which will be launched _1 year from now_.

Here are some examples that are not breaking news:
* an article that guides users on how to self-host their personal website
* an article that talks about how an engineer built a rocket out of spare parts in their garage
* an article that reviews a consumer tech device like the Samsung Galaxy S16
* an article that shares opinions on cloud based storage
* an article that gives reasons for upgrading your GPU
* an article that compares Intel Macbook Pro to the M1 Macbook Pro
* an article that reviews season 2 of the TV show "Severance" 