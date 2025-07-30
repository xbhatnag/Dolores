'use client';
import React, { useState, useEffect } from 'react';

interface Article {
  _id: string,
  title: string,
  url: string,
  favicon_url: string,
  takeaways: Array<string>,
  search_terms: Array<string>,
  happy_scale: number,
  impact_scale: number,
  breaking_news: boolean,
  source: string,
  pub_date: string,
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

const App = () => {
  // State to hold the news events, initially an empty array
  const [stories, setStories] = useState<Array<Article>>([]);
  const [sources, setSources] = useState<Array<string>>([]);
  const [selectedArticle, setSelectedArticle] = useState<string | null>(null);
  const [selectedSource, setSelectedSource] = useState<string>("");
  const [input, setInput] = useState<Map<string, string>>(new Map());
  const [filter, setFilter] = useState<string>("");
  const [currentTime, setCurrentTime] = useState(new Date());
  const [happiness, setHappiness] = useState<number>(1);
  const [impact, setImpact] = useState<number>(1);
  const [breakingNews, setBreakingNews] = useState<boolean>(true);

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

  const get_all_stories = async () => {
    console.log("Getting all stories...");
    const stories: Array<Article> = await get_json_retry(url + "/all");

    stories.sort((a, b) => {
      const dateA = new Date(a.pub_date);
      const dateB = new Date(b.pub_date);
      return dateA.getTime() - dateB.getTime(); // Sort in descending order
    });

    var new_sources = new Set<string>();
    for (const story of stories) {
      new_sources.add(story.source)
    }

    setSources([...new_sources]);
    setStories(stories);
    setTimeout(get_all_stories, 10000);
  }

  useEffect(() => {
    get_all_stories();
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

  const visibleIfSelected = (article: Article) => {
    if (selectedArticle == article._id) {
      return "";
    } else {
      return "hidden"
    }
  }

  const ask = async () => {
    if (selectedArticle == null) {
      return;
    }
    const query = input.get(selectedArticle)
    if (query == null) {
      return;
    }
    console.log("Asking \"" + query + "\"")
    const ask_url = url + "/ask?id=" + selectedArticle + "&q=" + query
    const response = await fetch(ask_url, {
      headers: {
        'Accept': 'application/json'
      }
    });
    console.log(await response.text())
  }

  const onEnterPressed = (e: any) => {
    if (e.key == "Enter") {
      ask();
    }
  }

  const onInputChange = (e: any) => {
    if (selectedArticle == null) {
      return;
    }
    var new_input = input.set(selectedArticle, e.target.value);
    setInput(new_input);
  }

  const shouldIncludeArticle = (article: Article) => {
    if (article.breaking_news != breakingNews) {
      return false;
    }

    if (article.happy_scale < happiness) {
      return false;
    }

    if (article.impact_scale < impact) {
      return false;
    }

    if (filter && (!article.source.toLowerCase().includes(filter.toLowerCase()) && !article.search_terms.some((t) => t.toLowerCase().includes(filter.toLowerCase())))) {
      return false;
    }

    if (selectedSource && article.source != selectedSource) {
      return false;
    }

    return true;
  }

  return (
    // Main container with Inter font and minimal background
    <div className="min-h-screen bg-gray-50 p-8">
      {/* Page Title */}
      <header className="bg-gray-70 flex flex-col gap-5 mb-5">
        <h1 className="text-5xl text-gray-800 tracking-tight">
          Dolores
        </h1>
        <div>Breaking News?&nbsp;<input type="checkbox" checked={breakingNews} onChange={(e) => { setBreakingNews(e.target.checked) }}></input></div>
        <div>Happiness: <input type="range" min="1" max="5" value={happiness} onChange={(e) => { setHappiness(parseInt(e.target.value)) }}></input></div>
        <div>Impact: <input type="range" min="1" max="5" value={impact} onChange={(e) => { setImpact(parseInt(e.target.value)) }}></input></div>
        <input type="text" className="bg-white rounded-2xl shadow grow p-2 text-black text-xl" placeholder="Filter" value={filter} onChange={(e) => setFilter(e.target.value)} />
        <select value={selectedSource} onChange={(e) => { setSelectedSource(e.target.value) }}>
          {sources.map((source) => (
            <option>{source}</option>
          ))}
        </select>
      </header>

      {
        selectedArticle && (
          <div className="blur" onClick={() => { setSelectedArticle(null) }}></div>
        )
      }

      <div>
        {stories.toReversed().filter(s => shouldIncludeArticle(s)).map((s) => (
          <div key={s._id} className={`mb-3 p-3 article ${maybeShadow(s)}`}>
            <div onClick={() => { selectArticle(s) }}>
              <div className="flex text-gray-800 text-xl items-center gap-2">
                {breakingNews && (<div className="text-sm w-12 shrink-0">{relativeTime(s.pub_date)}</div>)}
                <a href={s.url} target="_blank" className="shrink-0 mr-3">
                  <img src={s.favicon_url} className="h-5 w-5" />
                </a>
                <div>{s.title} ({s.happy_scale}) ({s.impact_scale})</div>
              </div>
            </div>

            <div className={`flex flex-col mt-2 text-lg ${visibleIfSelected(s)}`}>
              <ul>
                {s.takeaways.map((t) => (
                  <li className="text-gray-600">➤ {t}</li>
                ))}
              </ul>
              <div className='flex gap-2 mt-2 mb-2 overflow-scroll'>
                {s.search_terms.map((tag) => (
                  <a href={`https://google.com/search?q=${tag}`} target='_blank'>
                    <div className="text-gray-600 mr-2 bg-gray-100 rounded-full pl-2 pr-2 whitespace-nowrap">
                      {tag}
                    </div>
                  </a>
                ))}
              </div>
              <input className="outline-1 p-2 rounded-full text-black bg-gray-100 mt-2" placeholder="Ask a question..." onKeyDown={onEnterPressed} onChange={onInputChange}></input>
            </div>
          </div>
        ))}
      </div>
    </div >
  );
};

export default App;
