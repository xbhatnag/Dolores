'use client';
import React, { useState, useEffect } from 'react';

interface NewsStory {
  uuid: string,
  conclusion: string,
  summary: string,
  subjects: Array<string>,
  url: string,
  favicon: string,
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

const App = () => {
  // State to hold the news events, initially an empty array
  const [id, setId] = useState<string>("");
  const [criteria, setCriteria] = useState("");
  const [stories, setStories] = useState<Array<NewsStory>>([]);
  const [isRunning, setRunning] = useState(true);
  const [gotAllStories, setGotAllStories] = useState(false);

  const url = "http://localhost:8080";
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
    const stories: Array<NewsStory> = await get_json_retry(url + "/all");
    setStories(stories);
    setGotAllStories(true);
  }

  const get_next_story = async () => {
    console.log("Refreshing...");
    const next_story: NewsStory = await get_json_retry(url + "/next");
    console.log(next_story)
    setStories(current_stories => current_stories.concat([next_story]));
    get_next_story();
  }

  useEffect(() => {
    if (!isRunning) {
      return;
    }
    if (!gotAllStories) {
      get_all_stories();
    } else {
      get_next_story();
    }
  }, [isRunning, gotAllStories])

  useEffect(() => {
    if (isRunning) {
      get_all_stories();
    }
  }, [isRunning]);

  const getFavicon = (url: string, favicon: string) => {
    return
  }

  return (
    // Main container with Inter font and minimal background
    <div className="min-h-screen bg-gray-50 p-8">
      {/* Page Title */}
      <header className="bg-gray-70 flex gap-5 items-center mb-5">
        <h1 className="text-5xl text-gray-800 tracking-tight">
          Dolores
        </h1>
      </header>

      <table>
        {stories.toReversed().map((s) => (
          <tr>
            <td className="align-top h-5 w-5"><a href={s.url} target="_blank"><img src={s.favicon} className='mt-1' /></a></td>
            <td className="ml-1 mb-3 flex flex-col">
              <div className="flex text-gray-800 text-xl">{s.conclusion}</div>
              <div className="text-gray-600">{s.summary}</div>
              <div className='flex'>
                {s.subjects.slice(0, 3).map((subject) => (
                  <div className="text-gray-600 mr-2 bg-gray-100 rounded-full pl-2 pr-2">
                    {subject}
                  </div>
                ))}
              </div>
            </td>
          </tr>
        ))}
      </table>
    </div>
  );
};

export default App;
