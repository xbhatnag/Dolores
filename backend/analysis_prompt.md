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

# Is this a article that makes the reader unhappy?

In addition to subjects that would make most people unhappy, the following subjects specifically make the reader unhappy:
* The current US government under Donald Trump
* AI causing harm and replacing humans
* Elon Musk and his companies

Return `true` if the article is likely to make the reader unhappy. Return `false` otherwise.


# Is this  
* Relations between countries (partnerships, war)
* Company/organization updates (product announcements, mergers, acquisitions, personnel changes)
* Government updates (new departments, new projects)
* Deals on products
* Weekly/Monthly newsletters

Example article titles:
* "US and China announce partnership to combat climate change"
* "Apple announces iPhone 25"
* "US Government creates Department of Household Pets"
* "HP Elite PC is $200 off until Memorial Day!"

An article is evergreen if it remains relevant and useful long after its publication date. The information is not tied to a specific event or breaking news, and people can find value in it for months or even years.

Here are the kinds of articles that are evergreen:
* Guides
* Hacks and Projects
* Reviews of products
* Advice

Example article titles:
* "Always wanted to self-serve your website? Here's how!"
* "Building a tennis ball launcher from spare machine parts"
* "Samsung S24 Review: the camera is the best part!"
* "5 ways I use a self-hosted LLM to help me be more organized and more productive"
* "6 ways my NAS can survive anything short of a data apocalypse"
* "I "debloated" Windows 11 through official means, and here's how you can too"
* "5 reasons your next gaming rig should have an NPU"