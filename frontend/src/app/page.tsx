'use client';
import React, { useState, useEffect } from 'react';

interface Analysis {
  _id: string,
  title: string,
  url: string,
  favicon_url: string,
  takeaways: Array<string>,
  tags: Array<string>,
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

const App = () => {
  // State to hold the news events, initially an empty array
  const [stories, setStories] = useState<Array<Analysis>>([]);
  const [selectedStory, setSelectedStory] = useState<string | null>(null);
  const [input, setInput] = useState<Map<string, string>>(new Map());
  const [filter, setFilter] = useState<string>("");

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
    const stories: Array<Analysis> = await get_json_retry(url + "/all");
    setStories(stories);
    setTimeout(get_all_stories, 10000);
  }

  useEffect(() => {
    get_all_stories();
  }, []);

  const selectStory = (story: Analysis) => {
    setSelectedStory(story._id);
  }

  const maybeShadow = (story: Analysis) => {
    if (selectedStory == story._id) {
      return "selected-story shadow-lg";
    } else {
      return "";
    }
  }

  const visibleIfSelected = (story: Analysis) => {
    if (selectedStory == story._id) {
      return "";
    } else {
      return "hidden"
    }
  }

  const ask = async () => {
    if (selectedStory == null) {
      return;
    }
    const query = input.get(selectedStory)
    if (query == null) {
      return;
    }
    console.log("Asking \"" + query + "\"")
    const ask_url = url + "/ask?id=" + selectedStory + "&q=" + query
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
    if (selectedStory == null) {
      return;
    }
    var new_input = input.set(selectedStory, e.target.value);
    setInput(new_input);
  }

  return (
    // Main container with Inter font and minimal background
    <div className="min-h-screen bg-gray-50 p-8">
      {/* Page Title */}
      <header className="bg-gray-70 flex gap-5 items-center mb-5">
        <h1 className="text-5xl text-gray-800 tracking-tight">
          Dolores
        </h1>
        <input type="text" placeholder="Filter by tag..." value={filter} onChange={(e) => setFilter(e.target.value)} />
      </header>

      {selectedStory && (
        <div className="blur" onClick={() => { setSelectedStory(null) }}></div>
      )}

      <div>
        {stories.toReversed().filter(s => s.tags.some(tag => tag.includes(filter))).map((s) => (
          <div key={s._id} className={`mb-5 p-3 story bg-white ${maybeShadow(s)} rounded-b-4xl`}>
            <div onClick={() => { selectStory(s) }}>
              <div className="flex text-gray-800 text-xl items-center gap-2">
                <a href={s.url} target="_blank" className="flex-shrink-0">
                  <img src={s.favicon_url} className="h-5 w-5" />
                </a>
                <div>{s.title}</div>
              </div>
              <ul>
                {s.takeaways.map((t) => (
                  <li className="text-gray-600">➤ {t}</li>
                ))}
              </ul>
            </div>

            <div className={`flex flex-col ${visibleIfSelected(s)}`}>
              <div className='flex gap-2 mt-2 mb-2 overflow-scroll'>
                {s.tags.map((tag) => (
                  <a href={`https://google.com/search?q=${tag}`} target='_blank'>
                    <div className="text-gray-600 mr-2 bg-gray-100 rounded-full pl-2 pr-2 whitespace-nowrap">
                      {tag}
                    </div>
                  </a>
                ))}
              </div>
              <div className="mt-2">
                {/* {s.articles.map((a) => selectedStory == s._id && (
                  <a key={a.url} href={a.url} target="_blank" className='text-gray-600 flex items-center gap-2'>
                    <img src={a.favicon} className="h-4 w-4" />
                    <div>{a.title}</div>
                  </a>
                ))} */}
              </div>
              <input className="outline-1 p-2 rounded-full text-black mt-4" placeholder="Ask a question..." onKeyDown={onEnterPressed} onChange={onInputChange}></input>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default App;
