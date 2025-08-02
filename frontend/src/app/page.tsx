'use client';
import React, { useState, useEffect } from 'react';

interface Article {
  _id: string,
  title: string,
  url: string,
  favicon_url: string,
  takeaways: Array<string>,
  search_terms: Array<string>,
  source: string,
  date: string,
  text: string,
  discussion_url: string
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

const App = () => {
  // State to hold the news events, initially an empty array
  const [articles, setArticles] = useState<Array<Article>>([]);
  const [selectedArticle, setSelectedArticle] = useState<string | null>(null);
  const [readArticles, setReadArticles] = useState<Array<string>>([])
  const [filter, setFilter] = useState<string>("");
  const [currentTime, setCurrentTime] = useState(new Date());
  const [onlyRead, setOnlyRead] = useState(false);

  useEffect(() => {
    // Set up an interval to update the currentTime state every second
    const intervalId = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000); // 1000 milliseconds = 1 second

    // Clean up the interval when the component unmounts
    return () => {
      clearInterval(intervalId);
    };
  }, []);

  const relativeTime = (date: string) => {
    const now = currentTime;
    const then = new Date(date);
    const diff = now.getTime() - then.getTime();
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    // "X days ago", "X hours ago", "X minutes ago", "X seconds ago" or "a really long time ago"
    if (hours > 0) {
      return `${hours} hr${hours > 1 ? 's' : ''}`;
    } else if (minutes > 0) {
      return `${minutes} min${minutes > 1 ? 's' : ''}`;
    } else {
      return `${seconds} sec${seconds > 1 ? 's' : ''}`;
    }
  }

  const url = "http://localhost:3000";
  const get_json_retry = async (url: string) => {
    while (true) {
      try {
        const response = await fetch(url, {
          headers: {
            'Accept': 'application/json'
          }
        });
        if (response.status != 200) {
          console.error("Error from API", response);
          continue;
        }
        return await response.json();
      } catch (e) {
        console.error("Error from API", e);
        await sleep(10000);
      }
    }
  }

  const get_all_articles = async () => {
    console.log("Getting all articles...");
    const articles: Array<Article> = await get_json_retry(url + "/all");

    articles.sort((a, b) => {
      const dateA = new Date(a.date);
      const dateB = new Date(b.date);
      return dateA.getTime() - dateB.getTime(); // Sort in descending order
    });

    var new_sources = new Set<string>();
    for (const story of articles) {
      new_sources.add(story.source)
    }

    setArticles(articles);
    setTimeout(get_all_articles, 10000);
  }

  useEffect(() => {
    get_all_articles();
  }, []);

  const selectArticle = (article: Article) => {
    setSelectedArticle(article._id);
  }

  const maybeShadow = (article: Article) => {
    if (selectedArticle == article._id) {
      return "selected-article shadow-2xl rounded-b-4xl bg-white";
    } else {
      return "w-fit";
    }
  }

  const clear = async () => {
    const clear_url = url + "/clear"
    await fetch(clear_url, {
      method: 'POST',
      headers: {
        'Accept': 'application/json'
      }
    });
    setArticles([]);
    setReadArticles([]);
    setSelectedArticle(null);
  }

  const shouldIncludeArticle = (article: Article) => {
    if (filter && (!article.source.toLowerCase().includes(filter.toLowerCase()) && !article.search_terms.some((t) => t.toLowerCase().includes(filter.toLowerCase())) && !article.url.includes(filter.toLowerCase()) && !article.title.includes(filter.toLowerCase()))) {
      return false;
    }

    if (onlyRead) {
      return readArticles.includes(article._id);
    }

    return !readArticles.includes(article._id);
  }

  const findSentenceWithPhrase = (text: string, searchPhrase: string): string | null => {
    // Check for invalid input to avoid unnecessary processing
    if (!text || !searchPhrase) {
      return null;
    }

    // Split the text into an array of sentences.
    // The regular expression `/[.?!]|\n|\r/` now splits the string by a period, question mark,
    // exclamation point, or a newline/carriage return character.
    const sentences = text.split(/[.?!]|\n|\r/);

    // Iterate over each sentence to find the one that includes the search phrase.
    for (const sentence of sentences) {
      // Check if the current sentence contains the search phrase, ignoring case differences.
      // We convert both the sentence and the search phrase to lowercase for a case-insensitive match.
      if (sentence.toLowerCase().includes(searchPhrase.toLowerCase())) {
        // If a match is found, return the sentence after trimming any leading/trailing whitespace.
        return sentence.trim();
      }
    }

    // If no sentence contains the search phrase after checking all of them, return null.
    return null;
  };

  const deselectArticle = () => {
    if (!selectedArticle) {
      return;
    }
    setReadArticles(prevReadArticles => [selectedArticle, ...prevReadArticles])
    setSelectedArticle(null)
  }

  const markAllRead = () => {
    const readArticles = articles.map((a) => a._id)
    setReadArticles(readArticles)
  }

  const unreadArticles = () => {
    return articles.toReversed().filter(s => shouldIncludeArticle(s));
  }

  const storyList = () => (
    <div className='w-[100%] 2xl:w-[60%] flex flex-col align-middle'>
      <center className='mb-10'>
        Have you ever seen anything so full of splendor?
      </center>
      {unreadArticles().map((s) => (
        <div key={s._id} className={`mb-3 p-3 article ${maybeShadow(s)}`}>
          <div onClick={() => { selectArticle(s) }}>
            <div className="flex text-gray-800 text-xl items-center gap-2">
              <div className="text-sm w-12 shrink-0">{relativeTime(s.date)}</div>
              <a href={s.url} target="_blank" className="shrink-0 mr-3">
                <img src={s.favicon_url} className="h-5 w-5" />
              </a>
              <a href={s.discussion_url} target="_blank" className="shrink-0 mr-3 text-xs">
                💬
              </a>
              <div>{s.title}</div>
            </div>
          </div>

          {selectedArticle == s._id && (<div className={`flex flex-col mt-2 text-lg`}>
            <ul>
              {s.takeaways.map((t) => (
                <li className="text-gray-600">➤ {t}</li>
              ))}
            </ul>
            <div className='flex gap-2 mt-2 mb-2 overflow-scroll'>
              {s.search_terms.map((tag) => (
                <a key={`${tag}`} href={`https://google.com/search?q=${tag}`} target='_blank'>
                  <div className="text-gray-600 mr-2 bg-gray-100 rounded-full pl-2 pr-2 whitespace-nowrap" title={findSentenceWithPhrase(s.text, tag)}>
                    {tag}
                  </div>
                </a>
              ))}
            </div>
          </div>)}
        </div>
      ))}
    </div>
  )

  return (
    <div className="min-h-screen bg-gray-50 p-8 flex flex-col items-center text-black">
      <header className="bg-gray-70 flex gap-5 mb-5 w-[100%] 2xl:w-[60%]">
        <h1 className="text-5xl tracking-tight">
          Dolores
        </h1>
        <input type="text" className="bg-white rounded-2xl shadow grow p-2 text-xl" placeholder="Search" value={filter} onChange={(e) => setFilter(e.target.value)} />
        <input
          type="checkbox"
          checked={onlyRead}
          onChange={(e) => setOnlyRead(!onlyRead)}
        />
        <button className='border border-gray-400 rounded-xl p-2' onClick={(e) => clear()}>Clear All</button>
        <button className='border border-gray-400 rounded-xl p-2' onClick={(e) => markAllRead()}>Mark All Read</button>
      </header>

      {
        selectedArticle && (
          <div className="blur" onClick={() => { deselectArticle() }}></div>
        )
      }

      {storyList()}
    </div>
  );
};

export default App;
